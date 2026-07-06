import copy

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_nonlinear_templates import (
    LABOR_EMPLOYMENT_NONLINEAR_TEMPLATE_REPORT_FILENAME,
    run_labor_employment_nonlinear_template_audit,
)
from lawfirm_os_intake.models import LaborEmploymentNonlinearTemplateAuditReport
from lawfirm_os_intake.util import load_json, write_json


TEMPLATE_SPEC = (
    "examples/synthetic/labor-employment/labor-employment-nonlinear-budget-templates.json"
)


def test_labor_employment_nonlinear_template_audit_accepts_candidate_contract(
    repo_root,
    tmp_path,
):
    report, run_dir = run_labor_employment_nonlinear_template_audit(
        template_spec_path=repo_root / TEMPLATE_SPEC,
        out_dir=tmp_path / "le-nonlinear-template",
    )
    persisted = LaborEmploymentNonlinearTemplateAuditReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_NONLINEAR_TEMPLATE_REPORT_FILENAME)
    )

    assert report.status == "labor_employment_nonlinear_templates_ready_for_review"
    assert persisted.template_count == 2
    assert persisted.phase_count == 12
    assert persisted.tier_block_count == 40
    assert persisted.period_driver_task_count == 2
    assert persisted.t4_staffing_block_count == 8
    assert persisted.failed_check_count == 0
    assert all(check.status == "passed" for check in persisted.checks)
    assert "labor_employment_nonlinear_template_contract_candidate" in (
        persisted.candidate_exception_lake_labels
    )
    assert persisted.budget_amount_output_authorized is False
    assert persisted.budget_submission_authorized is False
    assert persisted.conflict_conclusion_emitted is False
    assert persisted.matter_opening_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False


def test_labor_employment_nonlinear_template_cli_writes_report(repo_root, tmp_path, capsys):
    result = main(
        [
            "audit-labor-employment-nonlinear-budget-template-candidates",
            "--template-spec",
            str(repo_root / TEMPLATE_SPEC),
            "--out-dir",
            str(tmp_path / "le-nonlinear-template-cli"),
        ]
    )
    captured = capsys.readouterr().out
    persisted = load_json(
        tmp_path / "le-nonlinear-template-cli" / LABOR_EMPLOYMENT_NONLINEAR_TEMPLATE_REPORT_FILENAME
    )

    assert result == 0
    assert "labor_employment_nonlinear_templates_ready_for_review" in captured
    assert persisted["budget_amount_output_authorized"] is False
    assert persisted["lake_write_performed"] is False
    assert persisted["sqlite_write_performed"] is False
    assert persisted["external_writes_performed"] is False


def test_labor_employment_nonlinear_template_missing_tier_row_blocks(
    repo_root,
    tmp_path,
):
    spec = _spec(repo_root)
    class_template = spec["templates"][0]
    c300 = _phase(class_template, "C300")
    c300["tier_blocks"] = [block for block in c300["tier_blocks"] if block["tier_id"] != "t2"]
    report = _run_mutated(spec, tmp_path)

    assert report.status == "blocked_by_labor_employment_nonlinear_template_contract"
    assert _failed(report, "class_collective_tier_rows_complete").blocking_refs == ["C300:t2"]
    assert "labor_employment_nonlinear_template_contract_blocked" in (
        report.candidate_exception_lake_labels
    )


def test_labor_employment_nonlinear_template_rejects_cross_tier_interpolation(
    repo_root,
    tmp_path,
):
    spec = _spec(repo_root)
    class_template = spec["templates"][0]
    _phase(class_template, "C400")["tier_blocks"][1]["interpolation_allowed"] = True
    report = _run_mutated(spec, tmp_path)

    assert report.status == "blocked_by_labor_employment_nonlinear_template_contract"
    assert _failed(report, "no_cross_tier_interpolation").blocking_refs == ["C400:t1"]


def test_labor_employment_nonlinear_template_period_drivers_are_data_scope_only(
    repo_root,
    tmp_path,
):
    spec = _spec(repo_root)
    class_template = spec["templates"][0]
    task = _phase(class_template, "C400")["tasks"][0]
    task["period_drivers"] = ["class_period_months"]
    task["data_scope_task"] = False
    report = _run_mutated(spec, tmp_path)

    assert report.status == "blocked_by_labor_employment_nonlinear_template_contract"
    assert _failed(report, "period_drivers_are_data_scope_only").blocking_refs == [
        "C400-certification-briefing-hearing"
    ]


def test_labor_employment_nonlinear_template_paga_penalty_exposure_cannot_price(
    repo_root,
    tmp_path,
):
    spec = _spec(repo_root)
    paga_template = spec["templates"][1]
    penalty_task = _task(_phase(paga_template, "C500"), "C500-paga-penalty-exposure-exclusion")
    penalty_task["money_amount_allowed"] = True
    penalty_task["exposure_modeling_allowed"] = True
    report = _run_mutated(spec, tmp_path)

    assert report.status == "blocked_by_labor_employment_nonlinear_template_contract"
    assert _failed(report, "paga_period_scope_and_penalty_exclusion").blocking_refs == [
        "C500-paga-penalty-exposure-exclusion"
    ]


def test_labor_employment_nonlinear_template_paga_excludes_opt_in_tasks(
    repo_root,
    tmp_path,
):
    spec = _spec(repo_root)
    paga_template = spec["templates"][1]
    _phase(paga_template, "C600")["tasks"][0]["opt_in_sensitive"] = True
    report = _run_mutated(spec, tmp_path)

    assert report.status == "blocked_by_labor_employment_nonlinear_template_contract"
    assert _failed(report, "paga_template_excludes_opt_in_tasks").blocking_refs == [
        "C600-paga-resolution-approval-support"
    ]


def test_labor_employment_nonlinear_template_missing_scenario_gate_blocks(
    repo_root,
    tmp_path,
):
    spec = _spec(repo_root)
    class_template = spec["templates"][0]
    class_template["scenario_gates"] = [
        gate
        for gate in class_template["scenario_gates"]
        if gate["driver_id"] != "certification_posture"
    ]
    report = _run_mutated(spec, tmp_path)

    assert report.status == "blocked_by_labor_employment_nonlinear_template_contract"
    assert _failed(report, "class_collective_certification_scenario_gate").blocking_refs == [
        "certification_posture"
    ]


def _spec(repo_root):
    return copy.deepcopy(load_json(repo_root / TEMPLATE_SPEC))


def _run_mutated(spec, tmp_path):
    spec_path = tmp_path / "mutated-template-spec.json"
    write_json(spec_path, spec)
    report, _ = run_labor_employment_nonlinear_template_audit(
        template_spec_path=spec_path,
        out_dir=tmp_path / "audit",
    )
    return report


def _phase(template, phase_id):
    return next(phase for phase in template["phases"] if phase["phase_id"] == phase_id)


def _task(phase, task_id):
    return next(task for task in phase["tasks"] if task["task_id"] == task_id)


def _failed(report, check_id):
    return next(check for check in report.checks if check.check_id == check_id)
