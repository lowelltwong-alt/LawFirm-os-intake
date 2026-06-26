from __future__ import annotations

from pathlib import Path

from .models import (
    CarrierRejectionOrchestratorConnectorChannel,
    CarrierRejectionOrchestratorInterfaceDraft,
    CarrierRejectionOrchestratorWorkflowStep,
)
from .util import now_iso, write_json


INTERFACE_DRAFT_FILENAME = "carrier_rejection_orchestrator_interface.json"
INTERFACE_NOTES_FILENAME = "carrier_rejection_orchestrator_interface.md"


COMMON_SOURCE_METADATA = [
    "source_channel",
    "connector_owner",
    "received_at",
    "carrier_timestamp",
    "source_id",
    "source_record_id",
    "source_sha256",
    "parser_version",
    "idempotency_key",
]


def build_carrier_rejection_orchestrator_interface_draft() -> (
    CarrierRejectionOrchestratorInterfaceDraft
):
    channels = [
        CarrierRejectionOrchestratorConnectorChannel(
            channel_id="carrier_portal_notice",
            side_effect_class="read_capture_only",
            produces_candidate_artifacts=[
                "CarrierRejectionNotice",
                "CarrierAppealResult",
                "CarrierRejectionSourceRef",
            ],
            required_identifiers=[
                "carrier_id",
                "matter_id_or_claim_id",
                "budget_proposal_id_or_invoice_id",
                "submission_id",
                "notice_id",
            ],
            required_source_metadata=COMMON_SOURCE_METADATA,
        ),
        CarrierRejectionOrchestratorConnectorChannel(
            channel_id="email_rejection_notice",
            side_effect_class="read_capture_only",
            produces_candidate_artifacts=["CarrierRejectionNotice", "CarrierRejectionSourceRef"],
            required_identifiers=[
                "carrier_id",
                "message_id",
                "submission_id_or_claim_id",
                "attachment_inventory",
            ],
            required_source_metadata=[*COMMON_SOURCE_METADATA, "mailbox_ref", "thread_ref"],
        ),
        CarrierRejectionOrchestratorConnectorChannel(
            channel_id="ledes_response_file",
            side_effect_class="read_capture_only",
            produces_candidate_artifacts=["CarrierRejectionNotice", "CarrierRejectionSourceRef"],
            required_identifiers=[
                "carrier_id",
                "invoice_id",
                "submission_id",
                "ledes_response_id",
            ],
            required_source_metadata=[*COMMON_SOURCE_METADATA, "file_name", "file_sha256"],
        ),
        CarrierRejectionOrchestratorConnectorChannel(
            channel_id="returned_budget_workbook",
            side_effect_class="read_capture_only",
            produces_candidate_artifacts=["CarrierRejectionNotice", "CarrierRejectionSourceRef"],
            required_identifiers=[
                "carrier_id",
                "budget_proposal_id",
                "submission_id",
                "workbook_sha256",
            ],
            required_source_metadata=[*COMMON_SOURCE_METADATA, "worksheet_refs", "comment_refs"],
        ),
        CarrierRejectionOrchestratorConnectorChannel(
            channel_id="appeal_correspondence",
            side_effect_class="read_capture_only",
            produces_candidate_artifacts=["CarrierAppealResult", "CarrierRejectionSourceRef"],
            required_identifiers=[
                "carrier_id",
                "appeal_id",
                "related_notice_id",
                "submission_id",
            ],
            required_source_metadata=[*COMMON_SOURCE_METADATA, "appeal_result_state"],
        ),
        CarrierRejectionOrchestratorConnectorChannel(
            channel_id="manual_human_entry",
            side_effect_class="human_entered_record",
            produces_candidate_artifacts=[
                "CarrierRejectionNotice",
                "CarrierAppealResult",
                "CarrierRejectionSourceRef",
            ],
            required_identifiers=[
                "human_reviewer_id",
                "source_summary",
                "submission_id_or_investigation_reason",
            ],
            required_source_metadata=[
                "entered_at",
                "entered_by",
                "source_channel",
                "human_attestation",
                "idempotency_key",
            ],
        ),
    ]
    workflow_steps = [
        CarrierRejectionOrchestratorWorkflowStep(
            step_id="open_expected_response_state",
            owner_repo="LawFirm-os-orchestrator",
            action=(
                "Open one response-state ledger entry for each submitted budget, invoice, "
                "appeal, or portal action."
            ),
            input_artifacts=["submitted_budget_or_invoice_or_appeal_ref"],
            output_artifacts=["expected_response_state"],
            failure_exception_labels=["carrier_response_state_missing"],
        ),
        CarrierRejectionOrchestratorWorkflowStep(
            step_id="capture_connector_sources",
            owner_repo="LawFirm-os-orchestrator",
            action=(
                "Capture portal, email, LEDES, workbook, appeal, and manual source refs "
                "as untrusted connector evidence."
            ),
            input_artifacts=["expected_response_state", "connector_payload_metadata"],
            output_artifacts=[
                "CarrierRejectionNotice",
                "CarrierAppealResult",
                "CarrierRejectionSourceRef",
            ],
            failure_exception_labels=[
                "carrier_rejection_parse_failed",
                "carrier_rejection_unlinked",
            ],
        ),
        CarrierRejectionOrchestratorWorkflowStep(
            step_id="invoke_intake_reference_reconciliation",
            owner_repo="LawFirm-os-intake",
            action=(
                "Run the local reference reconciliation over typed synthetic or governed "
                "candidate artifacts."
            ),
            input_artifacts=["legal_budget_proposal.json", "carrier_rejection_source_bundle.json"],
            output_artifacts=[
                "carrier_rejection_reconciliation_report.json",
                "carrier_rejection_remediation_cases.json",
                "carrier_rejection_exception_lake_candidates.jsonl",
            ],
            intake_runtime_authority="reference_eval_only",
        ),
        CarrierRejectionOrchestratorWorkflowStep(
            step_id="human_rejection_review_pause",
            owner_repo="LawFirm-os-orchestrator",
            action="Pause for human triage, linkage review, fix/appeal decision, and owner assignment.",
            input_artifacts=[
                "carrier_rejection_reconciliation_report.json",
                "carrier_rejection_review_packet.json",
            ],
            output_artifacts=["append_only_human_rejection_review_outcome"],
            required_human_gate="human_carrier_rejection_review",
            failure_exception_labels=["carrier_rejection_review_missing"],
        ),
        CarrierRejectionOrchestratorWorkflowStep(
            step_id="human_authorized_appeal_submission",
            owner_repo="LawFirm-os-orchestrator",
            action=(
                "Submit an appeal or corrected artifact only after human authorization "
                "and connector policy checks."
            ),
            input_artifacts=[
                "append_only_human_rejection_review_outcome",
                "appeal_packet_ref",
                "connector_authority_check",
            ],
            output_artifacts=["appeal_submission_state", "expected_appeal_response_state"],
            required_human_gate="human_appeal_submission_authorization",
            external_write_allowed=True,
            failure_exception_labels=[
                "carrier_appeal_submission_blocked",
                "carrier_portal_submission_failure",
            ],
        ),
        CarrierRejectionOrchestratorWorkflowStep(
            step_id="capture_appeal_result_and_learning_candidates",
            owner_repo="LawFirm-os-intake",
            action=(
                "Build review and learning candidate reports from captured appeal outcomes "
                "without mutating rules or profiles."
            ),
            input_artifacts=[
                "carrier_rejection_reconciliation_report.json",
                "carrier_rejection_review_packet.json",
            ],
            output_artifacts=[
                "carrier_rejection_review_packet.json",
                "carrier_rejection_learning_report.json",
            ],
            intake_runtime_authority="dry_run_candidate_only",
        ),
        CarrierRejectionOrchestratorWorkflowStep(
            step_id="prepare_exception_lake_handoff",
            owner_repo="LawFirm-os-orchestrator",
            action=(
                "Assemble a validated evidence packet for Exception Lake admission review; "
                "intake emits dry-run candidates only."
            ),
            input_artifacts=[
                "carrier_rejection_exception_lake_candidates.jsonl",
                "append_only_human_rejection_review_outcome",
                "carrier_rejection_learning_report.json",
            ],
            output_artifacts=["orchestrator_evidence_packet_for_lake_review"],
            failure_exception_labels=["carrier_rejection_lake_handoff_blocked"],
        ),
        CarrierRejectionOrchestratorWorkflowStep(
            step_id="admit_append_only_lake_records",
            owner_repo="LawFirm-os-exceptions-lake-runtime",
            action=(
                "Validate and admit append-only rejection, appeal, outcome, and learning "
                "candidate evidence under Lake-owned schemas and record hashes."
            ),
            input_artifacts=["orchestrator_evidence_packet_for_lake_review"],
            output_artifacts=["admitted_exception_lake_records"],
            failure_exception_labels=["carrier_rejection_lake_admission_failed"],
        ),
    ]
    return CarrierRejectionOrchestratorInterfaceDraft(
        interface_id="orchestrator.carrier-rejection-capture-appeal.v0_1",
        status="candidate_only",
        purpose=(
            "Candidate interface for future Orchestrator-owned carrier rejection "
            "capture, response-state reconciliation, human pause routing, appeal "
            "submission, and guarded Exception Lake handoff."
        ),
        connector_channels=channels,
        workflow_steps=workflow_steps,
        required_human_pause_points=[
            "human_carrier_rejection_review",
            "human_linkage_correction",
            "human_fix_or_appeal_decision",
            "human_appeal_submission_authorization",
            "human_learning_candidate_review",
        ],
        required_intake_reference_commands=[
            "lawfirm-os-intake capture-carrier-rejections",
            "lawfirm-os-intake review-carrier-rejections",
            "lawfirm-os-intake propose-carrier-rejection-learning",
        ],
        expected_intake_outputs=[
            "carrier_rejection_reconciliation_report.json",
            "carrier_rejection_remediation_cases.json",
            "carrier_rejection_exception_lake_candidates.jsonl",
            "carrier_rejection_review_packet.json",
            "carrier_rejection_review_notes.md",
            "carrier_rejection_review_decision_template.json",
            "carrier_rejection_learning_report.json",
            "carrier_rejection_learning_report.md",
        ],
        expected_lake_handoff_candidates=[
            "carrier_rejection_notice_received",
            "carrier_rejection_duplicate_notice",
            "carrier_rejection_unlinked",
            "carrier_rejection_parse_failed",
            "carrier_response_missing_after_sla",
            "carrier_appeal_result_received",
            "carrier_rejection_learning_candidate",
        ],
        prohibited_intake_actions=[
            "production_connector_capture",
            "carrier_portal_write",
            "email_send",
            "appeal_submission",
            "budget_approval",
            "client_or_carrier_notification",
            "exception_lake_admission",
            "sqlite_write",
            "profile_mutation",
            "template_mutation",
            "canonical_route_or_event_assignment",
        ],
        proposed_contract_refs=[
            "orchestrator://candidate/interfaces/carrier-rejection-capture.v0_1",
            "orchestrator://candidate/interfaces/response-state-ledger.v0_1",
            "orchestrator://candidate/interfaces/human-carrier-rejection-pause.v0_1",
            "orchestrator://candidate/interfaces/appeal-submission-gate.v0_1",
            "orchestrator://candidate/interfaces/exception-lake-handoff.v0_1",
        ],
        promotion_blockers=[
            "no production connector contract approved",
            "no Orchestrator route IDs assigned",
            "no human approval workflow promoted",
            "no Exception Lake admission schema promoted",
            "intake remains reference/eval only",
        ],
        generated_at=now_iso(),
    )


def render_carrier_rejection_orchestrator_interface(
    draft: CarrierRejectionOrchestratorInterfaceDraft,
) -> str:
    lines = [
        "# Carrier Rejection Orchestrator Interface Draft",
        "",
        f"**Interface ID:** {draft.interface_id}",
        f"**Status:** {draft.status}",
        f"**Target repo:** {draft.target_repo}",
        "",
        "## Purpose",
        "",
        draft.purpose,
        "",
        "## Connector Channels",
        "",
    ]
    for channel in draft.connector_channels:
        lines.extend(
            [
                f"- `{channel.channel_id}`: owner={channel.connector_owner}; "
                f"side_effect={channel.side_effect_class}; "
                f"raw_payload_storage_allowed={channel.raw_payload_storage_allowed}; "
                f"intake_connector_implementation_allowed={channel.intake_connector_implementation_allowed}",
                f"  Produces: {', '.join(channel.produces_candidate_artifacts)}",
                f"  Required identifiers: {', '.join(channel.required_identifiers)}",
            ]
        )
    lines.extend(["", "## Workflow Steps", ""])
    for step in draft.workflow_steps:
        lines.extend(
            [
                f"- `{step.step_id}`: owner={step.owner_repo}; "
                f"external_write_allowed={step.external_write_allowed}; "
                f"human_gate={step.required_human_gate or 'none'}; "
                f"intake_authority={step.intake_runtime_authority}",
                f"  Action: {step.action}",
                f"  Outputs: {', '.join(step.output_artifacts) or 'none'}",
            ]
        )
    lines.extend(
        [
            "",
            "## Human Pauses",
            "",
            *(f"- {item}" for item in draft.required_human_pause_points),
            "",
            "## Intake Reference Commands",
            "",
            *(f"- `{item}`" for item in draft.required_intake_reference_commands),
            "",
            "## Prohibited Intake Actions",
            "",
            *(f"- {item}" for item in draft.prohibited_intake_actions),
            "",
            "## Boundary Flags",
            "",
            f"- Response-state ledger required: {draft.response_state_ledger_required}",
            f"- Deterministic reconciliation required: {draft.deterministic_reconciliation_required}",
            f"- No route IDs assigned: {draft.no_route_ids_assigned}",
            f"- No connector implemented: {draft.no_connector_implemented}",
            f"- No external writes performed: {draft.no_external_writes_performed}",
            f"- No Lake write performed: {draft.no_lake_write_performed}",
            f"- No canonical mutation: {draft.no_canonical_mutation}",
            "- Human approval required for external writes: "
            f"{draft.human_approval_required_for_external_writes}",
            "",
            "This draft does not implement connectors, assign routes, submit appeals, admit Lake records, or authorize intake to perform production capture.",
            "",
        ]
    )
    return "\n".join(lines)


def run_carrier_rejection_orchestrator_interface(
    out_dir: str | Path,
) -> tuple[CarrierRejectionOrchestratorInterfaceDraft, Path]:
    draft = build_carrier_rejection_orchestrator_interface_draft()
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    json_path = run_dir / INTERFACE_DRAFT_FILENAME
    notes_path = run_dir / INTERFACE_NOTES_FILENAME
    write_json(json_path, draft.model_dump(mode="json"))
    notes_path.write_text(render_carrier_rejection_orchestrator_interface(draft), encoding="utf-8")
    return draft, run_dir
