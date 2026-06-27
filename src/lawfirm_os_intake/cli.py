from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from .budget_actuals import run_budget_actual_comparison
from .budget_actual_variance_ledger import BUDGET_ACTUAL_VARIANCE_LEDGER_REPORT_FILENAME
from .budget_change_ledger import BUDGET_CHANGE_LEDGER_REPORT_FILENAME
from .budget_calibration_corpus import run_budget_calibration_corpus_audit
from .budget_calibration_readiness import run_budget_calibration_readiness_audit
from .budget_corpus_replay import run_budget_corpus_replay_plan
from .budget_corpus_replay_execution import run_budget_corpus_replay_execution
from .budget_corpus_replay_review import run_budget_corpus_replay_review
from .budget_corpus_replay_review_outcomes import (
    run_budget_corpus_replay_review_outcome_record,
)
from .budget_fixture_binding_handoff import run_budget_fixture_binding_handoff
from .budget_fixture_bindings import run_budget_fixture_binding_candidates
from .budget_fixture_update_pr_package import run_budget_fixture_update_pr_package
from .budget_fixture_update_review import run_budget_fixture_update_review_record
from .budget_form import build_budget_form_template_audit_report, render_budget_form
from .budget_lake_admission_bundle import run_budget_event_lake_admission_bundle
from .budget_lifecycle_audit import run_budget_lifecycle_audit
from .budget_lifecycle_owner_adoption import run_budget_lifecycle_owner_adoption
from .budget_revisions import run_budget_review_record
from .carrier_rejection_lake_admission import (
    run_carrier_rejection_lake_admission_proposal,
)
from .carrier_rejection_decision_ledger import (
    CARRIER_REJECTION_DECISION_LEDGER_REPORT_FILENAME,
)
from .carrier_rejection_learning import run_carrier_rejection_learning
from .carrier_rejection_orchestrator_interface import (
    run_carrier_rejection_orchestrator_interface,
)
from .carrier_rejection_roadmap_audit import run_carrier_rejection_roadmap_audit
from .carrier_rejection_review import run_carrier_rejection_review
from .carrier_rejections import run_carrier_rejection_capture
from .confirmation import bind_confirmation_to_packet_evidence
from .cross_repo_owner_adoption import run_cross_repo_owner_adoption
from .cross_repo_owner_issue_drafts import run_cross_repo_owner_issue_drafts
from .intake_local_closeout import run_intake_local_closeout
from .intake_vertical_readiness_audit import run_intake_vertical_readiness_audit
from .learning_promotion_readiness import run_learning_promotion_readiness
from .learning_owner_handoffs import run_learning_owner_handoffs
from .learning_proposed_changes import run_learning_proposed_changes
from .learning_shadow_eval_fixture_results import (
    run_learning_shadow_eval_fixture_results,
)
from .learning_shadow_eval_results import run_learning_shadow_eval_results
from .models import BudgetProposal, HumanConfirmation
from .pr_readiness_decision import run_pr_readiness_decision_record
from .pr_review_checklist import run_pr_review_checklist
from .public_source_methodology import run_public_source_methodology_audit
from .public_synthetic_fixture_pr_package import run_public_synthetic_fixture_pr_package
from .public_synthetic_fixture_conversion import (
    run_public_synthetic_fixture_conversion_plan,
)
from .public_synthetic_fixture_conversion_review import (
    run_public_synthetic_fixture_conversion_review,
)
from .public_synthetic_fixture_conversion_review_outcomes import (
    run_public_synthetic_fixture_conversion_review_outcome_record,
)
from .reviewed_learning_gate import run_reviewed_learning_gate
from .util import load_json, write_json
from .workflow import run_budget, run_preflight


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lawfirm-os-intake",
        description="Synthetic-only intake-to-budget reference workflow for LawFirm OS.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="Build a human-review intake preflight packet.")
    preflight.add_argument("--input", required=True)
    preflight.add_argument("--practice-profile", required=True)
    preflight.add_argument("--out-dir", default=".lawfirm-os-intake/runs")
    preflight.add_argument("--review-form-out")
    preflight.add_argument("--fixture-gold")
    preflight.add_argument(
        "--adapter", choices=["deterministic", "structured-model"], default="deterministic"
    )
    preflight.add_argument("--strict-evidence", action=argparse.BooleanOptionalAction, default=True)

    budget = sub.add_parser(
        "build-budget", help="Build conflict seed and budget proposal after human confirmation."
    )
    budget.add_argument("--preflight-packet", required=True)
    budget.add_argument("--confirmation", required=True)
    budget.add_argument("--practice-profile", required=True)
    budget.add_argument("--out-dir", required=True)
    budget.add_argument("--fixture-gold")

    demo = sub.add_parser("demo", help="Run the complete synthetic intake-to-budget demonstration.")
    demo.add_argument("--input", required=True)
    demo.add_argument("--practice-profile", required=True)
    demo.add_argument("--confirmation-template", required=True)
    demo.add_argument("--out-dir", default=".lawfirm-os-intake/demo")
    demo.add_argument("--fixture-gold")
    demo.add_argument(
        "--adapter", choices=["deterministic", "structured-model"], default="deterministic"
    )
    demo.add_argument("--strict-evidence", action=argparse.BooleanOptionalAction, default=True)

    budget_form = sub.add_parser(
        "budget-form",
        help="Render a legal budget proposal into a UTBMS budget form workbook (.xlsx).",
    )
    budget_form.add_argument("--budget", required=True, help="Path to legal_budget_proposal.json")
    budget_form.add_argument("--out", required=True, help="Output .xlsx path")
    budget_form.add_argument(
        "--template", help="Optional existing UTBMS budget form to fill instead of generating one"
    )
    budget_form.add_argument(
        "--mapping-report-out",
        help="Optional budget_form_mapping_report.json path; requires --template.",
    )

    budget_form_audit = sub.add_parser(
        "budget-form-audit",
        help="Audit a UTBMS budget form template before template-backed rendering.",
    )
    budget_form_audit.add_argument("--template", required=True, help="Existing UTBMS budget form")
    budget_form_audit.add_argument("--out", required=True, help="Output audit report JSON path")

    budget_review = sub.add_parser(
        "record-budget-review",
        help="Record append-only human budget review changes without mutating the proposal.",
    )
    budget_review.add_argument("--budget", required=True, help="Path to legal_budget_proposal.json")
    budget_review.add_argument("--review", required=True, help="Path to budget review changes JSON")
    budget_review.add_argument("--out-dir", required=True)

    budget_actuals = sub.add_parser(
        "compare-budget-actuals",
        help="Compare synthetic actual costs against an original or human-revised budget.",
    )
    budget_actuals.add_argument(
        "--budget", required=True, help="Path to legal_budget_proposal.json"
    )
    budget_actuals.add_argument("--actuals", required=True, help="Path to synthetic actuals JSON")
    budget_actuals.add_argument("--out-dir", required=True)
    budget_actuals.add_argument(
        "--budget-revision-report",
        help="Optional budget_revision_report.json from record-budget-review.",
    )

    budget_corpus = sub.add_parser(
        "audit-budget-calibration-corpus",
        help="Classify synthetic budget/rejection/actuals fixtures for calibration review.",
    )
    budget_corpus.add_argument(
        "--corpus-root",
        default="examples/synthetic",
        help="Synthetic fixture corpus root to audit.",
    )
    budget_corpus.add_argument("--out-dir", required=True)
    budget_corpus.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative artifact refs; defaults to current directory.",
    )

    budget_corpus_replay = sub.add_parser(
        "plan-budget-corpus-replay",
        help="Plan deterministic replay command chains for a budget calibration corpus audit.",
    )
    budget_corpus_replay.add_argument(
        "--corpus-report",
        required=True,
        help="Path to budget_calibration_corpus_report.json.",
    )
    budget_corpus_replay.add_argument("--out-dir", required=True)

    budget_corpus_replay_execution = sub.add_parser(
        "replay-budget-corpus",
        help="Dry-run or execute selected budget corpus replay command chains locally.",
    )
    budget_corpus_replay_execution.add_argument(
        "--replay-plan",
        required=True,
        help="Path to budget_corpus_replay_plan.json.",
    )
    budget_corpus_replay_execution.add_argument("--out-dir", required=True)
    budget_corpus_replay_execution.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative replay refs; defaults to current directory.",
    )
    budget_corpus_replay_execution.add_argument(
        "--execute",
        action="store_true",
        help="Execute selected planned replay command chains. Default is dry-run audit.",
    )
    budget_corpus_replay_execution.add_argument(
        "--case-id",
        action="append",
        default=[],
        help="Replay case ID to include. May be supplied multiple times. Defaults to all planned cases.",
    )
    budget_corpus_replay_execution.add_argument(
        "--proposed-change-set",
        help="Optional learning_proposed_change_set.json for shadow-eval replay cases.",
    )

    budget_corpus_replay_review = sub.add_parser(
        "review-budget-corpus-replay",
        help="Build a human-review packet for budget corpus replay execution results.",
    )
    budget_corpus_replay_review.add_argument(
        "--replay-execution-report",
        required=True,
        help="Path to budget_corpus_replay_execution_report.json.",
    )
    budget_corpus_replay_review.add_argument("--out-dir", required=True)

    budget_corpus_replay_review_outcome = sub.add_parser(
        "record-budget-corpus-replay-review-outcome",
        help="Record an append-only human outcome for a budget corpus replay review packet.",
    )
    budget_corpus_replay_review_outcome.add_argument(
        "--review-packet",
        required=True,
        help="Path to budget_corpus_replay_review_packet.json.",
    )
    budget_corpus_replay_review_outcome.add_argument(
        "--outcome",
        required=True,
        help="Path to budget corpus replay review outcome JSON.",
    )
    budget_corpus_replay_review_outcome.add_argument("--out-dir", required=True)

    budget_fixture_bindings = sub.add_parser(
        "propose-budget-fixture-bindings",
        help="Propose candidate fixture bindings from approved budget replay review outcomes.",
    )
    budget_fixture_bindings.add_argument(
        "--review-packet",
        required=True,
        help="Path to budget_corpus_replay_review_packet.json.",
    )
    budget_fixture_bindings.add_argument(
        "--review-outcome-report",
        required=True,
        help="Path to budget_corpus_replay_review_outcome_report.json.",
    )
    budget_fixture_bindings.add_argument("--out-dir", required=True)

    budget_fixture_binding_handoff = sub.add_parser(
        "build-budget-fixture-binding-handoff",
        help="Build a human fixture-update handoff from fixture-binding candidates.",
    )
    budget_fixture_binding_handoff.add_argument(
        "--fixture-binding-candidate-report",
        required=True,
        help="Path to budget_fixture_binding_candidate_report.json.",
    )
    budget_fixture_binding_handoff.add_argument("--out-dir", required=True)

    budget_calibration_readiness = sub.add_parser(
        "audit-budget-calibration-readiness",
        help="Audit the synthetic budget calibration chain before manual fixture update review.",
    )
    budget_calibration_readiness.add_argument("--corpus-report", required=True)
    budget_calibration_readiness.add_argument("--replay-plan", required=True)
    budget_calibration_readiness.add_argument("--replay-execution-report", required=True)
    budget_calibration_readiness.add_argument("--replay-review-packet", required=True)
    budget_calibration_readiness.add_argument("--replay-review-outcome-report", required=True)
    budget_calibration_readiness.add_argument("--fixture-binding-candidate-report", required=True)
    budget_calibration_readiness.add_argument("--fixture-binding-handoff-report", required=True)
    budget_calibration_readiness.add_argument("--out-dir", required=True)

    budget_fixture_update_review = sub.add_parser(
        "record-budget-fixture-update-review",
        help="Record a human fixture-update review decision without mutating fixtures.",
    )
    budget_fixture_update_review.add_argument(
        "--calibration-readiness-report",
        required=True,
        help="Path to budget_calibration_readiness_report.json.",
    )
    budget_fixture_update_review.add_argument(
        "--review",
        required=True,
        help="Path to budget fixture update review decision JSON.",
    )
    budget_fixture_update_review.add_argument("--out-dir", required=True)

    budget_fixture_update_pr_package = sub.add_parser(
        "build-budget-fixture-update-pr-package",
        help="Build a manual fixture-update PR package without creating a PR or editing fixtures.",
    )
    budget_fixture_update_pr_package.add_argument(
        "--fixture-update-review-report",
        required=True,
        help="Path to budget_fixture_update_review_report.json.",
    )
    budget_fixture_update_pr_package.add_argument("--out-dir", required=True)

    public_source_methodology = sub.add_parser(
        "audit-public-source-methodology",
        help="Audit planning-only public-source methodology before synthetic fixture use.",
    )
    public_source_methodology.add_argument("--out-dir", required=True)
    public_source_methodology.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to inspect; defaults to the current working directory.",
    )

    public_synthetic_conversion = sub.add_parser(
        "plan-public-synthetic-fixture-conversion",
        help="Plan human-reviewed public-structure to synthetic-fixture conversion.",
    )
    public_synthetic_conversion.add_argument(
        "--methodology-report",
        required=True,
        help="Path to public_source_methodology_report.json.",
    )
    public_synthetic_conversion.add_argument("--out-dir", required=True)

    public_synthetic_conversion_review = sub.add_parser(
        "review-public-synthetic-fixture-conversion",
        help="Build a human-review packet for public synthetic fixture conversion specs.",
    )
    public_synthetic_conversion_review.add_argument(
        "--conversion-plan",
        required=True,
        help="Path to public_synthetic_fixture_conversion_plan.json.",
    )
    public_synthetic_conversion_review.add_argument("--out-dir", required=True)

    public_synthetic_conversion_review_outcome = sub.add_parser(
        "record-public-synthetic-fixture-conversion-review",
        help="Record a human public synthetic fixture conversion review decision.",
    )
    public_synthetic_conversion_review_outcome.add_argument(
        "--review-packet",
        required=True,
        help="Path to public_synthetic_fixture_conversion_review_packet.json.",
    )
    public_synthetic_conversion_review_outcome.add_argument(
        "--review",
        required=True,
        help="Path to public synthetic fixture conversion review decision JSON.",
    )
    public_synthetic_conversion_review_outcome.add_argument("--out-dir", required=True)

    public_synthetic_fixture_pr_package = sub.add_parser(
        "build-public-synthetic-fixture-pr-package",
        help="Build manual public synthetic fixture PR instructions without editing fixtures.",
    )
    public_synthetic_fixture_pr_package.add_argument(
        "--review-outcome-report",
        required=True,
        help="Path to public_synthetic_fixture_conversion_review_outcome_report.json.",
    )
    public_synthetic_fixture_pr_package.add_argument(
        "--conversion-plan",
        required=True,
        help="Path to public_synthetic_fixture_conversion_plan.json.",
    )
    public_synthetic_fixture_pr_package.add_argument("--out-dir", required=True)

    carrier_rejections = sub.add_parser(
        "capture-carrier-rejections",
        help="Build a synthetic carrier rejection reconciliation and learning packet.",
    )
    carrier_rejections.add_argument("--budget", required=True)
    carrier_rejections.add_argument("--source-bundle", required=True)
    carrier_rejections.add_argument("--out-dir", required=True)

    carrier_rejection_review = sub.add_parser(
        "review-carrier-rejections",
        help="Build a human-review packet for carrier rejection remediation cases.",
    )
    carrier_rejection_review.add_argument("--reconciliation-report", required=True)
    carrier_rejection_review.add_argument("--out-dir", required=True)

    carrier_rejection_learning = sub.add_parser(
        "propose-carrier-rejection-learning",
        help="Build candidate-only learning proposals from a carrier rejection review packet.",
    )
    carrier_rejection_learning.add_argument("--review-packet", required=True)
    carrier_rejection_learning.add_argument("--out-dir", required=True)

    reviewed_learning_gate = sub.add_parser(
        "review-learning-gate",
        help="Aggregate candidate learning pressure and enforce reviewed-learning gates.",
    )
    reviewed_learning_gate.add_argument("--out-dir", required=True)
    reviewed_learning_gate.add_argument(
        "--carrier-learning-report",
        help="Optional carrier_rejection_learning_report.json.",
    )
    reviewed_learning_gate.add_argument(
        "--budget-revision-report",
        help="Optional budget_revision_report.json from record-budget-review.",
    )
    reviewed_learning_gate.add_argument(
        "--budget-actual-comparison-report",
        help="Optional budget_actual_comparison_report.json from compare-budget-actuals.",
    )

    learning_promotion_readiness = sub.add_parser(
        "audit-learning-promotion-readiness",
        help="Build shadow-eval plan and promotion-readiness audit for learning candidates.",
    )
    learning_promotion_readiness.add_argument(
        "--reviewed-learning-gate-report",
        required=True,
        help="Path to reviewed_learning_gate_report.json.",
    )
    learning_promotion_readiness.add_argument("--out-dir", required=True)

    learning_proposed_changes = sub.add_parser(
        "draft-learning-proposed-changes",
        help="Draft candidate learning proposed-change artifacts for human review.",
    )
    learning_proposed_changes.add_argument(
        "--shadow-eval-plan",
        required=True,
        help="Path to learning_shadow_eval_plan.json.",
    )
    learning_proposed_changes.add_argument("--out-dir", required=True)
    learning_proposed_changes.add_argument(
        "--promotion-readiness-report",
        help="Optional learning_promotion_readiness_report.json.",
    )

    learning_shadow_eval = sub.add_parser(
        "run-learning-shadow-eval",
        help="Run local synthetic shadow-eval result checks for proposed learning changes.",
    )
    learning_shadow_eval.add_argument(
        "--proposed-change-set",
        required=True,
        help="Path to learning_proposed_change_set.json.",
    )
    learning_shadow_eval.add_argument("--out-dir", required=True)
    learning_shadow_eval.add_argument(
        "--fixture-result",
        action="append",
        default=[],
        help="Synthetic shadow-eval fixture result JSON. May be supplied multiple times.",
    )
    learning_shadow_eval.add_argument(
        "--fixture-result-report",
        action="append",
        default=[],
        help=(
            "learning_shadow_eval_fixture_evidence_report.json containing reviewed "
            "synthetic fixture results. May be supplied multiple times."
        ),
    )

    learning_shadow_eval_fixture_results = sub.add_parser(
        "record-learning-shadow-eval-fixture-results",
        help="Record reviewed synthetic fixture evidence for current proposed learning changes.",
    )
    learning_shadow_eval_fixture_results.add_argument(
        "--proposed-change-set",
        required=True,
        help="Path to learning_proposed_change_set.json.",
    )
    learning_shadow_eval_fixture_results.add_argument(
        "--review",
        required=True,
        help="Path to a LearningShadowEvalFixtureReviewRecord JSON.",
    )
    learning_shadow_eval_fixture_results.add_argument("--out-dir", required=True)

    learning_owner_handoff = sub.add_parser(
        "build-learning-owner-handoffs",
        help="Group shadow-eval results into owner-specific review handoff packages.",
    )
    learning_owner_handoff.add_argument(
        "--shadow-eval-result-report",
        required=True,
        help="Path to learning_shadow_eval_result_report.json.",
    )
    learning_owner_handoff.add_argument("--out-dir", required=True)

    carrier_rejection_orchestrator = sub.add_parser(
        "draft-carrier-rejection-orchestrator-interface",
        help="Write the candidate Orchestrator interface for future carrier rejection capture and appeal workflows.",
    )
    carrier_rejection_orchestrator.add_argument("--out-dir", required=True)

    carrier_rejection_lake = sub.add_parser(
        "draft-carrier-rejection-lake-admission",
        help="Write the candidate Exception Lake admission proposal for carrier rejection records.",
    )
    carrier_rejection_lake.add_argument("--out-dir", required=True)

    budget_event_lake_bundle = sub.add_parser(
        "build-budget-event-lake-bundle",
        help="Bundle budget/rejection ledgers into candidate Exception Lake review evidence.",
    )
    budget_event_lake_bundle.add_argument("--out-dir", required=True)
    budget_event_lake_bundle.add_argument("--budget-change-ledger-report")
    budget_event_lake_bundle.add_argument("--budget-change-ledger-jsonl")
    budget_event_lake_bundle.add_argument("--budget-actual-variance-ledger-report")
    budget_event_lake_bundle.add_argument("--budget-actual-variance-ledger-jsonl")
    budget_event_lake_bundle.add_argument("--carrier-rejection-decision-ledger-report")
    budget_event_lake_bundle.add_argument("--carrier-rejection-decision-ledger-jsonl")

    budget_lifecycle_audit = sub.add_parser(
        "audit-budget-lifecycle",
        help="Audit budget change, actual variance, carrier rejection, and Lake-bundle evidence together.",
    )
    budget_lifecycle_audit.add_argument("--out-dir", required=True)
    budget_lifecycle_audit.add_argument("--budget-change-ledger-report", required=True)
    budget_lifecycle_audit.add_argument("--budget-actual-variance-ledger-report", required=True)
    budget_lifecycle_audit.add_argument("--carrier-rejection-decision-ledger-report", required=True)
    budget_lifecycle_audit.add_argument("--budget-event-lake-bundle-report", required=True)

    budget_lifecycle_owner_adoption = sub.add_parser(
        "build-budget-lifecycle-owner-adoption",
        help="Build owner-review packets for budget lifecycle adoption without writing sibling repos.",
    )
    budget_lifecycle_owner_adoption.add_argument(
        "--budget-lifecycle-audit-report",
        required=True,
        help="Path to budget_lifecycle_audit_report.json.",
    )
    budget_lifecycle_owner_adoption.add_argument("--out-dir", required=True)

    carrier_rejection_audit = sub.add_parser(
        "audit-carrier-rejection-roadmap",
        help="Write the local completion and sibling-adoption audit for carrier rejection work.",
    )
    carrier_rejection_audit.add_argument("--out-dir", required=True)
    carrier_rejection_audit.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to inspect; defaults to the current working directory.",
    )

    intake_vertical_audit = sub.add_parser(
        "audit-intake-vertical-readiness",
        help="Audit local intake vertical surfaces plus the generated learning artifact chain before PR readiness review.",
    )
    intake_vertical_audit.add_argument(
        "--owner-handoff-report",
        required=True,
        help="Path to learning_owner_handoff_report.json.",
    )
    intake_vertical_audit.add_argument(
        "--budget-event-lake-bundle-report",
        required=True,
        help="Path to budget_event_lake_admission_bundle_report.json.",
    )
    intake_vertical_audit.add_argument(
        "--budget-calibration-readiness-report",
        required=True,
        help="Path to budget_calibration_readiness_report.json.",
    )
    intake_vertical_audit.add_argument(
        "--budget-fixture-update-review-report",
        required=True,
        help="Path to budget_fixture_update_review_report.json.",
    )
    intake_vertical_audit.add_argument(
        "--budget-fixture-update-pr-package-report",
        required=True,
        help="Path to budget_fixture_update_pr_package_report.json.",
    )
    intake_vertical_audit.add_argument("--out-dir", required=True)
    intake_vertical_audit.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to inspect; defaults to the current working directory.",
    )
    pr_review_checklist = sub.add_parser(
        "build-pr-review-checklist",
        help="Build a human PR review checklist from intake vertical readiness evidence.",
    )
    pr_review_checklist.add_argument(
        "--readiness-audit-report",
        required=True,
        help="Path to intake_vertical_readiness_audit_report.json.",
    )
    pr_review_checklist.add_argument("--out-dir", required=True)
    pr_readiness_decision = sub.add_parser(
        "record-pr-readiness-decision",
        help="Record a human PR readiness decision without changing GitHub state.",
    )
    pr_readiness_decision.add_argument(
        "--pr-review-checklist",
        required=True,
        help="Path to pr_review_checklist.json.",
    )
    pr_readiness_decision.add_argument(
        "--intake-local-closeout-report",
        required=True,
        help="Path to intake_local_closeout_report.json.",
    )
    pr_readiness_decision.add_argument(
        "--decision",
        required=True,
        help="Path to human PR readiness decision JSON.",
    )
    pr_readiness_decision.add_argument("--out-dir", required=True)
    owner_adoption = sub.add_parser(
        "build-cross-repo-owner-adoption",
        help="Build owner-specific adoption packets from the promotion package and PR review evidence.",
    )
    owner_adoption.add_argument(
        "--promotion-package",
        required=True,
        help="Path to promotion/cross_repo_promotion_package.json.",
    )
    owner_adoption.add_argument(
        "--readiness-audit-report",
        required=True,
        help="Path to intake_vertical_readiness_audit_report.json.",
    )
    owner_adoption.add_argument(
        "--pr-review-checklist",
        required=True,
        help="Path to pr_review_checklist.json.",
    )
    owner_adoption.add_argument("--out-dir", required=True)
    owner_issue_drafts = sub.add_parser(
        "build-cross-repo-owner-issue-drafts",
        help="Build local GitHub issue draft text from owner adoption packets without creating issues.",
    )
    owner_issue_drafts.add_argument(
        "--owner-adoption-report",
        required=True,
        help="Path to cross_repo_owner_adoption_report.json.",
    )
    owner_issue_drafts.add_argument("--out-dir", required=True)
    local_closeout = sub.add_parser(
        "audit-intake-local-closeout",
        help="Audit final local closeout evidence and remaining manual external gates.",
    )
    local_closeout.add_argument(
        "--readiness-audit-report",
        required=True,
        help="Path to intake_vertical_readiness_audit_report.json.",
    )
    local_closeout.add_argument(
        "--pr-review-checklist",
        required=True,
        help="Path to pr_review_checklist.json.",
    )
    local_closeout.add_argument(
        "--owner-adoption-report",
        required=True,
        help="Path to cross_repo_owner_adoption_report.json.",
    )
    local_closeout.add_argument(
        "--owner-issue-draft-report",
        required=True,
        help="Path to cross_repo_owner_issue_draft_report.json.",
    )
    local_closeout.add_argument("--out-dir", required=True)
    local_closeout.add_argument("--observed-pr-number", type=int)
    local_closeout.add_argument("--observed-pr-url")
    local_closeout.add_argument(
        "--observed-pr-state",
        choices=["draft", "ready_for_review", "not_supplied"],
        default="not_supplied",
    )
    return parser


def _print(value: dict) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "preflight":
            packet, run_dir = run_preflight(
                args.input,
                args.practice_profile,
                args.out_dir,
                adapter=args.adapter,
                strict_evidence=args.strict_evidence,
                fixture_gold=args.fixture_gold,
            )
            if args.review_form_out and packet.intake_review_form_ref:
                shutil.copyfile(packet.intake_review_form_ref, args.review_form_out)
            _print(
                {
                    "status": packet.status,
                    "run_id": packet.run_id,
                    "packet_id": packet.packet_id,
                    "top_matter_candidate": packet.matter_family_candidates[0].label,
                    "human_confirmation_required": packet.human_confirmation_required,
                    "escalation": packet.escalation.model_dump(mode="json"),
                    "contract_state_report": packet.contract_state_report_ref,
                    "data_scope_gate_report": packet.data_scope_gate_report_ref,
                    "fixture_gold_report": packet.fixture_gold_report_ref,
                    "deadline_docketing_guard_report": (packet.deadline_docketing_guard_report_ref),
                    "evidence_completeness_report": packet.evidence_completeness_report_ref,
                    "context_boundary_report": packet.context_boundary_report_ref,
                    "exception_lake_handoff_manifest": packet.exception_lake_handoff_manifest_ref,
                    "run_ledger_integrity_report": packet.run_ledger_integrity_report_ref,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "build-budget":
            proposal, run_dir = run_budget(
                args.preflight_packet,
                args.confirmation,
                args.practice_profile,
                args.out_dir,
                fixture_gold=args.fixture_gold,
            )
            _print(
                {
                    "status": proposal.approval_state,
                    "budget_proposal_id": proposal.budget_proposal_id,
                    "pricing_status": proposal.pricing_status,
                    "total_proposed_budget": proposal.total_proposed_budget,
                    "not_authorized_for_client_submission": proposal.not_authorized_for_client_submission,
                    "matter_opening_review_package": str(
                        run_dir / "matter_opening_review_package.md"
                    ),
                    "review_package_manifest": str(run_dir / "review_package_manifest.json"),
                    "human_confirmation_history": str(run_dir / "human_confirmation_history.jsonl"),
                    "human_gate_status_report": str(run_dir / "human_gate_status_report.json"),
                    "budget_submission_guard_report": str(
                        run_dir / "budget_submission_guard_report.json"
                    ),
                    "budget_precondition_report": str(run_dir / "budget_precondition_report.json"),
                    "safety_gate_report": str(run_dir / "safety_gate_report.json"),
                    "exception_lake_handoff_manifest": str(
                        run_dir / "exception_lake_handoff_manifest.json"
                    ),
                    "run_ledger_integrity_report": str(
                        run_dir / "run_ledger_integrity_report.json"
                    ),
                    "fixture_gold_report": (
                        str(run_dir / "fixture_gold_report.json") if args.fixture_gold else None
                    ),
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "demo":
            root = Path(args.out_dir)
            if root.exists():
                shutil.rmtree(root)
            root.mkdir(parents=True)
            packet, run_dir = run_preflight(
                args.input,
                args.practice_profile,
                root / "preflight",
                adapter=args.adapter,
                strict_evidence=args.strict_evidence,
                fixture_gold=args.fixture_gold,
            )
            confirmation_data = load_json(args.confirmation_template)
            confirmation_data["preflight_packet_id"] = packet.packet_id
            confirmation = HumanConfirmation.model_validate(confirmation_data)
            confirmation = bind_confirmation_to_packet_evidence(packet, confirmation)
            confirmation_path = root / "human_confirmation.json"
            write_json(confirmation_path, confirmation.model_dump(mode="json"))
            proposal, budget_dir = run_budget(
                run_dir / "intake_preflight_packet.json",
                confirmation_path,
                args.practice_profile,
                root / "budget",
                fixture_gold=args.fixture_gold,
            )
            _print(
                {
                    "status": "demo_completed",
                    "preflight_packet": str(run_dir / "intake_preflight_packet.json"),
                    "contract_state_report": packet.contract_state_report_ref,
                    "data_scope_gate_report": packet.data_scope_gate_report_ref,
                    "deadline_docketing_guard_report": (packet.deadline_docketing_guard_report_ref),
                    "human_confirmation": str(confirmation_path),
                    "conflict_seed": str(budget_dir / "conflict_search_seed_packet.json"),
                    "legal_budget_proposal": str(budget_dir / "legal_budget_proposal.json"),
                    "matter_opening_readiness": str(budget_dir / "matter_opening_readiness.json"),
                    "matter_opening_review_package": str(
                        budget_dir / "matter_opening_review_package.md"
                    ),
                    "review_package_manifest": str(budget_dir / "review_package_manifest.json"),
                    "human_confirmation_history": str(
                        budget_dir / "human_confirmation_history.jsonl"
                    ),
                    "human_gate_status_report": str(budget_dir / "human_gate_status_report.json"),
                    "budget_submission_guard_report": str(
                        budget_dir / "budget_submission_guard_report.json"
                    ),
                    "budget_precondition_report": str(
                        budget_dir / "budget_precondition_report.json"
                    ),
                    "safety_gate_report": str(budget_dir / "safety_gate_report.json"),
                    "exception_lake_handoff_manifest": str(
                        budget_dir / "exception_lake_handoff_manifest.json"
                    ),
                    "run_ledger_integrity_report": str(
                        budget_dir / "run_ledger_integrity_report.json"
                    ),
                    "fixture_gold_report": (
                        str(budget_dir / "fixture_gold_report.json") if args.fixture_gold else None
                    ),
                    "total_proposed_budget": proposal.total_proposed_budget,
                    "final_boundary": "blocked_pending_conflicts_and_engagement",
                }
            )
            return 0

        if args.command == "budget-form":
            proposal = BudgetProposal.model_validate(load_json(args.budget))
            out_path = render_budget_form(
                proposal,
                args.out,
                template_path=args.template,
                mapping_report_out=args.mapping_report_out,
            )
            _print(
                {
                    "status": "budget_form_rendered",
                    "budget_proposal_id": proposal.budget_proposal_id,
                    "pricing_status": proposal.pricing_status,
                    "mode": "fill_existing" if args.template else "synthetic_form",
                    "out": str(out_path),
                    "budget_form_mapping_report": args.mapping_report_out,
                    "not_authorized_for_client_submission": (
                        proposal.not_authorized_for_client_submission
                    ),
                }
            )
            return 0

        if args.command == "budget-form-audit":
            report = build_budget_form_template_audit_report(args.template)
            write_json(args.out, report.model_dump(mode="json"))
            failed_checks = [
                check.check_id for check in report.formula_checks if check.status == "failed"
            ]
            _print(
                {
                    "status": "budget_form_template_audit_" + report.status,
                    "out": args.out,
                    "template_sha256": report.template_sha256,
                    "sheet_name": report.sheet_name,
                    "failed_checks": failed_checks,
                    "missing_template_codes": report.missing_template_codes,
                    "duplicate_template_codes": report.duplicate_template_codes,
                    "external_writes_performed": report.external_writes_performed,
                    "non_authoritative": report.non_authoritative,
                }
            )
            return 0 if report.status == "passed" else 2

        if args.command == "record-budget-review":
            report, run_dir = run_budget_review_record(
                budget_path=args.budget,
                review_path=args.review,
                out_dir=args.out_dir,
            )
            ledger_report = load_json(Path(run_dir) / BUDGET_CHANGE_LEDGER_REPORT_FILENAME)
            _print(
                {
                    "status": report.status,
                    "budget_revision_report_id": report.budget_revision_report_id,
                    "budget_change_ledger_report_id": (
                        ledger_report["budget_change_ledger_report_id"]
                    ),
                    "budget_change_ledger_entry_count": ledger_report["entry_count"],
                    "budget_review_change_record_id": report.budget_review_change_record_id,
                    "budget_proposal_id": report.budget_proposal_id,
                    "change_count": report.change_count,
                    "numeric_change_count": report.numeric_change_count,
                    "original_total": report.original_total,
                    "revised_total": report.revised_total,
                    "total_delta": report.total_delta,
                    "original_budget_mutated": report.original_budget_mutated,
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "carrier_submission_authorized": report.carrier_submission_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": ledger_report["sqlite_write_performed"],
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": ledger_report["silent_learning_performed"],
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "compare-budget-actuals":
            report, run_dir = run_budget_actual_comparison(
                budget_path=args.budget,
                actuals_path=args.actuals,
                out_dir=args.out_dir,
                budget_revision_report_path=args.budget_revision_report,
            )
            ledger_report = load_json(run_dir / BUDGET_ACTUAL_VARIANCE_LEDGER_REPORT_FILENAME)
            _print(
                {
                    "status": report.status,
                    "budget_actual_comparison_report_id": (
                        report.budget_actual_comparison_report_id
                    ),
                    "budget_actual_variance_ledger_report_id": (
                        ledger_report["budget_actual_variance_ledger_report_id"]
                    ),
                    "budget_actual_variance_ledger_entry_count": ledger_report["entry_count"],
                    "variance_review_event_count": ledger_report["variance_review_event_count"],
                    "actuals_without_budget_event_count": (
                        ledger_report["actuals_without_budget_event_count"]
                    ),
                    "budget_proposal_id": report.budget_proposal_id,
                    "comparison_scope": report.comparison_scope,
                    "comparison_budget_state": report.comparison_budget_state,
                    "phase_comparison_count": len(report.phase_comparisons),
                    "code_comparison_count": len(report.code_comparisons),
                    "variance_driver_candidate_count": len(report.variance_driver_candidates),
                    "learning_disposition_candidates": report.learning_disposition_candidates,
                    "billing_connector_read_performed": report.billing_connector_read_performed,
                    "billing_connector_write_performed": report.billing_connector_write_performed,
                    "sqlite_write_performed": ledger_report["sqlite_write_performed"],
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": ledger_report["silent_learning_performed"],
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "audit-budget-calibration-corpus":
            report, run_dir = run_budget_calibration_corpus_audit(
                corpus_root=args.corpus_root,
                out_dir=args.out_dir,
                repo_root=args.repo_root,
            )
            _print(
                {
                    "status": report.status,
                    "corpus_report_id": report.corpus_report_id,
                    "corpus_root_ref": report.corpus_root_ref,
                    "artifact_count": report.artifact_count,
                    "eligible_artifact_count": report.eligible_artifact_count,
                    "supporting_artifact_count": report.supporting_artifact_count,
                    "blocked_artifact_count": report.blocked_artifact_count,
                    "calibration_applied": report.calibration_applied,
                    "profile_mutation_performed": report.profile_mutation_performed,
                    "template_mutation_performed": report.template_mutation_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        report.carrier_guideline_mutation_performed
                    ),
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "synthetic_corpus_ready_for_review" else 2

        if args.command == "plan-budget-corpus-replay":
            plan, run_dir = run_budget_corpus_replay_plan(
                corpus_report_path=args.corpus_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": plan.status,
                    "replay_plan_id": plan.replay_plan_id,
                    "source_corpus_report_id": plan.source_corpus_report_id,
                    "source_corpus_status": plan.source_corpus_status,
                    "case_count": plan.case_count,
                    "planned_case_count": plan.planned_case_count,
                    "supporting_case_count": plan.supporting_case_count,
                    "blocked_case_count": plan.blocked_case_count,
                    "calibration_applied": plan.calibration_applied,
                    "profile_mutation_performed": plan.profile_mutation_performed,
                    "template_mutation_performed": plan.template_mutation_performed,
                    "budget_mutation_performed": plan.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        plan.carrier_guideline_mutation_performed
                    ),
                    "lake_write_performed": plan.lake_write_performed,
                    "sqlite_write_performed": plan.sqlite_write_performed,
                    "external_writes_performed": plan.external_writes_performed,
                    "silent_learning_performed": plan.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if plan.status == "replay_plan_ready_for_review" else 2

        if args.command == "replay-budget-corpus":
            report, run_dir = run_budget_corpus_replay_execution(
                replay_plan_path=args.replay_plan,
                out_dir=args.out_dir,
                repo_root=args.repo_root,
                execute=args.execute,
                case_ids=args.case_id,
                proposed_change_set_path=args.proposed_change_set,
            )
            _print(
                {
                    "status": report.status,
                    "replay_execution_report_id": report.replay_execution_report_id,
                    "replay_plan_id": report.replay_plan_id,
                    "execution_mode": report.execution_mode,
                    "case_count": report.case_count,
                    "executed_case_count": report.executed_case_count,
                    "dry_run_case_count": report.dry_run_case_count,
                    "skipped_case_count": report.skipped_case_count,
                    "blocked_case_count": report.blocked_case_count,
                    "failed_case_count": report.failed_case_count,
                    "command_count": report.command_count,
                    "executed_command_count": report.executed_command_count,
                    "failed_command_count": report.failed_command_count,
                    "calibration_applied": report.calibration_applied,
                    "profile_mutation_performed": report.profile_mutation_performed,
                    "template_mutation_performed": report.template_mutation_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        report.carrier_guideline_mutation_performed
                    ),
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0
                if report.status in {"dry_run_ready_for_review", "execution_passed_for_review"}
                else 2
            )

        if args.command == "review-budget-corpus-replay":
            packet, run_dir = run_budget_corpus_replay_review(
                replay_execution_report_path=args.replay_execution_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": packet.status,
                    "review_packet_id": packet.review_packet_id,
                    "replay_execution_report_id": packet.replay_execution_report_id,
                    "replay_execution_status": packet.replay_execution_status,
                    "replay_execution_mode": packet.replay_execution_mode,
                    "recommendation_count": packet.recommendation_count,
                    "decision_template_count": packet.decision_template_count,
                    "executed_passed_case_count": packet.executed_passed_case_count,
                    "dry_run_case_count": packet.dry_run_case_count,
                    "failed_case_count": packet.failed_case_count,
                    "blocked_case_count": packet.blocked_case_count,
                    "human_review_required": packet.human_review_required,
                    "append_only_review_outcome_required": (
                        packet.append_only_review_outcome_required
                    ),
                    "downstream_learning_gate_allowed_without_review": (
                        packet.downstream_learning_gate_allowed_without_review
                    ),
                    "calibration_applied": packet.calibration_applied,
                    "profile_mutation_performed": packet.profile_mutation_performed,
                    "template_mutation_performed": packet.template_mutation_performed,
                    "budget_mutation_performed": packet.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        packet.carrier_guideline_mutation_performed
                    ),
                    "lake_write_performed": packet.lake_write_performed,
                    "sqlite_write_performed": packet.sqlite_write_performed,
                    "external_writes_performed": packet.external_writes_performed,
                    "silent_learning_performed": packet.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0
                if packet.status
                in {"ready_for_human_replay_review", "blocked_pending_replay_execution"}
                else 2
            )

        if args.command == "record-budget-corpus-replay-review-outcome":
            report, run_dir = run_budget_corpus_replay_review_outcome_record(
                review_packet_path=args.review_packet,
                outcome_path=args.outcome,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "review_outcome_report_id": report.review_outcome_report_id,
                    "review_packet_id": report.review_packet_id,
                    "replay_execution_report_id": report.replay_execution_report_id,
                    "review_outcome_record_id": report.review_outcome_record_id,
                    "replay_case_id": report.replay_case_id,
                    "outcome": report.outcome,
                    "decision_action": report.decision_action,
                    "append_only_history_ref": report.append_only_history_ref,
                    "fixture_binding_approved": report.fixture_binding_approved,
                    "downstream_learning_gate_allowed": report.downstream_learning_gate_allowed,
                    "source_packet_mutated": report.source_packet_mutated,
                    "calibration_applied": report.calibration_applied,
                    "profile_mutation_performed": report.profile_mutation_performed,
                    "template_mutation_performed": report.template_mutation_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        report.carrier_guideline_mutation_performed
                    ),
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if not report.status.endswith("failed_validation") else 2

        if args.command == "propose-budget-fixture-bindings":
            report, run_dir = run_budget_fixture_binding_candidates(
                review_packet_path=args.review_packet,
                review_outcome_report_path=args.review_outcome_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "fixture_binding_candidate_report_id": (
                        report.fixture_binding_candidate_report_id
                    ),
                    "review_packet_id": report.review_packet_id,
                    "review_outcome_report_id": report.review_outcome_report_id,
                    "review_outcome_record_id": report.review_outcome_record_id,
                    "replay_execution_report_id": report.replay_execution_report_id,
                    "replay_case_id": report.replay_case_id,
                    "candidate_count": report.candidate_count,
                    "ready_candidate_count": report.ready_candidate_count,
                    "blocked_candidate_count": report.blocked_candidate_count,
                    "fixture_files_mutated": report.fixture_files_mutated,
                    "fixture_binding_applied": report.fixture_binding_applied,
                    "downstream_learning_gate_allowed": report.downstream_learning_gate_allowed,
                    "calibration_applied": report.calibration_applied,
                    "profile_mutation_performed": report.profile_mutation_performed,
                    "template_mutation_performed": report.template_mutation_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        report.carrier_guideline_mutation_performed
                    ),
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "build-budget-fixture-binding-handoff":
            report, run_dir = run_budget_fixture_binding_handoff(
                fixture_binding_candidate_report_path=args.fixture_binding_candidate_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "fixture_binding_handoff_report_id": (report.fixture_binding_handoff_report_id),
                    "source_fixture_binding_candidate_report_id": (
                        report.source_fixture_binding_candidate_report_id
                    ),
                    "source_fixture_binding_candidate_report_status": (
                        report.source_fixture_binding_candidate_report_status
                    ),
                    "item_count": report.item_count,
                    "ready_item_count": report.ready_item_count,
                    "blocked_item_count": report.blocked_item_count,
                    "target_owner": report.target_owner,
                    "fixture_update_authorized": report.fixture_update_authorized,
                    "fixture_update_pr_created": report.fixture_update_pr_created,
                    "fixture_files_mutated": report.fixture_files_mutated,
                    "fixture_binding_applied": report.fixture_binding_applied,
                    "downstream_learning_gate_allowed": report.downstream_learning_gate_allowed,
                    "calibration_applied": report.calibration_applied,
                    "profile_mutation_performed": report.profile_mutation_performed,
                    "template_mutation_performed": report.template_mutation_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        report.carrier_guideline_mutation_performed
                    ),
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "audit-budget-calibration-readiness":
            report, run_dir = run_budget_calibration_readiness_audit(
                corpus_report_path=args.corpus_report,
                replay_plan_path=args.replay_plan,
                replay_execution_report_path=args.replay_execution_report,
                replay_review_packet_path=args.replay_review_packet,
                replay_review_outcome_report_path=args.replay_review_outcome_report,
                fixture_binding_candidate_report_path=args.fixture_binding_candidate_report,
                fixture_binding_handoff_report_path=args.fixture_binding_handoff_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "budget_calibration_readiness_report_id": (
                        report.budget_calibration_readiness_report_id
                    ),
                    "corpus_report_id": report.corpus_report_id,
                    "replay_plan_id": report.replay_plan_id,
                    "replay_execution_report_id": report.replay_execution_report_id,
                    "review_packet_id": report.review_packet_id,
                    "review_outcome_report_id": report.review_outcome_report_id,
                    "fixture_binding_candidate_report_id": (
                        report.fixture_binding_candidate_report_id
                    ),
                    "fixture_binding_handoff_report_id": (report.fixture_binding_handoff_report_id),
                    "ready_fixture_binding_handoff_count": (
                        report.ready_fixture_binding_handoff_count
                    ),
                    "blocked_fixture_binding_handoff_count": (
                        report.blocked_fixture_binding_handoff_count
                    ),
                    "manual_fixture_update_review_required": (
                        report.manual_fixture_update_review_required
                    ),
                    "fixture_update_authorized": report.fixture_update_authorized,
                    "fixture_update_pr_created": report.fixture_update_pr_created,
                    "fixture_files_mutated": report.fixture_files_mutated,
                    "fixture_binding_applied": report.fixture_binding_applied,
                    "downstream_learning_gate_allowed": report.downstream_learning_gate_allowed,
                    "calibration_applied": report.calibration_applied,
                    "profile_mutation_performed": report.profile_mutation_performed,
                    "template_mutation_performed": report.template_mutation_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        report.carrier_guideline_mutation_performed
                    ),
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "ready_for_manual_fixture_update_review" else 2

        if args.command == "record-budget-fixture-update-review":
            report, run_dir = run_budget_fixture_update_review_record(
                calibration_readiness_report_path=args.calibration_readiness_report,
                review_path=args.review,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "fixture_update_review_report_id": (report.fixture_update_review_report_id),
                    "source_budget_calibration_readiness_report_id": (
                        report.source_budget_calibration_readiness_report_id
                    ),
                    "fixture_binding_handoff_report_id": (report.fixture_binding_handoff_report_id),
                    "fixture_update_review_id": report.fixture_update_review_id,
                    "decision": report.decision,
                    "accepted_for_fixture_update_pr": report.accepted_for_fixture_update_pr,
                    "separate_fixture_update_pr_required": (
                        report.separate_fixture_update_pr_required
                    ),
                    "fixture_update_pr_created": report.fixture_update_pr_created,
                    "fixture_files_mutated": report.fixture_files_mutated,
                    "fixture_binding_applied": report.fixture_binding_applied,
                    "downstream_learning_gate_allowed": report.downstream_learning_gate_allowed,
                    "calibration_applied": report.calibration_applied,
                    "profile_mutation_performed": report.profile_mutation_performed,
                    "template_mutation_performed": report.template_mutation_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        report.carrier_guideline_mutation_performed
                    ),
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_by_fixture_update_review_evidence":
                return 2
            return 0

        if args.command == "build-budget-fixture-update-pr-package":
            report, run_dir = run_budget_fixture_update_pr_package(
                fixture_update_review_report_path=args.fixture_update_review_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "fixture_update_pr_package_report_id": (
                        report.fixture_update_pr_package_report_id
                    ),
                    "source_budget_fixture_update_review_report_id": (
                        report.source_budget_fixture_update_review_report_id
                    ),
                    "fixture_update_review_id": report.fixture_update_review_id,
                    "decision": report.decision,
                    "item_count": report.item_count,
                    "ready_item_count": report.ready_item_count,
                    "blocked_item_count": report.blocked_item_count,
                    "manual_fixture_update_pr_required": (report.manual_fixture_update_pr_required),
                    "github_pr_created": report.github_pr_created,
                    "fixture_files_mutated": report.fixture_files_mutated,
                    "fixture_binding_applied": report.fixture_binding_applied,
                    "downstream_learning_gate_allowed": report.downstream_learning_gate_allowed,
                    "calibration_applied": report.calibration_applied,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_by_fixture_update_review":
                return 2
            return 0

        if args.command == "audit-public-source-methodology":
            report, run_dir = run_public_source_methodology_audit(
                repo_root=args.repo_root,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status != "passed"]
            _print(
                {
                    "status": report.status,
                    "public_source_methodology_report_id": (
                        report.public_source_methodology_report_id
                    ),
                    "source_count": report.source_count,
                    "missing_required_source_ids": report.missing_required_source_ids,
                    "failed_checks": failed_checks,
                    "direct_runtime_ingestion_allowed": (report.direct_runtime_ingestion_allowed),
                    "public_records_ingested": report.public_records_ingested,
                    "raw_public_payload_committed": report.raw_public_payload_committed,
                    "connector_implemented": report.connector_implemented,
                    "legal_knowledge_adapter_authorized": (
                        report.legal_knowledge_adapter_authorized
                    ),
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_public_source_methodology":
                return 2
            return 0

        if args.command == "plan-public-synthetic-fixture-conversion":
            plan, run_dir = run_public_synthetic_fixture_conversion_plan(
                methodology_report_path=args.methodology_report,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in plan.checks if check.status != "passed"]
            _print(
                {
                    "status": plan.status,
                    "conversion_plan_id": plan.conversion_plan_id,
                    "source_methodology_report_ref": plan.source_methodology_report_ref,
                    "spec_count": plan.spec_count,
                    "specs_output_ref": plan.specs_output_ref,
                    "failed_checks": failed_checks,
                    "public_records_ingested": plan.public_records_ingested,
                    "raw_public_payload_committed": plan.raw_public_payload_committed,
                    "synthetic_fixtures_created": plan.synthetic_fixtures_created,
                    "fixture_files_mutated": plan.fixture_files_mutated,
                    "connector_implemented": plan.connector_implemented,
                    "legal_knowledge_adapter_authorized": (plan.legal_knowledge_adapter_authorized),
                    "lake_write_performed": plan.lake_write_performed,
                    "sqlite_write_performed": plan.sqlite_write_performed,
                    "external_writes_performed": plan.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            if plan.status == "blocked_public_methodology_not_ready":
                return 2
            return 0

        if args.command == "review-public-synthetic-fixture-conversion":
            packet, run_dir = run_public_synthetic_fixture_conversion_review(
                conversion_plan_path=args.conversion_plan,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": packet.status,
                    "review_packet_id": packet.review_packet_id,
                    "conversion_plan_id": packet.conversion_plan_id,
                    "conversion_plan_status": packet.conversion_plan_status,
                    "spec_count": packet.spec_count,
                    "recommendation_count": packet.recommendation_count,
                    "red_team_note_count": packet.red_team_note_count,
                    "decision_template_count": packet.decision_template_count,
                    "human_readable_review_ref": packet.human_readable_review_ref,
                    "decision_template_ref": packet.decision_template_ref,
                    "public_records_ingested": packet.public_records_ingested,
                    "raw_public_payload_committed": packet.raw_public_payload_committed,
                    "synthetic_fixtures_created": packet.synthetic_fixtures_created,
                    "fixture_files_mutated": packet.fixture_files_mutated,
                    "fixture_pr_created": packet.fixture_pr_created,
                    "connector_implemented": packet.connector_implemented,
                    "legal_knowledge_adapter_authorized": (
                        packet.legal_knowledge_adapter_authorized
                    ),
                    "lake_write_performed": packet.lake_write_performed,
                    "sqlite_write_performed": packet.sqlite_write_performed,
                    "external_writes_performed": packet.external_writes_performed,
                    "silent_learning_performed": packet.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            if packet.status != "ready_for_human_conversion_review":
                return 2
            return 0

        if args.command == "record-public-synthetic-fixture-conversion-review":
            report, run_dir = run_public_synthetic_fixture_conversion_review_outcome_record(
                review_packet_path=args.review_packet,
                review_path=args.review,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "review_outcome_report_id": report.review_outcome_report_id,
                    "review_packet_id": report.review_packet_id,
                    "conversion_plan_id": report.conversion_plan_id,
                    "conversion_review_id": report.conversion_review_id,
                    "conversion_spec_id": report.conversion_spec_id,
                    "source_id": report.source_id,
                    "outcome": report.outcome,
                    "accepted_for_separate_fixture_pr": (report.accepted_for_separate_fixture_pr),
                    "separate_fixture_generation_pr_required": (
                        report.separate_fixture_generation_pr_required
                    ),
                    "fixture_generation_authorized": report.fixture_generation_authorized,
                    "fixture_pr_created": report.fixture_pr_created,
                    "fixture_files_mutated": report.fixture_files_mutated,
                    "public_records_ingested": report.public_records_ingested,
                    "raw_public_payload_committed": report.raw_public_payload_committed,
                    "connector_implemented": report.connector_implemented,
                    "legal_knowledge_adapter_authorized": (
                        report.legal_knowledge_adapter_authorized
                    ),
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "conversion_review_blocked_by_review_evidence":
                return 2
            return 0

        if args.command == "build-public-synthetic-fixture-pr-package":
            report, run_dir = run_public_synthetic_fixture_pr_package(
                review_outcome_report_path=args.review_outcome_report,
                conversion_plan_path=args.conversion_plan,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "fixture_pr_package_report_id": report.fixture_pr_package_report_id,
                    "source_review_outcome_report_id": (report.source_review_outcome_report_id),
                    "source_conversion_plan_id": report.source_conversion_plan_id,
                    "conversion_review_id": report.conversion_review_id,
                    "source_id": report.source_id,
                    "conversion_spec_id": report.conversion_spec_id,
                    "target_fixture_family": report.target_fixture_family,
                    "item_count": report.item_count,
                    "ready_item_count": report.ready_item_count,
                    "blocked_item_count": report.blocked_item_count,
                    "manual_fixture_generation_pr_required": (
                        report.manual_fixture_generation_pr_required
                    ),
                    "fixture_generation_authorized": report.fixture_generation_authorized,
                    "github_pr_created": report.github_pr_created,
                    "fixture_files_mutated": report.fixture_files_mutated,
                    "public_records_ingested": report.public_records_ingested,
                    "raw_public_payload_committed": report.raw_public_payload_committed,
                    "connector_implemented": report.connector_implemented,
                    "legal_knowledge_adapter_authorized": (
                        report.legal_knowledge_adapter_authorized
                    ),
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_by_public_fixture_review_outcome":
                return 2
            return 0

        if args.command == "capture-carrier-rejections":
            report, run_dir = run_carrier_rejection_capture(
                args.budget,
                args.source_bundle,
                args.out_dir,
            )
            decision_ledger = load_json(
                Path(run_dir) / CARRIER_REJECTION_DECISION_LEDGER_REPORT_FILENAME
            )
            _print(
                {
                    "status": report.status,
                    "reconciliation_report_id": report.reconciliation_report_id,
                    "decision_ledger_report_id": (decision_ledger["decision_ledger_report_id"]),
                    "decision_ledger_entry_count": decision_ledger["entry_count"],
                    "budget_proposal_id": report.budget_proposal_id,
                    "expected_response_count": report.expected_response_count,
                    "reconciled_response_count": report.reconciled_response_count,
                    "missing_response_count": report.missing_response_count,
                    "unlinked_notice_count": report.unlinked_notice_count,
                    "duplicate_notice_count": report.duplicate_notice_count,
                    "appeal_result_count": report.appeal_result_count,
                    "total_recovered_amount": decision_ledger["total_recovered_amount"],
                    "total_write_down_amount": decision_ledger["total_write_down_amount"],
                    "exception_lake_candidate_count": len(report.exception_lake_candidates),
                    "not_authorized_for_lake_write": report.not_authorized_for_lake_write,
                    "not_authorized_for_external_submission": (
                        report.not_authorized_for_external_submission
                    ),
                    "sqlite_write_performed": decision_ledger["sqlite_write_performed"],
                    "appeal_submission_performed": (decision_ledger["appeal_submission_performed"]),
                    "silent_learning_performed": decision_ledger["silent_learning_performed"],
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "review-carrier-rejections":
            packet, run_dir = run_carrier_rejection_review(
                args.reconciliation_report,
                args.out_dir,
            )
            _print(
                {
                    "status": packet.status,
                    "review_packet_id": packet.review_packet_id,
                    "reconciliation_report_id": packet.reconciliation_report_id,
                    "recommendation_count": len(packet.recommendations),
                    "red_team_note_count": len(packet.red_team_notes),
                    "decision_template_count": len(packet.decision_templates),
                    "not_authorized_for_lake_write": packet.not_authorized_for_lake_write,
                    "not_authorized_for_external_submission": (
                        packet.not_authorized_for_external_submission
                    ),
                    "external_writes_performed": packet.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "propose-carrier-rejection-learning":
            report, run_dir = run_carrier_rejection_learning(
                args.review_packet,
                args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "learning_report_id": report.learning_report_id,
                    "review_packet_id": report.review_packet_id,
                    "proposal_count": report.proposal_count,
                    "target_owners": report.target_owners,
                    "reviewed_outcome_required": report.reviewed_outcome_required,
                    "silent_learning_performed": report.silent_learning_performed,
                    "profile_mutation_performed": report.profile_mutation_performed,
                    "template_mutation_performed": report.template_mutation_performed,
                    "connector_mutation_performed": report.connector_mutation_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "review-learning-gate":
            report, run_dir = run_reviewed_learning_gate(
                out_dir=args.out_dir,
                carrier_rejection_learning_report_path=args.carrier_learning_report,
                budget_revision_report_path=args.budget_revision_report,
                budget_actual_comparison_report_path=args.budget_actual_comparison_report,
            )
            _print(
                {
                    "status": report.status,
                    "reviewed_learning_gate_report_id": report.reviewed_learning_gate_report_id,
                    "candidate_count": report.candidate_count,
                    "carrier_learning_candidate_count": (report.carrier_learning_candidate_count),
                    "budget_revision_candidate_count": (report.budget_revision_candidate_count),
                    "budget_actual_variance_candidate_count": (
                        report.budget_actual_variance_candidate_count
                    ),
                    "target_learning_loops": report.target_learning_loops,
                    "target_owners": report.target_owners,
                    "reviewed_outcome_required": report.reviewed_outcome_required,
                    "shadow_eval_required": report.shadow_eval_required,
                    "silent_learning_performed": report.silent_learning_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "audit-learning-promotion-readiness":
            plan, report, run_dir = run_learning_promotion_readiness(
                reviewed_learning_gate_report_path=args.reviewed_learning_gate_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "promotion_readiness_report_id": report.promotion_readiness_report_id,
                    "shadow_eval_plan_id": plan.shadow_eval_plan_id,
                    "candidate_count": report.candidate_count,
                    "blocked_candidate_count": report.blocked_candidate_count,
                    "ready_candidate_count": report.ready_candidate_count,
                    "target_learning_loops": report.target_learning_loops,
                    "target_owners": report.target_owners,
                    "promotion_authorized": report.promotion_authorized,
                    "proposed_changes_applied": report.proposed_changes_applied,
                    "silent_learning_performed": report.silent_learning_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "draft-learning-proposed-changes":
            change_set, run_dir = run_learning_proposed_changes(
                shadow_eval_plan_path=args.shadow_eval_plan,
                promotion_readiness_report_path=args.promotion_readiness_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": change_set.status,
                    "proposed_change_set_id": change_set.proposed_change_set_id,
                    "shadow_eval_plan_id": change_set.shadow_eval_plan_id,
                    "promotion_readiness_report_id": (change_set.promotion_readiness_report_id),
                    "change_count": change_set.change_count,
                    "target_learning_loops": change_set.target_learning_loops,
                    "target_owners": change_set.target_owners,
                    "promotion_authorized": change_set.promotion_authorized,
                    "proposed_changes_applied": change_set.proposed_changes_applied,
                    "baseline_mutated": change_set.baseline_mutated,
                    "silent_learning_performed": change_set.silent_learning_performed,
                    "external_writes_performed": change_set.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "run-learning-shadow-eval":
            report, run_dir = run_learning_shadow_eval_results(
                proposed_change_set_path=args.proposed_change_set,
                fixture_result_paths=args.fixture_result,
                fixture_result_report_paths=args.fixture_result_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "shadow_eval_result_report_id": report.shadow_eval_result_report_id,
                    "proposed_change_set_id": report.proposed_change_set_id,
                    "change_count": report.change_count,
                    "passed_result_count": report.passed_result_count,
                    "failed_result_count": report.failed_result_count,
                    "blocked_result_count": report.blocked_result_count,
                    "target_learning_loops": report.target_learning_loops,
                    "target_owners": report.target_owners,
                    "promotion_authorized": report.promotion_authorized,
                    "proposed_changes_applied": report.proposed_changes_applied,
                    "baseline_mutated": report.baseline_mutated,
                    "silent_learning_performed": report.silent_learning_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "record-learning-shadow-eval-fixture-results":
            report, run_dir = run_learning_shadow_eval_fixture_results(
                proposed_change_set_path=args.proposed_change_set,
                review_path=args.review,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "fixture_evidence_report_id": report.fixture_evidence_report_id,
                    "source_proposed_change_set_id": report.source_proposed_change_set_id,
                    "source_review_record_id": report.source_review_record_id,
                    "change_count": report.change_count,
                    "passed_item_count": report.passed_item_count,
                    "failed_item_count": report.failed_item_count,
                    "blocked_item_count": report.blocked_item_count,
                    "missing_item_count": report.missing_item_count,
                    "fixture_result_count": len(report.fixture_results),
                    "promotion_authorized": report.promotion_authorized,
                    "proposed_changes_applied": report.proposed_changes_applied,
                    "baseline_mutated": report.baseline_mutated,
                    "silent_learning_performed": report.silent_learning_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status != "blocked_by_fixture_review" else 2

        if args.command == "build-learning-owner-handoffs":
            report, run_dir = run_learning_owner_handoffs(
                shadow_eval_result_report_path=args.shadow_eval_result_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "owner_handoff_report_id": report.owner_handoff_report_id,
                    "source_shadow_eval_result_report_id": (
                        report.source_shadow_eval_result_report_id
                    ),
                    "package_count": report.package_count,
                    "target_owners": report.target_owners,
                    "passed_candidate_count": report.passed_candidate_count,
                    "failed_candidate_count": report.failed_candidate_count,
                    "blocked_candidate_count": report.blocked_candidate_count,
                    "promotion_authorized": report.promotion_authorized,
                    "proposed_changes_applied": report.proposed_changes_applied,
                    "silent_learning_performed": report.silent_learning_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "draft-carrier-rejection-orchestrator-interface":
            draft, run_dir = run_carrier_rejection_orchestrator_interface(args.out_dir)
            external_write_steps = [
                step.step_id for step in draft.workflow_steps if step.external_write_allowed
            ]
            _print(
                {
                    "status": draft.status,
                    "interface_id": draft.interface_id,
                    "target_repo": draft.target_repo,
                    "connector_channel_count": len(draft.connector_channels),
                    "workflow_step_count": len(draft.workflow_steps),
                    "external_write_steps": external_write_steps,
                    "no_connector_implemented": draft.no_connector_implemented,
                    "no_external_writes_performed": draft.no_external_writes_performed,
                    "no_lake_write_performed": draft.no_lake_write_performed,
                    "no_canonical_mutation": draft.no_canonical_mutation,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "draft-carrier-rejection-lake-admission":
            proposal, run_dir = run_carrier_rejection_lake_admission_proposal(args.out_dir)
            failed_checks = [
                check.check_id for check in proposal.checks if check.status == "failed"
            ]
            _print(
                {
                    "status": proposal.status,
                    "proposal_id": proposal.proposal_id,
                    "target_repo": proposal.target_repo,
                    "record_family_count": len(proposal.record_specs),
                    "failed_checks": failed_checks,
                    "admission_state": proposal.admission_state,
                    "sqlite_owner": proposal.sqlite_owner,
                    "sqlite_write_performed": proposal.sqlite_write_performed,
                    "lake_write_performed": proposal.lake_write_performed,
                    "raw_payload_storage_allowed": proposal.raw_payload_storage_allowed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "build-budget-event-lake-bundle":
            report, run_dir = run_budget_event_lake_admission_bundle(
                out_dir=args.out_dir,
                budget_change_ledger_report_path=args.budget_change_ledger_report,
                budget_change_ledger_jsonl_path=args.budget_change_ledger_jsonl,
                budget_actual_variance_ledger_report_path=(
                    args.budget_actual_variance_ledger_report
                ),
                budget_actual_variance_ledger_jsonl_path=(args.budget_actual_variance_ledger_jsonl),
                carrier_rejection_decision_ledger_report_path=(
                    args.carrier_rejection_decision_ledger_report
                ),
                carrier_rejection_decision_ledger_jsonl_path=(
                    args.carrier_rejection_decision_ledger_jsonl
                ),
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "bundle_report_id": report.bundle_report_id,
                    "target_repo": report.target_repo,
                    "artifact_count": report.artifact_count,
                    "ledger_report_count": report.ledger_report_count,
                    "jsonl_row_count": report.jsonl_row_count,
                    "total_event_count": report.total_event_count,
                    "candidate_record_families": report.candidate_record_families,
                    "failed_checks": failed_checks,
                    "admission_state": report.admission_state,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "lake_write_performed": report.lake_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "ready_for_exception_lake_review" else 2

        if args.command == "audit-budget-lifecycle":
            report, run_dir = run_budget_lifecycle_audit(
                out_dir=args.out_dir,
                budget_change_ledger_report_path=args.budget_change_ledger_report,
                budget_actual_variance_ledger_report_path=(
                    args.budget_actual_variance_ledger_report
                ),
                carrier_rejection_decision_ledger_report_path=(
                    args.carrier_rejection_decision_ledger_report
                ),
                budget_event_lake_bundle_report_path=args.budget_event_lake_bundle_report,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "lifecycle_audit_report_id": report.lifecycle_audit_report_id,
                    "budget_proposal_id": report.budget_proposal_id,
                    "preflight_packet_id": report.preflight_packet_id,
                    "total_lifecycle_event_count": report.total_lifecycle_event_count,
                    "pending_human_decision_count": report.pending_human_decision_count,
                    "candidate_record_families": report.candidate_record_families,
                    "failed_checks": failed_checks,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "ready_for_budget_lifecycle_review" else 2

        if args.command == "build-budget-lifecycle-owner-adoption":
            report, run_dir = run_budget_lifecycle_owner_adoption(
                budget_lifecycle_audit_report_path=args.budget_lifecycle_audit_report,
                out_dir=args.out_dir,
            )
            failed = report.status != "owner_adoption_packets_ready"
            _print(
                {
                    "status": report.status,
                    "owner_adoption_report_id": report.owner_adoption_report_id,
                    "source_budget_lifecycle_audit_report_id": (
                        report.source_budget_lifecycle_audit_report_id
                    ),
                    "source_budget_lifecycle_audit_status": (
                        report.source_budget_lifecycle_audit_status
                    ),
                    "packet_count": report.packet_count,
                    "ready_packet_count": report.ready_packet_count,
                    "blocked_packet_count": report.blocked_packet_count,
                    "target_repos": report.target_repos,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "connector_implemented": report.connector_implemented,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 2 if failed else 0

        if args.command == "audit-carrier-rejection-roadmap":
            report, run_dir = run_carrier_rejection_roadmap_audit(
                args.out_dir,
                repo_root=args.repo_root,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "audit_report_id": report.audit_report_id,
                    "implemented_slice_count": report.implemented_slice_count,
                    "total_slice_count": report.total_slice_count,
                    "review_readiness": report.review_readiness,
                    "failed_checks": failed_checks,
                    "missing_artifact_refs": report.missing_artifact_refs,
                    "missing_command_refs": report.missing_command_refs,
                    "external_adoption_target_repos": report.external_adoption_target_repos,
                    "external_writes_performed": report.external_writes_performed,
                    "no_sibling_repo_writes": report.no_sibling_repo_writes,
                    "no_canonical_mutation": report.no_canonical_mutation,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0 if report.status == "local_candidate_complete_external_adoption_required" else 2
            )

        if args.command == "audit-intake-vertical-readiness":
            report, run_dir = run_intake_vertical_readiness_audit(
                owner_handoff_report_path=args.owner_handoff_report,
                budget_event_lake_bundle_report_path=args.budget_event_lake_bundle_report,
                budget_calibration_readiness_report_path=(args.budget_calibration_readiness_report),
                budget_fixture_update_review_report_path=(args.budget_fixture_update_review_report),
                budget_fixture_update_pr_package_report_path=(
                    args.budget_fixture_update_pr_package_report
                ),
                out_dir=args.out_dir,
                repo_root=args.repo_root,
            )
            failed_checks = [
                check.check_id for check in report.artifact_checks if check.status == "failed"
            ]
            _print(
                {
                    "status": report.status,
                    "audit_report_id": report.audit_report_id,
                    "review_readiness": report.review_readiness,
                    "budget_event_lake_bundle_report_ref": (
                        report.source_budget_event_lake_bundle_report_ref
                    ),
                    "budget_calibration_readiness_report_ref": (
                        report.source_budget_calibration_readiness_report_ref
                    ),
                    "budget_fixture_update_review_report_ref": (
                        report.source_budget_fixture_update_review_report_ref
                    ),
                    "budget_fixture_update_pr_package_report_ref": (
                        report.source_budget_fixture_update_pr_package_report_ref
                    ),
                    "implemented_slice_count": report.implemented_slice_count,
                    "total_slice_count": report.total_slice_count,
                    "failed_artifact_checks": failed_checks,
                    "missing_artifact_refs": report.missing_artifact_refs,
                    "missing_command_refs": report.missing_command_refs,
                    "external_adoption_target_repos": report.external_adoption_target_repos,
                    "pr_marked_ready": report.pr_marked_ready,
                    "promotion_authorized": report.promotion_authorized,
                    "proposed_changes_applied": report.proposed_changes_applied,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "ready_for_pr_review_external_adoption_required" else 2

        if args.command == "build-pr-review-checklist":
            report, run_dir = run_pr_review_checklist(
                readiness_audit_report_path=args.readiness_audit_report,
                out_dir=args.out_dir,
            )
            blocking_items = [
                item.item_id
                for item in report.items
                if item.recommendation == "block_until_resolved"
            ]
            _print(
                {
                    "status": report.status,
                    "checklist_report_id": report.checklist_report_id,
                    "source_readiness_status": report.source_readiness_status,
                    "source_review_readiness": report.source_review_readiness,
                    "recommendation": report.recommendation,
                    "item_count": report.item_count,
                    "blocking_item_count": report.blocking_item_count,
                    "blocking_items": blocking_items,
                    "pr_marked_ready": report.pr_marked_ready,
                    "github_write_performed": report.github_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "proposed_changes_applied": report.proposed_changes_applied,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "ready_for_human_pr_review" else 2

        if args.command == "record-pr-readiness-decision":
            report, run_dir = run_pr_readiness_decision_record(
                pr_review_checklist_path=args.pr_review_checklist,
                intake_local_closeout_report_path=args.intake_local_closeout_report,
                decision_path=args.decision,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "pr_readiness_decision_report_id": (report.pr_readiness_decision_report_id),
                    "pr_readiness_decision_id": report.pr_readiness_decision_id,
                    "source_pr_review_checklist_status": (report.source_pr_review_checklist_status),
                    "source_closeout_status": report.source_closeout_status,
                    "decision": report.decision,
                    "observed_pr_number": report.observed_pr_number,
                    "observed_pr_state": report.observed_pr_state,
                    "manual_ready_action_required": report.manual_ready_action_required,
                    "failed_checks": failed_checks,
                    "pr_marked_ready": report.pr_marked_ready,
                    "github_write_performed": report.github_write_performed,
                    "github_issue_created": report.github_issue_created,
                    "github_pr_created": report.github_pr_created,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_by_pr_readiness_decision_evidence":
                return 2
            return 0

        if args.command == "build-cross-repo-owner-adoption":
            report, run_dir = run_cross_repo_owner_adoption(
                promotion_package_path=args.promotion_package,
                readiness_audit_report_path=args.readiness_audit_report,
                pr_review_checklist_path=args.pr_review_checklist,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "owner_adoption_report_id": report.owner_adoption_report_id,
                    "source_promotion_package_id": report.source_promotion_package_id,
                    "source_readiness_status": report.source_readiness_status,
                    "source_pr_review_checklist_status": (report.source_pr_review_checklist_status),
                    "packet_count": report.packet_count,
                    "ready_packet_count": report.ready_packet_count,
                    "blocked_packet_count": report.blocked_packet_count,
                    "proposal_count": report.proposal_count,
                    "target_repos": report.target_repos,
                    "github_issue_created": report.github_issue_created,
                    "github_pr_created": report.github_pr_created,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "owner_adoption_packets_ready" else 2

        if args.command == "build-cross-repo-owner-issue-drafts":
            report, run_dir = run_cross_repo_owner_issue_drafts(
                owner_adoption_report_path=args.owner_adoption_report,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "issue_draft_report_id": report.issue_draft_report_id,
                    "source_owner_adoption_status": report.source_owner_adoption_status,
                    "draft_count": report.draft_count,
                    "ready_draft_count": report.ready_draft_count,
                    "blocked_draft_count": report.blocked_draft_count,
                    "target_repos": report.target_repos,
                    "manual_creation_required": report.manual_creation_required,
                    "github_issue_created": report.github_issue_created,
                    "github_pr_created": report.github_pr_created,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "issue_drafts_ready_for_manual_creation" else 2

        if args.command == "audit-intake-local-closeout":
            report, run_dir = run_intake_local_closeout(
                readiness_audit_report_path=args.readiness_audit_report,
                pr_review_checklist_path=args.pr_review_checklist,
                owner_adoption_report_path=args.owner_adoption_report,
                owner_issue_draft_report_path=args.owner_issue_draft_report,
                out_dir=args.out_dir,
                observed_pr_number=args.observed_pr_number,
                observed_pr_url=args.observed_pr_url,
                observed_pr_state=args.observed_pr_state,
            )
            blocking_checks = [
                check.check_id for check in report.checks if check.status == "blocked"
            ]
            _print(
                {
                    "status": report.status,
                    "closeout_report_id": report.closeout_report_id,
                    "observed_pr_number": report.observed_pr_number,
                    "observed_pr_state": report.observed_pr_state,
                    "check_count": report.check_count,
                    "passed_check_count": report.passed_check_count,
                    "blocking_check_count": report.blocking_check_count,
                    "blocking_checks": blocking_checks,
                    "manual_actions_remaining": report.manual_actions_remaining,
                    "manual_pr_state_change_required": report.manual_pr_state_change_required,
                    "manual_owner_issue_creation_required": (
                        report.manual_owner_issue_creation_required
                    ),
                    "pr_state_change_performed": report.pr_state_change_performed,
                    "github_issue_created": report.github_issue_created,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0 if report.status == "intake_local_closeout_ready_manual_actions_required" else 2
            )
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    return 2
