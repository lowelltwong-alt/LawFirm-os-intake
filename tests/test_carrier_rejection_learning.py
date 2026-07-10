from lawfirm_os_intake.carrier_rejection_learning import run_carrier_rejection_learning
from lawfirm_os_intake.carrier_rejection_review import run_carrier_rejection_review
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    CarrierRejectionLearningReport,
    CarrierRejectionReviewPacket,
    HumanConfirmation,
)
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
    return budget_path


def _review_packet_path(tmp_path, repo_root):
    budget_path = _budget(tmp_path, repo_root)
    _, capture_dir = run_carrier_rejection_capture(
        budget_path,
        repo_root / "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json",
        tmp_path / "carrier-rejections",
    )
    _, review_dir = run_carrier_rejection_review(
        capture_dir / "carrier_rejection_reconciliation_report.json",
        tmp_path / "carrier-rejection-review",
    )
    return review_dir / "carrier_rejection_review_packet.json"


def test_carrier_rejection_learning_report_proposes_candidate_loops(
    tmp_path,
    repo_root,
):
    review_packet_path = _review_packet_path(tmp_path, repo_root)

    report, run_dir = run_carrier_rejection_learning(
        review_packet_path,
        tmp_path / "carrier-rejection-learning",
    )

    assert report.status == "candidate_learning_ready_for_review"
    assert report.proposal_count >= 5
    assert report.reviewed_outcome_required is True
    assert report.append_only_outcome_required is True
    assert report.silent_learning_performed is False
    assert report.profile_mutation_performed is False
    assert report.template_mutation_performed is False
    assert report.connector_mutation_performed is False
    assert report.external_writes_performed is False

    proposal_types = {proposal.proposal_type for proposal in report.proposals}
    assert {
        "preapproval_gate_candidate",
        "validation_rule_candidate",
        "capture_sla_candidate",
        "reconciliation_rule_candidate",
        "parser_rule_candidate",
        "appeal_outcome_candidate",
    } <= proposal_types
    assert all(proposal.status == "blocked_until_reviewed_outcome" for proposal in report.proposals)
    assert all(proposal.source_structured_refs for proposal in report.proposals)
    assert all(
        "human-reviewed outcome evidence" in proposal.required_evaluation
        for proposal in report.proposals
    )
    assert {
        "lesson_disclosure_proof_before_cross_repo_review",
        "chinese_wall_proof_before_lesson_firing",
    }.issubset(report.required_next_gates)

    notes_text = (run_dir / "carrier_rejection_learning_report.md").read_text(encoding="utf-8")
    assert "Required Next Gates" in notes_text
    assert "Silent learning performed: False" in notes_text
    assert "does not mutate profiles" in notes_text
    assert (run_dir / "carrier_rejection_learning_report.json").is_file()


def test_carrier_rejection_learning_report_handles_no_candidates(tmp_path, repo_root):
    review_packet_path = _review_packet_path(tmp_path, repo_root)
    raw_packet = load_json(review_packet_path)
    raw_packet["recommendations"] = []
    raw_packet["decision_templates"] = []
    raw_packet["red_team_notes"] = []
    empty_packet_path = write_json(tmp_path / "empty_review_packet.json", raw_packet)

    report, _ = run_carrier_rejection_learning(
        empty_packet_path,
        tmp_path / "carrier-rejection-learning",
    )

    assert report.status == "no_learning_candidates"
    assert report.proposal_count == 0
    assert report.proposals == []
    assert report.silent_learning_performed is False


def test_carrier_rejection_learning_report_blocks_when_review_packet_blocked(
    tmp_path,
    repo_root,
):
    review_packet_path = _review_packet_path(tmp_path, repo_root)
    raw_packet = load_json(review_packet_path)
    raw_packet["status"] = "blocked_missing_required_followup"
    blocked_packet_path = write_json(tmp_path / "blocked_review_packet.json", raw_packet)

    report, _ = run_carrier_rejection_learning(
        blocked_packet_path,
        tmp_path / "carrier-rejection-learning",
    )

    assert report.status == "blocked_pending_human_review_packet"
    assert report.proposal_count > 0


def test_carrier_rejection_learning_cli_writes_report(tmp_path, repo_root, capsys):
    review_packet_path = _review_packet_path(tmp_path, repo_root)

    exit_code = main(
        [
            "propose-carrier-rejection-learning",
            "--review-packet",
            str(review_packet_path),
            "--out-dir",
            str(tmp_path / "carrier-rejection-learning"),
        ]
    )
    captured = capsys.readouterr()
    payload = load_json(
        tmp_path / "carrier-rejection-learning" / "carrier_rejection_learning_report.json"
    )
    report = CarrierRejectionLearningReport.model_validate(payload)
    packet = CarrierRejectionReviewPacket.model_validate(load_json(review_packet_path))

    assert exit_code == 0
    assert report.review_packet_id == packet.review_packet_id
    assert '"silent_learning_performed": false' in captured.out
    assert report.proposals
