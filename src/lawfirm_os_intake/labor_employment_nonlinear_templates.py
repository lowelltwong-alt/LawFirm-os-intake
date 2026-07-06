from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentNonlinearTemplateAuditCheck,
    LaborEmploymentNonlinearTemplateAuditReport,
    LaborEmploymentNonlinearTemplateId,
    LaborEmploymentNonlinearTemplatePeriodDriver,
    LaborEmploymentNonlinearTemplateSpec,
    LaborEmploymentNonlinearTemplateSpecItem,
)
from .util import digest_json, load_json, now_iso, write_json


LABOR_EMPLOYMENT_NONLINEAR_TEMPLATE_REPORT_FILENAME = (
    "labor_employment_nonlinear_template_audit_report.json"
)
LABOR_EMPLOYMENT_NONLINEAR_TEMPLATE_NOTES_FILENAME = (
    "labor_employment_nonlinear_template_audit_report.md"
)
DEFAULT_LABOR_EMPLOYMENT_NONLINEAR_TEMPLATE_SPEC = (
    "examples/synthetic/labor-employment/labor-employment-nonlinear-budget-templates.json"
)

REQUIRED_TEMPLATE_IDS: tuple[LaborEmploymentNonlinearTemplateId, ...] = (
    "le-class-collective-defense",
    "le-paga-shaped-defense",
)
CLASS_PHASE_IDS = ("C100", "C200", "C300", "C400", "C500", "C600")
CLASS_TIERED_PHASE_IDS = ("C300", "C400", "C500", "C600")
PAGA_TIERED_PHASE_IDS = ("C300", "C400", "C500", "C600")
REQUIRED_TIERS = ("t0", "t1", "t2", "t3", "t4")
PERIOD_DRIVERS: tuple[LaborEmploymentNonlinearTemplatePeriodDriver, ...] = (
    "class_period_months",
    "paga_period_months",
)
REQUIRED_NEXT_GATES = [
    "human_labor_employment_template_selection_review",
    "no_amount_budget_from_nonlinear_template_contract",
    "budget_generator_must_consume_reviewed_template_contract_before_pricing",
    "no_lake_or_sqlite_write_from_nonlinear_template_audit",
]
SUCCESS_EXCEPTION_LABELS = [
    "labor_employment_nonlinear_template_contract_candidate",
    "labor_employment_class_collective_paga_template_review_candidate",
]
FAILURE_EXCEPTION_LABELS = SUCCESS_EXCEPTION_LABELS + [
    "labor_employment_nonlinear_template_contract_blocked",
]


def run_labor_employment_nonlinear_template_audit(
    *,
    template_spec_path: str | Path = DEFAULT_LABOR_EMPLOYMENT_NONLINEAR_TEMPLATE_SPEC,
    out_dir: str | Path,
) -> tuple[LaborEmploymentNonlinearTemplateAuditReport, Path]:
    spec_payload = load_json(template_spec_path)
    spec = LaborEmploymentNonlinearTemplateSpec.model_validate(spec_payload)
    checks = _checks(spec)
    failed_checks = [check for check in checks if check.status == "failed"]
    template_spec_hash = digest_json(spec_payload)
    report_core = {
        "template_spec_id": spec.template_spec_id,
        "template_spec_hash": template_spec_hash,
        "failed_checks": [check.check_id for check in failed_checks],
        "template_ids": [template.template_id for template in spec.templates],
    }
    phase_count = sum(len(template.phases) for template in spec.templates)
    task_count = sum(len(phase.tasks) for template in spec.templates for phase in template.phases)
    tier_block_count = sum(
        len(phase.tier_blocks) for template in spec.templates for phase in template.phases
    )
    period_driver_task_count = sum(
        1
        for template in spec.templates
        for phase in template.phases
        for task in phase.tasks
        if task.period_drivers
    )
    t4_staffing_block_count = sum(
        1
        for template in spec.templates
        for phase in template.phases
        for block in phase.tier_blocks
        if (
            block.tier_id == "t4"
            and block.action == "block_pending_staffing_plan"
            and block.blocker_id == "collective_scale_requires_staffing_plan"
        )
    )
    report = LaborEmploymentNonlinearTemplateAuditReport(
        nonlinear_template_audit_report_id="lenonlineartemplate_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 20],
        status=(
            "blocked_by_labor_employment_nonlinear_template_contract"
            if failed_checks
            else "labor_employment_nonlinear_templates_ready_for_review"
        ),
        template_spec_ref=str(template_spec_path),
        template_spec_id=spec.template_spec_id,
        template_spec_hash=template_spec_hash,
        template_count=len(spec.templates),
        phase_count=phase_count,
        task_count=task_count,
        tier_block_count=tier_block_count,
        period_driver_task_count=period_driver_task_count,
        t4_staffing_block_count=t4_staffing_block_count,
        failed_check_count=len(failed_checks),
        candidate_exception_lake_labels=(
            FAILURE_EXCEPTION_LABELS if failed_checks else SUCCESS_EXCEPTION_LABELS
        ),
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / LABOR_EMPLOYMENT_NONLINEAR_TEMPLATE_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / LABOR_EMPLOYMENT_NONLINEAR_TEMPLATE_NOTES_FILENAME).write_text(
        render_labor_employment_nonlinear_template_audit_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_labor_employment_nonlinear_template_audit_report(
    report: LaborEmploymentNonlinearTemplateAuditReport,
) -> str:
    failed = [check for check in report.checks if check.status == "failed"]
    lines = [
        "# Labor/Employment Nonlinear Template Audit Report",
        "",
        f"**Report ID:** {report.nonlinear_template_audit_report_id}",
        f"**Status:** {report.status}",
        f"**Template spec:** `{report.template_spec_ref}`",
        "",
        "## Boundary",
        "",
        "- Candidate-only and synthetic-only.",
        "- No dollar amounts, real rates, budget submission, matter opening, or Lake/SQLite writes.",
        "- Class/collective/PAGA template selection remains human-reviewed.",
        "",
        "## Summary",
        "",
        f"- Templates: {report.template_count}",
        f"- Phases: {report.phase_count}",
        f"- Tasks: {report.task_count}",
        f"- Tier blocks: {report.tier_block_count}",
        f"- Period-driver tasks: {report.period_driver_task_count}",
        f"- T4 staffing blocks: {report.t4_staffing_block_count}",
        f"- Failed checks: {report.failed_check_count}",
        "",
        "## Failed Checks",
        "",
    ]
    if failed:
        lines.extend(f"- `{check.check_id}`: {check.message}" for check in failed)
    else:
        lines.append("- None.")
    lines.extend(
        [
            "",
            "## Required Next Gates",
            "",
            *(f"- `{gate}`" for gate in report.required_next_gates),
            "",
        ]
    )
    return "\n".join(lines)


def _checks(
    spec: LaborEmploymentNonlinearTemplateSpec,
) -> list[LaborEmploymentNonlinearTemplateAuditCheck]:
    checks = [
        _required_templates_check(spec),
        _global_boundary_check(spec),
    ]
    templates = {template.template_id: template for template in spec.templates}
    class_template = templates.get("le-class-collective-defense")
    paga_template = templates.get("le-paga-shaped-defense")
    if class_template is not None:
        checks.extend(_class_collective_checks(class_template))
    if paga_template is not None:
        checks.extend(_paga_checks(paga_template))
    for template in spec.templates:
        checks.extend(_shared_template_checks(template))
    return checks


def _required_templates_check(
    spec: LaborEmploymentNonlinearTemplateSpec,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    template_ids = {template.template_id for template in spec.templates}
    missing = sorted(set(REQUIRED_TEMPLATE_IDS) - template_ids)
    undeclared = sorted(template_ids - set(spec.required_template_ids))
    if missing or undeclared:
        details = []
        if missing:
            details.append(f"missing templates: {', '.join(missing)}")
        if undeclared:
            details.append(f"templates not listed as required: {', '.join(undeclared)}")
        return _failed(
            "required_template_ids_present",
            "; ".join(details),
            blocking_refs=missing + undeclared,
        )
    return _passed(
        "required_template_ids_present",
        "Required class/collective and PAGA template contracts are present.",
        evidence_refs=sorted(template_ids),
    )


def _global_boundary_check(
    spec: LaborEmploymentNonlinearTemplateSpec,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    if not (
        spec.no_budget_amounts_declared
        and spec.no_real_rates_declared
        and spec.no_external_writes_allowed
        and spec.no_lake_or_sqlite_writes_allowed
        and spec.no_budget_submission_allowed
        and spec.no_matter_opening_allowed
        and spec.calibration_authorized is False
    ):
        return _failed(
            "nonlinear_template_contract_boundary",
            "Template spec must remain synthetic, no-amount, no-rate, no-write, and no-calibration.",
        )
    return _passed(
        "nonlinear_template_contract_boundary",
        "Template spec declares no amounts, no rates, no writes, no submission, and no calibration.",
    )


def _class_collective_checks(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> list[LaborEmploymentNonlinearTemplateAuditCheck]:
    return [
        _phase_skeleton_check(
            template,
            required_phase_ids=CLASS_PHASE_IDS,
            check_id="class_collective_c_phase_skeleton",
        ),
        _tier_rows_check(
            template,
            required_phase_ids=CLASS_TIERED_PHASE_IDS,
            check_id="class_collective_tier_rows_complete",
        ),
        _scenario_gate_check(
            template,
            driver_id="certification_posture",
            required_blocker_id="certification_scenario_requires_human_selection",
            check_id="class_collective_certification_scenario_gate",
        ),
        _hybrid_selection_check(template),
    ]


def _paga_checks(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> list[LaborEmploymentNonlinearTemplateAuditCheck]:
    return [
        _phase_skeleton_check(
            template,
            required_phase_ids=CLASS_PHASE_IDS,
            check_id="paga_c_phase_skeleton",
        ),
        _tier_rows_check(
            template,
            required_phase_ids=PAGA_TIERED_PHASE_IDS,
            check_id="paga_tier_rows_complete",
        ),
        _paga_no_opt_in_task_check(template),
        _paga_manageability_gate_check(template),
        _paga_period_and_penalty_exclusion_check(template),
        _hybrid_selection_check(template),
    ]


def _shared_template_checks(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> list[LaborEmploymentNonlinearTemplateAuditCheck]:
    return [
        _no_interpolation_check(template),
        _period_driver_scope_check(template),
        _t4_staffing_block_check(template),
    ]


def _phase_skeleton_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
    *,
    required_phase_ids: tuple[str, ...],
    check_id: str,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    phase_ids = [
        phase.phase_id for phase in sorted(template.phases, key=lambda phase: phase.phase_order)
    ]
    missing = [phase_id for phase_id in required_phase_ids if phase_id not in phase_ids]
    expected_positions = {
        phase_id: index for index, phase_id in enumerate(required_phase_ids, start=1)
    }
    out_of_order = [
        phase.phase_id
        for phase in template.phases
        if phase.phase_id in expected_positions
        and phase.phase_order != expected_positions[phase.phase_id]
    ]
    if missing or out_of_order:
        return _failed(
            check_id,
            "C100-C600 phase skeleton is missing or out of order.",
            template_id=template.template_id,
            blocking_refs=missing + out_of_order,
        )
    return _passed(
        check_id,
        "C100-C600 phase skeleton is present in order.",
        template_id=template.template_id,
        evidence_refs=list(required_phase_ids),
    )


def _tier_rows_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
    *,
    required_phase_ids: tuple[str, ...],
    check_id: str,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    phase_map = {phase.phase_id: phase for phase in template.phases}
    missing_refs: list[str] = []
    for phase_id in required_phase_ids:
        phase = phase_map.get(phase_id)
        if phase is None:
            missing_refs.append(f"{phase_id}:missing_phase")
            continue
        block_tiers = {block.tier_id for block in phase.tier_blocks}
        for tier_id in REQUIRED_TIERS:
            if tier_id not in block_tiers:
                missing_refs.append(f"{phase_id}:{tier_id}")
    if missing_refs:
        return _failed(
            check_id,
            "Tiered phases must declare t0-t4 rows; missing rows block instead of falling back.",
            template_id=template.template_id,
            blocking_refs=missing_refs,
        )
    return _passed(
        check_id,
        "Tiered phases declare every t0-t4 row.",
        template_id=template.template_id,
        evidence_refs=[
            f"{phase_id}:{tier_id}" for phase_id in required_phase_ids for tier_id in REQUIRED_TIERS
        ],
    )


def _scenario_gate_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
    *,
    driver_id: str,
    required_blocker_id: str,
    check_id: str,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    gates = [gate for gate in template.scenario_gates if gate.driver_id == driver_id]
    if not gates:
        return _failed(
            check_id,
            f"Template requires a human-reviewed {driver_id} scenario gate.",
            template_id=template.template_id,
            blocking_refs=[driver_id],
        )
    failed_refs = [
        gate.gate_id
        for gate in gates
        if not (
            gate.all_scenarios_emitted
            and gate.human_selection_required
            and gate.blocks_auto_selection
            and required_blocker_id in gate.blocker_ids
        )
    ]
    if failed_refs:
        return _failed(
            check_id,
            f"{driver_id} gate must emit all scenarios and require human selection.",
            template_id=template.template_id,
            blocking_refs=failed_refs,
        )
    return _passed(
        check_id,
        f"{driver_id} gate emits all scenarios and blocks automatic selection.",
        template_id=template.template_id,
        evidence_refs=[gate.gate_id for gate in gates],
    )


def _paga_no_opt_in_task_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    opt_in_refs = [
        task.task_id
        for phase in template.phases
        for task in phase.tasks
        if task.opt_in_sensitive
        or _contains_token(task.task_id, "opt_in")
        or _contains_token(task.label, "opt-in")
    ]
    if opt_in_refs:
        return _failed(
            "paga_template_excludes_opt_in_tasks",
            "PAGA-shaped template must not include opt-in administration tasks.",
            template_id=template.template_id,
            blocking_refs=opt_in_refs,
        )
    return _passed(
        "paga_template_excludes_opt_in_tasks",
        "PAGA-shaped template excludes opt-in administration tasks.",
        template_id=template.template_id,
    )


def _paga_manageability_gate_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    manageability_tasks = [
        task.task_id
        for phase in template.phases
        for task in phase.tasks
        if "manageability" in task.tags or _contains_token(task.label, "manageability")
    ]
    gate_check = _scenario_gate_check(
        template,
        driver_id="manageability_posture",
        required_blocker_id="manageability_scenario_requires_human_selection",
        check_id="paga_manageability_scenario_gate",
    )
    if gate_check.status == "failed":
        return gate_check
    if not manageability_tasks:
        return _failed(
            "paga_manageability_scenario_gate",
            "PAGA-shaped template requires manageability motion/scenario tasks.",
            template_id=template.template_id,
            blocking_refs=["manageability_task"],
        )
    return _passed(
        "paga_manageability_scenario_gate",
        "PAGA-shaped template includes manageability tasks and scenario gate.",
        template_id=template.template_id,
        evidence_refs=manageability_tasks + gate_check.evidence_refs,
    )


def _paga_period_and_penalty_exclusion_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    period_tasks = [
        task.task_id
        for phase in template.phases
        for task in phase.tasks
        if "paga_period_months" in task.period_drivers and task.data_scope_task
    ]
    penalty_failures = [
        task.task_id
        for phase in template.phases
        for task in phase.tasks
        if _is_penalty_or_exposure_task(task.task_id, task.label, task.tags)
        and (task.money_amount_allowed or task.exposure_modeling_allowed)
    ]
    if not period_tasks or penalty_failures:
        blocking_refs = list(penalty_failures)
        if not period_tasks:
            blocking_refs.append("paga_period_data_scope_task")
        return _failed(
            "paga_period_scope_and_penalty_exclusion",
            "PAGA period drivers must be data-scope only, and penalty/exposure tasks cannot model money.",
            template_id=template.template_id,
            blocking_refs=blocking_refs,
        )
    return _passed(
        "paga_period_scope_and_penalty_exclusion",
        "PAGA period scope is limited to data tasks and penalty/exposure modeling is excluded.",
        template_id=template.template_id,
        evidence_refs=period_tasks,
    )


def _hybrid_selection_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    gates = [gate for gate in template.scenario_gates if gate.driver_id == "template_selection"]
    if not (
        template.hybrid_template_selection_requires_human
        and gates
        and all(
            gate.all_scenarios_emitted
            and gate.human_selection_required
            and "hybrid_paga_class_requires_primary_template_selection" in gate.blocker_ids
            for gate in gates
        )
    ):
        return _failed(
            "hybrid_paga_class_template_selection_gate",
            "Hybrid PAGA/class posture requires explicit human primary-template selection.",
            template_id=template.template_id,
            blocking_refs=[gate.gate_id for gate in gates] or ["template_selection"],
        )
    return _passed(
        "hybrid_paga_class_template_selection_gate",
        "Hybrid PAGA/class posture blocks automatic template merging.",
        template_id=template.template_id,
        evidence_refs=[gate.gate_id for gate in gates],
    )


def _no_interpolation_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    interpolated = [
        f"{phase.phase_id}:{block.tier_id}"
        for phase in template.phases
        for block in phase.tier_blocks
        if block.interpolation_allowed
    ]
    if interpolated:
        return _failed(
            "no_cross_tier_interpolation",
            "Tier tables must not interpolate across rows.",
            template_id=template.template_id,
            blocking_refs=interpolated,
        )
    return _passed(
        "no_cross_tier_interpolation",
        "Tier tables prohibit cross-tier interpolation.",
        template_id=template.template_id,
    )


def _period_driver_scope_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    violations = [
        task.task_id
        for phase in template.phases
        for task in phase.tasks
        if any(driver in PERIOD_DRIVERS for driver in task.period_drivers)
        and not task.data_scope_task
    ]
    if violations:
        return _failed(
            "period_drivers_are_data_scope_only",
            "class_period_months and paga_period_months may affect only data-scope tasks.",
            template_id=template.template_id,
            blocking_refs=violations,
        )
    return _passed(
        "period_drivers_are_data_scope_only",
        "Period drivers are limited to data-scope tasks.",
        template_id=template.template_id,
    )


def _t4_staffing_block_check(
    template: LaborEmploymentNonlinearTemplateSpecItem,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    phase_map = {phase.phase_id: phase for phase in template.phases}
    failures = []
    evidence_refs = []
    for phase_id in template.tiered_phase_ids:
        phase = phase_map.get(phase_id)
        if phase is None:
            failures.append(f"{phase_id}:missing_phase")
            continue
        t4_blocks = [block for block in phase.tier_blocks if block.tier_id == "t4"]
        if not t4_blocks:
            failures.append(f"{phase_id}:t4")
            continue
        t4_block = t4_blocks[0]
        if not (
            t4_block.action == "block_pending_staffing_plan"
            and t4_block.blocker_id == "collective_scale_requires_staffing_plan"
        ):
            failures.append(f"{phase_id}:t4")
        else:
            evidence_refs.append(f"{phase_id}:t4")
    if failures:
        return _failed(
            "t4_collective_scale_requires_staffing_plan",
            "Resolved t4 collective scale must block pending a human staffing plan.",
            template_id=template.template_id,
            blocking_refs=failures,
        )
    return _passed(
        "t4_collective_scale_requires_staffing_plan",
        "Every tiered phase has t4 staffing-plan block.",
        template_id=template.template_id,
        evidence_refs=evidence_refs,
    )


def _is_penalty_or_exposure_task(task_id: str, label: str, tags: list[str]) -> bool:
    searchable = [task_id, label, *tags]
    return any(
        _contains_token(value, "penalty") or _contains_token(value, "exposure")
        for value in searchable
    )


def _contains_token(value: str, token: str) -> bool:
    normalized = value.lower().replace("-", "_").replace(" ", "_")
    return token.lower().replace("-", "_") in normalized


def _passed(
    check_id: str,
    message: str,
    *,
    template_id: LaborEmploymentNonlinearTemplateId | None = None,
    evidence_refs: list[str] | None = None,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    return LaborEmploymentNonlinearTemplateAuditCheck(
        check_id=check_id,
        status="passed",
        message=message,
        template_id=template_id,
        evidence_refs=evidence_refs or [],
    )


def _failed(
    check_id: str,
    message: str,
    *,
    template_id: LaborEmploymentNonlinearTemplateId | None = None,
    blocking_refs: list[str] | None = None,
) -> LaborEmploymentNonlinearTemplateAuditCheck:
    return LaborEmploymentNonlinearTemplateAuditCheck(
        check_id=check_id,
        status="failed",
        message=message,
        template_id=template_id,
        blocking_refs=blocking_refs or [],
    )
