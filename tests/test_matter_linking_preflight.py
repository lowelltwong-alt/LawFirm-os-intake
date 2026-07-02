from copy import deepcopy
import json

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.matter_linking_preflight import (
    MATTER_LINKING_PREFLIGHT_NOTES_FILENAME,
    MATTER_LINKING_PREFLIGHT_REPORT_FILENAME,
    build_matter_linking_preflight_report,
    run_matter_linking_preflight,
)
from lawfirm_os_intake.util import load_json


FIXED_TIME = "2026-07-02T00:00:00Z"


def _fixture(repo_root):
    return load_json(
        repo_root / "examples/synthetic/upfront/upfront-like-intake-output.example.json"
    )


def test_matter_linking_preflight_reports_ambiguous_same_sender_clusters(repo_root, tmp_path):
    report, run_dir = run_matter_linking_preflight(
        input_path=repo_root / "examples/synthetic/upfront/upfront-like-intake-output.example.json",
        out_dir=tmp_path,
        generated_at=FIXED_TIME,
    )

    assert report.status == "matter_linking_preflight_requires_review"
    assert (
        report.source_artifact_id == "upfront_like_intake_output.synthetic.multi_case_adjuster.v0_1"
    )
    assert report.official_matter_number_status == "not_available"
    assert report.overall_link_state == "ambiguous_multiple_candidates"
    assert report.cluster_count == 2
    assert report.high_evidence_candidate_count == 2
    assert report.weak_signal_count == 2
    assert set(report.weak_merge_signal_types) == {"same_sender", "same_carrier"}
    assert report.strong_negative_signal_count == 2
    assert set(report.candidate_exception_lake_labels).issuperset(
        {
            "source_matter_link_ambiguous",
            "multiple_possible_matters_same_sender",
            "missing_official_matter_number",
            "document_cluster_split_required",
        }
    )
    assert "human_matter_linking_review" in report.required_next_gates
    assert "sender_reference_followup" in report.required_next_gates
    assert "no_budget_amount_until_cluster_and_roles_confirmed" in report.required_next_gates
    assert "no_matter_opening_without_official_authority" in report.required_next_gates
    assert all(check.status == "passed" for check in report.checks)
    assert (run_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME).is_file()
    assert (run_dir / MATTER_LINKING_PREFLIGHT_NOTES_FILENAME).is_file()

    for cluster in report.clusters:
        assert cluster.requires_human_confirmation is True
        assert cluster.matter_link_finalized is False
        assert cluster.strong_supporting_signal_count >= 2
        assert cluster.strong_negative_signal_count == 1
        assert cluster.source_hashes


def test_matter_linking_preflight_preserves_no_write_and_no_budget_boundaries(repo_root):
    report = build_matter_linking_preflight_report(
        payload=_fixture(repo_root),
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )

    assert report.upfront_connector_implemented is False
    assert report.vendor_api_called is False
    assert report.external_write_performed is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.matter_opening_authorized is False
    assert report.budget_amount_output_authorized is False
    assert report.budget_submission_authorized is False
    assert report.conflict_conclusion_emitted is False
    assert report.screen_created is False
    assert report.silent_learning_performed is False


def test_matter_linking_preflight_blocks_missing_negative_split_evidence(repo_root):
    payload = deepcopy(_fixture(repo_root))
    for cluster in payload["matter_linking"]["candidate_clusters"]:
        cluster["negative_signals"] = []

    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert "clusters_have_negative_split_evidence" in failed


def test_matter_linking_preflight_blocks_missing_source_hash_without_raising(repo_root):
    payload = deepcopy(_fixture(repo_root))
    payload["source_inventory"][1].pop("source_hash")

    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert "clusters_have_source_bound_strong_support" in failed


def test_matter_linking_preflight_blocks_connector_and_write_boundary_violation(repo_root):
    payload = deepcopy(_fixture(repo_root))
    payload["output_boundaries"]["vendor_api_called"] = True
    payload["output_boundaries"]["lake_write_performed"] = True

    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )
    failed_checks = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert "no_connector_or_external_write" in failed_checks
    assert set(failed_checks["no_connector_or_external_write"].blocking_refs) == {
        "vendor_api_called",
        "lake_write_performed",
    }
    assert report.vendor_api_called is True
    assert report.lake_write_performed is True


def test_matter_linking_preflight_cli_writes_report_and_returns_review_status(repo_root, tmp_path):
    exit_code = main(
        [
            "audit-matter-linking-preflight",
            "--input",
            str(repo_root / "examples/synthetic/upfront/upfront-like-intake-output.example.json"),
            "--out-dir",
            str(tmp_path),
            "--generated-at",
            FIXED_TIME,
        ]
    )

    assert exit_code == 0
    report = load_json(tmp_path / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME)
    assert report["status"] == "matter_linking_preflight_requires_review"
    assert report["cluster_count"] == 2
    assert report["weak_merge_signal_types"] == ["same_carrier", "same_sender"]


def test_matter_linking_preflight_cli_returns_blocked_for_bad_boundaries(repo_root, tmp_path):
    payload = deepcopy(_fixture(repo_root))
    payload["output_boundaries"]["vendor_api_called"] = True
    input_path = tmp_path / "bad-upfront-like-output.json"
    input_path.write_text(json.dumps(payload), encoding="utf-8")

    exit_code = main(
        [
            "audit-matter-linking-preflight",
            "--input",
            str(input_path),
            "--out-dir",
            str(tmp_path / "report"),
            "--generated-at",
            FIXED_TIME,
        ]
    )

    assert exit_code == 2
    report = load_json(tmp_path / "report" / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME)
    assert report["status"] == "blocked_matter_linking_preflight"
    assert report["vendor_api_called"] is True
