"""Tests for dry-run synthetic configuration change packages."""

import json
import shutil

import yaml

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.synthetic_budget_configuration_change import (
    REPORT_FILENAME,
    build_synthetic_budget_configuration_change_package,
    run_synthetic_budget_configuration_change_package,
)
from lawfirm_os_intake.synthetic_budget_configuration_workbench import SOURCE_SPECS
from lawfirm_os_intake.util import load_json


FIXED_TIME = "2026-07-14T00:00:00Z"


def _copy_sources(repo_root, root):
    for _, source_ref, _ in SOURCE_SPECS:
        destination = root / source_ref
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(repo_root / source_ref, destination)


def _candidate_with_one_rate_change(repo_root, root):
    _copy_sources(repo_root, root)
    card_path = root / "config/synthetic-carrier-rate-card.yaml"
    card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
    card["carriers"]["synthetic-carrier-a"]["schedule"]["NV"]["partner"] = 455
    card_path.write_text(yaml.safe_dump(card, sort_keys=False), encoding="utf-8")


def test_change_package_reports_one_source_bound_numeric_counterfactual(tmp_path, repo_root):
    candidate_root = tmp_path / "candidate"
    _candidate_with_one_rate_change(repo_root, candidate_root)
    report, out_dir = run_synthetic_budget_configuration_change_package(
        baseline_root=repo_root,
        candidate_root=candidate_root,
        out_dir=tmp_path / "out",
        generated_at=FIXED_TIME,
    )

    assert report.status == "synthetic_budget_configuration_change_ready_for_review"
    assert report.change_count == 1
    assert report.changed_source_ids == ["rate_card"]
    change = report.changes[0]
    assert change.config_path == "carriers.synthetic-carrier-a.schedule.NV.partner"
    assert change.baseline_value == 450.0
    assert change.candidate_value == 455.0
    assert change.delta == 5.0
    assert change.math_effect == "proposal_rate_fallback"
    assert report.budget_recalculated is False
    assert report.workbook_import_performed is False
    assert report.external_writes_performed is False
    assert load_json(out_dir / REPORT_FILENAME) == report.model_dump(mode="json")


def test_change_package_blocks_real_data_candidate(tmp_path, repo_root):
    candidate_root = tmp_path / "candidate"
    _candidate_with_one_rate_change(repo_root, candidate_root)
    card_path = candidate_root / "config/synthetic-carrier-rate-card.yaml"
    card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
    card["contains_real_negotiated_rates"] = True
    card_path.write_text(yaml.safe_dump(card, sort_keys=False), encoding="utf-8")

    report = build_synthetic_budget_configuration_change_package(
        baseline_root=repo_root, candidate_root=candidate_root, generated_at=FIXED_TIME
    )

    assert report.status == "blocked_by_synthetic_budget_configuration_change"
    assert "candidate_configuration_valid" in {
        check.check_id for check in report.checks if check.status == "failed"
    }


def test_change_package_blocks_structural_or_noop_candidate(tmp_path, repo_root):
    unchanged = build_synthetic_budget_configuration_change_package(
        baseline_root=repo_root, candidate_root=repo_root, generated_at=FIXED_TIME
    )
    assert unchanged.status == "blocked_by_synthetic_budget_configuration_change"
    assert "at_least_one_numeric_change" in {
        check.check_id for check in unchanged.checks if check.status == "failed"
    }

    candidate_root = tmp_path / "candidate"
    _candidate_with_one_rate_change(repo_root, candidate_root)
    card_path = candidate_root / "config/synthetic-carrier-rate-card.yaml"
    card = yaml.safe_load(card_path.read_text(encoding="utf-8"))
    del card["carriers"]["synthetic-carrier-a"]["schedule"]["NV"]["paralegal"]
    card_path.write_text(yaml.safe_dump(card, sort_keys=False), encoding="utf-8")
    structural = build_synthetic_budget_configuration_change_package(
        baseline_root=repo_root, candidate_root=candidate_root, generated_at=FIXED_TIME
    )
    assert structural.status == "blocked_by_synthetic_budget_configuration_change"
    assert "configuration_structure_unchanged" in {
        check.check_id for check in structural.checks if check.status == "failed"
    }


def test_change_package_cli_never_recalculates_or_imports(tmp_path, repo_root, capsys):
    candidate_root = tmp_path / "candidate"
    _candidate_with_one_rate_change(repo_root, candidate_root)
    code = main(
        [
            "compare-synthetic-budget-configuration",
            "--baseline-root",
            str(repo_root),
            "--candidate-root",
            str(candidate_root),
            "--out-dir",
            str(tmp_path / "out"),
            "--generated-at",
            FIXED_TIME,
        ]
    )
    payload = json.loads(capsys.readouterr().out)

    assert code == 0
    assert payload["change_count"] == 1
    assert payload["budget_recalculated"] is False
    assert payload["workbook_import_performed"] is False
    assert payload["external_writes_performed"] is False
