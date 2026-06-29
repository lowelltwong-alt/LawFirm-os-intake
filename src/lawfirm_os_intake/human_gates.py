from __future__ import annotations

from .models import (
    BudgetProposal,
    ConflictSeedPacket,
    HumanConfirmation,
    HumanGateStatus,
    HumanGateStatusReport,
    HumanReviewOutcomeRecord,
    IntakePreflightPacket,
    MatterOpeningReadiness,
)
from .util import new_id, now_iso


REQUIRED_HUMAN_GATE_IDS = [
    "human_intake_confirmation",
    "human_conflicts_clearance",
    "human_engagement_authorization",
    "human_budget_review",
    "human_matter_opening_authorization",
]


def build_human_gate_status_report(
    *,
    packet: IntakePreflightPacket,
    confirmation: HumanConfirmation,
    human_review_outcome: HumanReviewOutcomeRecord,
    conflict_seed: ConflictSeedPacket,
    budget: BudgetProposal,
    readiness: MatterOpeningReadiness,
    artifact_refs: dict[str, str],
) -> HumanGateStatusReport:
    intake_gate_completed = (
        confirmation.status == "confirmed" and human_review_outcome.budget_stage_allowed is True
    )
    gates = [
        HumanGateStatus(
            gate_id="human_intake_confirmation",
            label="Human intake confirmation",
            status="completed" if intake_gate_completed else "pending",
            authority_owner="human_intake_reviewer",
            completed_by_human=intake_gate_completed,
            artifact_refs=[
                artifact_refs["preflight_packet"],
                artifact_refs["human_confirmation"],
                artifact_refs["human_review_outcome"],
            ],
            structured_refs=["config/human_gates.yaml#intake_classification_confirmation"],
            notes=(
                "Matter family, representation posture, and principal party roles were "
                "human-confirmed for this synthetic run."
            ),
        ),
        HumanGateStatus(
            gate_id="human_conflicts_clearance",
            label="Human conflicts clearance",
            status="pending",
            authority_owner="conflicts_review",
            completed_by_human=False,
            artifact_refs=[
                artifact_refs["conflict_search_seed"],
                artifact_refs["matter_opening_readiness"],
            ],
            structured_refs=["config/human_gates.yaml#conflicts_review"],
            blocks=["conflicts_cleared", "matter_opened", "representation_accepted"],
            notes=(
                f"Current conflict output remains `{conflict_seed.conclusion}` and is "
                "a search seed only."
            ),
        ),
        HumanGateStatus(
            gate_id="human_engagement_authorization",
            label="Human engagement authorization",
            status="pending",
            authority_owner="engagement_and_matter_opening",
            completed_by_human=False,
            artifact_refs=[artifact_refs["matter_opening_readiness"]],
            structured_refs=["config/human_gates.yaml#engagement_and_matter_opening"],
            blocks=["accept_representation", "send_engagement_letter", "matter_opened"],
            notes="Engagement authorization remains outside the intake workflow.",
        ),
        HumanGateStatus(
            gate_id="human_budget_review",
            label="Human budget review",
            status="pending",
            authority_owner="human_budget_review",
            completed_by_human=False,
            artifact_refs=[
                artifact_refs["legal_budget_proposal"],
                artifact_refs["legal_budget_review_form"],
            ],
            structured_refs=["config/human_gates.yaml#budget_review"],
            blocks=["budget_submitted", "billing_handoff", "client_or_carrier_delivery"],
            notes=f"Budget proposal `{budget.budget_proposal_id}` remains proposed for human review.",
        ),
        *(
            [
                HumanGateStatus(
                    gate_id="human_carrier_preapproval",
                    label="Human carrier preapproval review",
                    status="pending",
                    authority_owner="human_budget_review",
                    completed_by_human=False,
                    artifact_refs=[
                        artifact_refs["legal_budget_proposal"],
                        artifact_refs["legal_budget_review_form"],
                        artifact_refs.get("carrier_preapproval_report", ""),
                    ],
                    structured_refs=[
                        "config/human_gates.yaml#carrier_preapproval_review",
                        f"carrier-preapproval-report://{budget.carrier_preapproval_report.report_id}",
                    ],
                    blocks=[
                        "carrier_budget_submission",
                        "budget_submitted",
                        "carrier_preapproval_bypassed",
                    ],
                    notes=(
                        "Synthetic carrier guideline thresholds require human carrier "
                        "preapproval review before any carrier-facing submission."
                    ),
                )
            ]
            if budget.carrier_preapproval_report is not None
            and budget.carrier_preapproval_report.required_count > 0
            else []
        ),
        HumanGateStatus(
            gate_id="human_matter_opening_authorization",
            label="Human matter-opening authorization",
            status="pending",
            authority_owner="engagement_and_matter_opening",
            completed_by_human=False,
            artifact_refs=[artifact_refs["matter_opening_readiness"]],
            structured_refs=["config/human_gates.yaml#engagement_and_matter_opening"],
            blocks=["open_matter", "create_imanage_workspace"],
            notes=f"Current readiness remains `{readiness.status}`.",
        ),
    ]
    completed = sum(1 for gate in gates if gate.status == "completed")
    pending = sum(1 for gate in gates if gate.status == "pending")
    required_gate_ids = list(REQUIRED_HUMAN_GATE_IDS)
    if any(gate.gate_id == "human_carrier_preapproval" for gate in gates):
        required_gate_ids.append("human_carrier_preapproval")
    return HumanGateStatusReport(
        human_gate_status_report_id=new_id("humangates"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        confirmation_id=confirmation.confirmation_id,
        status="all_human_gates_complete" if pending == 0 else "pending_human_gates",
        required_gate_ids=required_gate_ids,
        completed_gate_count=completed,
        pending_gate_count=pending,
        gates=gates,
        generated_at=now_iso(),
    )


def enforce_human_gate_status_report(report: HumanGateStatusReport) -> None:
    gates_by_id = {gate.gate_id: gate for gate in report.gates}
    missing = [gate_id for gate_id in REQUIRED_HUMAN_GATE_IDS if gate_id not in gates_by_id]
    if missing:
        raise ValueError("human gate status report missing gates: " + ", ".join(missing))
    if gates_by_id["human_intake_confirmation"].status != "completed":
        raise ValueError("human gate status report missing completed intake confirmation")
    pending_required = [
        "human_conflicts_clearance",
        "human_engagement_authorization",
        "human_budget_review",
        "human_matter_opening_authorization",
    ]
    not_pending = [
        gate_id for gate_id in pending_required if gates_by_id[gate_id].status != "pending"
    ]
    if not_pending:
        raise ValueError(
            "human gate status report has non-pending required gates: " + ", ".join(not_pending)
        )
    unsupported = [
        gate.gate_id for gate in report.gates if not gate.artifact_refs or not gate.structured_refs
    ]
    if unsupported:
        raise ValueError(
            "human gate status report has unsupported gates: " + ", ".join(unsupported)
        )
    actual_pending = sum(1 for gate in report.gates if gate.status == "pending")
    if report.status != "pending_human_gates" or report.pending_gate_count != actual_pending:
        raise ValueError("human gate status report does not preserve pending human gates")
    if "human_carrier_preapproval" in gates_by_id:
        gate = gates_by_id["human_carrier_preapproval"]
        if gate.status != "pending" or gate.completed_by_human:
            raise ValueError("carrier preapproval gate must remain pending")
        if "carrier_budget_submission" not in gate.blocks:
            raise ValueError("carrier preapproval gate must block carrier submission")
