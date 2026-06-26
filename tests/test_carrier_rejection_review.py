from copy import deepcopy

from lawfirm_os_intake.carrier_rejection_review import run_carrier_rejection_review
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import CarrierRejectionReviewPacket, HumanConfirmation
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


def _reconciliation_report(tmp_path, repo_root):
    _, budget_path = _budget(tmp_path, repo_root)
    report, run_dir = run_carrier_rejection_capture(
        budget_path,
        _fixture_path(repo_root),
        tmp_path / "carrier-rejections",
    )
    return report, run_dir


def test_carrier_rejection_review_packet_surfaces_recommendations_and_red_team(
    tmp_path,
    repo_root,
):
    report, reconciliation_dir = _reconciliation_report(tmp_path, repo_root)

    packet, review_dir = run_carrier_rejection_review(
        reconciliation_dir / "carrier_rejection_reconciliation_report.json",
        tmp_path / "carrier-rejection-review",
    )

    assert packet.status == "ready_for_human_review"
    assert packet.reconciliation_report_id == report.reconciliation_report_id
    assert packet.remediation_case_count == 4
    assert packet.total_financial_exposure > 0
    assert packet.not_authorized_for_lake_write is True
    assert packet.not_authorized_for_external_submission is True
    assert packet.external_writes_performed is False
    assert packet.silent_learning_performed is False

    actions = {item.recommended_action for item in packet.recommendations}
    assert {
        "record_appeal_result",
        "confirm_missing_response_followup",
        "link_or_escalate_unlinked_notice",
        "parse_repair_required",
    } <= actions
    assert all(item.why for item in packet.recommendations)
    notes_text = (review_dir / "carrier_rejection_review_notes.md").read_text(encoding="utf-8")
    assert "Why:" in notes_text
    assert "Red-Team Notes" in notes_text

    scopes = {note.scope for note in packet.red_team_notes}
    assert {
        "boundary",
        "learning_loop",
        "idempotency",
        "linkage",
        "parser_failure",
        "capture_completeness",
    } <= scopes
    assert all(
        not template.external_submission_authorized for template in packet.decision_templates
    )
    assert all(not template.silent_learning_allowed for template in packet.decision_templates)
    assert (review_dir / "carrier_rejection_review_packet.json").is_file()
    assert (review_dir / "carrier_rejection_review_decision_template.json").is_file()


def test_carrier_rejection_review_packet_blocks_missing_followup_metadata(
    tmp_path,
    repo_root,
):
    budget, budget_path = _budget(tmp_path, repo_root)
    raw = _bound_fixture(repo_root, budget)
    for notice in raw["notices"]:
        notice["human_owner"] = None
        notice["followup_due_at"] = None
    source_path = write_json(tmp_path / "carrier_rejections_missing_followup.json", raw)
    _, reconciliation_dir = run_carrier_rejection_capture(
        budget_path,
        source_path,
        tmp_path / "carrier-rejections",
    )

    packet, _ = run_carrier_rejection_review(
        reconciliation_dir / "carrier_rejection_reconciliation_report.json",
        tmp_path / "carrier-rejection-review",
    )

    assert packet.status == "blocked_missing_required_followup"
    assert packet.gap_report
    assert any(note.severity == "critical" for note in packet.red_team_notes)
    assert any(rec.priority == "critical" for rec in packet.recommendations)


def test_carrier_rejection_review_cli_writes_packet(tmp_path, repo_root, capsys):
    _, reconciliation_dir = _reconciliation_report(tmp_path, repo_root)
    exit_code = main(
        [
            "review-carrier-rejections",
            "--reconciliation-report",
            str(reconciliation_dir / "carrier_rejection_reconciliation_report.json"),
            "--out-dir",
            str(tmp_path / "carrier-rejection-review"),
        ]
    )
    captured = capsys.readouterr()
    payload = load_json(
        tmp_path / "carrier-rejection-review" / "carrier_rejection_review_packet.json"
    )
    packet = CarrierRejectionReviewPacket.model_validate(payload)

    assert exit_code == 0
    assert '"status": "ready_for_human_review"' in captured.out
    assert packet.recommendations
