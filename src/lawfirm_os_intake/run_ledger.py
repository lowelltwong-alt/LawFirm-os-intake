from __future__ import annotations

from pathlib import Path
from typing import Literal

from .models import RunEvent, RunLedgerIntegrityCheck, RunLedgerIntegrityReport
from .util import new_id, now_iso


EXTERNAL_REF_PREFIXES = ("http://", "https://", "imap://", "smtp://", "s3://", "gs://")
FORBIDDEN_REF_TERMS = (
    "gmail",
    "outlook",
    "imanage",
    "conflicts_system",
    "carrier_portal",
    "court_connector",
    "billing_system",
)


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    event_step_names: list[str] | None = None,
    details: dict[str, object] | None = None,
) -> RunLedgerIntegrityCheck:
    return RunLedgerIntegrityCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        event_step_names=event_step_names or [],
        details=details or {},
    )


def _steps_in_order(observed: list[str], required: list[str]) -> bool:
    cursor = 0
    for step in observed:
        if cursor < len(required) and step == required[cursor]:
            cursor += 1
    return cursor == len(required)


def _refs_are_local(refs: list[str]) -> tuple[bool, list[str]]:
    failures = []
    for ref in refs:
        lowered = ref.casefold()
        if lowered.startswith(EXTERNAL_REF_PREFIXES) or any(
            term in lowered for term in FORBIDDEN_REF_TERMS
        ):
            failures.append(ref)
    return not failures, failures


def _missing_output_refs(events: list[RunEvent]) -> list[str]:
    missing = []
    for event in events:
        for ref in event.output_refs:
            if ref and not Path(ref).exists():
                missing.append(ref)
    return sorted(set(missing))


def build_run_ledger_integrity_report(
    *,
    run_id: str,
    stage: Literal["preflight", "budget_success", "budget_precondition_blocked"],
    run_ledger_ref: str,
    events: list[RunEvent],
    required_steps: list[str],
    terminal_step_name: str,
    terminal_status: Literal["started", "completed", "blocked", "failed"],
) -> RunLedgerIntegrityReport:
    observed_steps = [event.step_name for event in events]
    step_indices = [event.step_index for event in events]
    all_refs = [ref for event in events for ref in [*event.input_refs, *event.output_refs] if ref]
    refs_are_local, external_refs = _refs_are_local(all_refs)
    missing_outputs = _missing_output_refs(events)
    terminal_event = events[-1] if events else None
    status_failures = [event.step_name for event in events if event.status == "failed"]
    blocked_steps = [event.step_name for event in events if event.status == "blocked"]

    checks = [
        _check(
            "events_present",
            bool(events),
            "Run ledger has at least one event.",
            event_step_names=observed_steps,
            details={"event_count": len(events)},
        ),
        _check(
            "run_id_consistent",
            all(event.run_id == run_id for event in events),
            "Every event carries the expected run ID.",
            event_step_names=[event.step_name for event in events if event.run_id != run_id],
        ),
        _check(
            "step_indices_strictly_increase",
            step_indices == sorted(set(step_indices)),
            "Step indices are unique and strictly increasing.",
            event_step_names=observed_steps,
            details={"step_indices": step_indices},
        ),
        _check(
            "required_steps_present_in_order",
            _steps_in_order(observed_steps, required_steps),
            "Required ledger steps are present in the expected order.",
            event_step_names=observed_steps,
            details={"required_steps": required_steps},
        ),
        _check(
            "terminal_step_matches_stage",
            bool(
                terminal_event
                and terminal_event.step_name == terminal_step_name
                and terminal_event.status == terminal_status
            ),
            "The ledger terminal event matches the expected stage terminal step.",
            event_step_names=[terminal_event.step_name] if terminal_event else [],
            details={
                "expected_terminal_step": terminal_step_name,
                "expected_terminal_status": terminal_status,
                "actual_terminal_step": terminal_event.step_name if terminal_event else None,
                "actual_terminal_status": terminal_event.status if terminal_event else None,
            },
        ),
        _check(
            "no_failed_events",
            not status_failures,
            "No ledger event has failed status.",
            event_step_names=status_failures,
        ),
        _check(
            "blocked_status_matches_stage",
            bool(blocked_steps) == (stage == "budget_precondition_blocked"),
            "Blocked ledger events appear only in the blocked budget-precondition path.",
            event_step_names=blocked_steps,
            details={"blocked_steps": blocked_steps, "stage": stage},
        ),
        _check(
            "artifact_refs_are_local",
            refs_are_local,
            "Ledger input and output refs stay local and avoid production connector targets.",
            details={"external_or_forbidden_refs": external_refs},
        ),
        _check(
            "output_refs_exist",
            not missing_outputs,
            "Ledger output refs exist on disk when the integrity report is built.",
            details={"missing_output_refs": missing_outputs},
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return RunLedgerIntegrityReport(
        run_ledger_integrity_report_id=new_id("ledgercheck"),
        run_id=run_id,
        stage=stage,
        status=status,
        run_ledger_ref=run_ledger_ref,
        event_count=len(events),
        required_steps=required_steps,
        observed_steps=observed_steps,
        terminal_step_name=terminal_step_name,
        terminal_status=terminal_status,
        local_artifact_refs_only=refs_are_local,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_run_ledger_integrity(report: RunLedgerIntegrityReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("run ledger integrity failed: " + ", ".join(failed))
