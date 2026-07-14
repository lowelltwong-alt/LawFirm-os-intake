"""Deterministic synthetic EPLI actuals-versus-budget workbench artifacts."""

from __future__ import annotations

from pathlib import Path

from .budget_actuals import build_budget_actual_comparison_report
from .models import (
    BudgetActualsSource,
    BudgetProposal,
    SyntheticActualsWorkbenchCheck,
    SyntheticActualsWorkbenchReport,
)
from .util import digest_json, digest_text, load_json, now_iso, write_json

SYNTHETIC_ACTUALS_WORKBENCH_REPORT_FILENAME = "synthetic_actuals_workbench_report.json"
SYNTHETIC_ACTUALS_WORKBENCH_MARKDOWN_FILENAME = "synthetic_actuals_workbench.md"
METHODOLOGY_VERSION = "synthetic_actuals_workbench.v0_1"
BUDGET_PROPOSAL_REF = (
    "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/"
    "legal_budget_proposal.json"
)
ACTUALS_SOURCE_REF = (
    "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/"
    "budget_actuals_source.json"
)


def _check(check_id: str, passed: bool, message: str, *refs: str) -> SyntheticActualsWorkbenchCheck:
    return SyntheticActualsWorkbenchCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=[ref for ref in refs if ref],
    )


def _total(rows: list[object], field: str) -> float:
    return round(sum(float(getattr(row, field) or 0) for row in rows), 2)


def build_synthetic_actuals_workbench_report(
    *,
    repo_root: str | Path,
    generated_at: str | None = None,
) -> SyntheticActualsWorkbenchReport:
    """Build a fixed-source EPLI actuals review packet for local UI evidence.

    The phase and code views are alternate mappings of the same synthetic outcome.
    They are reconciled independently and are never added together.
    """

    root = Path(repo_root)
    return _build_synthetic_actuals_workbench_report(
        budget_path=root / BUDGET_PROPOSAL_REF,
        actuals_path=root / ACTUALS_SOURCE_REF,
        generated_at=generated_at,
    )


def _build_synthetic_actuals_workbench_report(
    *,
    budget_path: Path,
    actuals_path: Path,
    generated_at: str | None = None,
) -> SyntheticActualsWorkbenchReport:
    """Build the report from supplied paths for deterministic hostile-fixture tests.

    The public CLI deliberately only uses the fixed synthetic EPLI paths above.
    """

    budget_text = budget_path.read_text(encoding="utf-8")
    actuals_text = actuals_path.read_text(encoding="utf-8")
    budget = BudgetProposal.model_validate(load_json(budget_path))
    actuals = BudgetActualsSource.model_validate(load_json(actuals_path))
    generated = generated_at or now_iso()
    comparison = build_budget_actual_comparison_report(
        run_id="syntheticactualsworkbench-epli-carrier-clean-v0-1",
        comparison_report_id="syntheticactualcomparison-epli-carrier-clean-v0-1",
        preflight_packet_id=budget.preflight_packet_id,
        budget=budget,
        actuals_by_phase=actuals.actuals_by_phase,
        actuals_by_code=actuals.actuals_by_code,
        actuals_source_ref=actuals.source_ref or ACTUALS_SOURCE_REF,
        actual_resolution_scenario_id=actuals.actual_resolution_scenario_id,
    ).model_copy(update={"generated_at": generated})
    # The comparison builder is also used for runtime candidate packets and gives
    # variance drivers fresh IDs. Checked UI evidence must be byte-stable, so bind
    # those IDs to the observable driver payload before hashing this local packet.
    stable_drivers = []
    for driver in comparison.variance_driver_candidates:
        driver_basis = driver.model_dump(mode="json", exclude={"candidate_id"})
        stable_drivers.append(
            driver.model_copy(
                update={
                    "candidate_id": (
                        "synactualdriver-" + digest_json(driver_basis).removeprefix("sha256:")[:16]
                    )
                }
            )
        )
    comparison = comparison.model_copy(update={"variance_driver_candidates": stable_drivers})
    phases = comparison.phase_comparisons
    codes = comparison.code_comparisons
    phase_budgeted_total = _total(phases, "budgeted_total")
    phase_actual_total = _total(phases, "actual_total")
    code_budgeted_total = _total(codes, "budgeted_total")
    code_actual_total = _total(codes, "actual_total")
    checks = [
        _check(
            "synthetic_actuals_source_boundary",
            actuals.data_origin == "synthetic"
            and actuals.contains_real_client_data is False
            and actuals.contains_real_matter_data is False
            and actuals.contains_privileged_data is False
            and actuals.billing_connector_read_performed is False
            and actuals.billing_connector_write_performed is False
            and actuals.external_writes_performed is False
            and actuals.non_authoritative is True,
            "Actuals source must be synthetic, non-authoritative, and connector-free.",
            ACTUALS_SOURCE_REF,
        ),
        _check(
            "phase_and_code_views_present",
            comparison.comparison_scope == "phase_and_code" and bool(phases) and bool(codes),
            "The workbench requires non-empty alternate phase and code comparison views.",
            BUDGET_PROPOSAL_REF,
            ACTUALS_SOURCE_REF,
        ),
        _check(
            "original_budget_baseline_declared",
            comparison.comparison_budget_state == "original_proposal"
            and comparison.budget_revision_report_id is None
            and comparison.budget_revision_report_ref is None,
            "The fixed EPLI workbench must disclose an original-proposal baseline.",
            BUDGET_PROPOSAL_REF,
        ),
        _check(
            "phase_budget_total_reconciles",
            phase_budgeted_total == comparison.total_budgeted,
            "Phase budget totals must equal the displayed comparison budget total.",
        ),
        _check(
            "phase_actual_total_reconciles",
            phase_actual_total == comparison.total_actual,
            "Phase actual totals must equal the displayed comparison actual total.",
        ),
        _check(
            "code_budget_total_reconciles",
            code_budgeted_total == comparison.total_budgeted,
            "Code budget totals must independently equal the comparison budget total.",
        ),
        _check(
            "code_actual_total_reconciles",
            code_actual_total == comparison.total_actual,
            "Code actual totals must independently equal the comparison actual total.",
        ),
        _check(
            "complete_actuals_coverage",
            all(row.actual_total is not None for row in phases)
            and all(row.actual_total is not None for row in codes),
            "Every displayed phase and code row must have an actual amount; partial feeds are blocked.",
            ACTUALS_SOURCE_REF,
        ),
        _check(
            "no_unbudgeted_actuals",
            not any(
                row.status == "over_threshold" and row.budgeted_total == 0
                for row in [*phases, *codes]
            ),
            "Unbudgeted actuals require a distinct human-review path and cannot appear ready.",
            ACTUALS_SOURCE_REF,
        ),
        _check(
            "review_pending_variance",
            comparison.status == "variance_review_required"
            and any(row.status == "over_threshold" for row in [*phases, *codes])
            and all(row.requires_human_review for row in [*phases, *codes]),
            "Synthetic over-threshold variance must remain human-review pending.",
        ),
        _check(
            "no_auto_learning_or_runtime_write",
            comparison.actuals_are_synthetic is True
            and comparison.billing_connector_read_performed is False
            and comparison.billing_connector_write_performed is False
            and comparison.external_writes_performed is False
            and all(
                driver.silent_learning_performed is False
                for driver in comparison.variance_driver_candidates
            ),
            "Comparison must not read billing systems, write externally, or learn silently.",
        ),
    ]
    failed_check_count = sum(check.status == "failed" for check in checks)
    report_basis = {
        "budget_proposal_sha256": digest_text(budget_text),
        "actuals_source_sha256": digest_text(actuals_text),
        "comparison": comparison.model_dump(mode="json"),
        "methodology_version": METHODOLOGY_VERSION,
    }
    return SyntheticActualsWorkbenchReport(
        synthetic_actuals_workbench_report_id=(
            "synactualsworkbench-" + digest_json(report_basis).removeprefix("sha256:")[:16]
        ),
        status=(
            "synthetic_actuals_workbench_ready_for_review"
            if failed_check_count == 0
            else "blocked_by_synthetic_actuals_workbench"
        ),
        budget_proposal_ref=BUDGET_PROPOSAL_REF,
        budget_proposal_sha256=digest_text(budget_text),
        actuals_source_id=actuals.actuals_source_id,
        actuals_source_ref=ACTUALS_SOURCE_REF,
        actuals_source_sha256=digest_text(actuals_text),
        comparison=comparison,
        phase_budgeted_total=phase_budgeted_total,
        phase_actual_total=phase_actual_total,
        code_budgeted_total=code_budgeted_total,
        code_actual_total=code_actual_total,
        phase_row_count=len(phases),
        code_row_count=len(codes),
        checks=checks,
        failed_check_count=failed_check_count,
        display_banner={
            "summary": (
                "Synthetic actuals versus candidate budget only. Phase and code totals are "
                "alternate reconciled views and must never be added together."
            ),
            "synthetic_only": True,
            "candidate_only": True,
            "human_review_required": True,
            "blocked_actions": [
                "production_billing_inference",
                "automatic_budget_calibration",
                "profile_or_template_mutation",
                "exception_lake_write",
                "budget_submission",
                "matter_opening",
            ],
        },
        candidate_exception_lake_labels=[
            "labor_employment_actual_variance_candidate",
            "synthetic_actuals_variance_review_candidate",
        ],
        required_next_gates=[
            "human_actuals_variance_review",
            "reviewed_learning_gate_before_candidate_changes",
            "exception_lake_owner_review_before_admission",
        ],
        generated_at=generated,
    )


def _render_markdown(report: SyntheticActualsWorkbenchReport) -> str:
    comparison = report.comparison
    lines = [
        "# Synthetic Actuals Workbench",
        "",
        report.display_banner["summary"],
        "",
        f"- Budget source: `{report.budget_proposal_ref}` ({report.budget_proposal_sha256})",
        f"- Actuals source: `{report.actuals_source_ref}` ({report.actuals_source_sha256})",
        f"- Actuals source ID: `{report.actuals_source_id}`",
        f"- Comparison state: `{comparison.comparison_budget_state}`",
        f"- Budget total: `{comparison.total_budgeted}`",
        f"- Actual total: `{comparison.total_actual}`",
        f"- Variance: `{comparison.total_variance_amount}` ({comparison.total_variance_percent}%)",
        "",
        "## Checks",
        "",
    ]
    lines.extend(
        f"- `{check.status}` `{check.check_id}`: {check.message}" for check in report.checks
    )
    return "\n".join(lines) + "\n"


def run_synthetic_actuals_workbench(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[SyntheticActualsWorkbenchReport, Path]:
    report = build_synthetic_actuals_workbench_report(
        repo_root=repo_root,
        generated_at=generated_at,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / SYNTHETIC_ACTUALS_WORKBENCH_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / SYNTHETIC_ACTUALS_WORKBENCH_MARKDOWN_FILENAME).write_text(
        _render_markdown(report), encoding="utf-8"
    )
    return report, run_dir
