from __future__ import annotations

from pathlib import Path
from typing import Any

from .confirmation import bind_confirmation_to_packet_evidence
from .models import (
    BlockedBudgetAttemptAuditCheck,
    BlockedBudgetAttemptAuditReport,
    BudgetPreconditionReport,
    ExceptionLakeHandoffManifest,
    ExceptionLakeReadinessReport,
    HumanConfirmation,
    HumanReviewOutcomeRecord,
    IntakePreflightPacket,
)
from .util import load_json, load_jsonl, new_id, now_iso, write_json
from .workflow import run_budget


EXPECTED_BLOCKED_STATE = "budget_blocked_before_human_confirmation"

ALLOWED_BLOCKED_OUTPUTS = {
    "budget_precondition_report.json",
    "exception_lake_candidates.jsonl",
    "exception_lake_handoff_manifest.json",
    "exception_lake_readiness_report.json",
    "human_confirmation_history.jsonl",
    "run_ledger.jsonl",
}

PROHIBITED_BLOCKED_OUTPUTS = {
    "conflict_search_seed_packet.json",
    "legal_budget_proposal.json",
    "legal_budget_review_form.md",
    "matter_opening_readiness.json",
    "matter_opening_review_package.md",
    "review_package_manifest.json",
    "review_package_completeness_report.json",
    "safety_gate_report.json",
    "evidence_graph.json",
}


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    details: dict[str, Any] | None = None,
) -> BlockedBudgetAttemptAuditCheck:
    return BlockedBudgetAttemptAuditCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        details=details or {},
    )


def _human_review_outcome_path(budget_dir: Path) -> Path | None:
    matches = sorted(budget_dir.glob("human_review_outcome.*.json"))
    return matches[0] if len(matches) == 1 else None


def _model_or_none(model: type, path: Path) -> Any | None:
    if not path.exists() or not path.is_file():
        return None
    try:
        return model.model_validate(load_json(path))
    except (OSError, ValueError):
        return None


def _write_blocking_confirmation(
    *,
    packet: IntakePreflightPacket,
    confirmation_template_path: str | Path,
    out_dir: Path,
) -> Path:
    raw = load_json(confirmation_template_path)
    raw["preflight_packet_id"] = packet.packet_id
    raw["confirmation_id"] = f"{raw.get('confirmation_id', 'human-confirmation')}-blocked"
    raw["status"] = "needs_more_information"
    raw["notes"] = (
        "Synthetic blocked-budget audit. Reviewer needs more information; no conflict seed, "
        "budget proposal, readiness packet, safety gate, or final review package may be emitted."
    )
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw),
    )
    return write_json(out_dir / "blocked_confirmation.json", confirmation.model_dump(mode="json"))


def build_blocked_budget_attempt_audit_report(
    *,
    preflight_packet_path: str | Path,
    confirmation_path: str | Path,
    budget_dir: str | Path,
    exception_raised: bool,
    blocked_error: str | None,
) -> BlockedBudgetAttemptAuditReport:
    preflight_packet_path = Path(preflight_packet_path)
    confirmation_path = Path(confirmation_path)
    budget_dir = Path(budget_dir)
    precondition_path = budget_dir / "budget_precondition_report.json"
    outcome_path = _human_review_outcome_path(budget_dir)
    history_path = budget_dir / "human_confirmation_history.jsonl"
    exception_candidates_path = budget_dir / "exception_lake_candidates.jsonl"
    exception_readiness_path = budget_dir / "exception_lake_readiness_report.json"
    exception_handoff_path = budget_dir / "exception_lake_handoff_manifest.json"
    ledger_path = budget_dir / "run_ledger.jsonl"

    report = _model_or_none(BudgetPreconditionReport, precondition_path)
    outcome = _model_or_none(HumanReviewOutcomeRecord, outcome_path) if outcome_path else None
    exception_readiness = _model_or_none(ExceptionLakeReadinessReport, exception_readiness_path)
    exception_handoff = _model_or_none(ExceptionLakeHandoffManifest, exception_handoff_path)
    history = load_jsonl(history_path)
    exception_candidates = load_jsonl(exception_candidates_path)
    ledger = load_jsonl(ledger_path)
    prohibited_present = sorted(
        name for name in PROHIBITED_BLOCKED_OUTPUTS if (budget_dir / name).exists()
    )
    allowed_missing = sorted(
        name for name in ALLOWED_BLOCKED_OUTPUTS if not (budget_dir / name).exists()
    )
    if outcome_path is None:
        allowed_missing.append("human_review_outcome.<confirmation_id>.json")

    checks = [
        _check(
            "budget_call_failed_closed",
            exception_raised and bool(blocked_error),
            "The blocked budget attempt raised before returning a budget proposal.",
            artifact_refs=[str(budget_dir)],
            details={"blocked_error": blocked_error},
        ),
        _check(
            "budget_precondition_failed_before_confirmation",
            bool(
                report
                and report.status == "failed"
                and report.blocked_state == EXPECTED_BLOCKED_STATE
                and any(
                    check.check_id == "confirmation_status_confirmed" and check.status == "failed"
                    for check in report.checks
                )
            ),
            "Budget precondition report failed on non-confirmed review status.",
            artifact_refs=[str(precondition_path)],
        ),
        _check(
            "human_review_outcome_recorded_as_blocked",
            bool(
                outcome
                and outcome.status == "needs_more_information"
                and outcome.budget_stage_allowed is False
                and outcome.required_next_gate == "collect_missing_information"
                and outcome.mutation_policy == "append_or_supersede_only"
                and outcome.decision_evidence_refs
                and outcome.confirmed_party_evidence_refs
                and history
                and history[0].get("confirmation_id") == outcome.confirmation_id
            ),
            "Human review outcome and append-only history show budget-stage output is blocked.",
            artifact_refs=[str(path) for path in [outcome_path, history_path] if path],
        ),
        _check(
            "no_prohibited_budget_outputs_emitted",
            not prohibited_present,
            "Blocked attempt emitted no conflict seed, budget proposal, readiness, safety, or final package artifacts.",
            artifact_refs=[str(budget_dir / name) for name in PROHIBITED_BLOCKED_OUTPUTS],
            details={"prohibited_outputs_present": prohibited_present},
        ),
        _check(
            "blocked_artifacts_present",
            not allowed_missing,
            "Blocked attempt preserved the expected failure report, exception, history, and ledger artifacts.",
            artifact_refs=[
                str(precondition_path),
                str(exception_candidates_path),
                str(exception_readiness_path),
                str(exception_handoff_path),
                str(history_path),
                str(ledger_path),
            ],
            details={"missing_allowed_artifacts": allowed_missing},
        ),
        _check(
            "exception_candidate_records_blocked_state",
            bool(
                exception_candidates
                and exception_candidates[0].get("local_event_label") == EXPECTED_BLOCKED_STATE
                and exception_candidates[0].get("canonical_lake_class") == "workflow_escalation"
                and exception_candidates[0].get("raw_payload_included") is False
                and exception_candidates[0].get("canonical_promotion_required") is True
                and exception_readiness
                and exception_readiness.status == "passed"
                and exception_readiness.admission_state == "dry_run_not_admitted"
                and exception_handoff
                and exception_handoff.status == "dry_run_ready_not_admitted"
                and exception_handoff.stage == "budget_precondition_blocked"
                and exception_handoff.sqlite_write_performed is False
                and exception_handoff.candidate_count == len(exception_candidates)
            ),
            "Blocked precondition becomes a dry-run workflow-escalation candidate, not a Lake admission.",
            artifact_refs=[
                str(exception_candidates_path),
                str(exception_readiness_path),
                str(exception_handoff_path),
            ],
        ),
        _check(
            "ledger_stops_at_blocked_generation",
            bool(
                any(
                    event.get("step_name") == "budget_generation_blocked"
                    and event.get("status") == "blocked"
                    for event in ledger
                )
                and not any(
                    event.get("step_name") == "conflict_seed_and_budget_proposal_built"
                    for event in ledger
                )
                and not any(
                    event.get("step_name") == "matter_opening_review_package_built"
                    for event in ledger
                )
            ),
            "Run ledger records the block and has no post-precondition generation steps.",
            artifact_refs=[str(ledger_path)],
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return BlockedBudgetAttemptAuditReport(
        blocked_budget_attempt_audit_report_id=new_id("blocked_budget_audit"),
        status=status,
        preflight_packet_ref=str(preflight_packet_path),
        confirmation_ref=str(confirmation_path),
        blocked_budget_dir=str(budget_dir),
        expected_blocked_state=EXPECTED_BLOCKED_STATE,
        exception_raised=exception_raised,
        blocked_error=blocked_error,
        checks=checks,
        generated_at=now_iso(),
    )


def run_blocked_budget_attempt_audit(
    *,
    preflight_packet_path: str | Path,
    confirmation_template_path: str | Path,
    practice_profile_path: str | Path,
    out_dir: str | Path,
) -> tuple[BlockedBudgetAttemptAuditReport, Path]:
    preflight_packet_path = Path(preflight_packet_path)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    packet = IntakePreflightPacket.model_validate(load_json(preflight_packet_path))
    confirmation_path = _write_blocking_confirmation(
        packet=packet,
        confirmation_template_path=confirmation_template_path,
        out_dir=out_dir,
    )
    budget_dir = out_dir / "budget"
    exception_raised = False
    blocked_error: str | None = None
    try:
        run_budget(
            preflight_packet_path,
            confirmation_path,
            practice_profile_path,
            budget_dir,
        )
    except ValueError as exc:
        exception_raised = True
        blocked_error = str(exc)
    report = build_blocked_budget_attempt_audit_report(
        preflight_packet_path=preflight_packet_path,
        confirmation_path=confirmation_path,
        budget_dir=budget_dir,
        exception_raised=exception_raised,
        blocked_error=blocked_error,
    )
    write_json(out_dir / "blocked_budget_attempt_audit_report.json", report.model_dump(mode="json"))
    enforce_blocked_budget_attempt_audit(report)
    return report, out_dir


def enforce_blocked_budget_attempt_audit(report: BlockedBudgetAttemptAuditReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("blocked budget attempt audit failed: " + ", ".join(failed))
