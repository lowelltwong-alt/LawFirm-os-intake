"""Independent portfolio acceptance check for the synthetic budget workbenches."""

import shutil

import yaml

from lawfirm_os_intake.synthetic_actuals_workbench import build_synthetic_actuals_workbench_report
from lawfirm_os_intake.synthetic_budget_configuration_change import (
    build_synthetic_budget_configuration_change_package,
)
from lawfirm_os_intake.synthetic_budget_configuration_workbench import (
    SOURCE_SPECS,
    build_synthetic_budget_configuration_workbench_report,
)
from lawfirm_os_intake.synthetic_budget_input_workbench import (
    build_synthetic_budget_input_workbench_report,
)
from lawfirm_os_intake.synthetic_configuration_regeneration_binding import (
    build_synthetic_configuration_regeneration_binding_report,
)
from lawfirm_os_intake.synthetic_guideline_projection_workbench import (
    SOURCE_REFS,
    build_synthetic_guideline_projection_workbench_report,
)
from lawfirm_os_intake.synthetic_rate_card_workbench import (
    build_synthetic_rate_card_workbench_report,
)
from lawfirm_os_intake.synthetic_rejection_appeal_workbench import (
    build_synthetic_rejection_appeal_workbench_report,
)


FIXED_TIME = "2026-07-14T00:00:00Z"


def _candidate_root(repo_root, root):
    refs = {ref for _, ref, _ in SOURCE_SPECS} | {ref for _, _, ref in SOURCE_REFS}
    for source_ref in refs:
        target = root / source_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / source_ref, target)
    rate_path = root / "config/synthetic-carrier-rate-card.yaml"
    rate_card = yaml.safe_load(rate_path.read_text(encoding="utf-8"))
    rate_card["carriers"]["synthetic-carrier-a"]["schedule"]["NV"]["partner"] = 455
    rate_path.write_text(yaml.safe_dump(rate_card, sort_keys=False), encoding="utf-8")


def test_synthetic_budget_workbench_portfolio_acceptance(tmp_path, repo_root):
    candidate_root = tmp_path / "candidate"
    _candidate_root(repo_root, candidate_root)
    reports = [
        build_synthetic_rate_card_workbench_report(
            repo_root / "config/synthetic-carrier-rate-card.yaml",
            repo_root=repo_root,
            generated_at=FIXED_TIME,
        ),
        build_synthetic_budget_input_workbench_report(repo_root=repo_root, generated_at=FIXED_TIME),
        build_synthetic_guideline_projection_workbench_report(
            repo_root=repo_root, generated_at=FIXED_TIME
        ),
        build_synthetic_actuals_workbench_report(repo_root=repo_root, generated_at=FIXED_TIME),
        build_synthetic_rejection_appeal_workbench_report(
            repo_root=repo_root, generated_at=FIXED_TIME
        ),
        build_synthetic_budget_configuration_workbench_report(
            repo_root=repo_root, generated_at=FIXED_TIME
        ),
        build_synthetic_budget_configuration_change_package(
            baseline_root=repo_root, candidate_root=candidate_root, generated_at=FIXED_TIME
        ),
        build_synthetic_configuration_regeneration_binding_report(
            baseline_root=repo_root, candidate_root=candidate_root, generated_at=FIXED_TIME
        ),
    ]
    assert all("ready" in report.status for report in reports)
    assert all(getattr(report, "candidate_only", True) for report in reports)
    assert all(not getattr(report, "external_writes_performed", False) for report in reports)
    assert all(not getattr(report, "lake_write_performed", False) for report in reports)
    assert all(not getattr(report, "sqlite_write_performed", False) for report in reports)
    assert all(not getattr(report, "budget_submission_authorized", False) for report in reports)
    assert all(not getattr(report, "matter_opening_authorized", False) for report in reports)
    assert all(not getattr(report, "silent_learning_performed", False) for report in reports)
    assert reports[-2].changed_source_ids == ["rate_card"]
    assert reports[-1].changed_source_ids == ["rate_card"]
