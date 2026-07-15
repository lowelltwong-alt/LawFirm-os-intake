from lawfirm_os_intake.labor_employment_budget_outcome_replay_generation import (
    run_labor_employment_complete_replay_generation,
    run_labor_employment_partial_actuals_replay_generation,
)
from lawfirm_os_intake.models import BudgetLearningLoopReport
from lawfirm_os_intake.util import load_json


def test_complete_replay_generator_materializes_only_complete_synthetic_cases(repo_root, tmp_path):
    manifest_path = run_labor_employment_complete_replay_generation(
        repo_root=repo_root,
        out_dir=tmp_path / "complete-replay",
    )
    manifest = load_json(manifest_path)

    assert manifest["status"] == "candidate_complete_replay_generation"
    assert len(manifest["cases"]) == 3
    assert manifest["candidate_only"] is True
    assert manifest["synthetic_only"] is True
    assert manifest["external_writes_performed"] is False
    assert {case["learning_fixture_id"] for case in manifest["cases"]} == {
        "le-learning-discrimination-harassment-clean.v0_1",
        "le-learning-wage-hour-clean.v0_1",
        "le-learning-epli-carrier-clean.v0_1",
    }
    for case in manifest["cases"]:
        report = BudgetLearningLoopReport.model_validate(
            load_json(case["budget_learning_loop_report_ref"])
        )
        assert report.candidate_only is True
        assert report.synthetic_only is True
        assert report.lake_write_performed is False
        assert report.external_writes_performed is False


def test_partial_actuals_generator_does_not_fabricate_carrier_or_aggregate_evidence(
    repo_root, tmp_path
):
    manifest = load_json(
        run_labor_employment_partial_actuals_replay_generation(
            repo_root=repo_root,
            out_dir=tmp_path / "partial-actuals-replay",
        )
    )

    assert manifest["status"] == "candidate_partial_actuals_replay_generation"
    assert len(manifest["cases"]) == 1
    case = manifest["cases"][0]
    assert case["learning_fixture_id"] == "le-learning-class-collective-clean.v0_1"
    assert case["carrier_rejection_generated"] is False
    assert case["aggregate_learning_loop_generated"] is False
    assert case["budget_actual_comparison_report_ref"]
    assert manifest["external_writes_performed"] is False
