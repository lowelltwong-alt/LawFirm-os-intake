import json
import shutil

import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import SyntheticRejectionAppealWorkbenchReport
from lawfirm_os_intake.synthetic_rejection_appeal_workbench import (
    REPORT_FILENAME,
    BUDGET_REF,
    BUNDLE_REF,
    PINNED_SOURCE_MANIFEST_REF,
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


def test_rejection_appeal_workbench_case_financials_match_synthetic_gold(repo_root):
    report = build_synthetic_rejection_appeal_workbench_report(
        repo_root=repo_root, generated_at=FIXED_TIME
    )
    gold = load_json(
        repo_root
        / "fixtures/synthetic/rejection-appeal-workbench/epli-case-financials.expected.json"
    )

    assert gold["data_origin"] == "synthetic"
    assert gold["candidate_only"] is True
    assert gold["source_bundle_ref"] == report.source_bundle_ref
    actual_by_case = {
        case.remediation_case_id: {
            "appeal_result_ids": case.appeal_result_ids,
            "recovered_amount": case.recovered_amount,
            "write_down_amount": case.write_down_amount,
        }
        for case in report.cases
    }
    expected_by_case = {
        case["remediation_case_id"]: {
            "appeal_result_ids": case["appeal_result_ids"],
            "recovered_amount": case["recovered_amount"],
            "write_down_amount": case["write_down_amount"],
        }
        for case in gold["expected_case_financials"]
    }
    assert actual_by_case == expected_by_case
    assert sum(case.recovered_amount for case in report.cases) == report.total_recovered_amount
    assert sum(case.write_down_amount for case in report.cases) == report.total_write_down_amount
    assert gold["expected_ledger_totals"] == {
        "recovered_amount": report.total_recovered_amount,
        "write_down_amount": report.total_write_down_amount,
    }


def test_rejection_appeal_workbench_blocks_pinned_source_digest_drift(tmp_path, repo_root):
    candidate_root = tmp_path / "candidate"
    for source_ref in (BUDGET_REF, BUNDLE_REF, PINNED_SOURCE_MANIFEST_REF):
        source = repo_root / source_ref
        target = candidate_root / source_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    bundle_path = candidate_root / BUNDLE_REF
    bundle_path.write_text(bundle_path.read_text(encoding="utf-8") + " ", encoding="utf-8")

    report = build_synthetic_rejection_appeal_workbench_report(
        repo_root=candidate_root, generated_at=FIXED_TIME
    )

    assert report.status == "blocked_by_synthetic_rejection_appeal_workbench"
    assert "pinned_synthetic_source_hashes_match" in {
        check.check_id for check in report.checks if check.status == "failed"
    }


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


def test_rejection_appeal_workbench_case_financial_fix_preserves_no_write_boundary(repo_root):
    report = build_synthetic_rejection_appeal_workbench_report(
        repo_root=repo_root, generated_at=FIXED_TIME
    )

    assert report.appeal_submission_performed is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
