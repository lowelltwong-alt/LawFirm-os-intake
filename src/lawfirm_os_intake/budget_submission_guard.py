from __future__ import annotations

from .models import (
    BudgetProposal,
    BudgetSubmissionGuardCheck,
    BudgetSubmissionGuardReport,
    HumanGateStatusReport,
    MatterOpeningReadiness,
)
from .util import new_id, now_iso


BUDGET_REVIEW_WORKFLOW_REF = "workflow/intake-to-budget.workflow.yaml#human_budget_review"
BUDGET_REVIEW_GATE_REF = "config/human_gates.yaml#budget_review"
BUDGET_SUBMISSION_TRANSITION_REF = (
    "workflow/prohibited-transitions.yaml#budget_proposal_ready->budget_submitted"
)

GUARDED_ACTIONS = [
    "client_budget_submission",
    "carrier_budget_submission",
    "billing_handoff",
]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    artifact_refs: list[str] | None = None,
    structured_refs: list[str] | None = None,
) -> BudgetSubmissionGuardCheck:
    return BudgetSubmissionGuardCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        structured_refs=structured_refs or [],
    )


def _artifact_refs_are_local(refs: list[str]) -> bool:
    external_prefixes = ("http://", "https://", "imap://", "smtp://", "s3://", "gs://")
    forbidden_terms = (
        "imanage",
        "gmail",
        "outlook",
        "conflicts_system",
        "carrier_portal",
        "court",
        "billing_system",
    )
    for value in refs:
        lowered = value.casefold()
        if lowered.startswith(external_prefixes):
            return False
        if any(term in lowered for term in forbidden_terms):
            return False
    return True


def _budget_review_gate_pending(report: HumanGateStatusReport) -> bool:
    gates = {gate.gate_id: gate for gate in report.gates}
    gate = gates.get("human_budget_review")
    return bool(
        report.status == "pending_human_gates"
        and gate
        and gate.status == "pending"
        and gate.completed_by_human is False
        and {"budget_submitted", "billing_handoff", "client_or_carrier_delivery"}.issubset(
            set(gate.blocks)
        )
        and gate.artifact_refs
        and gate.structured_refs
    )


def _readiness_blocks_budget_submission(readiness: MatterOpeningReadiness) -> bool:
    blocker = next(
        (
            item
            for item in readiness.blocker_details
            if item.blocker_code == "budget_review_not_completed"
        ),
        None,
    )
    guardrail = next(
        (
            item
            for item in readiness.prohibited_action_details
            if item.action_code == "do_not_submit_budget"
        ),
        None,
    )
    return bool(
        "do_not_submit_budget" in set(readiness.prohibited_actions)
        and blocker
        and blocker.required_human_gate == "human_budget_review"
        and {"budget_submitted", "billing_handoff"}.issubset(set(blocker.prohibits))
        and blocker.structured_ref
        and guardrail
        and guardrail.transition_blocked == "budget_submitted"
        and guardrail.required_human_gate == "human_budget_review"
        and guardrail.structured_ref == BUDGET_SUBMISSION_TRANSITION_REF
    )


def build_budget_submission_guard_report(
    *,
    run_id: str,
    preflight_packet_id: str,
    confirmation_id: str,
    budget: BudgetProposal,
    readiness: MatterOpeningReadiness,
    human_gate_status_report: HumanGateStatusReport,
    artifact_refs: dict[str, str],
) -> BudgetSubmissionGuardReport:
    controlled_artifact_refs = [
        artifact_refs["legal_budget_proposal"],
        artifact_refs["legal_budget_review_form"],
        artifact_refs["human_gate_status_report"],
        artifact_refs["matter_opening_readiness"],
    ]
    structured_refs = [
        BUDGET_REVIEW_WORKFLOW_REF,
        BUDGET_REVIEW_GATE_REF,
        BUDGET_SUBMISSION_TRANSITION_REF,
    ]
    checks = [
        _check(
            "budget_proposal_review_only",
            budget.approval_state == "proposed_for_human_review"
            and budget.not_authorized_for_client_submission is True,
            "Budget proposal remains proposed for human review and is not submittable.",
            [artifact_refs["legal_budget_proposal"]],
            structured_refs,
        ),
        _check(
            "human_budget_review_gate_pending",
            _budget_review_gate_pending(human_gate_status_report),
            "Human budget review remains pending and blocks client/carrier delivery and billing.",
            [artifact_refs["human_gate_status_report"]],
            [BUDGET_REVIEW_GATE_REF],
        ),
        _check(
            "readiness_blocks_budget_submission",
            _readiness_blocks_budget_submission(readiness),
            "Matter-opening readiness preserves budget-review blocker and submission guardrail.",
            [artifact_refs["matter_opening_readiness"]],
            [BUDGET_REVIEW_WORKFLOW_REF, BUDGET_SUBMISSION_TRANSITION_REF],
        ),
        _check(
            "no_submission_or_billing_handoff_performed",
            True,
            "No client submission, carrier submission, billing handoff, or external write occurred.",
            controlled_artifact_refs,
            structured_refs,
        ),
        _check(
            "controlled_artifacts_are_local",
            _artifact_refs_are_local(controlled_artifact_refs),
            "Budget submission guard controls only local review artifacts.",
            controlled_artifact_refs,
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return BudgetSubmissionGuardReport(
        budget_submission_guard_report_id=new_id("budgetguard"),
        run_id=run_id,
        preflight_packet_id=preflight_packet_id,
        confirmation_id=confirmation_id,
        budget_proposal_id=budget.budget_proposal_id,
        status=status,
        approval_state=budget.approval_state,
        not_authorized_for_client_submission=budget.not_authorized_for_client_submission,
        guarded_actions=GUARDED_ACTIONS,
        controlled_artifact_refs=controlled_artifact_refs,
        structured_refs=structured_refs,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_budget_submission_guard_report(report: BudgetSubmissionGuardReport) -> None:
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    if report.status != "passed":
        failed.append("budget_submission_guard_status")
    if report.approval_state != "proposed_for_human_review":
        failed.append("approval_state")
    if report.not_authorized_for_client_submission is not True:
        failed.append("not_authorized_for_client_submission")
    if report.client_submission_performed is not False:
        failed.append("client_submission_performed")
    if report.carrier_submission_performed is not False:
        failed.append("carrier_submission_performed")
    if report.billing_handoff_performed is not False:
        failed.append("billing_handoff_performed")
    if report.external_writes_performed is not False:
        failed.append("external_writes_performed")
    if report.non_authoritative is not True:
        failed.append("non_authoritative")
    if report.required_human_gate != "human_budget_review":
        failed.append("required_human_gate")
    if set(report.guarded_actions) != set(GUARDED_ACTIONS):
        failed.append("guarded_actions")
    if not report.controlled_artifact_refs or not _artifact_refs_are_local(
        report.controlled_artifact_refs
    ):
        failed.append("controlled_artifact_refs")
    if not failed:
        return
    raise ValueError("budget submission guard failed: " + ", ".join(failed))
