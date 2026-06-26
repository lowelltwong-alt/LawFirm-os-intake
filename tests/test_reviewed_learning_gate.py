from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.budget_revisions import run_budget_review_record
from lawfirm_os_intake.carrier_rejection_learning import run_carrier_rejection_learning
from lawfirm_os_intake.carrier_rejection_review import run_carrier_rejection_review
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation, ReviewedLearningGateReport
from lawfirm_os_intake.reviewed_learning_gate import run_reviewed_learning_gate
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _budget_dir(tmp_path, repo_root):
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
    _, budget_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return budget_dir


def _budget_revision_and_actuals(tmp_path, repo_root):
    budget_dir = _budget_dir(tmp_path, repo_root)
    _, review_dir = run_budget_review_record(
        budget_path=budget_dir / "legal_budget_proposal.json",
        review_path=repo_root
        / "examples/synthetic/budget-review/medmal-human-budget-review-change.json",
        out_dir=tmp_path / "budget-review",
    )
    _, actuals_dir = run_budget_actual_comparison(
        budget_path=budget_dir / "legal_budget_proposal.json",
        actuals_path=repo_root / "examples/synthetic/actuals/medmal-phase-code-actuals.json",
        budget_revision_report_path=review_dir / "budget_revision_report.json",
        out_dir=tmp_path / "actuals",
    )
    return review_dir, actuals_dir


def _carrier_learning_report_path(tmp_path, repo_root):
    budget_dir = _budget_dir(tmp_path, repo_root)
    _, capture_dir = run_carrier_rejection_capture(
        budget_dir / "legal_budget_proposal.json",
        repo_root / "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json",
        tmp_path / "carrier-rejections",
    )
    _, review_dir = run_carrier_rejection_review(
        capture_dir / "carrier_rejection_reconciliation_report.json",
        tmp_path / "carrier-rejection-review",
    )
    _, learning_dir = run_carrier_rejection_learning(
        review_dir / "carrier_rejection_review_packet.json",
        tmp_path / "carrier-rejection-learning",
    )
    return learning_dir / "carrier_rejection_learning_report.json"


def test_reviewed_learning_gate_aggregates_budget_revision_and_actuals(
    tmp_path,
    repo_root,
):
    review_dir, actuals_dir = _budget_revision_and_actuals(tmp_path, repo_root)

    report, run_dir = run_reviewed_learning_gate(
        budget_revision_report_path=review_dir / "budget_revision_report.json",
        budget_actual_comparison_report_path=actuals_dir / "budget_actual_comparison_report.json",
        out_dir=tmp_path / "reviewed-learning-gate",
    )
    persisted = ReviewedLearningGateReport.model_validate(
        load_json(run_dir / "reviewed_learning_gate_report.json")
    )
    candidates = load_jsonl(run_dir / "reviewed_learning_gate_candidates.jsonl")

    assert persisted.reviewed_learning_gate_report_id == report.reviewed_learning_gate_report_id
    assert persisted.status == "candidate_learning_gate_ready"
    assert persisted.budget_revision_candidate_count == 2
    assert persisted.budget_actual_variance_candidate_count >= 1
    assert persisted.candidate_count == len(candidates)
    assert {candidate.source_kind for candidate in persisted.candidates} >= {
        "budget_revision_delta",
        "budget_actual_variance_driver",
    }
    assert set(persisted.target_learning_loops) >= {"budget_model", "template_mapping"}
    assert all(
        candidate.status == "blocked_until_reviewed_learning_gate"
        for candidate in persisted.candidates
    )
    assert all(candidate.support_refs for candidate in persisted.candidates)
    assert all(
        "shadow eval before promotion" in candidate.required_evaluation
        for candidate in persisted.candidates
    )
    assert persisted.silent_learning_performed is False
    assert persisted.profile_mutation_performed is False
    assert persisted.template_mutation_performed is False
    assert persisted.budget_mutation_performed is False
    assert persisted.lake_write_performed is False
    assert persisted.external_writes_performed is False

    notes_text = (run_dir / "reviewed_learning_gate_report.md").read_text(encoding="utf-8")
    assert "Reviewed Learning Gate Report" in notes_text
    assert "Silent learning performed: False" in notes_text
    assert "does not mutate profiles" in notes_text


def test_reviewed_learning_gate_aggregates_carrier_learning(
    tmp_path,
    repo_root,
):
    carrier_learning_report_path = _carrier_learning_report_path(tmp_path, repo_root)

    report, _ = run_reviewed_learning_gate(
        carrier_rejection_learning_report_path=carrier_learning_report_path,
        out_dir=tmp_path / "reviewed-learning-gate",
    )

    assert report.status == "candidate_learning_gate_ready"
    assert report.carrier_learning_candidate_count >= 5
    assert "LawFirm-os-orchestrator" in report.target_owners
    assert "capture_completeness" in report.target_learning_loops
    assert {candidate.source_kind for candidate in report.candidates} == {
        "carrier_rejection_learning_proposal"
    }
    assert all(candidate.owning_repo_review_required for candidate in report.candidates)
    assert all(candidate.silent_learning_performed is False for candidate in report.candidates)


def test_reviewed_learning_gate_cli_and_missing_input(tmp_path, repo_root, capsys):
    review_dir, actuals_dir = _budget_revision_and_actuals(tmp_path, repo_root)

    exit_code = main(
        [
            "review-learning-gate",
            "--budget-revision-report",
            str(review_dir / "budget_revision_report.json"),
            "--budget-actual-comparison-report",
            str(actuals_dir / "budget_actual_comparison_report.json"),
            "--out-dir",
            str(tmp_path / "learning-gate-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "candidate_learning_gate_ready"' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert (tmp_path / "learning-gate-cli" / "reviewed_learning_gate_report.json").is_file()

    missing_exit = main(
        [
            "review-learning-gate",
            "--out-dir",
            str(tmp_path / "learning-gate-missing"),
        ]
    )
    missing_captured = capsys.readouterr()
    assert missing_exit == 2
    assert "requires at least one source report" in missing_captured.err
