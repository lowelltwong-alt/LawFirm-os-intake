from __future__ import annotations

import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.matter_linking import build_matter_linking_cluster_report
from lawfirm_os_intake.matter_linking_cluster_review import (
    MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_HISTORY_FILENAME,
    MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_REPORT_FILENAME,
    build_matter_linking_cluster_review_outcome_report,
)
from lawfirm_os_intake.matter_link_keys import (
    DEFAULT_MATTER_LINK_POLICY_PATH,
    build_matter_link_key_extraction_report,
    load_matter_link_policy,
)
from lawfirm_os_intake.models import (
    BudgetPreconditionReport,
    HumanConfirmation,
    MatterLinkingClusterReport,
    MatterLinkingClusterReviewDecision,
    MatterLinkingClusterReviewOutcomeRecord,
    SourceBundle,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


FIXED_TIME = "2026-07-06T00:00:00Z"
PROFILE_REF = "context/synthetic-profiles/insurance-defense.yaml"
INTAKE_REF = "examples/synthetic/inbound/carrier-assignment-medmal.json"
CONFIRMATION_REF = (
    "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
)


def _confirmed_budget_inputs(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / INTAKE_REF,
        repo_root / PROFILE_REF,
        tmp_path / "preflight",
    )
    raw = load_json(repo_root / CONFIRMATION_REF)
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(raw)
    )
    confirmation_path = write_json(
        tmp_path / "human_confirmation.json",
        confirmation.model_dump(mode="json"),
    )
    return run_dir / "intake_preflight_packet.json", confirmation_path


def _cluster_report(repo_root, fixture_name: str, *, only_source_ids: set[str] | None = None):
    bundle = SourceBundle.model_validate(
        load_json(repo_root / "examples" / "synthetic" / "inbound" / fixture_name)
    )
    if only_source_ids is not None:
        bundle = bundle.model_copy(
            update={
                "sources": [
                    source for source in bundle.sources if source.source_id in only_source_ids
                ]
            }
        )
    key_report = build_matter_link_key_extraction_report(
        bundle=bundle,
        policy=load_matter_link_policy(repo_root / DEFAULT_MATTER_LINK_POLICY_PATH),
        policy_ref=str(DEFAULT_MATTER_LINK_POLICY_PATH),
        generated_at=FIXED_TIME,
    )
    return build_matter_linking_cluster_report(
        key_report=key_report,
        generated_at=FIXED_TIME,
    )


def _review_record(
    report: MatterLinkingClusterReport,
    *,
    outcome: str = "confirm_budget_scope_cluster",
    selected_cluster_ids: list[str] | None = None,
) -> MatterLinkingClusterReviewOutcomeRecord:
    cluster_ids = selected_cluster_ids or [report.clusters[0].cluster_id]
    return MatterLinkingClusterReviewOutcomeRecord(
        matter_linking_cluster_review_outcome_record_id="ml_cluster_review_confirm_001",
        matter_linking_cluster_report_id=report.matter_linking_cluster_report_id,
        source_matter_linking_cluster_report_ref=(
            f"matter-linking-cluster-report://{report.matter_linking_cluster_report_id}"
        ),
        reviewer_id="synthetic-reviewer",
        reviewer_role="intake_review_simulator",
        reviewed_at=FIXED_TIME,
        overall_outcome=outcome,  # type: ignore[arg-type]
        decision_reason="Synthetic reviewer confirms the deterministic cluster scope.",
        decisions=[
            MatterLinkingClusterReviewDecision(
                decision_id="ml_cluster_review_decision_001",
                outcome=outcome,  # type: ignore[arg-type]
                selected_cluster_ids=cluster_ids,
                decision_reason="Selected cluster IDs match the reviewed synthetic intake scope.",
                evidence_refs=[f"matter-cluster://{cluster_id}" for cluster_id in cluster_ids],
                red_team_notes=[
                    "Do not treat this as matter opening, conflict clearance, or Lake admission."
                ],
                candidate_exception_lake_labels=["matter_linking_cluster_review_outcome_candidate"],
            )
        ],
    )


def _review_report(report: MatterLinkingClusterReport):
    return build_matter_linking_cluster_review_outcome_report(
        matter_linking_cluster_report=report,
        matter_linking_cluster_report_ref=(
            f"matter-linking-cluster-report://{report.matter_linking_cluster_report_id}"
        ),
        outcome_record=_review_record(report),
        history_ref="matter_linking_cluster_review_outcome_history.jsonl",
        generated_at=FIXED_TIME,
    )


def test_single_cluster_review_confirms_budget_scope_without_side_effects(repo_root):
    cluster_report = _cluster_report(
        repo_root,
        "linking-two-matters-one-sender.source-bundle.json",
        only_source_ids={"syn-linking-email-a1", "syn-linking-email-a2"},
    )

    review_report = _review_report(cluster_report)

    assert cluster_report.cluster_count == 1
    assert review_report.status == "matter_linking_cluster_review_confirmed_for_budget_scope"
    assert review_report.budget_scope_cluster_count == 1
    assert review_report.unreviewed_cluster_count == 0
    assert review_report.budget_blocking_cluster_count == 0
    assert review_report.budget_amount_output_authorized is False
    assert review_report.budget_submission_authorized is False
    assert review_report.matter_opening_authorized is False
    assert review_report.lake_write_performed is False
    assert review_report.sqlite_write_performed is False
    assert "matter_linking_cluster_confirmed_budget_scope_candidate" in (
        review_report.candidate_lake_event_labels
    )


def test_build_budget_blocks_when_cluster_report_lacks_review_outcome(
    tmp_path,
    repo_root,
):
    preflight_packet_path, confirmation_path = _confirmed_budget_inputs(tmp_path, repo_root)
    cluster_report = _cluster_report(
        repo_root,
        "linking-two-matters-one-sender.source-bundle.json",
        only_source_ids={"syn-linking-email-a1", "syn-linking-email-a2"},
    )
    cluster_report_path = write_json(
        tmp_path / "matter_linking_cluster_report.json",
        cluster_report.model_dump(mode="json"),
    )
    budget_dir = tmp_path / "budget"

    with pytest.raises(ValueError, match="matter_linking_cluster_review_outcome_supplied"):
        run_budget(
            preflight_packet_path,
            confirmation_path,
            repo_root / PROFILE_REF,
            budget_dir,
            matter_linking_cluster_report=cluster_report_path,
        )

    report = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    candidates = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")

    assert report.status == "failed"
    assert report.blocked_state == "matter_linking_confirmation_blocked"
    assert report.matter_linking_cluster_report_ref == str(cluster_report_path)
    assert candidates[0]["local_event_label"] == "matter_linking_confirmation_blocked"
    assert str(cluster_report_path) in candidates[0]["structured_refs"]
    assert not (budget_dir / "legal_budget_proposal.json").exists()
    assert not (budget_dir / "conflict_search_seed_packet.json").exists()


def test_build_budget_allows_confirmed_single_cluster_gate(
    tmp_path,
    repo_root,
):
    preflight_packet_path, confirmation_path = _confirmed_budget_inputs(tmp_path, repo_root)
    cluster_report = _cluster_report(
        repo_root,
        "linking-two-matters-one-sender.source-bundle.json",
        only_source_ids={"syn-linking-email-a1", "syn-linking-email-a2"},
    )
    review_report = _review_report(cluster_report)
    cluster_report_path = write_json(
        tmp_path / "matter_linking_cluster_report.json",
        cluster_report.model_dump(mode="json"),
    )
    review_report_path = write_json(
        tmp_path / "matter_linking_cluster_review_outcome_report.json",
        review_report.model_dump(mode="json"),
    )

    _proposal, budget_dir = run_budget(
        preflight_packet_path,
        confirmation_path,
        repo_root / PROFILE_REF,
        tmp_path / "budget",
        matter_linking_cluster_report=cluster_report_path,
        matter_linking_cluster_review_outcome_report=review_report_path,
    )

    precondition = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    assert precondition.status == "passed"
    assert precondition.matter_linking_cluster_report_ref == str(cluster_report_path)
    assert precondition.matter_linking_cluster_review_outcome_report_ref == str(review_report_path)
    assert precondition.matter_linking_cluster_review_status == (
        "matter_linking_cluster_review_confirmed_for_budget_scope"
    )
    assert precondition.matter_linking_budget_scope_cluster_ids == (
        review_report.budget_scope_cluster_ids
    )
    assert (budget_dir / "legal_budget_proposal.json").exists()


def test_multi_cluster_split_review_blocks_budget_scope(repo_root):
    cluster_report = _cluster_report(
        repo_root,
        "linking-two-matters-one-sender.source-bundle.json",
    )
    split_record = _review_record(
        cluster_report,
        outcome="confirm_split",
        selected_cluster_ids=[cluster.cluster_id for cluster in cluster_report.clusters],
    )

    report = build_matter_linking_cluster_review_outcome_report(
        matter_linking_cluster_report=cluster_report,
        matter_linking_cluster_report_ref=(
            f"matter-linking-cluster-report://{cluster_report.matter_linking_cluster_report_id}"
        ),
        outcome_record=split_record,
        history_ref="matter_linking_cluster_review_outcome_history.jsonl",
        generated_at=FIXED_TIME,
    )

    assert cluster_report.cluster_count == 2
    assert report.status == "blocked_by_matter_linking_cluster_review"
    assert "budget_scope_exactly_one_cluster" in {
        check.check_id for check in report.checks if check.status == "failed"
    }
    assert "matter_linking_confirmation_blocked" in report.candidate_lake_event_labels


def test_cluster_review_cli_writes_append_only_report(repo_root, tmp_path):
    cluster_report = _cluster_report(
        repo_root,
        "linking-two-matters-one-sender.source-bundle.json",
        only_source_ids={"syn-linking-email-a1", "syn-linking-email-a2"},
    )
    cluster_report_path = write_json(
        tmp_path / "matter_linking_cluster_report.json",
        cluster_report.model_dump(mode="json"),
    )
    outcome_path = write_json(
        tmp_path / "matter_linking_cluster_review_outcome_record.json",
        _review_record(cluster_report).model_dump(mode="json"),
    )

    exit_code = main(
        [
            "record-matter-linking-cluster-review-outcome",
            "--matter-linking-cluster-report",
            str(cluster_report_path),
            "--outcome",
            str(outcome_path),
            "--out-dir",
            str(tmp_path / "review"),
            "--generated-at",
            FIXED_TIME,
        ]
    )

    assert exit_code == 0
    report = load_json(tmp_path / "review" / MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_REPORT_FILENAME)
    history = load_jsonl(
        tmp_path / "review" / MATTER_LINKING_CLUSTER_REVIEW_OUTCOME_HISTORY_FILENAME
    )
    assert report["status"] == "matter_linking_cluster_review_confirmed_for_budget_scope"
    assert report["budget_scope_cluster_count"] == 1
    assert report["budget_amount_output_authorized"] is False
    assert history[0]["matter_linking_cluster_review_outcome_record_id"]
