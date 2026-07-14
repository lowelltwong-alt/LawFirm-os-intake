import json

import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import SyntheticRejectionAppealWorkbenchReport
from lawfirm_os_intake.synthetic_rejection_appeal_workbench import (
    REPORT_FILENAME,
    WORKBOOK_FILENAME,
    _safe_text,
    build_synthetic_rejection_appeal_workbench_report,
    run_synthetic_rejection_appeal_workbench,
)
from lawfirm_os_intake.util import load_json


FIXED_TIME = "2026-07-14T00:00:00Z"


def test_rejection_appeal_workbench_replays_synthetic_epli_chain(tmp_path, repo_root):
    report, out_dir = run_synthetic_rejection_appeal_workbench(
        repo_root=repo_root, out_dir=tmp_path / "workbench", generated_at=FIXED_TIME
    )
    assert report.status == "synthetic_rejection_appeal_workbench_ready_for_review"
    assert len(report.cases) == 2
    assert report.total_disputed_amount == 3900.0
    assert report.total_recovered_amount == 900.0
    assert report.total_write_down_amount == 1200.0
    assert report.failed_check_count == 0
    assert all(case.source_ref_count > 0 for case in report.cases)
    assert all(
        not proposal.silent_learning_performed for proposal in report.learning_report.proposals
    )
    assert load_json(out_dir / REPORT_FILENAME) == report.model_dump(mode="json")
    assert (out_dir / WORKBOOK_FILENAME).is_file()


def test_rejection_appeal_workbench_model_rejects_tampered_financial_total(repo_root):
    payload = build_synthetic_rejection_appeal_workbench_report(
        repo_root=repo_root, generated_at=FIXED_TIME
    ).model_dump(mode="json")
    payload["total_recovered_amount"] += 1
    with pytest.raises(ValueError, match="recovered total must match ledger"):
        SyntheticRejectionAppealWorkbenchReport.model_validate(payload)


def test_rejection_appeal_workbench_is_deterministic_for_pinned_synthetic_inputs(repo_root):
    first = build_synthetic_rejection_appeal_workbench_report(
        repo_root=repo_root, generated_at=FIXED_TIME
    )
    second = build_synthetic_rejection_appeal_workbench_report(
        repo_root=repo_root, generated_at=FIXED_TIME
    )

    assert second.model_dump(mode="json") == first.model_dump(mode="json")


@pytest.mark.parametrize("value", ["=formula()", "+formula()", "-formula()", "@formula()"])
def test_rejection_appeal_workbench_escapes_formula_like_spreadsheet_text(value):
    assert _safe_text(value) == f"'{value}"


def test_rejection_appeal_workbench_cli_has_no_submission_or_learning_write(
    tmp_path, repo_root, capsys
):
    code = main(
        [
            "build-synthetic-rejection-appeal-workbench",
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path),
            "--generated-at",
            FIXED_TIME,
        ]
    )
    result = json.loads(capsys.readouterr().out)
    assert code == 0
    assert result["appeal_submission_performed"] is False
    assert result["lake_write_performed"] is False
    assert result["silent_learning_performed"] is False
