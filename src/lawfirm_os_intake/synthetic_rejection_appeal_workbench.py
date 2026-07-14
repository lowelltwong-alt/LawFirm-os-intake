"""Read-only synthetic rejection, appeal, and learning review workbench."""

from __future__ import annotations

from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile

from .carrier_rejection_learning import run_carrier_rejection_learning
from .carrier_rejection_review import run_carrier_rejection_review
from .carrier_rejections import run_carrier_rejection_capture
from .models import (
    CarrierRejectionDecisionLedgerReport,
    SyntheticRejectionAppealWorkbenchCase,
    SyntheticRejectionAppealWorkbenchCheck,
    SyntheticRejectionAppealWorkbenchReport,
)
from .util import digest_json, digest_text, load_json, now_iso, write_json

REPORT_FILENAME = "synthetic_rejection_appeal_workbench_report.json"
MARKDOWN_FILENAME = "synthetic_rejection_appeal_workbench.md"
WORKBOOK_FILENAME = "synthetic_rejection_appeal_workbench.xlsx"
BUDGET_REF = "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/legal_budget_proposal.json"
BUNDLE_REF = "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/carrier_rejection_capture_source_bundle_with_appeal_results.json"


def _check(check_id: str, passed: bool, message: str, *refs: str):
    return SyntheticRejectionAppealWorkbenchCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=list(refs),
    )


def _safe_text(value: str) -> str:
    """Prevent synthetic fixture text from being interpreted as a spreadsheet formula."""
    return f"'{value}" if value.startswith(("=", "+", "-", "@")) else value


def build_synthetic_rejection_appeal_workbench_report(
    *, repo_root: str | Path, generated_at: str | None = None
) -> SyntheticRejectionAppealWorkbenchReport:
    root = Path(repo_root)
    generated = generated_at or now_iso()
    budget_path, bundle_path = root / BUDGET_REF, root / BUNDLE_REF
    with TemporaryDirectory(prefix="lawfirm-os-intake-rejection-") as temporary:
        capture, capture_dir = run_carrier_rejection_capture(
            budget_path, bundle_path, Path(temporary) / "capture"
        )
        review, review_dir = run_carrier_rejection_review(
            capture_dir / "carrier_rejection_reconciliation_report.json", Path(temporary) / "review"
        )
        learning, _ = run_carrier_rejection_learning(
            review_dir / "carrier_rejection_review_packet.json", Path(temporary) / "learning"
        )
        ledger = CarrierRejectionDecisionLedgerReport.model_validate(
            load_json(capture_dir / "carrier_rejection_decision_ledger_report.json")
        )
    # The underlying workflow records current time and a temporary review location.
    # Normalize those transport details so a pinned synthetic replay is reproducible.
    capture = capture.model_copy(update={"generated_at": generated})
    review = review.model_copy(
        update={
            "generated_at": generated,
            "human_readable_review_ref": "synthetic-rejection-appeal-workbench://review-notes",
        }
    )
    learning = learning.model_copy(update={"generated_at": generated})
    ledger = ledger.model_copy(update={"generated_at": generated})
    recommendation_by_case = {item.remediation_case_id: item for item in review.recommendations}
    events_by_case = {}
    for event in ledger.events:
        if event.remediation_case_id:
            events_by_case.setdefault(event.remediation_case_id, []).append(event)
    cases = []
    for case in capture.remediation_cases:
        recommendation = recommendation_by_case[case.remediation_case_id]
        events = events_by_case.get(case.remediation_case_id, [])
        appeal_events = [event for event in events if event.appeal_result_id]
        learning_ids = [
            proposal.proposal_id
            for proposal in learning.proposals
            if case.remediation_case_id in proposal.remediation_case_ids
        ]
        cases.append(
            SyntheticRejectionAppealWorkbenchCase(
                remediation_case_id=case.remediation_case_id,
                local_event_label=case.local_event_label,
                status=case.status,
                recommended_action=recommendation.recommended_action,
                priority=recommendation.priority,
                disputed_amount=case.disputed_amount,
                current_financial_exposure=case.current_financial_exposure,
                notice_ids=case.duplicate_notice_ids,
                source_ref_count=len(case.source_refs),
                appeal_result_ids=case.linked_appeal_result_ids,
                appeal_results=sorted(
                    {event.appeal_result or "unknown" for event in appeal_events}
                ),
                recovered_amount=round(sum(event.recovered_amount for event in appeal_events), 2),
                write_down_amount=round(sum(event.write_down_amount for event in appeal_events), 2),
                pending_human_decisions=recommendation.required_human_decisions,
                learning_proposal_ids=learning_ids,
                candidate_exception_lake_ids=recommendation.exception_candidate_ids,
            )
        )
    checks = [
        _check(
            "source_hashes_present",
            budget_path.is_file() and bundle_path.is_file(),
            "Pinned synthetic proposal and rejection bundle must exist.",
            BUDGET_REF,
            BUNDLE_REF,
        ),
        _check(
            "case_recommendation_join_complete",
            len(cases) == len(capture.remediation_cases)
            and all(item.source_ref_count > 0 for item in cases),
            "Every captured case must have source-bound review evidence.",
        ),
        _check(
            "appeal_financial_partition_reconciles",
            ledger.total_recovered_amount + ledger.total_write_down_amount
            <= ledger.total_disputed_amount,
            "Recovered and write-down amounts cannot exceed disputed amount.",
        ),
        _check(
            "learning_remains_human_gated",
            all(
                proposal.human_review_required
                and proposal.shadow_eval_required
                and not proposal.silent_learning_performed
                for proposal in learning.proposals
            ),
            "Learning proposals remain candidates pending human review and shadow evaluation.",
        ),
        _check(
            "no_submission_or_lake_write",
            not ledger.appeal_submission_performed
            and not ledger.lake_write_performed
            and not ledger.external_writes_performed,
            "The workbench cannot submit appeals or write to the Lake.",
        ),
    ]
    failed = sum(item.status == "failed" for item in checks)
    basis = {
        "budget": digest_text(budget_path.read_text(encoding="utf-8")),
        "bundle": digest_text(bundle_path.read_text(encoding="utf-8")),
        "case_ids": [item.remediation_case_id for item in cases],
    }
    return SyntheticRejectionAppealWorkbenchReport(
        synthetic_rejection_appeal_workbench_report_id="synrejectionappeal-"
        + digest_json(basis).removeprefix("sha256:")[:16],
        status="synthetic_rejection_appeal_workbench_ready_for_review"
        if not failed
        else "blocked_by_synthetic_rejection_appeal_workbench",
        budget_proposal_id=capture.budget_proposal_id,
        budget_proposal_sha256=digest_text(budget_path.read_text(encoding="utf-8")),
        source_bundle_ref=BUNDLE_REF,
        source_bundle_sha256=digest_text(bundle_path.read_text(encoding="utf-8")),
        reconciliation_report=capture,
        decision_ledger=ledger,
        review_packet=review,
        learning_report=learning,
        cases=cases,
        total_disputed_amount=ledger.total_disputed_amount,
        total_recovered_amount=ledger.total_recovered_amount,
        total_write_down_amount=ledger.total_write_down_amount,
        checks=checks,
        failed_check_count=failed,
        workbook_filename=WORKBOOK_FILENAME,
        markdown_filename=MARKDOWN_FILENAME,
        display_banner={
            "summary": "Synthetic rejection and appeal review evidence only. No appeal is submitted and no learning is applied.",
            "candidate_only": True,
            "synthetic_only": True,
            "read_only_ui": True,
            "blocked_actions": [
                "appeal_submission",
                "budget_mutation",
                "exception_lake_write",
                "sqlite_write",
                "silent_learning",
            ],
        },
        candidate_exception_lake_labels=[
            "carrier_rejection_review_candidate",
            "carrier_appeal_result_review_candidate",
            "carrier_rejection_learning_candidate",
        ],
        required_next_gates=[
            "human_rejection_decision_review",
            "orchestrator_owned_appeal_submission_if_approved",
            "exception_lake_admission_by_owner",
            "reviewed_learning_gate_before_candidate_change",
        ],
        generated_at=generated,
    )


def run_synthetic_rejection_appeal_workbench(
    *, repo_root: str | Path, out_dir: str | Path, generated_at: str | None = None
):
    report = build_synthetic_rejection_appeal_workbench_report(
        repo_root=repo_root, generated_at=generated_at
    )
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / REPORT_FILENAME, report.model_dump(mode="json"))
    (target / MARKDOWN_FILENAME).write_text(
        "# Synthetic Rejection And Appeal Workbench\n\n" + report.display_banner["summary"] + "\n",
        encoding="utf-8",
    )
    if report.status.endswith("ready_for_review"):
        from openpyxl import Workbook

        book = Workbook()
        sheet = book.active
        sheet.title = "Rejections"
        sheet.append(["Synthetic candidate-only review. No appeal submission or Lake write."])
        sheet.append(
            ["Case", "Label", "Action", "Disputed", "Recovered", "Write-down", "Appeal Results"]
        )
        for item in report.cases:
            sheet.append(
                [
                    _safe_text(item.remediation_case_id),
                    _safe_text(item.local_event_label),
                    _safe_text(item.recommended_action),
                    item.disputed_amount,
                    item.recovered_amount,
                    item.write_down_amount,
                    _safe_text(" | ".join(item.appeal_results)),
                ]
            )
        book.save(target / WORKBOOK_FILENAME)
        with ZipFile(target / WORKBOOK_FILENAME) as archive:
            if any("vbaProject" in name or "externalLinks/" in name for name in archive.namelist()):
                raise ValueError("active workbook content prohibited")
    return report, target
