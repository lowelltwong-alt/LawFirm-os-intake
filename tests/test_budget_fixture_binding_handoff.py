from lawfirm_os_intake.budget_fixture_binding_handoff import (
    build_budget_fixture_binding_handoff_report,
    run_budget_fixture_binding_handoff,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetFixtureBindingCandidate,
    BudgetFixtureBindingCandidateReport,
    BudgetFixtureBindingHandoffReport,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


def _candidate(*, status="candidate_ready_for_fixture_update_review"):
    ready = status == "candidate_ready_for_fixture_update_review"
    return BudgetFixtureBindingCandidate(
        fixture_binding_candidate_id=f"fixturebinding-{status}",
        review_outcome_report_id="review-outcome-report-1",
        review_outcome_record_id="review-outcome-record-1",
        review_packet_id="review-packet-1",
        replay_execution_report_id="replay-execution-1",
        replay_case_id="replay-case-1",
        source_artifact_ref="examples/synthetic/budget-review/medmal-human-budget-review-change.json",
        artifact_kind="budget_review_fixture",
        approved_output_refs=[".lawfirm-os-intake/replay/budget_revision_report.json"]
        if ready
        else [],
        proposed_target_fixture_refs=[
            "examples/synthetic/budget-review/medmal-human-budget-review-change.json"
        ]
        if ready
        else [],
        proposed_binding_action=(
            "bind_replay_outputs_to_synthetic_fixture" if ready else "exclude_from_fixture_binding"
        ),
        status=status,
        why=["synthetic fixture-binding candidate for handoff tests"],
        required_human_steps=["human fixture update review"],
    )


def _candidate_report(*, status="candidate_ready_for_fixture_update_review"):
    candidate = _candidate(status=status)
    ready_count = int(status == "candidate_ready_for_fixture_update_review")
    if status == "candidate_ready_for_fixture_update_review":
        report_status = "fixture_binding_candidates_ready_for_review"
    elif status == "blocked_missing_approved_outputs":
        report_status = "blocked_missing_approved_outputs"
    else:
        report_status = "blocked_pending_approved_outcome"
    return BudgetFixtureBindingCandidateReport(
        fixture_binding_candidate_report_id=f"fixture-binding-report-{status}",
        review_packet_id="review-packet-1",
        review_outcome_report_id="review-outcome-report-1",
        review_outcome_record_id="review-outcome-record-1",
        replay_execution_report_id="replay-execution-1",
        replay_case_id="replay-case-1",
        source_review_packet_ref=".lawfirm-os-intake/replay/review_packet.json",
        source_review_outcome_report_ref=".lawfirm-os-intake/replay/outcome_report.json",
        status=report_status,
        candidate_count=1,
        ready_candidate_count=ready_count,
        blocked_candidate_count=1 - ready_count,
        candidates=[candidate],
        checks=[
            {
                "check_id": "synthetic_check",
                "status": "passed" if ready_count else "failed",
                "message": "synthetic check for handoff tests",
                "candidate_ids": [candidate.fixture_binding_candidate_id],
                "replay_case_ids": [candidate.replay_case_id],
            }
        ],
        required_next_gates=["human_fixture_update_review"],
        generated_at="2026-06-26T00:00:00Z",
    )


def test_fixture_binding_handoff_ready_candidate_needs_human_update_review():
    candidate_report = _candidate_report()
    report = build_budget_fixture_binding_handoff_report(
        candidate_report=candidate_report,
        candidate_report_ref="budget_fixture_binding_candidate_report.json",
    )
    item = report.handoff_items[0]

    assert report.status == "fixture_binding_handoff_ready_for_human_review"
    assert report.ready_item_count == 1
    assert report.blocked_item_count == 0
    assert item.disposition == "ready_for_human_fixture_update_review"
    assert item.target_owner == "LawFirm-os-intake"
    assert item.approved_output_refs
    assert item.proposed_target_fixture_refs
    assert any("separate fixture-update PR" in action for action in item.recommended_owner_actions)
    assert item.red_team_notes
    assert report.fixture_update_authorized is False
    assert report.fixture_update_pr_created is False
    assert report.fixture_files_mutated is False
    assert report.fixture_binding_applied is False
    assert report.downstream_learning_gate_allowed is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_fixture_binding_handoff_blocks_pending_approved_outcome():
    candidate_report = _candidate_report(status="blocked_pending_approved_outcome")
    report = build_budget_fixture_binding_handoff_report(
        candidate_report=candidate_report,
        candidate_report_ref="budget_fixture_binding_candidate_report.json",
    )
    item = report.handoff_items[0]

    assert report.status == "fixture_binding_handoff_blocked"
    assert report.ready_item_count == 0
    assert report.blocked_item_count == 1
    assert item.disposition == "blocked_pending_approved_outcome"
    assert item.approved_output_refs == []
    assert item.proposed_target_fixture_refs == []
    assert any("Do not update fixtures" in action for action in item.recommended_owner_actions)
    assert report.fixture_files_mutated is False
    assert report.silent_learning_performed is False


def test_fixture_binding_handoff_cli_writes_report(tmp_path, capsys):
    candidate_report_path = write_json(
        tmp_path / "budget_fixture_binding_candidate_report.json",
        _candidate_report().model_dump(mode="json"),
    )

    exit_code = main(
        [
            "build-budget-fixture-binding-handoff",
            "--fixture-binding-candidate-report",
            str(candidate_report_path),
            "--out-dir",
            str(tmp_path / "fixture-binding-handoff"),
        ]
    )
    captured = capsys.readouterr()
    report_path = (
        tmp_path / "fixture-binding-handoff" / "budget_fixture_binding_handoff_report.json"
    )
    notes_path = tmp_path / "fixture-binding-handoff" / "budget_fixture_binding_handoff_report.md"
    items_path = tmp_path / "fixture-binding-handoff" / "budget_fixture_binding_handoff_items.jsonl"
    report = BudgetFixtureBindingHandoffReport.model_validate(load_json(report_path))
    items = load_jsonl(items_path)

    assert exit_code == 0
    assert report.status == "fixture_binding_handoff_ready_for_human_review"
    assert report.handoff_item_output_ref == str(items_path)
    assert len(items) == 1
    assert '"fixture_update_authorized": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert "does not update fixtures" in notes_path.read_text(encoding="utf-8")


def test_run_fixture_binding_handoff_persists_jsonl(tmp_path):
    candidate_report_path = write_json(
        tmp_path / "budget_fixture_binding_candidate_report.json",
        _candidate_report(status="blocked_missing_approved_outputs").model_dump(mode="json"),
    )

    report, run_dir = run_budget_fixture_binding_handoff(
        fixture_binding_candidate_report_path=candidate_report_path,
        out_dir=tmp_path / "fixture-binding-handoff",
    )
    persisted = BudgetFixtureBindingHandoffReport.model_validate(
        load_json(run_dir / "budget_fixture_binding_handoff_report.json")
    )
    items = load_jsonl(run_dir / "budget_fixture_binding_handoff_items.jsonl")

    assert report.status == "fixture_binding_handoff_blocked"
    assert persisted.fixture_binding_handoff_report_id == report.fixture_binding_handoff_report_id
    assert persisted.handoff_item_output_ref == str(
        run_dir / "budget_fixture_binding_handoff_items.jsonl"
    )
    assert items[0]["disposition"] == "blocked_missing_approved_outputs"
    assert persisted.fixture_update_authorized is False
    assert persisted.fixture_files_mutated is False
