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


def _resolved_fixture(repo_root):
    return load_json(
        repo_root
        / "examples/synthetic/upfront/upfront-like-intake-output.resolved-followup.example.json"
    )


def _weak_single_fixture(repo_root):
    return load_json(
        repo_root
        / "examples/synthetic/upfront/upfront-like-intake-output.weak-single-candidate.example.json"
    )


def _resolved_single_fixture(repo_root):
    return load_json(
        repo_root
        / "examples/synthetic/upfront/upfront-like-intake-output.resolved-single-candidate.example.json"
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
    assert report.weak_only_candidate_count == 0
    assert report.negative_split_evidence_required is True
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
    assert "no_lake_or_sqlite_write_from_matter_linking_preflight" in report.required_next_gates
    assert all(check.status == "passed" for check in report.checks)
    assert (run_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME).is_file()
    assert (run_dir / MATTER_LINKING_PREFLIGHT_NOTES_FILENAME).is_file()

    for cluster in report.clusters:
        assert cluster.requires_human_confirmation is True
        assert cluster.matter_link_finalized is False
        assert cluster.source_bound_strong_support_present is True
        assert cluster.weak_only_candidate is False
        assert cluster.negative_split_evidence_required is True
        assert cluster.strong_supporting_signal_count >= 2
        assert cluster.strong_negative_signal_count == 1
        assert cluster.source_hashes


def test_matter_linking_preflight_reports_resolved_followup_candidates(repo_root, tmp_path):
    report, run_dir = run_matter_linking_preflight(
        input_path=(
            repo_root
            / "examples/synthetic/upfront/upfront-like-intake-output.resolved-followup.example.json"
        ),
        out_dir=tmp_path,
        generated_at=FIXED_TIME,
    )

    assert report.status == "matter_linking_preflight_resolved_candidate_requires_review"
    assert (
        report.source_artifact_id == "upfront_like_intake_output.synthetic.resolved_followup.v0_1"
    )
    assert report.overall_link_state == "resolved_split_candidates_pending_human_confirmation"
    assert report.official_matter_number_status == "not_available"
    assert report.requires_human_confirmation is True
    assert report.requires_sender_followup is False
    assert report.sender_followup_required is False
    assert report.cluster_count == 2
    assert report.high_evidence_candidate_count == 2
    assert report.weak_only_candidate_count == 0
    assert report.negative_split_evidence_required is True
    assert set(report.weak_merge_signal_types) == {"same_sender", "same_carrier"}
    assert "sender_reference_followup" not in report.required_next_gates
    assert "human_matter_linking_review" in report.required_next_gates
    assert "no_budget_amount_until_cluster_and_roles_confirmed" in report.required_next_gates
    assert "no_matter_opening_without_official_authority" in report.required_next_gates
    assert set(report.candidate_exception_lake_labels).issuperset(
        {
            "source_matter_link_resolved_candidate",
            "missing_official_matter_number",
            "document_cluster_split_resolved_candidate",
            "human_matter_linking_confirmation_required",
        }
    )
    assert all(check.status == "passed" for check in report.checks)
    assert (run_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME).is_file()

    for cluster in report.clusters:
        assert "upfront_like_request_id" in cluster.supporting_signal_types
        assert "sender_followup_claim_cluster_confirmation" in cluster.supporting_signal_types
        assert cluster.requires_human_confirmation is True
        assert cluster.matter_link_finalized is False
        assert cluster.source_bound_strong_support_present is True
        assert cluster.weak_only_candidate is False
        assert cluster.negative_split_evidence_required is True


def test_matter_linking_preflight_blocks_weak_single_candidate(repo_root, tmp_path):
    report, run_dir = run_matter_linking_preflight(
        input_path=(
            repo_root
            / "examples/synthetic/upfront/upfront-like-intake-output.weak-single-candidate.example.json"
        ),
        out_dir=tmp_path,
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert report.overall_link_state == "weak_single_candidate_requires_followup"
    assert report.cluster_count == 1
    assert report.high_evidence_candidate_count == 0
    assert report.weak_only_candidate_count == 1
    assert report.negative_split_evidence_required is False
    assert report.strong_negative_signal_count == 0
    assert report.sender_followup_required is True
    assert set(report.candidate_exception_lake_labels).issuperset(
        {
            "source_matter_link_weak_only_candidate",
            "missing_official_matter_number",
            "sender_reference_followup_required",
            "human_matter_linking_confirmation_required",
        }
    )
    assert "weak_only_candidates_block_matter_linking" in failed
    assert "clusters_have_source_bound_strong_support" in failed
    assert "clusters_have_negative_split_evidence" not in failed
    assert (run_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME).is_file()

    cluster = report.clusters[0]
    assert cluster.source_bound_strong_support_present is False
    assert cluster.weak_only_candidate is True
    assert cluster.negative_split_evidence_required is False
    assert cluster.strong_supporting_signal_count == 0
    assert cluster.source_hashes


def test_matter_linking_preflight_allows_resolved_single_candidate_without_split_evidence(
    repo_root,
):
    report = build_matter_linking_preflight_report(
        payload=_resolved_single_fixture(repo_root),
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )

    assert report.status == "matter_linking_preflight_resolved_candidate_requires_review"
    assert report.overall_link_state == "resolved_single_candidate_pending_human_confirmation"
    assert report.cluster_count == 1
    assert report.high_evidence_candidate_count == 1
    assert report.weak_only_candidate_count == 0
    assert report.negative_split_evidence_required is False
    assert report.strong_negative_signal_count == 0
    assert report.requires_human_confirmation is True
    assert report.matter_opening_authorized is False
    assert report.budget_amount_output_authorized is False
    assert set(report.candidate_exception_lake_labels).issuperset(
        {
            "source_matter_link_resolved_candidate",
            "missing_official_matter_number",
            "human_matter_linking_confirmation_required",
        }
    )
    assert "document_cluster_split_resolved_candidate" not in (
        report.candidate_exception_lake_labels
    )
    assert all(check.status == "passed" for check in report.checks)
    assert "sender_reference_followup" not in report.required_next_gates

    cluster = report.clusters[0]
    assert cluster.source_bound_strong_support_present is True
    assert cluster.weak_only_candidate is False
    assert cluster.negative_split_evidence_required is False
    assert cluster.strong_negative_signal_count == 0


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


def test_matter_linking_preflight_preserves_resolved_candidate_no_write_boundaries(repo_root):
    report = build_matter_linking_preflight_report(
        payload=_resolved_fixture(repo_root),
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


def test_matter_linking_preflight_blocks_negative_split_signal_without_known_source_ref(
    repo_root,
):
    payload = deepcopy(_fixture(repo_root))
    payload["matter_linking"]["candidate_clusters"][0]["negative_signals"][0]["source_refs"] = [
        "source.unknown.999:page1:1-5"
    ]

    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert "clusters_have_negative_split_evidence" in failed


def test_matter_linking_preflight_blocks_malformed_signal_ref_without_locator(repo_root):
    payload = deepcopy(_resolved_single_fixture(repo_root))
    payload["matter_linking"]["candidate_clusters"][0]["supporting_signals"][0]["source_refs"] = [
        "source.attachment.001"
    ]

    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert "clusters_have_source_bound_strong_support" in failed


def test_matter_linking_preflight_blocks_weak_signal_promoted_to_strong(repo_root):
    payload = deepcopy(_weak_single_fixture(repo_root))
    for signal in payload["matter_linking"]["candidate_clusters"][0]["supporting_signals"]:
        if signal["signal_type"] in {"same_sender", "same_carrier"}:
            signal["weight_class"] = "strong"

    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert "weak_signals_cannot_be_promoted_to_strong_support" in failed
    assert "clusters_have_source_bound_strong_support" in failed
    assert report.clusters[0].weak_only_candidate is True


def test_matter_linking_preflight_blocks_missing_output_boundary_contract_state(repo_root):
    payload = deepcopy(_resolved_single_fixture(repo_root))
    payload["output_boundaries"].pop("lake_write_performed")

    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )
    failed_checks = {check.check_id: check for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert "no_connector_or_external_write" in failed_checks
    assert "lake_write_performed" in failed_checks["no_connector_or_external_write"].blocking_refs


def test_matter_linking_preflight_blocks_invalid_split_state_cardinality(repo_root):
    payload = deepcopy(_fixture(repo_root))
    payload["matter_linking"]["candidate_clusters"] = [
        payload["matter_linking"]["candidate_clusters"][0]
    ]

    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert "link_state_cluster_cardinality_valid" in failed


def test_matter_linking_preflight_blocks_resolved_without_resolution_signal(repo_root):
    payload = deepcopy(_resolved_fixture(repo_root))
    for cluster in payload["matter_linking"]["candidate_clusters"]:
        cluster["supporting_signals"] = [
            signal
            for signal in cluster["supporting_signals"]
            if signal["signal_type"]
            not in {"sender_followup_claim_cluster_confirmation", "upfront_like_request_id"}
        ]

    report = build_matter_linking_preflight_report(
        payload=payload,
        source_artifact_ref="fixture.json",
        generated_at=FIXED_TIME,
    )
    failed = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_matter_linking_preflight"
    assert "resolved_candidates_have_source_bound_resolution_signal" in failed


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
