from lawfirm_os_intake.labor_employment_budget_outcome_replay_generation import (
    run_labor_employment_complete_replay_generation,
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
