from copy import deepcopy

import pytest

from lawfirm_os_intake.cli import main
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
