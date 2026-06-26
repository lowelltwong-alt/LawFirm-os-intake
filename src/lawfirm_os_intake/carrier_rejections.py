from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import re

from .carrier_rejection_decision_ledger import (
    CARRIER_REJECTION_DECISION_LEDGER_REPORT_FILENAME,
    build_carrier_rejection_decision_ledger_report,
    write_carrier_rejection_decision_ledger_outputs,
)
from .models import (
    BudgetProposal,
    CarrierAppealResult,
    CarrierExpectedResponse,
    CarrierRejectionCaptureSourceBundle,
    CarrierRejectionNotice,
    CarrierRejectionRemediationCase,
    CarrierResponseReconciliationReport,
    ExceptionLakeCandidate,
    RunEvent,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


SYNTHETIC_BUDGET_ID_PLACEHOLDER = "filled-by-test-budget-proposal"
SYNTHETIC_PREFLIGHT_ID_PLACEHOLDER = "filled-by-test-preflight-packet"


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)


def _norm(value: str | None) -> str:
    if not value:
        return ""
    return re.sub(r"\s+", " ", value.strip().casefold())


def _label_for_notice(notice: CarrierRejectionNotice, linked: bool) -> str:
    if notice.parse_status == "parse_failed":
        return "carrier_rejection_parse_failed"
    if not linked:
        return "carrier_rejection_unlinked"
    text = _norm(" ".join([notice.reason_code or "", notice.reason_text_excerpt]))
    checks = [
        ("carrier_portal_submission_failure", ["transport", "portal", "upload failed"]),
        (
            "carrier_guideline_version_drift",
            ["guideline version", "stale guideline", "old guideline"],
        ),
        ("carrier_rate_reduction", ["rate", "timekeeper", "keeper", "title rate"]),
        ("carrier_preapproval_missing", ["preapproval", "pre-approval", "prior approval"]),
        ("carrier_expense_disallowed", ["expense", "vendor", "expert", "travel", "copy"]),
        ("carrier_staffing_or_leverage_rejection", ["staffing", "leverage", "partner"]),
        ("carrier_narrative_deficiency", ["narrative", "block billing", "description"]),
        ("carrier_code_mapping_rejection", ["utbms", "ledes", "task code", "code mismatch"]),
        (
            "carrier_budget_phase_variance_rejection",
            ["over budget", "budget exceeded", "phase cap"],
        ),
    ]
    for label, needles in checks:
        if any(needle in text for needle in needles):
            return label
    return "carrier_rejection_notice_received"


def _canonical_class(label: str) -> str:
    if label == "carrier_rejection_unlinked":
        return "retrieval_miss"
    if label == "carrier_guideline_version_drift":
        return "authority_conflict_override"
    return "workflow_escalation"


def _status_for_label(label: str) -> str:
    if label == "carrier_rejection_unlinked":
        return "needs_linkage_review"
    if label == "carrier_response_missing_after_sla":
        return "missing_response_followup"
    if label == "carrier_rejection_parse_failed":
        return "parse_failed"
    return "captured_for_human_review"


def _learning_candidates(label: str) -> list[str]:
    mapping = {
        "carrier_rate_reduction": [
            "timekeeper_rate_candidate",
            "guideline_profile_change_candidate",
        ],
        "carrier_expense_disallowed": [
            "guideline_profile_change_candidate",
            "eval_fixture_candidate",
        ],
        "carrier_preapproval_missing": ["validation_rule_candidate", "preapproval_gate_candidate"],
        "carrier_staffing_or_leverage_rejection": [
            "guideline_profile_change_candidate",
            "staffing_rule_candidate",
        ],
        "carrier_narrative_deficiency": ["narrative_rule_candidate", "eval_fixture_candidate"],
        "carrier_code_mapping_rejection": [
            "template_mapping_candidate",
            "validation_rule_candidate",
        ],
        "carrier_budget_phase_variance_rejection": [
            "budget_driver_candidate",
            "variance_threshold_candidate",
        ],
        "carrier_guideline_version_drift": ["guideline_version_review_candidate"],
        "carrier_rejection_parse_failed": ["parser_rule_candidate"],
        "carrier_rejection_unlinked": ["reconciliation_rule_candidate"],
        "carrier_response_missing_after_sla": ["capture_sla_candidate"],
    }
    return mapping.get(label, ["eval_fixture_candidate"])


def _case_key_for_notice(notice: CarrierRejectionNotice) -> str:
    return notice.idempotency_key


def _source_structured_refs(case: CarrierRejectionRemediationCase) -> list[str]:
    refs = [
        f"carrier-rejection-case://{case.remediation_case_id}",
        *[
            f"carrier-source://{ref.source_channel}/{ref.source_id}/{ref.source_record_id}"
            for ref in case.source_refs
        ],
    ]
    if case.budget_proposal_id:
        refs.append(f"budget-proposal://{case.budget_proposal_id}")
    if case.submission_id:
        refs.append(f"carrier-submission://{case.submission_id}")
    return refs


def _candidate_for_case(case: CarrierRejectionRemediationCase) -> ExceptionLakeCandidate:
    return ExceptionLakeCandidate(
        candidate_id=_stable_id("exc", f"{case.remediation_case_id}|{case.local_event_label}"),
        run_id="carrier-rejection-reconciliation",
        preflight_packet_id=case.budget_proposal_id or "unknown-preflight",
        local_event_label=case.local_event_label,
        canonical_lake_class=case.canonical_lake_class,
        reason=(
            f"Carrier rejection remediation case requires human review: {case.local_event_label}"
        ),
        structured_refs=_source_structured_refs(case),
        blocked_state=case.status,
    )


def _duplicate_candidate(case: CarrierRejectionRemediationCase) -> ExceptionLakeCandidate:
    return ExceptionLakeCandidate(
        candidate_id=_stable_id("exc", f"{case.remediation_case_id}|duplicate"),
        run_id="carrier-rejection-reconciliation",
        preflight_packet_id=case.budget_proposal_id or "unknown-preflight",
        local_event_label="carrier_rejection_duplicate_notice",
        canonical_lake_class="workflow_escalation",
        reason=(
            "Multiple carrier notices share one idempotency key and were collapsed "
            "to one logical rejection while preserving all notice IDs."
        ),
        structured_refs=_source_structured_refs(case),
        blocked_state="duplicate_notice_review",
    )


def _appeal_candidate(
    bundle: CarrierRejectionCaptureSourceBundle,
    result: CarrierAppealResult,
    case: CarrierRejectionRemediationCase,
) -> ExceptionLakeCandidate:
    source_refs = [
        f"carrier-source://{ref.source_channel}/{ref.source_id}/{ref.source_record_id}"
        for ref in result.source_refs
    ]
    return ExceptionLakeCandidate(
        candidate_id=_stable_id("exc", f"{result.appeal_result_id}|appeal-result"),
        run_id=bundle.run_id,
        preflight_packet_id=bundle.preflight_packet_id,
        local_event_label="carrier_appeal_result_received",
        canonical_lake_class="workflow_escalation",
        reason=(f"Carrier appeal result was captured as append-only evidence: {result.result}."),
        structured_refs=[
            f"carrier-appeal-result://{result.appeal_result_id}",
            f"carrier-rejection-case://{case.remediation_case_id}",
            *source_refs,
        ],
        blocked_state="appeal_result_requires_review",
    )


def _learning_candidate(
    case: CarrierRejectionRemediationCase, bundle: CarrierRejectionCaptureSourceBundle
) -> ExceptionLakeCandidate:
    return ExceptionLakeCandidate(
        candidate_id=_stable_id("exc", f"{case.remediation_case_id}|learning"),
        run_id=bundle.run_id,
        preflight_packet_id=bundle.preflight_packet_id,
        local_event_label="carrier_rejection_learning_candidate",
        canonical_lake_class="workflow_escalation",
        reason=(
            "Carrier rejection outcome may support a reviewed future learning proposal; "
            "silent learning is prohibited."
        ),
        structured_refs=[
            f"carrier-rejection-case://{case.remediation_case_id}",
            "docs/carrier-rejection-learning-loop-roadmap.md#learning-loops",
        ],
        blocked_state="learning_requires_human_review",
    )


def _case_from_notice_group(
    key: str,
    notices: list[CarrierRejectionNotice],
    expected_by_submission: dict[str, CarrierExpectedResponse],
    bundle: CarrierRejectionCaptureSourceBundle,
) -> CarrierRejectionRemediationCase:
    primary = sorted(notices, key=lambda item: (item.status_timestamp, item.notice_id))[-1]
    linked = bool(primary.submission_id and primary.submission_id in expected_by_submission)
    expected = expected_by_submission.get(primary.submission_id or "")
    label = _label_for_notice(primary, linked)
    source_refs = [ref for notice in notices for ref in notice.source_refs]
    exposure = round(
        max(
            [
                primary.amount_disputed or 0,
                primary.amount_rejected or 0,
                (primary.amount_submitted or 0) - (primary.amount_allowed or 0),
                0,
            ]
        ),
        2,
    )
    return CarrierRejectionRemediationCase(
        remediation_case_id=_stable_id("carrierrejcase", f"{bundle.bundle_id}|{key}"),
        case_key=key,
        status=_status_for_label(label),
        local_event_label=label,
        canonical_lake_class=_canonical_class(label),  # type: ignore[arg-type]
        carrier_id=primary.carrier_id,
        submission_id=primary.submission_id,
        budget_proposal_id=primary.budget_proposal_id or bundle.budget_proposal_id,
        invoice_id=primary.invoice_id,
        phase_id=primary.phase_id,
        task_id=primary.task_id,
        external_code_candidate=primary.external_code_candidate,
        duplicate_notice_ids=sorted(notice.notice_id for notice in notices),
        source_refs=source_refs,
        disputed_amount=exposure,
        current_financial_exposure=exposure,
        human_owner=primary.human_owner or (expected.human_owner if expected else None),
        followup_due_at=primary.followup_due_at
        or (expected.expected_response_due_at if expected else None),
        required_human_decisions=[
            "confirm_rejection_class",
            "confirm_linked_submission",
            "confirm_fix_or_appeal_path",
            "confirm_financial_exposure",
        ],
        learning_disposition_candidates=_learning_candidates(label),
    )


def _missing_response_case(
    expected: CarrierExpectedResponse,
    bundle: CarrierRejectionCaptureSourceBundle,
) -> CarrierRejectionRemediationCase:
    label = "carrier_response_missing_after_sla"
    return CarrierRejectionRemediationCase(
        remediation_case_id=_stable_id(
            "carrierrejcase", f"{bundle.bundle_id}|{expected.submission_id}|missing"
        ),
        case_key=f"{expected.submission_id}|missing_response",
        status="missing_response_followup",
        local_event_label=label,
        canonical_lake_class="workflow_escalation",
        carrier_id=expected.carrier_id,
        submission_id=expected.submission_id,
        budget_proposal_id=expected.budget_proposal_id or bundle.budget_proposal_id,
        invoice_id=expected.invoice_id,
        disputed_amount=expected.amount_submitted or 0,
        current_financial_exposure=expected.amount_submitted or 0,
        human_owner=expected.human_owner,
        followup_due_at=expected.expected_response_due_at,
        required_human_decisions=[
            "confirm_response_still_missing",
            "assign_followup_owner",
            "decide_carrier_followup_path",
        ],
        learning_disposition_candidates=_learning_candidates(label),
    )


def _bind_synthetic_placeholders(value: object, budget: BudgetProposal) -> object:
    if isinstance(value, dict):
        replaced = {}
        for key, item in value.items():
            if key == "budget_proposal_id" and item == SYNTHETIC_BUDGET_ID_PLACEHOLDER:
                replaced[key] = budget.budget_proposal_id
            elif key == "preflight_packet_id" and item == SYNTHETIC_PREFLIGHT_ID_PLACEHOLDER:
                replaced[key] = budget.preflight_packet_id
            else:
                replaced[key] = _bind_synthetic_placeholders(item, budget)
        return replaced
    if isinstance(value, list):
        return [_bind_synthetic_placeholders(item, budget) for item in value]
    return value


def build_carrier_response_reconciliation_report(
    budget: BudgetProposal,
    bundle: CarrierRejectionCaptureSourceBundle,
) -> CarrierResponseReconciliationReport:
    if bundle.budget_proposal_id != budget.budget_proposal_id:
        raise ValueError("carrier rejection bundle budget_proposal_id does not match budget")
    if bundle.preflight_packet_id != budget.preflight_packet_id:
        raise ValueError("carrier rejection bundle preflight_packet_id does not match budget")

    expected_by_submission = {item.submission_id: item for item in bundle.expected_responses}
    notices_by_key: dict[str, list[CarrierRejectionNotice]] = defaultdict(list)
    for notice in bundle.notices:
        if notice.budget_proposal_id and notice.budget_proposal_id != budget.budget_proposal_id:
            raise ValueError("carrier rejection notice budget_proposal_id does not match budget")
        notices_by_key[_case_key_for_notice(notice)].append(notice)

    cases = [
        _case_from_notice_group(key, notices, expected_by_submission, bundle)
        for key, notices in sorted(notices_by_key.items())
    ]
    noticed_submission_ids = {
        notice.submission_id for notice in bundle.notices if notice.submission_id
    }
    as_of = _parse_time(bundle.as_of)
    for expected in bundle.expected_responses:
        if expected.submission_id in noticed_submission_ids:
            continue
        if _parse_time(expected.expected_response_due_at) < as_of:
            cases.append(_missing_response_case(expected, bundle))

    notice_to_case = {notice_id: case for case in cases for notice_id in case.duplicate_notice_ids}
    for result in bundle.appeal_results:
        case = notice_to_case.get(result.related_notice_id)
        if not case:
            continue
        case.linked_appeal_result_ids.append(result.appeal_result_id)
        case.status = "appeal_result_captured"

    candidates: list[ExceptionLakeCandidate] = []
    for case in cases:
        candidates.append(
            _candidate_for_case(case).model_copy(
                update={
                    "run_id": bundle.run_id,
                    "preflight_packet_id": bundle.preflight_packet_id,
                }
            )
        )
        if len(case.duplicate_notice_ids) > 1:
            candidates.append(
                _duplicate_candidate(case).model_copy(
                    update={
                        "run_id": bundle.run_id,
                        "preflight_packet_id": bundle.preflight_packet_id,
                    }
                )
            )
        if case.learning_disposition_candidates:
            candidates.append(_learning_candidate(case, bundle))
    for result in bundle.appeal_results:
        case = notice_to_case.get(result.related_notice_id)
        if case:
            candidates.append(_appeal_candidate(bundle, result, case))

    gaps = []
    for case in cases:
        if not case.human_owner:
            gaps.append(f"{case.remediation_case_id}: missing human owner")
        if not case.followup_due_at:
            gaps.append(f"{case.remediation_case_id}: missing follow-up due date")
    if not cases:
        status = "no_rejections_or_missing_responses"
    elif gaps:
        status = "blocked_missing_required_followup"
    else:
        status = "dry_run_ready_for_review"

    reconciled = len(
        {
            notice.submission_id
            for notice in bundle.notices
            if notice.submission_id and notice.submission_id in expected_by_submission
        }
    )
    return CarrierResponseReconciliationReport(
        reconciliation_report_id=_stable_id(
            "carrierrecon", f"{bundle.bundle_id}|{budget.budget_proposal_id}"
        ),
        source_bundle_id=bundle.bundle_id,
        run_id=bundle.run_id,
        preflight_packet_id=bundle.preflight_packet_id,
        budget_proposal_id=bundle.budget_proposal_id,
        status=status,
        expected_response_count=len(bundle.expected_responses),
        reconciled_response_count=reconciled,
        missing_response_count=sum(
            1 for case in cases if case.local_event_label == "carrier_response_missing_after_sla"
        ),
        unlinked_notice_count=sum(
            1 for case in cases if case.local_event_label == "carrier_rejection_unlinked"
        ),
        duplicate_notice_count=sum(max(0, len(case.duplicate_notice_ids) - 1) for case in cases),
        parser_failure_count=sum(
            1 for case in cases if case.local_event_label == "carrier_rejection_parse_failed"
        ),
        appeal_result_count=len(bundle.appeal_results),
        remediation_cases=cases,
        exception_lake_candidates=candidates,
        gap_report=gaps,
        generated_at=now_iso(),
    )


def run_carrier_rejection_capture(
    budget_path: str | Path,
    source_bundle_path: str | Path,
    out_dir: str | Path,
) -> tuple[CarrierResponseReconciliationReport, Path]:
    budget = BudgetProposal.model_validate(load_json(budget_path))
    raw_bundle = _bind_synthetic_placeholders(load_json(source_bundle_path), budget)
    bundle = CarrierRejectionCaptureSourceBundle.model_validate(raw_bundle)
    report = build_carrier_response_reconciliation_report(budget, bundle)

    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / "carrier_rejection_reconciliation_report.json"
    cases_path = run_dir / "carrier_rejection_remediation_cases.json"
    candidates_path = run_dir / "carrier_rejection_exception_lake_candidates.jsonl"
    ledger_path = run_dir / "run_ledger.jsonl"
    write_json(report_path, report.model_dump(mode="json"))
    write_json(
        cases_path,
        [case.model_dump(mode="json") for case in report.remediation_cases],
    )
    decision_ledger_report = build_carrier_rejection_decision_ledger_report(
        report=report,
        bundle=bundle,
    )
    write_carrier_rejection_decision_ledger_outputs(
        run_dir=run_dir,
        ledger_report=decision_ledger_report,
    )
    if candidates_path.exists():
        candidates_path.unlink()
    for candidate in report.exception_lake_candidates:
        append_jsonl(candidates_path, candidate.model_dump(mode="json"))
    append_jsonl(
        ledger_path,
        RunEvent(
            run_id=bundle.run_id,
            step_index=0,
            step_name="carrier_rejection_reconciliation_built",
            status="blocked" if report.status.startswith("blocked") else "completed",
            timestamp=now_iso(),
            input_refs=[str(budget_path), str(source_bundle_path)],
            output_refs=[
                str(report_path),
                str(cases_path),
                str(candidates_path),
                str(run_dir / CARRIER_REJECTION_DECISION_LEDGER_REPORT_FILENAME),
            ],
        ).model_dump(mode="json"),
    )
    return report, run_dir
