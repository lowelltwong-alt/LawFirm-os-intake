from copy import deepcopy

import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import run_preflight


def test_preflight_fixture_gold_report_passes_and_is_ledgermarked(tmp_path, repo_root):
    gold_path = repo_root / "examples/synthetic/gold/north-star-messy-intake.fixture-gold.json"
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/north-star-messy-intake.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
        fixture_gold=gold_path,
    )

    report = load_json(run_dir / "fixture_gold_report.json")
    ledger = load_jsonl(run_dir / "run_ledger.jsonl")

    assert packet.fixture_gold_report_ref == str(run_dir / "fixture_gold_report.json")
    assert report["status"] == "passed"
    assert report["stage"] == "preflight"
    assert report["reviewed_gold"] is True
    assert report["non_authoritative"] is True
    assert {check["status"] for check in report["checks"]} == {"passed"}
    assert any(
        event["step_name"] == "fixture_gold_evaluated"
        and event["status"] == "completed"
        and str(run_dir / "fixture_gold_report.json") in event["output_refs"]
        for event in ledger
    )


def test_demo_fixture_gold_report_covers_terminal_boundaries(tmp_path, repo_root):
    code = main(
        [
            "demo",
            "--input",
            str(repo_root / "examples/synthetic/inbound/north-star-messy-intake.json"),
            "--practice-profile",
            str(repo_root / "context/synthetic-profiles/insurance-defense.yaml"),
            "--confirmation-template",
            str(
                repo_root
                / "examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json"
            ),
            "--fixture-gold",
            str(repo_root / "examples/synthetic/gold/north-star-messy-intake.fixture-gold.json"),
            "--out-dir",
            str(tmp_path / "demo"),
        ]
    )

    assert code == 0
    budget_dir = tmp_path / "demo/budget"
    report = load_json(budget_dir / "fixture_gold_report.json")
    manifest = load_json(budget_dir / "review_package_manifest.json")
    review_text = (budget_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")

    assert report["status"] == "passed"
    assert report["stage"] == "demo"
    assert report["evaluated_artifact_refs"]["fixture_gold_report"].endswith(
        "fixture_gold_report.json"
    )
    assert {check["status"] for check in report["checks"]} == {"passed"}
    assert "fixture_gold_report" in manifest["artifact_refs"]
    assert "fixture_gold_report.json" in review_text


def test_fixture_gold_fails_closed_after_writing_report(tmp_path, repo_root):
    gold = load_json(
        repo_root / "examples/synthetic/gold/north-star-messy-intake.fixture-gold.json"
    )
    impossible = deepcopy(gold)
    impossible["expected_top_inbound_event"] = "impossible_synthetic_event"
    gold_path = tmp_path / "impossible.fixture-gold.json"
    write_json(gold_path, impossible)

    with pytest.raises(ValueError, match="fixture gold evaluation failed"):
        run_preflight(
            repo_root / "examples/synthetic/inbound/north-star-messy-intake.json",
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            tmp_path / "run",
            fixture_gold=gold_path,
        )

    run_dir = next((tmp_path / "run").iterdir())
    report = load_json(run_dir / "fixture_gold_report.json")
    assert report["status"] == "failed"
    assert any(
        check["check_id"] == "top_inbound_event" and check["status"] == "failed"
        for check in report["checks"]
    )


def test_build_budget_fixture_gold_covers_hours_only_mode(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
        fixture_gold=(
            repo_root
            / "examples/synthetic/gold/carrier-assignment-medmal-hours-only.fixture-gold.json"
        ),
    )
    confirmation_data = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    confirmation_data["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(confirmation_data)
    )
    confirmation_path = tmp_path / "human_confirmation.json"
    write_json(confirmation_path, confirmation.model_dump(mode="json"))

    code = main(
        [
            "build-budget",
            "--preflight-packet",
            str(run_dir / "intake_preflight_packet.json"),
            "--confirmation",
            str(confirmation_path),
            "--practice-profile",
            str(repo_root / "context/synthetic-profiles/insurance-defense-hours-only.yaml"),
            "--fixture-gold",
            str(
                repo_root
                / "examples/synthetic/gold/carrier-assignment-medmal-hours-only.fixture-gold.json"
            ),
            "--out-dir",
            str(tmp_path / "budget"),
        ]
    )

    assert code == 0
    budget = load_json(tmp_path / "budget/legal_budget_proposal.json")
    report = load_json(tmp_path / "budget/fixture_gold_report.json")
    exception_labels = {
        item["local_event_label"]
        for item in load_jsonl(tmp_path / "budget/exception_lake_candidates.jsonl")
    }
    assert budget["pricing_status"] == "hours_only"
    assert budget["total_proposed_budget"] is None
    assert report["status"] == "passed"
    assert any(
        check["check_id"] == "budget_pricing_status"
        and check["actual"] == "hours_only"
        and check["status"] == "passed"
        for check in report["checks"]
    )
    assert "budget_hours_only_missing_rates" in exception_labels
