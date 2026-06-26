from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.budget_revisions import run_budget_review_record
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.learning_promotion_readiness import run_learning_promotion_readiness
from lawfirm_os_intake.models import (
    HumanConfirmation,
    LearningPromotionReadinessReport,
    LearningShadowEvalPlan,
    ReviewedLearningGateReport,
)
from lawfirm_os_intake.reviewed_learning_gate import run_reviewed_learning_gate
from lawfirm_os_intake.util import load_json, write_json
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


def _reviewed_learning_gate_report_path(tmp_path, repo_root):
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
    _, gate_dir = run_reviewed_learning_gate(
        budget_revision_report_path=review_dir / "budget_revision_report.json",
        budget_actual_comparison_report_path=actuals_dir / "budget_actual_comparison_report.json",
        out_dir=tmp_path / "reviewed-learning-gate",
    )
    return gate_dir / "reviewed_learning_gate_report.json"


def test_learning_promotion_readiness_blocks_until_shadow_eval(
    tmp_path,
    repo_root,
):
    gate_report_path = _reviewed_learning_gate_report_path(tmp_path, repo_root)

    plan, report, run_dir = run_learning_promotion_readiness(
        reviewed_learning_gate_report_path=gate_report_path,
        out_dir=tmp_path / "promotion-readiness",
    )
    persisted_plan = LearningShadowEvalPlan.model_validate(
        load_json(run_dir / "learning_shadow_eval_plan.json")
    )
    persisted_report = LearningPromotionReadinessReport.model_validate(
        load_json(run_dir / "learning_promotion_readiness_report.json")
    )
    gate_report = ReviewedLearningGateReport.model_validate(load_json(gate_report_path))

    assert persisted_plan.shadow_eval_plan_id == plan.shadow_eval_plan_id
    assert persisted_report.promotion_readiness_report_id == report.promotion_readiness_report_id
    assert persisted_plan.status == "shadow_eval_required"
    assert persisted_report.status == "promotion_blocked_shadow_eval_required"
    assert persisted_plan.case_count == gate_report.candidate_count
    assert persisted_report.candidate_count == gate_report.candidate_count
    assert persisted_report.blocked_candidate_count == gate_report.candidate_count
    assert persisted_report.ready_candidate_count == 0
    assert all(case.status == "blocked_missing_proposed_change" for case in persisted_plan.cases)
    assert all(case.required_fixture_updates for case in persisted_plan.cases)
    assert all("fixture-gold replay" in case.required_eval_suites for case in persisted_plan.cases)
    assert all("no silent learning" in case.regression_guardrails for case in persisted_plan.cases)
    assert {check.check_id for check in persisted_report.checks if check.status == "blocked"} >= {
        "proposed_change_artifacts_present",
        "shadow_eval_results_present",
        "owning_repo_review_required",
    }
    assert persisted_report.promotion_authorized is False
    assert persisted_report.proposed_changes_applied is False
    assert persisted_report.silent_learning_performed is False
    assert persisted_report.external_writes_performed is False

    notes_text = (run_dir / "learning_promotion_readiness_report.md").read_text(encoding="utf-8")
    assert "Promotion authorized: False" in notes_text
    assert "Promotion remains blocked" in notes_text


def test_learning_promotion_readiness_cli_and_no_candidates(
    tmp_path,
    repo_root,
    capsys,
):
    gate_report_path = _reviewed_learning_gate_report_path(tmp_path, repo_root)

    exit_code = main(
        [
            "audit-learning-promotion-readiness",
            "--reviewed-learning-gate-report",
            str(gate_report_path),
            "--out-dir",
            str(tmp_path / "promotion-readiness-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "promotion_blocked_shadow_eval_required"' in captured.out
    assert '"promotion_authorized": false' in captured.out
    assert (
        tmp_path / "promotion-readiness-cli" / "learning_promotion_readiness_report.json"
    ).is_file()

    raw_gate = load_json(gate_report_path)
    raw_gate["status"] = "no_learning_candidates"
    raw_gate["candidate_count"] = 0
    raw_gate["budget_revision_candidate_count"] = 0
    raw_gate["budget_actual_variance_candidate_count"] = 0
    raw_gate["target_learning_loops"] = []
    raw_gate["target_owners"] = []
    raw_gate["candidates"] = []
    empty_gate_path = write_json(tmp_path / "empty_gate.json", raw_gate)
    _, report, _ = run_learning_promotion_readiness(
        reviewed_learning_gate_report_path=empty_gate_path,
        out_dir=tmp_path / "promotion-readiness-empty",
    )

    assert report.status == "no_learning_candidates"
    assert report.candidate_count == 0
    assert report.blocked_candidate_count == 0
