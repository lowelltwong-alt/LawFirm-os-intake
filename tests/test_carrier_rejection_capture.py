from copy import deepcopy

import pytest

from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    CarrierRejectionCaptureSourceBundle,
    CarrierRejectionDecisionLedgerReport,
    HumanConfirmation,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _budget(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw_confirmation = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw_confirmation["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw_confirmation),
    )
    confirmation_path = write_json(
        tmp_path / "human_confirmation.json",
        confirmation.model_dump(mode="json"),
    )
    budget, _ = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    budget_path = write_json(tmp_path / "budget.json", budget.model_dump(mode="json"))
    return budget, budget_path


def _fixture_path(repo_root):
    return (
        repo_root / "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json"
    )


def _bound_fixture(repo_root, budget):
    raw = deepcopy(load_json(_fixture_path(repo_root)))
    raw["budget_proposal_id"] = budget.budget_proposal_id
    raw["preflight_packet_id"] = budget.preflight_packet_id
    for expected in raw["expected_responses"]:
        expected["budget_proposal_id"] = budget.budget_proposal_id
    for notice in raw["notices"]:
        notice["budget_proposal_id"] = budget.budget_proposal_id
    return raw


def test_carrier_rejection_capture_reconciles_duplicates_missing_unlinked_and_appeal(
    tmp_path,
    repo_root,
):
    budget, budget_path = _budget(tmp_path, repo_root)

    report, run_dir = run_carrier_rejection_capture(
        budget_path,
        _fixture_path(repo_root),
        tmp_path / "carrier-rejections",
    )

    assert report.status == "dry_run_ready_for_review"
    assert report.expected_response_count == 3
    assert report.reconciled_response_count == 2
    assert report.missing_response_count == 1
    assert report.unlinked_notice_count == 1
    assert report.duplicate_notice_count == 1
    assert report.parser_failure_count == 1
    assert report.appeal_result_count == 1
    assert report.not_authorized_for_lake_write is True
    assert report.not_authorized_for_external_submission is True
    assert report.external_writes_performed is False

    labels = {case.local_event_label for case in report.remediation_cases}
    assert {
        "carrier_preapproval_missing",
        "carrier_response_missing_after_sla",
        "carrier_rejection_unlinked",
        "carrier_rejection_parse_failed",
    } <= labels

    duplicate_case = next(
        case
        for case in report.remediation_cases
        if case.local_event_label == "carrier_preapproval_missing"
    )
    assert duplicate_case.duplicate_notice_ids == ["notice-email-001", "notice-portal-001"]
    assert duplicate_case.status == "appeal_result_captured"
    assert duplicate_case.linked_appeal_result_ids == ["appeal-result-001"]
    assert duplicate_case.silent_learning_performed is False

    candidate_labels = {
        candidate.local_event_label for candidate in report.exception_lake_candidates
    }
    assert {
        "carrier_preapproval_missing",
        "carrier_rejection_duplicate_notice",
        "carrier_response_missing_after_sla",
        "carrier_rejection_unlinked",
        "carrier_rejection_parse_failed",
        "carrier_appeal_result_received",
        "carrier_rejection_learning_candidate",
    } <= candidate_labels
    assert all(not candidate.raw_payload_included for candidate in report.exception_lake_candidates)
    assert all(
        candidate.canonical_promotion_required for candidate in report.exception_lake_candidates
    )
    assert (run_dir / "carrier_rejection_reconciliation_report.json").is_file()
    assert (run_dir / "carrier_rejection_remediation_cases.json").is_file()
    assert (run_dir / "carrier_rejection_exception_lake_candidates.jsonl").is_file()

    ledger = CarrierRejectionDecisionLedgerReport.model_validate(
        load_json(run_dir / "carrier_rejection_decision_ledger_report.json")
    )
    ledger_rows = load_jsonl(run_dir / "carrier_rejection_decision_ledger.jsonl")
    event_kinds = {event.event_kind for event in ledger.events}

    assert ledger.status == "decision_ledger_ready_for_review"
    assert ledger.reconciliation_report_id == report.reconciliation_report_id
    assert ledger.source_bundle_id == "synthetic-carrier-rejection-capture-001"
    assert ledger.entry_count == len(ledger_rows)
    assert ledger.remediation_case_event_count == len(report.remediation_cases)
    assert ledger.pending_decision_event_count == 3
    assert ledger.appeal_result_event_count == 1
    assert ledger.financial_outcome_event_count == 1
    assert ledger.total_disputed_amount == 21950.0
    assert ledger.total_recovered_amount == 8000.0
    assert ledger.total_write_down_amount == 7000.0
    assert {
        "carrier_rejection_notice_captured",
        "carrier_response_missing_after_sla",
        "carrier_rejection_unlinked_notice",
        "carrier_rejection_parse_failed",
        "carrier_duplicate_notice_collapsed",
        "carrier_fix_or_appeal_decision_pending",
        "carrier_appeal_result_received",
        "carrier_financial_outcome_recorded",
    } <= event_kinds
    financial_event = next(
        event for event in ledger.events if event.event_kind == "carrier_financial_outcome_recorded"
    )
    assert financial_event.appeal_result_id == "appeal-result-001"
    assert financial_event.appealed_amount == 15000.0
    assert financial_event.recovered_amount == 8000.0
    assert financial_event.write_down_amount == 7000.0
    assert financial_event.remaining_write_down_amount == 7000.0
    assert all(event.requires_exception_lake_admission_review for event in ledger.events)
    assert ledger.lake_write_performed is False
    assert ledger.sqlite_write_performed is False
    assert ledger.external_writes_performed is False
    assert ledger.appeal_submission_performed is False
    assert ledger.silent_learning_performed is False
    assert (run_dir / "carrier_rejection_decision_ledger_report.md").is_file()


def test_carrier_rejection_capture_blocks_missing_followup_owner_or_due_date(
    tmp_path,
    repo_root,
):
    budget, budget_path = _budget(tmp_path, repo_root)
    raw = _bound_fixture(repo_root, budget)
    raw["notices"][0]["human_owner"] = None
    raw["notices"][0]["followup_due_at"] = None
    raw["notices"][1]["human_owner"] = None
    raw["notices"][1]["followup_due_at"] = None
    raw["notices"][2]["human_owner"] = None
    raw["notices"][2]["followup_due_at"] = None
    source_path = write_json(tmp_path / "carrier_rejections_missing_followup.json", raw)

    report, _ = run_carrier_rejection_capture(
        budget_path,
        source_path,
        tmp_path / "carrier-rejections",
    )

    assert report.status == "blocked_missing_required_followup"
    assert any("missing human owner" in gap for gap in report.gap_report)
    assert any("missing follow-up due date" in gap for gap in report.gap_report)
    ledger = CarrierRejectionDecisionLedgerReport.model_validate(
        load_json(tmp_path / "carrier-rejections" / "carrier_rejection_decision_ledger_report.json")
    )
    assert ledger.status == "decision_ledger_blocked_missing_followup"
    assert ledger.lake_write_performed is False


def test_carrier_rejection_capture_is_synthetic_only(tmp_path, repo_root):
    budget, _ = _budget(tmp_path, repo_root)
    raw = _bound_fixture(repo_root, budget)
    raw["data_origin"] = "production"

    with pytest.raises(ValueError, match="synthetic-only"):
        CarrierRejectionCaptureSourceBundle.model_validate(raw)


def test_carrier_rejection_capture_rejects_budget_mismatch(tmp_path, repo_root):
    budget, budget_path = _budget(tmp_path, repo_root)
    raw = _bound_fixture(repo_root, budget)
    raw["budget_proposal_id"] = "wrong-budget"
    source_path = write_json(tmp_path / "carrier_rejections_wrong_budget.json", raw)

    with pytest.raises(ValueError, match="does not match budget"):
        run_carrier_rejection_capture(
            budget_path,
            source_path,
            tmp_path / "carrier-rejections",
        )


def test_carrier_rejection_capture_cli_reports_decision_ledger(tmp_path, repo_root, capsys):
    _, budget_path = _budget(tmp_path, repo_root)

    exit_code = main(
        [
            "capture-carrier-rejections",
            "--budget",
            str(budget_path),
            "--source-bundle",
            str(_fixture_path(repo_root)),
            "--out-dir",
            str(tmp_path / "carrier-rejections-cli"),
        ]
    )
    captured = capsys.readouterr()
    ledger = CarrierRejectionDecisionLedgerReport.model_validate(
        load_json(
            tmp_path / "carrier-rejections-cli" / "carrier_rejection_decision_ledger_report.json"
        )
    )

    assert exit_code == 0
    assert ledger.entry_count > 0
    assert '"decision_ledger_entry_count":' in captured.out
    assert '"total_recovered_amount": 8000.0' in captured.out
    assert '"total_write_down_amount": 7000.0' in captured.out
    assert '"sqlite_write_performed": false' in captured.out
    assert '"appeal_submission_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
