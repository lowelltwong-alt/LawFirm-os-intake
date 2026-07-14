import shutil

import yaml

from lawfirm_os_intake.synthetic_budget_configuration_workbench import SOURCE_SPECS
from lawfirm_os_intake.synthetic_configuration_regeneration_binding import (
    build_synthetic_configuration_regeneration_binding_report,
)
from lawfirm_os_intake.synthetic_guideline_projection_workbench import SOURCE_REFS


FIXED_TIME = "2026-07-14T00:00:00Z"


def _copy_required_sources(repo_root, root):
    refs = {ref for _, ref, _ in SOURCE_SPECS} | {ref for _, _, ref in SOURCE_REFS}
    for source_ref in refs:
        target = root / source_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / source_ref, target)


def test_regeneration_binding_matches_changed_rate_card_hash(tmp_path, repo_root):
    candidate = tmp_path / "candidate"
    _copy_required_sources(repo_root, candidate)
    path = candidate / "config/synthetic-carrier-rate-card.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    payload["carriers"]["synthetic-carrier-a"]["schedule"]["NV"]["partner"] = 455
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")

    report = build_synthetic_configuration_regeneration_binding_report(
        baseline_root=repo_root, candidate_root=candidate, generated_at=FIXED_TIME
    )

    assert report.status == "ready_for_review"
    assert report.changed_source_ids == ["rate_card"]
    assert report.failed_check_count == 0
    assert (
        report.candidate_projection_source_hashes["rate_card"]
        != report.candidate_projection_source_hashes["guideline"]
    )
    assert report.budget_recalculated is False
    assert report.external_writes_performed is False


def test_regeneration_binding_blocks_unconsumed_nonlinear_change(tmp_path, repo_root):
    candidate = tmp_path / "candidate"
    _copy_required_sources(repo_root, candidate)
    path = (
        candidate
        / "examples/synthetic/labor-employment/labor-employment-nonlinear-budget-templates.json"
    )
    payload = __import__("json").loads(path.read_text(encoding="utf-8"))
    payload["templates"][0]["phases"][0]["phase_order"] = 9
    path.write_text(__import__("json").dumps(payload), encoding="utf-8")

    report = build_synthetic_configuration_regeneration_binding_report(
        baseline_root=repo_root, candidate_root=candidate, generated_at=FIXED_TIME
    )

    assert report.status == "blocked"
    assert "changed_sources_consumed_by_projection" in {
        check.check_id for check in report.checks if check.status == "failed"
    }
