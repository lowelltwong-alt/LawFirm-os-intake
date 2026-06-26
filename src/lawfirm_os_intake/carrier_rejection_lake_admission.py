from __future__ import annotations

from pathlib import Path

from .models import (
    CarrierRejectionLakeAdmissionCheck,
    CarrierRejectionLakeAdmissionProposal,
    CarrierRejectionLakeAdmissionRecordSpec,
)
from .util import now_iso, write_json


LAKE_ADMISSION_PROPOSAL_FILENAME = "carrier_rejection_lake_admission_proposal.json"
LAKE_ADMISSION_NOTES_FILENAME = "carrier_rejection_lake_admission_proposal.md"


def _record_spec(
    *,
    record_type: str,
    table: str,
    labels: list[str],
    lake_classes: list[str],
    artifacts: list[str],
    identifiers: list[str],
    idempotency: list[str],
    hashes: list[str],
    human_fields: list[str] | None = None,
) -> CarrierRejectionLakeAdmissionRecordSpec:
    return CarrierRejectionLakeAdmissionRecordSpec(
        record_type=record_type,  # type: ignore[arg-type]
        proposed_sqlite_table=table,
        local_event_labels=labels,
        canonical_lake_class_candidates=lake_classes,  # type: ignore[arg-type]
        source_artifact_refs=artifacts,
        required_identifiers=identifiers,
        idempotency_fields=idempotency,
        required_hash_fields=hashes,
        required_human_review_fields=human_fields or [],
    )


def _build_record_specs() -> list[CarrierRejectionLakeAdmissionRecordSpec]:
    return [
        _record_spec(
            record_type="carrier_rejection_notice_record",
            table="carrier_rejection_notice_events",
            labels=[
                "carrier_rejection_notice_received",
                "carrier_rejection_duplicate_notice",
                "carrier_rejection_unlinked",
                "carrier_rejection_parse_failed",
                "carrier_rate_reduction",
                "carrier_expense_disallowed",
                "carrier_preapproval_missing",
                "carrier_staffing_or_leverage_rejection",
                "carrier_narrative_deficiency",
                "carrier_code_mapping_rejection",
                "carrier_budget_phase_variance_rejection",
                "carrier_portal_submission_failure",
                "carrier_guideline_version_drift",
            ],
            lake_classes=[
                "retrieval_miss",
                "workflow_escalation",
                "authority_conflict_override",
            ],
            artifacts=[
                "CarrierRejectionNotice",
                "CarrierRejectionSourceRef",
                "carrier_rejection_reconciliation_report.json",
                "carrier_rejection_exception_lake_candidates.jsonl",
            ],
            identifiers=[
                "notice_id",
                "carrier_id",
                "source_channel",
                "source_id",
                "source_record_id",
                "submission_id_or_unlinked_reason",
            ],
            idempotency=["idempotency_key", "source_sha256", "notice_id"],
            hashes=["source_sha256", "record_hash", "evidence_packet_hash"],
        ),
        _record_spec(
            record_type="carrier_rejection_reconciliation_record",
            table="carrier_rejection_reconciliation_events",
            labels=[
                "carrier_response_missing_after_sla",
                "carrier_rejection_unlinked",
                "carrier_rejection_duplicate_notice",
            ],
            lake_classes=["retrieval_miss", "workflow_escalation"],
            artifacts=[
                "CarrierResponseReconciliationReport",
                "CarrierRejectionRemediationCase",
                "CarrierRejectionDecisionLedgerReport",
                "carrier_rejection_reconciliation_report.json",
                "carrier_rejection_decision_ledger_report.json",
            ],
            identifiers=[
                "reconciliation_report_id",
                "expected_response_state_id",
                "submission_id",
                "budget_proposal_id_or_invoice_id",
                "run_id",
            ],
            idempotency=["reconciliation_report_id", "submission_id", "local_event_label"],
            hashes=[
                "expected_response_ledger_hash",
                "reconciliation_report_hash",
                "record_hash",
            ],
        ),
        _record_spec(
            record_type="carrier_rejection_review_outcome_record",
            table="carrier_rejection_review_outcome_events",
            labels=[
                "carrier_rejection_review_confirmed",
                "carrier_rejection_classification_corrected",
                "carrier_rejection_linkage_corrected",
                "carrier_rejection_fix_or_appeal_decided",
                "carrier_rejection_write_down_accepted",
            ],
            lake_classes=["workflow_escalation"],
            artifacts=[
                "CarrierRejectionReviewPacket",
                "carrier_rejection_review_packet.json",
                "carrier_rejection_review_decision_template.json",
                "append_only_human_rejection_review_outcome",
            ],
            identifiers=[
                "review_outcome_id",
                "review_packet_id",
                "remediation_case_id",
                "reviewer_id",
                "reviewed_at",
            ],
            idempotency=["review_outcome_id", "remediation_case_id", "reviewed_at"],
            hashes=["review_packet_hash", "review_outcome_hash", "record_hash"],
            human_fields=[
                "reviewer_id",
                "reviewed_at",
                "decision_reason",
                "supporting_source_refs_or_structured_refs",
                "supersedes_record_id_if_correction",
            ],
        ),
        _record_spec(
            record_type="carrier_appeal_submission_record",
            table="carrier_appeal_submission_events",
            labels=["carrier_appeal_submitted"],
            lake_classes=["workflow_escalation"],
            artifacts=[
                "append_only_human_rejection_review_outcome",
                "appeal_packet_ref",
                "connector_authority_check",
                "appeal_submission_state",
            ],
            identifiers=[
                "appeal_submission_id",
                "appeal_id",
                "remediation_case_id",
                "submission_id",
                "authorized_by",
                "submitted_at",
            ],
            idempotency=["appeal_id", "remediation_case_id", "submitted_at"],
            hashes=["appeal_packet_hash", "connector_authority_hash", "record_hash"],
            human_fields=[
                "human_appeal_submission_authorization",
                "authorized_by",
                "authorization_reason",
            ],
        ),
        _record_spec(
            record_type="carrier_appeal_result_record",
            table="carrier_appeal_result_events",
            labels=["carrier_appeal_result_received"],
            lake_classes=["workflow_escalation"],
            artifacts=[
                "CarrierAppealResult",
                "CarrierRejectionSourceRef",
                "carrier_rejection_reconciliation_report.json",
            ],
            identifiers=[
                "appeal_result_id",
                "appeal_id",
                "related_notice_id",
                "remediation_case_id",
                "result",
            ],
            idempotency=["appeal_result_id", "appeal_id", "related_notice_id"],
            hashes=["source_sha256", "appeal_result_hash", "record_hash"],
        ),
        _record_spec(
            record_type="carrier_financial_outcome_record",
            table="carrier_financial_outcome_events",
            labels=[
                "carrier_rejection_financial_outcome_recorded",
                "carrier_rejection_recovered_amount_recorded",
                "carrier_rejection_write_down_recorded",
            ],
            lake_classes=["workflow_escalation"],
            artifacts=[
                "CarrierRejectionRemediationCase",
                "CarrierAppealResult",
                "CarrierRejectionDecisionLedgerEvent",
                "append_only_human_rejection_review_outcome",
            ],
            identifiers=[
                "financial_outcome_id",
                "remediation_case_id",
                "budget_proposal_id_or_invoice_id",
                "currency",
            ],
            idempotency=["financial_outcome_id", "remediation_case_id", "outcome_version"],
            hashes=["financial_outcome_hash", "supporting_outcome_hash", "record_hash"],
            human_fields=[
                "reviewer_id",
                "reviewed_at",
                "disputed_amount",
                "appealed_amount",
                "recovered_amount",
                "remaining_write_down",
            ],
        ),
        _record_spec(
            record_type="carrier_rejection_learning_candidate_record",
            table="carrier_rejection_learning_candidate_events",
            labels=["carrier_rejection_learning_candidate"],
            lake_classes=["workflow_escalation"],
            artifacts=[
                "CarrierRejectionLearningReport",
                "CarrierRejectionLearningProposal",
                "carrier_rejection_learning_report.json",
            ],
            identifiers=[
                "proposal_id",
                "learning_report_id",
                "review_packet_id",
                "target_owner",
                "proposal_type",
            ],
            idempotency=["proposal_id", "learning_report_id", "proposal_type"],
            hashes=["learning_report_hash", "proposal_hash", "record_hash"],
            human_fields=[
                "human_learning_candidate_review",
                "reviewed_outcome_ref",
                "shadow_eval_ref",
            ],
        ),
    ]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    record_types: list[str] | None = None,
) -> CarrierRejectionLakeAdmissionCheck:
    return CarrierRejectionLakeAdmissionCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        record_types=record_types or [],
    )


def build_carrier_rejection_lake_admission_proposal() -> CarrierRejectionLakeAdmissionProposal:
    specs = _build_record_specs()
    required_record_types = {
        "carrier_rejection_notice_record",
        "carrier_rejection_reconciliation_record",
        "carrier_rejection_review_outcome_record",
        "carrier_appeal_submission_record",
        "carrier_appeal_result_record",
        "carrier_financial_outcome_record",
        "carrier_rejection_learning_candidate_record",
    }
    record_types = {spec.record_type for spec in specs}
    non_append = [
        spec.record_type for spec in specs if spec.correction_policy != "append_only_supersession"
    ]
    raw_payload_allowed = [spec.record_type for spec in specs if spec.raw_payload_storage_allowed]
    intake_admitted = [spec.record_type for spec in specs if spec.admitted_by_intake]
    missing_hashes = [spec.record_type for spec in specs if not spec.required_hash_fields]
    missing_idempotency = [spec.record_type for spec in specs if not spec.idempotency_fields]
    missing_orchestrator_packet = [
        spec.record_type for spec in specs if not spec.requires_orchestrator_evidence_packet
    ]
    checks = [
        _check(
            "required_record_families_present",
            required_record_types.issubset(record_types),
            "Proposal includes rejection, reconciliation, review outcome, appeal submission, appeal result, financial outcome, and learning candidate record families.",
            sorted(required_record_types - record_types),
        ),
        _check(
            "append_only_supersession_required",
            not non_append,
            "Every proposed record family uses append-only supersession for corrections.",
            non_append,
        ),
        _check(
            "raw_payload_storage_disallowed",
            not raw_payload_allowed,
            "Raw carrier, client, matter, privileged, email, portal, and workbook payload storage is disallowed.",
            raw_payload_allowed,
        ),
        _check(
            "intake_does_not_admit_records",
            not intake_admitted,
            "Intake proposes schemas and dry-run candidates only; it does not admit Lake records.",
            intake_admitted,
        ),
        _check(
            "record_hashes_required",
            not missing_hashes,
            "Every record family requires source/support hashes and a record hash.",
            missing_hashes,
        ),
        _check(
            "idempotency_required",
            not missing_idempotency,
            "Every record family declares idempotency fields.",
            missing_idempotency,
        ),
        _check(
            "orchestrator_packet_required",
            not missing_orchestrator_packet,
            "Lake admission requires an Orchestrator evidence packet; direct intake admission is prohibited.",
            missing_orchestrator_packet,
        ),
    ]
    return CarrierRejectionLakeAdmissionProposal(
        proposal_id="lake.carrier-rejection-admission.v0_1",
        status="candidate_only",
        purpose=(
            "Candidate Exception Lake admission proposal for append-only carrier rejection, "
            "reconciliation, review outcome, appeal, financial outcome, and learning "
            "candidate records."
        ),
        record_specs=specs,
        checks=checks,
        required_upstream_artifacts=[
            "carrier_rejection_reconciliation_report.json",
            "carrier_rejection_exception_lake_candidates.jsonl",
            "carrier_rejection_decision_ledger_report.json",
            "carrier_rejection_decision_ledger.jsonl",
            "carrier_rejection_review_packet.json",
            "carrier_rejection_learning_report.json",
            "carrier_rejection_orchestrator_interface.json",
            "orchestrator_evidence_packet_for_lake_review",
        ],
        proposed_contract_refs=[
            "exception-lake://candidate/admission/carrier-rejection-notice.v0_1",
            "exception-lake://candidate/admission/carrier-rejection-reconciliation.v0_1",
            "exception-lake://candidate/admission/carrier-rejection-review-outcome.v0_1",
            "exception-lake://candidate/admission/carrier-appeal-submission.v0_1",
            "exception-lake://candidate/admission/carrier-appeal-result.v0_1",
            "exception-lake://candidate/admission/carrier-financial-outcome.v0_1",
            "exception-lake://candidate/admission/carrier-rejection-learning.v0_1",
        ],
        promotion_blockers=[
            "no Exception Lake admission schema promoted",
            "no canonical carrier rejection event classes assigned",
            "no Lake SQLite migration written",
            "no Orchestrator evidence-packet handoff promoted",
            "no real-data pilot approved",
        ],
        prohibited_intake_actions=[
            "exception_lake_admission",
            "sqlite_write",
            "record_hash_authority",
            "canonical_event_class_assignment",
            "correction_in_place",
            "raw_payload_storage",
            "production_connector_capture",
            "appeal_submission",
        ],
        generated_at=now_iso(),
    )


def render_carrier_rejection_lake_admission_proposal(
    proposal: CarrierRejectionLakeAdmissionProposal,
) -> str:
    lines = [
        "# Carrier Rejection Exception Lake Admission Proposal",
        "",
        f"**Proposal ID:** {proposal.proposal_id}",
        f"**Status:** {proposal.status}",
        f"**Target repo:** {proposal.target_repo}",
        f"**Admission state:** {proposal.admission_state}",
        "",
        "## Purpose",
        "",
        proposal.purpose,
        "",
        "## Record Families",
        "",
    ]
    for spec in proposal.record_specs:
        lines.extend(
            [
                f"- `{spec.record_type}` -> `{spec.proposed_sqlite_table}`",
                f"  Labels: {', '.join(spec.local_event_labels)}",
                f"  Lake classes: {', '.join(spec.canonical_lake_class_candidates)}",
                f"  Idempotency: {', '.join(spec.idempotency_fields)}",
                f"  Hashes: {', '.join(spec.required_hash_fields)}",
                f"  Human fields: {', '.join(spec.required_human_review_fields) or 'none'}",
                f"  Correction policy: {spec.correction_policy}",
                f"  Raw payload storage allowed: {spec.raw_payload_storage_allowed}",
                f"  Admitted by intake: {spec.admitted_by_intake}",
            ]
        )
    lines.extend(["", "## Admission Checks", ""])
    for check in proposal.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
    lines.extend(
        [
            "",
            "## Required Upstream Artifacts",
            "",
            *(f"- `{item}`" for item in proposal.required_upstream_artifacts),
            "",
            "## Prohibited Intake Actions",
            "",
            *(f"- {item}" for item in proposal.prohibited_intake_actions),
            "",
            "## Boundary Flags",
            "",
            f"- Append-only required: {proposal.append_only_required}",
            f"- Correction supersession required: {proposal.correction_supersession_required}",
            f"- Record hash required: {proposal.record_hash_required}",
            f"- SQLite owner: {proposal.sqlite_owner}",
            f"- SQLite write performed: {proposal.sqlite_write_performed}",
            f"- Lake write performed: {proposal.lake_write_performed}",
            f"- Raw payload storage allowed: {proposal.raw_payload_storage_allowed}",
            f"- No canonical mutation: {proposal.no_canonical_mutation}",
            "",
            "This proposal does not create Lake tables, write SQLite, admit records, assign canonical event classes, or authorize intake to persist runtime evidence.",
            "",
        ]
    )
    return "\n".join(lines)


def run_carrier_rejection_lake_admission_proposal(
    out_dir: str | Path,
) -> tuple[CarrierRejectionLakeAdmissionProposal, Path]:
    proposal = build_carrier_rejection_lake_admission_proposal()
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / LAKE_ADMISSION_PROPOSAL_FILENAME
    notes_path = run_dir / LAKE_ADMISSION_NOTES_FILENAME
    write_json(json_path, proposal.model_dump(mode="json"))
    notes_path.write_text(
        render_carrier_rejection_lake_admission_proposal(proposal),
        encoding="utf-8",
    )
    return proposal, run_dir
