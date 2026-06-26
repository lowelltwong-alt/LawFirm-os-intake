from copy import deepcopy

import pytest

from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import CarrierRejectionCaptureSourceBundle, HumanConfirmation
from lawfirm_os_intake.util import load_json, write_json
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
