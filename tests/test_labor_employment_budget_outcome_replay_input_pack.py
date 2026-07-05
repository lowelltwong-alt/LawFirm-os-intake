import pytest

from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.carrier_rejection_learning import run_carrier_rejection_learning
from lawfirm_os_intake.carrier_rejection_review import run_carrier_rejection_review
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.labor_employment_budget_learning_fixtures import (
    LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME,
    run_labor_employment_budget_learning_fixture_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_builder_binding import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_builder_binding_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_execution import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_execution,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_input_pack import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_input_pack_audit,
)
from lawfirm_os_intake.labor_employment_budget_outcome_replay_readiness import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_readiness_audit,
)
from lawfirm_os_intake.models import (
    BudgetActualComparisonReport,
    BudgetActualVarianceLedgerReport,
    CarrierRejectionLearningReport,
    CarrierRejectionDecisionLedgerReport,
    CarrierRejectionReviewPacket,
    LaborEmploymentBudgetOutcomeReplayInputPackManifest,
    LaborEmploymentBudgetOutcomeReplayInputPackReport,
    ReviewedLearningGateReport,
)
from lawfirm_os_intake.reviewed_learning_gate import run_reviewed_learning_gate
from lawfirm_os_intake.util import load_json, write_json


FIXTURE_ROOT = "apps/legal-intake-budget/src/fixtures"
LEARNING_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-learning-fixtures.json"
)
OUTCOME_SEED_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-seeds.json"
)
INPUT_PACK_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json"
)
DISCRIMINATION_REPLAY_INPUT_ROOT = (
    "examples/synthetic/labor-employment/replay-inputs/discrimination-harassment-clean"
)
WAGE_HOUR_REPLAY_INPUT_ROOT = "examples/synthetic/labor-employment/replay-inputs/wage-hour-clean"


def _qa_gate(repo_root):
    return repo_root / FIXTURE_ROOT / "demo-labor-employment-budget-qa-gate-report.json"


def _learning_manifest(repo_root):
    return repo_root / LEARNING_MANIFEST_REF


def _seed_manifest(repo_root):
    return repo_root / OUTCOME_SEED_MANIFEST_REF


def _input_pack_manifest(repo_root):
    return repo_root / INPUT_PACK_MANIFEST_REF


def _discrimination_budget(repo_root):
    return repo_root / DISCRIMINATION_REPLAY_INPUT_ROOT / "legal_budget_proposal.json"


def _discrimination_actuals(repo_root):
    return repo_root / DISCRIMINATION_REPLAY_INPUT_ROOT / "budget_actuals_source.json"


def _discrimination_carrier_bundle(repo_root):
    return (
        repo_root
        / DISCRIMINATION_REPLAY_INPUT_ROOT
        / "carrier_rejection_capture_source_bundle.json"
    )


def _wage_hour_budget(repo_root):
    return repo_root / WAGE_HOUR_REPLAY_INPUT_ROOT / "legal_budget_proposal.json"


def _wage_hour_actuals(repo_root):
    return repo_root / WAGE_HOUR_REPLAY_INPUT_ROOT / "budget_actuals_source.json"


def _wage_hour_carrier_bundle(repo_root):
    return repo_root / WAGE_HOUR_REPLAY_INPUT_ROOT / "carrier_rejection_capture_source_bundle.json"


def _rel(root, path):
    return path.relative_to(root).as_posix()


def _stage_discrimination_case_anchors(repo_root, runtime_root):
    anchors = runtime_root / "anchors"
    budget_path = write_json(
        anchors / "legal_budget_proposal.json",
        load_json(_discrimination_budget(repo_root)),
    )
    actuals_path = write_json(
        anchors / "budget_actuals_source.json",
        load_json(_discrimination_actuals(repo_root)),
    )
    carrier_bundle_path = write_json(
        anchors / "carrier_rejection_capture_source_bundle.json",
        load_json(_discrimination_carrier_bundle(repo_root)),
    )
    return {
        "budget": budget_path,
        "actuals": actuals_path,
        "carrier_bundle": carrier_bundle_path,
    }


def _stage_wage_hour_case_anchors(repo_root, runtime_root):
    anchors = runtime_root / "anchors"
    budget_path = write_json(
        anchors / "legal_budget_proposal.json",
        load_json(_wage_hour_budget(repo_root)),
    )
    actuals_path = write_json(
        anchors / "budget_actuals_source.json",
        load_json(_wage_hour_actuals(repo_root)),
    )
    carrier_bundle_path = write_json(
        anchors / "carrier_rejection_capture_source_bundle.json",
        load_json(_wage_hour_carrier_bundle(repo_root)),
    )
    return {
        "budget": budget_path,
        "actuals": actuals_path,
        "carrier_bundle": carrier_bundle_path,
    }


def _run_discrimination_carrier_learning_chain(repo_root, tmp_path):
    _, carrier_dir = run_carrier_rejection_capture(
        _discrimination_budget(repo_root),
        _discrimination_carrier_bundle(repo_root),
        tmp_path / "le-discrimination-carrier-rejection-replay",
    )
    review_packet, review_dir = run_carrier_rejection_review(
        carrier_dir / "carrier_rejection_reconciliation_report.json",
        tmp_path / "le-discrimination-carrier-rejection-review",
    )
    learning_report, learning_dir = run_carrier_rejection_learning(
        review_dir / "carrier_rejection_review_packet.json",
        tmp_path / "le-discrimination-carrier-rejection-learning",
    )
    gate_report, gate_dir = run_reviewed_learning_gate(
        carrier_rejection_learning_report_path=(
            learning_dir / "carrier_rejection_learning_report.json"
        ),
        out_dir=tmp_path / "le-discrimination-reviewed-learning-gate",
    )
    return {
        "carrier_dir": carrier_dir,
        "review_packet": review_packet,
        "review_dir": review_dir,
        "learning_report": learning_report,
        "learning_dir": learning_dir,
        "gate_report": gate_report,
        "gate_dir": gate_dir,
    }


def _run_wage_hour_carrier_learning_chain(repo_root, tmp_path):
    _, carrier_dir = run_carrier_rejection_capture(
        _wage_hour_budget(repo_root),
        _wage_hour_carrier_bundle(repo_root),
        tmp_path / "le-wage-hour-carrier-rejection-replay",
    )
    review_packet, review_dir = run_carrier_rejection_review(
        carrier_dir / "carrier_rejection_reconciliation_report.json",
        tmp_path / "le-wage-hour-carrier-rejection-review",
    )
    learning_report, learning_dir = run_carrier_rejection_learning(
        review_dir / "carrier_rejection_review_packet.json",
        tmp_path / "le-wage-hour-carrier-rejection-learning",
    )
    gate_report, gate_dir = run_reviewed_learning_gate(
        carrier_rejection_learning_report_path=(
            learning_dir / "carrier_rejection_learning_report.json"
        ),
        out_dir=tmp_path / "le-wage-hour-reviewed-learning-gate",
    )
    return {
        "carrier_dir": carrier_dir,
        "review_packet": review_packet,
        "review_dir": review_dir,
        "learning_report": learning_report,
        "learning_dir": learning_dir,
        "gate_report": gate_report,
        "gate_dir": gate_dir,
    }


def _reviewed_learning_signal_manifest(runtime_root, anchors, learning_report_path):
    return write_json(
        runtime_root / "runtime-reviewed-learning-signal-input-pack.json",
        {
            "schema_version": "0.1",
            "manifest_id": "runtime-reviewed-learning-signal-input-pack.v0_1",
            "status": "candidate_labor_employment_budget_outcome_replay_input_pack_manifest",
            "practice_area": "labor_employment",
            "source_builder_binding_report_ref": "synthetic-test-builder-binding-report",
            "entries": [
                {
                    "entry_id": "le-discrimination-budget-anchor.v0_1",
                    "learning_fixture_id": ("le-learning-discrimination-harassment-clean.v0_1"),
                    "loop_type": "actuals_variance",
                    "expected_artifact_name": "budget_actual_comparison_report.json",
                    "required_input_artifact": "legal_budget_proposal.json",
                    "input_ref": _rel(runtime_root, anchors["budget"]),
                    "input_role": "builder_input",
                    "notes": "Same-case synthetic budget anchor for reviewed learning signal validation.",
                },
                {
                    "entry_id": "le-discrimination-actuals-anchor.v0_1",
                    "learning_fixture_id": ("le-learning-discrimination-harassment-clean.v0_1"),
                    "loop_type": "actuals_variance",
                    "expected_artifact_name": "budget_actual_comparison_report.json",
                    "required_input_artifact": "budget_actuals_source.json",
                    "input_ref": _rel(runtime_root, anchors["actuals"]),
                    "input_role": "builder_input",
                    "notes": "Same-case synthetic actuals anchor for reviewed learning signal validation.",
                },
                {
                    "entry_id": "le-discrimination-carrier-anchor.v0_1",
                    "learning_fixture_id": ("le-learning-discrimination-harassment-clean.v0_1"),
                    "loop_type": "carrier_rejection_capture",
                    "expected_artifact_name": "carrier_rejection_reconciliation_report.json",
                    "required_input_artifact": "carrier_rejection_capture_source_bundle.json",
                    "input_ref": _rel(runtime_root, anchors["carrier_bundle"]),
                    "input_role": "builder_input",
                    "notes": "Same-case synthetic carrier source anchor for reviewed learning signal validation.",
                },
                {
                    "entry_id": "le-discrimination-carrier-learning-signal.v0_1",
                    "learning_fixture_id": ("le-learning-discrimination-harassment-clean.v0_1"),
                    "loop_type": "reviewed_learning_gate",
                    "expected_artifact_name": "reviewed_learning_gate_report.json",
                    "required_input_artifact": "carrier_rejection_learning_report.json",
                    "input_ref": _rel(runtime_root, learning_report_path),
                    "input_role": "one_of_signal",
                    "notes": "Generated synthetic carrier learning report used as one-of reviewed learning signal.",
                },
            ],
        },
    )


def _wage_hour_reviewed_learning_signal_manifest(runtime_root, anchors, learning_report_path):
    return write_json(
        runtime_root / "runtime-wage-hour-reviewed-learning-signal-input-pack.json",
        {
            "schema_version": "0.1",
            "manifest_id": "runtime-wage-hour-reviewed-learning-signal-input-pack.v0_1",
            "status": "candidate_labor_employment_budget_outcome_replay_input_pack_manifest",
            "practice_area": "labor_employment",
            "source_builder_binding_report_ref": "synthetic-test-builder-binding-report",
            "entries": [
                {
                    "entry_id": "le-wage-hour-budget-anchor.v0_1",
                    "learning_fixture_id": "le-learning-wage-hour-clean.v0_1",
                    "loop_type": "actuals_variance",
                    "expected_artifact_name": "budget_actual_comparison_report.json",
                    "required_input_artifact": "legal_budget_proposal.json",
                    "input_ref": _rel(runtime_root, anchors["budget"]),
                    "input_role": "builder_input",
                    "notes": "Same-case synthetic wage/hour budget anchor for reviewed learning signal validation.",
                },
                {
                    "entry_id": "le-wage-hour-actuals-anchor.v0_1",
                    "learning_fixture_id": "le-learning-wage-hour-clean.v0_1",
                    "loop_type": "actuals_variance",
                    "expected_artifact_name": "budget_actual_comparison_report.json",
                    "required_input_artifact": "budget_actuals_source.json",
                    "input_ref": _rel(runtime_root, anchors["actuals"]),
                    "input_role": "builder_input",
                    "notes": "Same-case synthetic wage/hour actuals anchor for reviewed learning signal validation.",
                },
                {
                    "entry_id": "le-wage-hour-carrier-anchor.v0_1",
                    "learning_fixture_id": "le-learning-wage-hour-clean.v0_1",
                    "loop_type": "carrier_rejection_capture",
                    "expected_artifact_name": "carrier_rejection_reconciliation_report.json",
                    "required_input_artifact": "carrier_rejection_capture_source_bundle.json",
                    "input_ref": _rel(runtime_root, anchors["carrier_bundle"]),
                    "input_role": "builder_input",
                    "notes": "Same-case synthetic wage/hour carrier source anchor for reviewed learning signal validation.",
                },
                {
                    "entry_id": "le-wage-hour-carrier-learning-signal.v0_1",
                    "learning_fixture_id": "le-learning-wage-hour-clean.v0_1",
                    "loop_type": "reviewed_learning_gate",
                    "expected_artifact_name": "reviewed_learning_gate_report.json",
                    "required_input_artifact": "carrier_rejection_learning_report.json",
                    "input_ref": _rel(runtime_root, learning_report_path),
                    "input_role": "one_of_signal",
                    "notes": "Generated synthetic wage/hour carrier learning report used as one-of reviewed learning signal.",
                },
            ],
        },
    )


def _learning_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_learning_fixture_audit(
        manifest_path=_learning_manifest(repo_root),
        budget_qa_gate_report_path=_qa_gate(repo_root),
        out_dir=tmp_path / "le-budget-learning-fixtures",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME


def _readiness_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_outcome_replay_readiness_audit(
        seed_manifest_path=_seed_manifest(repo_root),
        learning_fixture_report_path=_learning_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-readiness",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME


def _execution_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_outcome_replay_execution(
        seed_manifest_path=_seed_manifest(repo_root),
        readiness_report_path=_readiness_report(repo_root, tmp_path),
        out_dir=tmp_path / "le-budget-outcome-replay-execution",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME


def _builder_binding_report(repo_root, tmp_path):
    _, run_dir = run_labor_employment_budget_outcome_replay_builder_binding_audit(
        execution_report_path=_execution_report(repo_root, tmp_path),
        out_dir=tmp_path / "le-budget-outcome-replay-builder-binding",
        generated_at="2026-07-04T00:00:00Z",
    )
    return run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME


def test_labor_employment_budget_replay_input_pack_marks_ready_and_missing_inputs(
    repo_root,
    tmp_path,
):
    manifest = LaborEmploymentBudgetOutcomeReplayInputPackManifest.model_validate(
        load_json(_input_pack_manifest(repo_root))
    )
    report, run_dir = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=_input_pack_manifest(repo_root),
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack",
        generated_at="2026-07-04T00:00:00Z",
    )
    persisted = LaborEmploymentBudgetOutcomeReplayInputPackReport.model_validate(
        load_json(run_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME)
    )

    assert manifest.manifest_id == "labor-employment-budget-outcome-replay-input-pack.v0_1"
    assert persisted.input_pack_report_id == report.input_pack_report_id
    assert report.status == "labor_employment_budget_replay_input_pack_partially_ready_for_review"
    assert report.case_count == 8
    assert report.ready_case_count == 1
    assert report.partial_case_count == 7
    assert report.blocked_case_count == 0
    assert report.ready_input_count == 21
    assert report.missing_input_count > 0
    assert report.invalid_input_count == 0
    assert report.one_of_signal_missing_count > 0
    assert all(check.status == "passed" for check in report.checks)
    blocked_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-ada-fmla-adversarial.v0_1"
    )
    assert blocked_case.status == "ready"
    assert {
        item.required_input_artifact for item in blocked_case.items if item.input_status == "ready"
    } == {
        "labor_employment_budget_output_expectations_report.json",
        "labor_employment_blocked_driver_impact_review_report.json",
        "labor_employment_executable_coverage_report.json",
        "labor_employment_budget_learning_fixtures.json",
        "labor_employment_budget_qa_gate_report.json",
    }
    assert any(
        item.required_input_artifact == "labor_employment_executable_coverage_report.json"
        and item.validation_model == "LaborEmploymentExecutableCoverageReport"
        for item in blocked_case.items
    )
    discrimination_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-discrimination-harassment-clean.v0_1"
    )
    assert discrimination_case.status == "partially_ready"
    assert discrimination_case.ready_input_count == 8
    assert discrimination_case.missing_input_count > 0
    assert {
        item.required_input_artifact
        for item in discrimination_case.items
        if item.input_status == "ready"
    } >= {
        "legal_budget_proposal.json",
        "budget_actuals_source.json",
        "carrier_rejection_capture_source_bundle.json",
    }
    assert any(
        item.input_role == "one_of_signal" and item.input_status == "missing"
        for item in discrimination_case.items
    )
    wage_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-wage-hour-clean.v0_1"
    )
    assert wage_case.status == "partially_ready"
    assert wage_case.ready_input_count == 8
    assert wage_case.missing_input_count > 0
    assert {
        item.required_input_artifact for item in wage_case.items if item.input_status == "ready"
    } >= {
        "legal_budget_proposal.json",
        "budget_actuals_source.json",
        "carrier_rejection_capture_source_bundle.json",
    }
    assert any(
        item.input_role == "one_of_signal" and item.input_status == "missing"
        for item in wage_case.items
    )
    assert report.runtime_artifacts_created is False
    assert report.budget_submission_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    notes = (run_dir / "labor_employment_budget_outcome_replay_input_pack_report.md").read_text(
        encoding="utf-8"
    )
    assert "does not run builders" in notes
    assert "Rust Transition Candidates" in notes
    assert {path.name for path in run_dir.iterdir()} == {
        "labor_employment_budget_outcome_replay_input_pack_report.json",
        "labor_employment_budget_outcome_replay_input_pack_report.md",
    }


def test_labor_employment_budget_replay_input_pack_without_manifest_is_all_missing(
    repo_root,
    tmp_path,
):
    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-missing",
        generated_at="2026-07-04T00:00:00Z",
    )

    assert report.status == "labor_employment_budget_replay_input_pack_partially_ready_for_review"
    assert report.ready_input_count == 0
    assert report.missing_input_count == report.required_input_count
    assert report.invalid_input_count == 0
    assert report.ready_case_count == 0
    assert report.partial_case_count == 8
    assert report.blocked_case_count == 0
    assert all(check.status == "passed" for check in report.checks)


def test_labor_employment_budget_replay_input_pack_blocks_invalid_declared_ref(
    repo_root,
    tmp_path,
):
    bad_payload_path = write_json(tmp_path / "bad-qa-gate-report.json", {"schema_version": "0.1"})
    manifest = load_json(_input_pack_manifest(repo_root))
    for entry in manifest["entries"]:
        if entry["required_input_artifact"] == "labor_employment_budget_qa_gate_report.json":
            entry["input_ref"] = str(bad_payload_path)
    manifest_path = write_json(tmp_path / "bad-input-pack-manifest.json", manifest)

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-invalid",
        generated_at="2026-07-04T00:00:00Z",
    )
    failed_checks = {check.check_id for check in report.checks if check.status == "failed"}

    assert report.status == "blocked_by_labor_employment_budget_replay_input_pack"
    assert report.invalid_input_count == 1
    assert report.blocked_case_count == 1
    assert "declared_input_refs_are_schema_valid" in failed_checks
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_labor_employment_budget_replay_input_pack_rejects_absolute_refs(
    repo_root,
    tmp_path,
):
    manifest = load_json(_input_pack_manifest(repo_root))
    for entry in manifest["entries"]:
        if (
            entry["learning_fixture_id"] == "le-learning-discrimination-harassment-clean.v0_1"
            and entry["loop_type"] == "actuals_variance"
            and entry["required_input_artifact"] == "legal_budget_proposal.json"
        ):
            entry["input_ref"] = str(_discrimination_budget(repo_root))
    manifest_path = write_json(tmp_path / "absolute-ref-input-pack-manifest.json", manifest)

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-absolute-ref",
        generated_at="2026-07-04T00:00:00Z",
    )

    assert report.status == "blocked_by_labor_employment_budget_replay_input_pack"
    assert report.invalid_input_count >= 2
    assert any(
        item.required_input_artifact == "legal_budget_proposal.json"
        and item.input_status == "invalid"
        and item.validation_message == "Input ref is not a local JSON file ref."
        for case in report.cases
        for item in case.items
    )


def test_labor_employment_budget_replay_input_pack_rejects_authorization_inversion(
    repo_root,
    tmp_path,
):
    bad_budget = load_json(_discrimination_budget(repo_root))
    bad_budget["not_authorized_for_client_submission"] = False
    write_json(tmp_path / "bad-budget.json", bad_budget)
    manifest_path = write_json(
        tmp_path / "bad-boundary-input-pack-manifest.json",
        {
            "schema_version": "0.1",
            "manifest_id": "bad-boundary-input-pack.v0_1",
            "status": "candidate_labor_employment_budget_outcome_replay_input_pack_manifest",
            "practice_area": "labor_employment",
            "source_builder_binding_report_ref": "synthetic-test-builder-binding-report",
            "entries": [
                {
                    "entry_id": "bad-boundary-budget-entry.v0_1",
                    "learning_fixture_id": "le-learning-discrimination-harassment-clean.v0_1",
                    "loop_type": "actuals_variance",
                    "required_input_artifact": "legal_budget_proposal.json",
                    "input_ref": "bad-budget.json",
                    "input_role": "builder_input",
                    "notes": "Negative test fixture with inverted submission authorization flag.",
                }
            ],
        },
    )

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=tmp_path,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-boundary",
        generated_at="2026-07-04T00:00:00Z",
    )

    assert report.status == "blocked_by_labor_employment_budget_replay_input_pack"
    assert report.invalid_input_count == 2
    assert any(
        "$.not_authorized_for_client_submission" in item.validation_message
        for case in report.cases
        for item in case.items
        if item.input_status == "invalid"
    )


def test_labor_employment_budget_replay_input_pack_cli_writes_report(
    repo_root,
    tmp_path,
    capsys,
):
    exit_code = main(
        [
            "audit-labor-employment-budget-outcome-replay-input-pack",
            "--builder-binding-report",
            str(_builder_binding_report(repo_root, tmp_path)),
            "--input-pack-manifest",
            str(_input_pack_manifest(repo_root)),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "le-budget-outcome-replay-input-pack-cli"),
            "--generated-at",
            "2026-07-04T00:00:00Z",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert (
        '"status": "labor_employment_budget_replay_input_pack_partially_ready_for_review"'
        in captured.out
    )
    assert '"ready_case_count": 1' in captured.out
    assert '"ready_input_count": 21' in captured.out
    assert '"invalid_input_count": 0' in captured.out
    assert '"runtime_artifacts_created": false' in captured.out
    assert (
        tmp_path
        / "le-budget-outcome-replay-input-pack-cli"
        / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME
    ).is_file()


def test_labor_employment_discrimination_actuals_replay_inputs_run_builder(
    repo_root,
    tmp_path,
):
    report, run_dir = run_budget_actual_comparison(
        budget_path=_discrimination_budget(repo_root),
        actuals_path=_discrimination_actuals(repo_root),
        out_dir=tmp_path / "le-discrimination-actuals-replay",
    )
    persisted = BudgetActualComparisonReport.model_validate(
        load_json(run_dir / "budget_actual_comparison_report.json")
    )
    ledger = BudgetActualVarianceLedgerReport.model_validate(
        load_json(run_dir / "budget_actual_variance_ledger_report.json")
    )
    phase_statuses = {row.phase_id: row.status for row in persisted.phase_comparisons}
    code_statuses = {row.code: row.status for row in persisted.code_comparisons}

    assert persisted.budget_actual_comparison_report_id == report.budget_actual_comparison_report_id
    assert report.budget_proposal_id == "le-budget-discrimination-harassment-clean.v0_1"
    assert report.preflight_packet_id == "le-preflight-discrimination-harassment-clean.v0_1"
    assert report.status == "variance_review_required"
    assert report.comparison_scope == "phase_and_code"
    assert phase_statuses["L300"] == "over_threshold"
    assert code_statuses["L330"] == "over_threshold"
    assert "budget_driver" in report.learning_disposition_candidates
    assert report.billing_connector_read_performed is False
    assert report.billing_connector_write_performed is False
    assert report.external_writes_performed is False
    assert ledger.status == "variance_ledger_ready_for_review"
    assert ledger.budget_proposal_id == report.budget_proposal_id
    assert ledger.lake_write_performed is False
    assert ledger.sqlite_write_performed is False
    assert ledger.billing_connector_read_performed is False
    assert ledger.billing_connector_write_performed is False
    assert ledger.external_writes_performed is False
    assert ledger.silent_learning_performed is False


def test_labor_employment_discrimination_actuals_reject_mismatched_budget_id(
    repo_root,
    tmp_path,
):
    bad_actuals = load_json(_discrimination_actuals(repo_root))
    bad_actuals["budget_proposal_id"] = "wrong-budget-proposal-id"
    bad_actuals_path = write_json(tmp_path / "bad-actuals.json", bad_actuals)

    with pytest.raises(ValueError, match="actuals source budget_proposal_id does not match"):
        run_budget_actual_comparison(
            budget_path=_discrimination_budget(repo_root),
            actuals_path=bad_actuals_path,
            out_dir=tmp_path / "bad-actuals-run",
        )


def test_labor_employment_discrimination_carrier_rejection_inputs_run_builder(
    repo_root,
    tmp_path,
):
    report, run_dir = run_carrier_rejection_capture(
        _discrimination_budget(repo_root),
        _discrimination_carrier_bundle(repo_root),
        tmp_path / "le-discrimination-carrier-rejection-replay",
    )
    ledger = CarrierRejectionDecisionLedgerReport.model_validate(
        load_json(run_dir / "carrier_rejection_decision_ledger_report.json")
    )

    assert report.status == "dry_run_ready_for_review"
    assert report.budget_proposal_id == "le-budget-discrimination-harassment-clean.v0_1"
    assert report.preflight_packet_id == "le-preflight-discrimination-harassment-clean.v0_1"
    assert report.source_bundle_id == "le-carrier-rejection-discrimination-harassment-clean.v0_1"
    assert report.expected_response_count == 1
    assert report.reconciled_response_count == 1
    assert report.missing_response_count == 0
    assert report.unlinked_notice_count == 0
    assert report.parser_failure_count == 0
    assert report.appeal_result_count == 0
    assert {case.local_event_label for case in report.remediation_cases} == {
        "carrier_rate_reduction"
    }
    assert "carrier_rejection_learning_candidate" in {
        candidate.local_event_label for candidate in report.exception_lake_candidates
    }
    assert report.not_authorized_for_lake_write is True
    assert report.not_authorized_for_external_submission is True
    assert report.external_writes_performed is False
    assert ledger.status == "decision_ledger_ready_for_review"
    assert ledger.reconciliation_report_id == report.reconciliation_report_id
    assert ledger.source_bundle_id == report.source_bundle_id
    assert ledger.pending_decision_event_count == 1
    assert ledger.lake_write_performed is False
    assert ledger.sqlite_write_performed is False
    assert ledger.external_writes_performed is False
    assert ledger.appeal_submission_performed is False
    assert ledger.silent_learning_performed is False


def test_labor_employment_discrimination_carrier_rejection_rejects_mismatched_ids(
    repo_root,
    tmp_path,
):
    bad_bundle = load_json(_discrimination_carrier_bundle(repo_root))
    bad_bundle["preflight_packet_id"] = "wrong-preflight-packet-id"
    bad_bundle["budget_proposal_id"] = "le-budget-discrimination-harassment-clean.v0_1"
    bad_bundle_path = write_json(tmp_path / "bad-carrier-bundle.json", bad_bundle)

    with pytest.raises(ValueError, match="preflight_packet_id does not match"):
        run_carrier_rejection_capture(
            _discrimination_budget(repo_root),
            bad_bundle_path,
            tmp_path / "bad-carrier-rejection-run",
        )


def test_labor_employment_wage_hour_actuals_replay_inputs_run_builder(
    repo_root,
    tmp_path,
):
    report, run_dir = run_budget_actual_comparison(
        budget_path=_wage_hour_budget(repo_root),
        actuals_path=_wage_hour_actuals(repo_root),
        out_dir=tmp_path / "le-wage-hour-actuals-replay",
    )
    persisted = BudgetActualComparisonReport.model_validate(
        load_json(run_dir / "budget_actual_comparison_report.json")
    )
    ledger = BudgetActualVarianceLedgerReport.model_validate(
        load_json(run_dir / "budget_actual_variance_ledger_report.json")
    )
    phase_statuses = {row.phase_id: row.status for row in persisted.phase_comparisons}
    code_statuses = {row.code: row.status for row in persisted.code_comparisons}

    assert persisted.budget_actual_comparison_report_id == report.budget_actual_comparison_report_id
    assert report.budget_proposal_id == "le-budget-wage-hour-clean.v0_1"
    assert report.preflight_packet_id == "le-preflight-wage-hour-clean.v0_1"
    assert report.status == "variance_review_required"
    assert report.comparison_scope == "phase_and_code"
    assert phase_statuses["L300"] == "over_threshold"
    assert code_statuses["L310"] == "over_threshold"
    assert code_statuses["E118"] == "over_threshold"
    assert "budget_driver" in report.learning_disposition_candidates
    assert report.billing_connector_read_performed is False
    assert report.billing_connector_write_performed is False
    assert report.external_writes_performed is False
    assert ledger.status == "variance_ledger_ready_for_review"
    assert ledger.budget_proposal_id == report.budget_proposal_id
    assert ledger.lake_write_performed is False
    assert ledger.sqlite_write_performed is False
    assert ledger.billing_connector_read_performed is False
    assert ledger.billing_connector_write_performed is False
    assert ledger.external_writes_performed is False
    assert ledger.silent_learning_performed is False


def test_labor_employment_wage_hour_carrier_rejection_inputs_run_builder(
    repo_root,
    tmp_path,
):
    report, run_dir = run_carrier_rejection_capture(
        _wage_hour_budget(repo_root),
        _wage_hour_carrier_bundle(repo_root),
        tmp_path / "le-wage-hour-carrier-rejection-replay",
    )
    ledger = CarrierRejectionDecisionLedgerReport.model_validate(
        load_json(run_dir / "carrier_rejection_decision_ledger_report.json")
    )

    assert report.status == "dry_run_ready_for_review"
    assert report.budget_proposal_id == "le-budget-wage-hour-clean.v0_1"
    assert report.preflight_packet_id == "le-preflight-wage-hour-clean.v0_1"
    assert report.source_bundle_id == "le-carrier-rejection-wage-hour-clean.v0_1"
    assert report.expected_response_count == 1
    assert report.reconciled_response_count == 1
    assert report.missing_response_count == 0
    assert report.unlinked_notice_count == 0
    assert report.parser_failure_count == 0
    assert report.appeal_result_count == 0
    assert {case.local_event_label for case in report.remediation_cases} == {
        "carrier_code_mapping_rejection"
    }
    assert "carrier_rejection_learning_candidate" in {
        candidate.local_event_label for candidate in report.exception_lake_candidates
    }
    assert report.not_authorized_for_lake_write is True
    assert report.not_authorized_for_external_submission is True
    assert report.external_writes_performed is False
    assert ledger.status == "decision_ledger_ready_for_review"
    assert ledger.reconciliation_report_id == report.reconciliation_report_id
    assert ledger.source_bundle_id == report.source_bundle_id
    assert ledger.pending_decision_event_count == 1
    assert ledger.lake_write_performed is False
    assert ledger.sqlite_write_performed is False
    assert ledger.external_writes_performed is False
    assert ledger.appeal_submission_performed is False
    assert ledger.silent_learning_performed is False


def test_labor_employment_replay_input_pack_rejects_wrong_family_budget_anchor(
    repo_root,
    tmp_path,
):
    manifest = load_json(_input_pack_manifest(repo_root))
    for entry in manifest["entries"]:
        if (
            entry["learning_fixture_id"] == "le-learning-wage-hour-clean.v0_1"
            and entry["required_input_artifact"] == "legal_budget_proposal.json"
        ):
            entry["input_ref"] = (
                "examples/synthetic/labor-employment/replay-inputs/"
                "discrimination-harassment-clean/legal_budget_proposal.json"
            )
    manifest_path = write_json(tmp_path / "wrong-family-input-pack-manifest.json", manifest)

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-wrong-family",
        generated_at="2026-07-04T00:00:00Z",
    )
    wage_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-wage-hour-clean.v0_1"
    )

    assert report.status == "blocked_by_labor_employment_budget_replay_input_pack"
    assert wage_case.status == "blocked"
    assert wage_case.invalid_input_count >= 2
    assert any(
        item.required_input_artifact == "legal_budget_proposal.json"
        and item.input_status == "invalid"
        and "matter_family='discrimination_harassment' expected 'wage_hour_flsa_state'"
        in item.validation_message
        for item in wage_case.items
    )


def test_labor_employment_replay_input_pack_rejects_swapped_wage_hour_actuals_source(
    repo_root,
    tmp_path,
):
    manifest = load_json(_input_pack_manifest(repo_root))
    for entry in manifest["entries"]:
        if (
            entry["learning_fixture_id"] == "le-learning-wage-hour-clean.v0_1"
            and entry["loop_type"] == "actuals_variance"
            and entry["required_input_artifact"] == "budget_actuals_source.json"
        ):
            entry["input_ref"] = (
                "examples/synthetic/labor-employment/replay-inputs/"
                "discrimination-harassment-clean/budget_actuals_source.json"
            )
    manifest_path = write_json(tmp_path / "swapped-actuals-input-pack-manifest.json", manifest)

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-swapped-actuals",
        generated_at="2026-07-04T00:00:00Z",
    )
    wage_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-wage-hour-clean.v0_1"
    )
    actuals_item = next(
        item
        for item in wage_case.items
        if item.loop_type == "actuals_variance"
        and item.required_input_artifact == "budget_actuals_source.json"
    )

    assert report.status == "blocked_by_labor_employment_budget_replay_input_pack"
    assert wage_case.status == "blocked"
    assert actuals_item.input_status == "invalid"
    assert actuals_item.validation_model == "BudgetActualsSource"
    assert "source case token='wage-hour-clean'" in actuals_item.validation_message
    assert "actuals_source_id" in actuals_item.validation_message
    assert "source_ref" in actuals_item.validation_message
    assert "le-actuals-discrimination-harassment-clean.v0_1" in (actuals_item.validation_message)


def test_labor_employment_replay_input_pack_rejects_swapped_wage_hour_carrier_bundle(
    repo_root,
    tmp_path,
):
    manifest = load_json(_input_pack_manifest(repo_root))
    for entry in manifest["entries"]:
        if (
            entry["learning_fixture_id"] == "le-learning-wage-hour-clean.v0_1"
            and entry["loop_type"] == "carrier_rejection_capture"
            and entry["required_input_artifact"] == "carrier_rejection_capture_source_bundle.json"
        ):
            entry["input_ref"] = (
                "examples/synthetic/labor-employment/replay-inputs/"
                "discrimination-harassment-clean/carrier_rejection_capture_source_bundle.json"
            )
    manifest_path = write_json(tmp_path / "swapped-carrier-input-pack-manifest.json", manifest)

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-swapped-carrier",
        generated_at="2026-07-04T00:00:00Z",
    )
    wage_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-wage-hour-clean.v0_1"
    )
    carrier_item = next(
        item
        for item in wage_case.items
        if item.loop_type == "carrier_rejection_capture"
        and item.required_input_artifact == "carrier_rejection_capture_source_bundle.json"
    )

    assert report.status == "blocked_by_labor_employment_budget_replay_input_pack"
    assert wage_case.status == "blocked"
    assert carrier_item.input_status == "invalid"
    assert carrier_item.validation_model == "CarrierRejectionCaptureSourceBundle"
    assert "source case token='wage-hour-clean'" in carrier_item.validation_message
    assert "bundle_id" in carrier_item.validation_message
    assert "run_id" in carrier_item.validation_message
    assert "le-carrier-rejection-discrimination-harassment-clean.v0_1" in (
        carrier_item.validation_message
    )


def test_labor_employment_discrimination_reviewed_learning_signal_runs_and_validates(
    repo_root,
    tmp_path,
):
    chain = _run_discrimination_carrier_learning_chain(repo_root, tmp_path)
    runtime_root = tmp_path / "runtime-reviewed-learning-input-pack"
    anchors = _stage_discrimination_case_anchors(repo_root, runtime_root)
    learning_report_path = write_json(
        runtime_root / "runtime" / "carrier_rejection_learning_report.json",
        load_json(chain["learning_dir"] / "carrier_rejection_learning_report.json"),
    )
    manifest_path = _reviewed_learning_signal_manifest(
        runtime_root,
        anchors,
        learning_report_path,
    )
    review_packet = CarrierRejectionReviewPacket.model_validate(
        load_json(chain["review_dir"] / "carrier_rejection_review_packet.json")
    )
    learning_report = CarrierRejectionLearningReport.model_validate(load_json(learning_report_path))
    gate_report = ReviewedLearningGateReport.model_validate(
        load_json(chain["gate_dir"] / "reviewed_learning_gate_report.json")
    )

    assert review_packet.status == "ready_for_human_review"
    assert review_packet.remediation_case_count == 1
    assert review_packet.total_financial_exposure == 1800
    assert {note.scope for note in review_packet.red_team_notes} >= {"boundary", "learning_loop"}
    assert {item.recommended_action for item in review_packet.recommendations} == {
        "appeal_review_required"
    }
    assert {item.priority for item in review_packet.recommendations} == {"high"}
    assert learning_report.status == "candidate_learning_ready_for_review"
    assert learning_report.proposal_count == 2
    assert {proposal.proposal_type for proposal in learning_report.proposals} == {
        "guideline_profile_change_candidate",
        "timekeeper_rate_candidate",
    }
    assert all(
        proposal.status == "blocked_until_reviewed_outcome"
        for proposal in learning_report.proposals
    )
    assert gate_report.status == "candidate_learning_gate_ready"
    assert gate_report.carrier_learning_candidate_count == 2
    assert all(
        candidate.status == "blocked_until_reviewed_learning_gate"
        for candidate in gate_report.candidates
    )

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=runtime_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-reviewed-signal",
        generated_at="2026-07-04T00:00:00Z",
    )
    discrimination_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-discrimination-harassment-clean.v0_1"
    )
    reviewed_signal = next(
        item
        for item in discrimination_case.items
        if item.loop_type == "reviewed_learning_gate" and item.input_role == "one_of_signal"
    )

    assert report.invalid_input_count == 0
    assert reviewed_signal.input_status == "ready"
    assert reviewed_signal.selected_alternative_artifacts == [
        "carrier_rejection_learning_report.json"
    ]
    assert reviewed_signal.validation_model == "CarrierRejectionLearningReport"
    assert "At least one reviewed learning signal validated" in reviewed_signal.validation_message
    assert "reviewed_learning_signal_input_candidate" in (
        reviewed_signal.candidate_exception_lake_labels
    )


def test_labor_employment_wage_hour_reviewed_learning_signal_runs_and_validates(
    repo_root,
    tmp_path,
):
    chain = _run_wage_hour_carrier_learning_chain(repo_root, tmp_path)
    runtime_root = tmp_path / "runtime-wage-hour-reviewed-learning-input-pack"
    anchors = _stage_wage_hour_case_anchors(repo_root, runtime_root)
    learning_report_path = write_json(
        runtime_root / "runtime" / "carrier_rejection_learning_report.json",
        load_json(chain["learning_dir"] / "carrier_rejection_learning_report.json"),
    )
    manifest_path = _wage_hour_reviewed_learning_signal_manifest(
        runtime_root,
        anchors,
        learning_report_path,
    )
    review_packet = CarrierRejectionReviewPacket.model_validate(
        load_json(chain["review_dir"] / "carrier_rejection_review_packet.json")
    )
    learning_report = CarrierRejectionLearningReport.model_validate(load_json(learning_report_path))
    gate_report = ReviewedLearningGateReport.model_validate(
        load_json(chain["gate_dir"] / "reviewed_learning_gate_report.json")
    )

    assert review_packet.status == "ready_for_human_review"
    assert review_packet.remediation_case_count == 1
    assert review_packet.total_financial_exposure == 1200
    assert {note.scope for note in review_packet.red_team_notes} >= {"boundary", "learning_loop"}
    assert {item.recommended_action for item in review_packet.recommendations} == {
        "appeal_review_required"
    }
    assert {item.priority for item in review_packet.recommendations} == {"high"}
    assert {
        candidate
        for item in review_packet.recommendations
        for candidate in item.learning_disposition_candidates
    } == {"template_mapping_candidate", "validation_rule_candidate"}
    assert learning_report.status == "candidate_learning_ready_for_review"
    assert learning_report.proposal_count == 2
    assert {proposal.proposal_type for proposal in learning_report.proposals} == {
        "template_mapping_candidate",
        "validation_rule_candidate",
    }
    assert {proposal.target_learning_loop for proposal in learning_report.proposals} == {
        "template_mapping",
        "validation_rule",
    }
    assert all(
        proposal.status == "blocked_until_reviewed_outcome"
        for proposal in learning_report.proposals
    )
    assert gate_report.status == "candidate_learning_gate_ready"
    assert gate_report.carrier_learning_candidate_count == 2
    assert gate_report.target_learning_loops == ["template_mapping", "validation_rule"]
    assert gate_report.target_owners == ["LawFirm-os-intake"]
    assert all(
        candidate.status == "blocked_until_reviewed_learning_gate"
        for candidate in gate_report.candidates
    )

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=runtime_root,
        out_dir=tmp_path / "le-wage-hour-input-pack-reviewed-signal",
        generated_at="2026-07-04T00:00:00Z",
    )
    wage_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-wage-hour-clean.v0_1"
    )
    reviewed_signal = next(
        item
        for item in wage_case.items
        if item.loop_type == "reviewed_learning_gate" and item.input_role == "one_of_signal"
    )

    assert report.invalid_input_count == 0
    assert reviewed_signal.input_status == "ready"
    assert reviewed_signal.selected_alternative_artifacts == [
        "carrier_rejection_learning_report.json"
    ]
    assert reviewed_signal.validation_model == "CarrierRejectionLearningReport"
    assert "At least one reviewed learning signal validated" in reviewed_signal.validation_message
    assert "reviewed_learning_signal_input_candidate" in (
        reviewed_signal.candidate_exception_lake_labels
    )


def test_labor_employment_reviewed_learning_signal_rejects_wrong_case_report(
    repo_root,
    tmp_path,
):
    chain = _run_discrimination_carrier_learning_chain(repo_root, tmp_path)
    runtime_root = tmp_path / "runtime-wrong-case-reviewed-learning-input-pack"
    anchors = _stage_discrimination_case_anchors(repo_root, runtime_root)
    wrong_case_learning_report = load_json(
        chain["learning_dir"] / "carrier_rejection_learning_report.json"
    )
    wrong_case_learning_report["budget_proposal_id"] = "wrong-budget-proposal-id"
    learning_report_path = write_json(
        runtime_root / "runtime" / "wrong_case_carrier_rejection_learning_report.json",
        wrong_case_learning_report,
    )
    manifest_path = _reviewed_learning_signal_manifest(
        runtime_root,
        anchors,
        learning_report_path,
    )

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=runtime_root,
        out_dir=tmp_path / "le-budget-outcome-replay-input-pack-wrong-case-signal",
        generated_at="2026-07-04T00:00:00Z",
    )
    discrimination_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-discrimination-harassment-clean.v0_1"
    )
    reviewed_signal = next(
        item
        for item in discrimination_case.items
        if item.loop_type == "reviewed_learning_gate" and item.input_role == "one_of_signal"
    )

    assert report.status == "blocked_by_labor_employment_budget_replay_input_pack"
    assert report.invalid_input_count == 1
    assert reviewed_signal.input_status == "invalid"
    assert "budget_proposal_id" in reviewed_signal.validation_message
    assert "wrong-budget-proposal-id" in reviewed_signal.validation_message


def test_labor_employment_wage_hour_reviewed_learning_signal_rejects_wrong_family_report(
    repo_root,
    tmp_path,
):
    discrimination_chain = _run_discrimination_carrier_learning_chain(repo_root, tmp_path)
    runtime_root = tmp_path / "runtime-wage-hour-wrong-family-reviewed-learning-input-pack"
    anchors = _stage_wage_hour_case_anchors(repo_root, runtime_root)
    wrong_family_learning_report_path = write_json(
        runtime_root / "runtime" / "wrong_family_carrier_rejection_learning_report.json",
        load_json(discrimination_chain["learning_dir"] / "carrier_rejection_learning_report.json"),
    )
    manifest_path = _wage_hour_reviewed_learning_signal_manifest(
        runtime_root,
        anchors,
        wrong_family_learning_report_path,
    )

    report, _ = run_labor_employment_budget_outcome_replay_input_pack_audit(
        builder_binding_report_path=_builder_binding_report(repo_root, tmp_path),
        input_pack_manifest_path=manifest_path,
        repo_root=runtime_root,
        out_dir=tmp_path / "le-wage-hour-input-pack-wrong-family-signal",
        generated_at="2026-07-04T00:00:00Z",
    )
    wage_case = next(
        case
        for case in report.cases
        if case.learning_fixture_id == "le-learning-wage-hour-clean.v0_1"
    )
    reviewed_signal = next(
        item
        for item in wage_case.items
        if item.loop_type == "reviewed_learning_gate" and item.input_role == "one_of_signal"
    )

    assert report.status == "blocked_by_labor_employment_budget_replay_input_pack"
    assert report.invalid_input_count == 1
    assert reviewed_signal.input_status == "invalid"
    assert "budget_proposal_id" in reviewed_signal.validation_message
    assert "le-budget-discrimination-harassment-clean.v0_1" in (reviewed_signal.validation_message)
    assert "le-budget-wage-hour-clean.v0_1" in reviewed_signal.validation_message


def test_learning_report_count_invariants_fail_closed(repo_root, tmp_path):
    chain = _run_discrimination_carrier_learning_chain(repo_root, tmp_path)
    bad_learning_report = load_json(
        chain["learning_dir"] / "carrier_rejection_learning_report.json"
    )
    bad_learning_report["proposal_count"] += 1
    bad_gate_report = load_json(chain["gate_dir"] / "reviewed_learning_gate_report.json")
    bad_gate_report["candidate_count"] += 1

    with pytest.raises(ValueError, match="proposal_count mismatch"):
        CarrierRejectionLearningReport.model_validate(bad_learning_report)
    with pytest.raises(ValueError, match="candidate_count mismatch"):
        ReviewedLearningGateReport.model_validate(bad_gate_report)
