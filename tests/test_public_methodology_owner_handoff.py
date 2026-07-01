import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import PublicMethodologyOwnerHandoffReport
from lawfirm_os_intake.public_methodology_owner_handoff import (
    run_public_methodology_owner_handoff,
)
from lawfirm_os_intake.public_source_methodology import run_public_source_methodology_audit
from lawfirm_os_intake.public_synthetic_fixture_conversion import (
    run_public_synthetic_fixture_conversion_plan,
)
from lawfirm_os_intake.public_synthetic_fixture_conversion_review import (
    run_public_synthetic_fixture_conversion_review,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


TARGET_REPOS = {
    "LawFirm-os-intake",
    "LawFirm-os-legal-knowledge-runtime",
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
}


def _ready_public_methodology_chain(tmp_path, repo_root):
    _, methodology_dir = run_public_source_methodology_audit(
        repo_root=repo_root,
        out_dir=tmp_path / "public-source-methodology",
    )
    _, conversion_dir = run_public_synthetic_fixture_conversion_plan(
        methodology_report_path=methodology_dir / "public_source_methodology_report.json",
        out_dir=tmp_path / "public-synthetic-fixture-conversion",
    )
    _, review_dir = run_public_synthetic_fixture_conversion_review(
        conversion_plan_path=conversion_dir / "public_synthetic_fixture_conversion_plan.json",
        out_dir=tmp_path / "public-synthetic-fixture-conversion-review",
    )
    return (
        methodology_dir / "public_source_methodology_report.json",
        conversion_dir / "public_synthetic_fixture_conversion_plan.json",
        review_dir / "public_synthetic_fixture_conversion_review_packet.json",
    )


def _assert_no_write_or_authority_flags(report):
    assert report.human_review_required is True
    assert report.owning_repo_review_required is True
    assert report.direct_runtime_ingestion_allowed is False
    assert report.direct_promotion_performed is False
    assert report.promotion_authorized is False
    assert report.sibling_repo_write_performed is False
    assert report.github_issue_created is False
    assert report.github_pr_created is False
    assert report.github_write_performed is False
    assert report.public_records_ingested is False
    assert report.raw_public_payload_committed is False
    assert report.real_party_records_committed is False
    assert report.real_matter_records_committed is False
    assert report.synthetic_fixtures_created is False
    assert report.fixture_files_mutated is False
    assert report.fixture_generation_authorized is False
    assert report.fixture_pr_created is False
    assert report.connector_implemented is False
    assert report.legal_knowledge_adapter_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_public_methodology_owner_handoff_ready(tmp_path, repo_root):
    methodology_path, conversion_path, review_path = _ready_public_methodology_chain(
        tmp_path,
        repo_root,
    )

    report, run_dir = run_public_methodology_owner_handoff(
        methodology_report_path=methodology_path,
        conversion_plan_path=conversion_path,
        conversion_review_packet_path=review_path,
        out_dir=tmp_path / "public-methodology-owner-handoff",
    )
    persisted = PublicMethodologyOwnerHandoffReport.model_validate(
        load_json(run_dir / "public_methodology_owner_handoff_report.json")
    )
    packets = load_jsonl(run_dir / "public_methodology_owner_handoff_packets.jsonl")

    assert persisted.owner_handoff_report_id == report.owner_handoff_report_id
    assert persisted.status == "public_methodology_owner_handoff_packets_ready"
    assert set(persisted.target_repos) == TARGET_REPOS
    assert "LawFirm-os-skills-registry" not in persisted.target_repos
    assert persisted.target_repo_count == 5
    assert persisted.packet_count == 5
    assert persisted.ready_packet_count == 5
    assert persisted.blocked_packet_count == 0
    assert persisted.source_public_methodology_status == (
        "ready_for_human_public_source_methodology_review"
    )
    assert persisted.source_conversion_plan_status == "ready_for_human_conversion_review"
    assert persisted.source_conversion_review_packet_status == "ready_for_human_conversion_review"
    assert {check.status for check in persisted.checks} == {"passed"}
    assert len(packets) == 5
    assert all(packet["status"] == "ready_for_owner_review" for packet in packets)
    assert all(packet["source_count"] == 6 for packet in packets)
    assert all(packet["spec_count"] == 6 for packet in packets)
    assert all(packet["recommendation_count"] == 6 for packet in packets)
    assert all(packet["source_artifact_refs"] for packet in packets)
    assert all(packet["candidate_contract_refs"] for packet in packets)
    assert all(packet["required_owner_actions"] for packet in packets)
    assert all(packet["acceptance_checks"] for packet in packets)
    assert all(packet["red_team_notes"] for packet in packets)
    assert any(
        packet["handoff_focus"] == "legal_knowledge_public_adapter_boundary" for packet in packets
    )
    assert any(
        packet["handoff_focus"] == "local_intake_candidate_stewardship" for packet in packets
    )
    assert all(
        "skills-registry://" not in ref
        for packet in packets
        for ref in packet["candidate_contract_refs"]
    )
    _assert_no_write_or_authority_flags(persisted)

    assert (run_dir / "public_methodology_owner_handoff_report.md").is_file()
    assert (
        run_dir
        / "public_methodology_owner_packets"
        / "legal-knowledge-runtime.public_methodology_owner_packet.json"
    ).is_file()
    notes = (run_dir / "public_methodology_owner_handoff_report.md").read_text(encoding="utf-8")
    assert "Legal Knowledge adapter authorized: False" in notes
    assert "This report is local owner-handoff planning evidence only." in notes


def test_public_methodology_owner_handoff_blocks_unready_chain(tmp_path, repo_root):
    methodology_path, conversion_path, _ = _ready_public_methodology_chain(tmp_path, repo_root)
    payload = load_json(conversion_path)
    payload["status"] = "blocked_public_methodology_not_ready"
    payload["checks"][0]["status"] = "blocked"
    payload["checks"][0]["message"] = "Synthetic blocked conversion plan fixture."
    payload["spec_count"] = 0
    payload["specs"] = []
    blocked_conversion_path = write_json(
        tmp_path / "blocked-conversion-plan" / "public_synthetic_fixture_conversion_plan.json",
        payload,
    )
    review_packet, review_dir = run_public_synthetic_fixture_conversion_review(
        conversion_plan_path=blocked_conversion_path,
        out_dir=tmp_path / "blocked-conversion-review",
    )

    report, run_dir = run_public_methodology_owner_handoff(
        methodology_report_path=methodology_path,
        conversion_plan_path=blocked_conversion_path,
        conversion_review_packet_path=(
            review_dir / "public_synthetic_fixture_conversion_review_packet.json"
        ),
        out_dir=tmp_path / "blocked-public-methodology-owner-handoff",
    )

    assert review_packet.status == "blocked_by_conversion_plan"
    assert report.status == "blocked_by_public_methodology_chain"
    assert report.ready_packet_count == 0
    assert report.blocked_packet_count == 5
    assert all(packet.status == "blocked_by_public_methodology_chain" for packet in report.packets)
    assert any(check.status == "blocked" for check in report.checks)
    assert (run_dir / "public_methodology_owner_handoff_report.json").is_file()
    _assert_no_write_or_authority_flags(report)


def test_public_methodology_owner_handoff_blocks_lineage_mismatch(tmp_path, repo_root):
    methodology_path, conversion_path, review_path = _ready_public_methodology_chain(
        tmp_path,
        repo_root,
    )
    payload = load_json(review_path)
    payload["conversion_plan_id"] = "synthetic_wrong_conversion_plan_id"
    mismatched_review_path = write_json(
        tmp_path
        / "mismatched-review-packet"
        / "public_synthetic_fixture_conversion_review_packet.json",
        payload,
    )

    report, _ = run_public_methodology_owner_handoff(
        methodology_report_path=methodology_path,
        conversion_plan_path=conversion_path,
        conversion_review_packet_path=mismatched_review_path,
        out_dir=tmp_path / "mismatched-public-methodology-owner-handoff",
    )

    assert report.status == "blocked_by_public_methodology_chain"
    assert report.ready_packet_count == 0
    assert report.blocked_packet_count == 5
    assert any(
        check.check_id == "public_methodology_lineage_matches" and check.status == "blocked"
        for check in report.checks
    )


def test_public_methodology_owner_handoff_model_rejects_target_repo_drift(
    tmp_path,
    repo_root,
):
    methodology_path, conversion_path, review_path = _ready_public_methodology_chain(
        tmp_path,
        repo_root,
    )
    report, _ = run_public_methodology_owner_handoff(
        methodology_report_path=methodology_path,
        conversion_plan_path=conversion_path,
        conversion_review_packet_path=review_path,
        out_dir=tmp_path / "public-methodology-owner-handoff",
    )
    payload = report.model_dump(mode="json")
    payload["target_repos"] = payload["target_repos"][:-1]
    payload["target_repo_count"] = len(payload["target_repos"])

    with pytest.raises(ValueError, match="target repos do not match packets"):
        PublicMethodologyOwnerHandoffReport.model_validate(payload)


def test_public_methodology_owner_handoff_cli(tmp_path, repo_root, capsys):
    methodology_path, conversion_path, review_path = _ready_public_methodology_chain(
        tmp_path,
        repo_root,
    )

    exit_code = main(
        [
            "build-public-methodology-owner-handoff",
            "--methodology-report",
            str(methodology_path),
            "--conversion-plan",
            str(conversion_path),
            "--conversion-review-packet",
            str(review_path),
            "--out-dir",
            str(tmp_path / "public-methodology-owner-handoff-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "public_methodology_owner_handoff_packets_ready"' in captured.out
    assert '"target_repo_count": 5' in captured.out
    assert '"github_issue_created": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (
        tmp_path
        / "public-methodology-owner-handoff-cli"
        / "public_methodology_owner_handoff_report.json"
    ).is_file()


def test_public_methodology_owner_handoff_cli_fails_closed_on_forbidden_input_flag(
    tmp_path,
    repo_root,
    capsys,
):
    methodology_path, conversion_path, review_path = _ready_public_methodology_chain(
        tmp_path,
        repo_root,
    )
    payload = load_json(methodology_path)
    payload["public_records_ingested"] = True
    forbidden_methodology_path = write_json(
        tmp_path / "forbidden-methodology" / "public_source_methodology_report.json",
        payload,
    )

    exit_code = main(
        [
            "build-public-methodology-owner-handoff",
            "--methodology-report",
            str(forbidden_methodology_path),
            "--conversion-plan",
            str(conversion_path),
            "--conversion-review-packet",
            str(review_path),
            "--out-dir",
            str(tmp_path / "forbidden-public-methodology-owner-handoff"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert '"status": "blocked"' in captured.err
    assert "public_records_ingested" in captured.err
