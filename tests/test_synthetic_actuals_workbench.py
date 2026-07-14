"""Tests for the synthetic-only actuals variance workbench."""

from copy import deepcopy
import json

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.synthetic_actuals_workbench import (
    ACTUALS_SOURCE_REF,
    BUDGET_PROPOSAL_REF,
    SYNTHETIC_ACTUALS_WORKBENCH_REPORT_FILENAME,
    _build_synthetic_actuals_workbench_report,
    build_synthetic_actuals_workbench_report,
    run_synthetic_actuals_workbench,
)
from lawfirm_os_intake.util import load_json


FIXED_GENERATED_AT = "2026-07-13T00:00:00Z"


def _paths(repo_root):
    return repo_root / BUDGET_PROPOSAL_REF, repo_root / ACTUALS_SOURCE_REF


def _write_actuals(path, payload):
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _actuals(repo_root):
    return load_json(repo_root / ACTUALS_SOURCE_REF)


def test_actuals_workbench_renders_reconciled_epli_candidate_packet(tmp_path, repo_root):
    report, run_dir = run_synthetic_actuals_workbench(
        repo_root=repo_root,
        out_dir=tmp_path / "workbench",
        generated_at=FIXED_GENERATED_AT,
    )

    assert report.status == "synthetic_actuals_workbench_ready_for_review"
    assert report.actuals_source_id == "le-actuals-epli-carrier-clean.v0_1"
    assert report.comparison.comparison_budget_state == "original_proposal"
    assert report.comparison.total_budgeted == 54090.0
    assert report.comparison.total_actual == 60350.0
    assert report.comparison.total_variance_amount == 6260.0
    assert report.comparison.total_variance_percent == 11.57
    assert report.phase_budgeted_total == report.code_budgeted_total == 54090.0
    assert report.phase_actual_total == report.code_actual_total == 60350.0
    assert report.phase_row_count == 5
    assert report.code_row_count == 9
    assert {
        row.phase_id
        for row in report.comparison.phase_comparisons
        if row.status == "over_threshold"
    } == {
        "L300",
        "L500",
    }
    assert {
        row.code for row in report.comparison.code_comparisons if row.status == "over_threshold"
    } == {
        "L330",
        "E112",
        "E124",
    }
    assert report.failed_check_count == 0
    assert report.data_origin == "synthetic"
    assert report.external_writes_performed is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.silent_learning_performed is False
    assert load_json(run_dir / SYNTHETIC_ACTUALS_WORKBENCH_REPORT_FILENAME) == report.model_dump(
        mode="json"
    )


def test_ui_actuals_fixture_is_the_exact_audited_epli_render(repo_root):
    expected = build_synthetic_actuals_workbench_report(
        repo_root=repo_root,
        generated_at=FIXED_GENERATED_AT,
    )
    fixture = (
        repo_root
        / "apps/legal-intake-budget/src/fixtures/demo-synthetic-actuals-workbench-report.json"
    )

    assert load_json(fixture) == expected.model_dump(mode="json")


def test_actuals_workbench_fails_closed_when_code_view_does_not_reconcile(tmp_path, repo_root):
    budget_path, _ = _paths(repo_root)
    payload = deepcopy(_actuals(repo_root))
    payload["actuals_by_code"]["L330"]["fees"] += 1
    actuals_path = tmp_path / "mismatched-code-actuals.json"
    _write_actuals(actuals_path, payload)

    report = _build_synthetic_actuals_workbench_report(
        budget_path=budget_path,
        actuals_path=actuals_path,
        generated_at=FIXED_GENERATED_AT,
    )

    assert report.status == "blocked_by_synthetic_actuals_workbench"
    assert "code_actual_total_reconciles" in {
        check.check_id for check in report.checks if check.status == "failed"
    }
    assert report.phase_actual_total == report.comparison.total_actual
    assert report.code_actual_total != report.comparison.total_actual


def test_actuals_workbench_blocks_partial_or_unbudgeted_actuals(tmp_path, repo_root):
    budget_path, _ = _paths(repo_root)
    partial = deepcopy(_actuals(repo_root))
    del partial["actuals_by_phase"]["L500"]
    partial_path = tmp_path / "partial-actuals.json"
    _write_actuals(partial_path, partial)
    partial_report = _build_synthetic_actuals_workbench_report(
        budget_path=budget_path,
        actuals_path=partial_path,
        generated_at=FIXED_GENERATED_AT,
    )
    assert partial_report.status == "blocked_by_synthetic_actuals_workbench"
    assert "complete_actuals_coverage" in {
        check.check_id for check in partial_report.checks if check.status == "failed"
    }

    unbudgeted = deepcopy(_actuals(repo_root))
    unbudgeted["actuals_by_phase"]["L599"] = {"fees": 25, "expenses": 0}
    unbudgeted_path = tmp_path / "unbudgeted-actuals.json"
    _write_actuals(unbudgeted_path, unbudgeted)
    unbudgeted_report = _build_synthetic_actuals_workbench_report(
        budget_path=budget_path,
        actuals_path=unbudgeted_path,
        generated_at=FIXED_GENERATED_AT,
    )
    assert unbudgeted_report.status == "blocked_by_synthetic_actuals_workbench"
    assert "no_unbudgeted_actuals" in {
        check.check_id for check in unbudgeted_report.checks if check.status == "failed"
    }


def test_actuals_workbench_cli_uses_fixed_synthetic_source_and_no_writes(
    tmp_path, repo_root, capsys
):
    exit_code = main(
        [
            "build-synthetic-actuals-workbench",
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "workbench"),
            "--generated-at",
            FIXED_GENERATED_AT,
        ]
    )

    output = json.loads(capsys.readouterr().out)
    assert exit_code == 0
    assert output["status"] == "synthetic_actuals_workbench_ready_for_review"
    assert output["phase_row_count"] == 5
    assert output["code_row_count"] == 9
    assert output["external_writes_performed"] is False
    assert output["lake_write_performed"] is False
    assert output["sqlite_write_performed"] is False
    assert output["budget_submission_authorized"] is False
    assert output["matter_opening_authorized"] is False
