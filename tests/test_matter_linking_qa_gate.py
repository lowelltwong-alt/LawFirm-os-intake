from lawfirm_os_intake.cli import main
from lawfirm_os_intake.matter_linking_qa_gate import (
    MATTER_LINKING_QA_GATE_NOTES_FILENAME,
    MATTER_LINKING_QA_GATE_REPORT_FILENAME,
    run_matter_linking_qa_gate,
)
from lawfirm_os_intake.util import load_json


FIXED_TIME = "2026-07-04T00:00:00Z"


def test_matter_linking_qa_gate_replays_upfront_like_fixture_matrix(repo_root, tmp_path):
    report, run_dir = run_matter_linking_qa_gate(
        repo_root=repo_root,
        out_dir=tmp_path / "matter-linking-qa-gate",
        generated_at=FIXED_TIME,
    )
    cases = {case.case_id: case for case in report.cases}

    assert report.status == "matter_linking_qa_gate_ready_for_review"
    assert report.case_count == len(report.cases) == 5
    assert report.passed_case_count == 5
    assert report.failed_case_count == 0
    assert report.missing_coverage_tags == []
    assert report.observed_coverage_tag_count == report.required_coverage_tag_count
    assert set(cases) == {
        "ambiguous_same_sender_multi_case",
        "resolved_followup_split_candidate",
        "weak_only_followup_blocked",
        "resolved_single_candidate",
        "conflicting_identifier_blocked",
    }
    assert cases["weak_only_followup_blocked"].observed_status == (
        "blocked_matter_linking_preflight"
    )
    assert "weak_only_candidates_block_matter_linking" in (
        cases["weak_only_followup_blocked"].observed_failed_check_ids
    )
    assert cases["conflicting_identifier_blocked"].observed_status == (
        "blocked_matter_linking_preflight"
    )
    assert "conflicting_identifiers_block_linking" in (
        cases["conflicting_identifier_blocked"].observed_failed_check_ids
    )
    assert "matter_linking_qa_gate_candidate" in report.candidate_exception_lake_labels
    assert "no_lake_or_sqlite_write_from_matter_linking_qa_gate" in (report.required_next_gates)
    assert report.budget_amount_output_authorized is False
    assert report.matter_opening_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False
    assert (run_dir / MATTER_LINKING_QA_GATE_REPORT_FILENAME).is_file()
    assert (run_dir / MATTER_LINKING_QA_GATE_NOTES_FILENAME).is_file()
    assert all(
        (run_dir / "cases" / case_id / "matter_linking_preflight_report.json").is_file()
        for case_id in cases
    )


def test_matter_linking_qa_gate_cli_writes_report(repo_root, tmp_path, capsys):
    code = main(
        [
            "audit-matter-linking-qa-gate",
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "cli-qa-gate"),
            "--generated-at",
            FIXED_TIME,
        ]
    )
    captured = capsys.readouterr()
    payload = load_json(tmp_path / "cli-qa-gate" / MATTER_LINKING_QA_GATE_REPORT_FILENAME)

    assert code == 0
    assert payload["status"] == "matter_linking_qa_gate_ready_for_review"
    assert payload["case_count"] == 5
    assert payload["failed_case_count"] == 0
    assert payload["missing_coverage_tags"] == []
    assert '"matter_opening_authorized": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
