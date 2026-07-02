from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from pydantic import ValidationError

from .budget_actuals import run_budget_actual_comparison
from .budget_actual_variance_ledger import BUDGET_ACTUAL_VARIANCE_LEDGER_REPORT_FILENAME
from .budget_actual_variance_owner_adoption import (
    run_budget_actual_variance_owner_adoption,
)
from .budget_calibration_starter_pack import run_budget_calibration_starter_pack
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
from .budget_human_review_outcome_owner_adoption import (
    run_budget_human_review_outcome_owner_adoption,
)
from .budget_human_review_packet import run_budget_human_review_packet
from .budget_human_review_outcomes import run_budget_human_review_outcome_record
from .budget_lake_admission_bundle import run_budget_event_lake_admission_bundle
from .budget_lifecycle_audit import run_budget_lifecycle_audit
from .budget_lifecycle_owner_adoption import run_budget_lifecycle_owner_adoption
from .budget_revisions import run_budget_review_record
from .coherence import validate_budget_artifacts
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
from .courtlistener_dataset_strategy import run_courtlistener_dataset_strategy_audit
from .courtlistener_fixture_audit import run_courtlistener_fixture_audit
from .cross_repo_owner_adoption import run_cross_repo_owner_adoption
from .cross_repo_owner_issue_draft_quality import run_owner_issue_draft_quality_audit
from .cross_repo_owner_issue_drafts import run_cross_repo_owner_issue_drafts
from .dad_review_issue_outbox import record_dad_review_issue_to_outbox
from .intake_local_closeout import run_intake_local_closeout
from .intake_vertical_readiness_audit import run_intake_vertical_readiness_audit
from .learning_promotion_readiness import run_learning_promotion_readiness
from .learning_owner_handoffs import run_learning_owner_handoffs
from .learning_proposed_changes import run_learning_proposed_changes
from .learning_shadow_eval_fixture_results import (
    run_learning_shadow_eval_fixture_results,
)
from .learning_shadow_eval_results import run_learning_shadow_eval_results
from .labor_employment_budget_facts import run_labor_employment_budget_fact_audit
from .labor_employment_budget_fact_gold import (
    run_labor_employment_budget_fact_gold_validation,
)
from .labor_employment_executable_coverage import (
    run_labor_employment_executable_coverage_audit,
)
from .labor_employment_executable_fact_binding import (
    run_labor_employment_executable_fact_binding_audit,
)
from .labor_employment_executable_driver_binding import (
    run_labor_employment_executable_driver_binding_audit,
)
from .labor_employment_executable_driver_impact import (
    run_labor_employment_executable_driver_impact_audit,
)
from .labor_employment_driver_impact_review import (
    DEFAULT_LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_SPEC,
    run_labor_employment_driver_impact_review,
)
from .labor_employment_blocked_driver_impact_review import (
    run_labor_employment_blocked_driver_impact_review,
)
from .labor_employment_budget_output_expectations import (
    run_labor_employment_budget_output_expectations_audit,
)
from .labor_employment_executable_fixtures import (
    run_labor_employment_executable_fixture_audit,
)
from .labor_employment_fixture_family_pack import (
    run_labor_employment_fixture_family_pack_audit,
)
from .labor_employment_qa_matrix import run_labor_employment_qa_matrix
from .matter_linking_preflight import run_matter_linking_preflight
from .models import BudgetProposal, HumanConfirmation
from .orchestrator_owner_review_request import run_orchestrator_owner_review_request
from .pr_readiness_decision import run_pr_readiness_decision_record
from .pr_review_checklist import run_pr_review_checklist
from .public_data_cache import run_public_data_cache_audit
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
from .remaining_roadmap import run_remaining_roadmap_plan
from .reviewed_learning_gate import run_reviewed_learning_gate
from .synthetic_fixture_depth_audit import run_synthetic_fixture_depth_audit
from .synthetic_fixture_expansion import run_synthetic_fixture_expansion_audit
from .synthetic_qa_bundle import run_synthetic_qa_bundle
from .synthetic_qa_review_run import run_synthetic_qa_review_run
from .ui_review_data_bundle import build_ui_review_data_bundle
from .ui_review_manifest import build_ui_review_manifest
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
    budget.add_argument(
        "--labor-employment-budget-fact-report",
        help=(
            "Optional labor_employment_budget_fact_audit_report.json used as a "
            "budget precondition gate."
        ),
    )
    budget.add_argument(
        "--labor-employment-driver-impact-report",
        help=(
            "Optional labor_employment_executable_driver_impact_report.json used as "
            "a candidate budget-impact precondition and range/scenario review input."
        ),
    )

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

    validate_budget_artifact = sub.add_parser(
        "validate-budget-artifact",
        help="Validate serialized budget/projection artifacts for deterministic coherence.",
    )
    validate_budget_artifact.add_argument("--budget-proposal", required=True)
    validate_budget_artifact.add_argument("--carrier-projection")
    validate_budget_artifact.add_argument("--report-out")

    ui_review_manifest = sub.add_parser(
        "build-ui-review-manifest",
        help="Build a read-only frontend manifest from local synthetic run and QA artifacts.",
    )
    ui_review_manifest.add_argument("--run-root", required=True)
    ui_review_manifest.add_argument("--out", required=True)
    ui_review_manifest.add_argument(
        "--generated-at",
        help="Optional fixed timestamp for deterministic tests and replayed manifests.",
    )

    ui_review_data_bundle = sub.add_parser(
        "build-ui-review-data-bundle",
        help="Build a read-only local JSON bundle for the review UI detail reports.",
    )
    ui_review_data_bundle.add_argument("--run-root", required=True)
    ui_review_data_bundle.add_argument("--out", required=True)
    ui_review_data_bundle.add_argument(
        "--generated-at",
        help="Optional fixed timestamp for deterministic tests and replayed bundles.",
    )

    synthetic_qa_bundle = sub.add_parser(
        "build-synthetic-qa-bundle",
        help="Bundle local synthetic QA evidence and refresh the read-only review UI manifest.",
    )
    synthetic_qa_bundle.add_argument("--run-root", required=True)
    synthetic_qa_bundle.add_argument("--out-dir", required=True)
    synthetic_qa_bundle.add_argument("--budget-coherence-report")
    synthetic_qa_bundle.add_argument("--fixture-depth-report")
    synthetic_qa_bundle.add_argument(
        "--fixture-depth-manifest",
        help="Optional synthetic fixture expansion manifest; generates a depth audit into out-dir.",
    )
    synthetic_qa_bundle.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for fixture-depth generation when --fixture-depth-manifest is used.",
    )
    synthetic_qa_bundle.add_argument("--budget-calibration-readiness-report")
    synthetic_qa_bundle.add_argument(
        "--ui-manifest-out",
        help="Optional ui_review_manifest.json path to refresh after bundling QA artifacts.",
    )
    synthetic_qa_bundle.add_argument(
        "--generated-at",
        help="Optional fixed timestamp for deterministic tests and replayed manifests.",
    )

    synthetic_qa_review_run = sub.add_parser(
        "build-synthetic-qa-review-run",
        help=(
            "Build the deterministic synthetic QA review chain, including L&E QA "
            "reports and read-only UI artifacts."
        ),
    )
    synthetic_qa_review_run.add_argument("--run-root", required=True)
    synthetic_qa_review_run.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for synthetic examples and config.",
    )
    synthetic_qa_review_run.add_argument(
        "--generated-at",
        help="Optional fixed timestamp for deterministic tests and replayed reports.",
    )

    calibration_starter_pack = sub.add_parser(
        "build-budget-calibration-starter-pack",
        help=(
            "Build a deterministic synthetic budget calibration review chain for QA "
            "without applying calibration."
        ),
    )
    calibration_starter_pack.add_argument(
        "--corpus-root",
        default="examples/synthetic",
        help="Synthetic fixture corpus root to use for the starter chain.",
    )
    calibration_starter_pack.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative fixture and replay refs.",
    )
    calibration_starter_pack.add_argument("--out-dir", required=True)
    calibration_starter_pack.add_argument(
        "--artifact-kind",
        default="budget_review_fixture",
        choices=[
            "budget_review_fixture",
            "actuals_fixture",
            "carrier_rejection_fixture",
            "reviewed_gold_fixture",
            "learning_gate_fixture",
        ],
        help="Planned replay artifact kind to execute for the starter chain.",
    )
    calibration_starter_pack.add_argument(
        "--reviewed-at",
        help="Optional fixed timestamp for the synthetic QA review outcome.",
    )

    le_qa_matrix = sub.add_parser(
        "build-labor-employment-qa-matrix",
        help=(
            "Build a deterministic synthetic L&E QA matrix for critical fact blockers "
            "and range-only review posture."
        ),
    )
    le_qa_matrix.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative synthetic L&E manifest refs.",
    )
    le_qa_matrix.add_argument("--out-dir", required=True)

    le_fixture_family_pack = sub.add_parser(
        "audit-labor-employment-fixture-family-pack",
        help=(
            "Audit the synthetic L&E budget fixture-family pack for family, "
            "variant, fact-need, driver, and no-write coverage."
        ),
    )
    le_fixture_family_pack.add_argument(
        "--pack",
        default=(
            "examples/synthetic/labor-employment/labor-employment-budget-fixture-family-pack.json"
        ),
        help="Path to labor-employment-budget-fixture-family-pack.json.",
    )
    le_fixture_family_pack.add_argument(
        "--fact-needs",
        default="config/labor-employment-budget-fact-needs.yaml",
        help="Path to the candidate L&E budget fact-needs policy.",
    )
    le_fixture_family_pack.add_argument("--out-dir", required=True)

    le_executable_fixtures = sub.add_parser(
        "audit-labor-employment-executable-fixtures",
        help=(
            "Run selected synthetic L&E source bundles through preflight and audit "
            "their pack links, source signals, exception labels, and no-write boundaries."
        ),
    )
    le_executable_fixtures.add_argument(
        "--manifest",
        default=(
            "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
        ),
        help="Path to labor-employment-executable-fixtures-manifest.json.",
    )
    le_executable_fixtures.add_argument(
        "--pack",
        help="Optional override path to labor-employment-budget-fixture-family-pack.json.",
    )
    le_executable_fixtures.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative synthetic L&E executable fixture refs.",
    )
    le_executable_fixtures.add_argument("--out-dir", required=True)

    le_executable_coverage = sub.add_parser(
        "audit-labor-employment-executable-coverage",
        help=(
            "Compare the L&E executable fixture manifest to the full fixture-family "
            "pack and report remaining executable coverage gaps."
        ),
    )
    le_executable_coverage.add_argument(
        "--manifest",
        default=(
            "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
        ),
        help="Path to labor-employment-executable-fixtures-manifest.json.",
    )
    le_executable_coverage.add_argument(
        "--pack",
        help="Optional override path to labor-employment-budget-fixture-family-pack.json.",
    )
    le_executable_coverage.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative synthetic L&E coverage refs.",
    )
    le_executable_coverage.add_argument("--out-dir", required=True)

    le_executable_fact_binding = sub.add_parser(
        "audit-labor-employment-executable-fact-binding",
        help=(
            "Bind executable synthetic L&E preflight evidence to candidate "
            "budget-fact gaps without producing an amount budget."
        ),
    )
    le_executable_fact_binding.add_argument(
        "--binding-manifest",
        default=(
            "examples/synthetic/labor-employment/"
            "labor-employment-executable-budget-fact-bindings.json"
        ),
        help="Path to labor-employment-executable-budget-fact-bindings.json.",
    )
    le_executable_fact_binding.add_argument(
        "--executable-fixture-report",
        required=True,
        help="Path to labor_employment_executable_fixtures_report.json.",
    )
    le_executable_fact_binding.add_argument(
        "--fact-policy",
        help="Optional override path to config/labor-employment-budget-fact-needs.yaml.",
    )
    le_executable_fact_binding.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative synthetic L&E binding refs.",
    )
    le_executable_fact_binding.add_argument("--out-dir", required=True)

    le_executable_driver_binding = sub.add_parser(
        "audit-labor-employment-executable-driver-binding",
        help=(
            "Bind executable synthetic L&E fact-gap evidence to budget-driver "
            "focus dimensions without producing an amount budget."
        ),
    )
    le_executable_driver_binding.add_argument(
        "--executable-fixture-report",
        required=True,
        help="Path to labor_employment_executable_fixtures_report.json.",
    )
    le_executable_driver_binding.add_argument(
        "--executable-fact-binding-report",
        required=True,
        help="Path to labor_employment_executable_fact_binding_report.json.",
    )
    le_executable_driver_binding.add_argument(
        "--pack",
        help="Optional override path to labor-employment-budget-fixture-family-pack.json.",
    )
    le_executable_driver_binding.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative synthetic L&E driver-binding refs.",
    )
    le_executable_driver_binding.add_argument("--out-dir", required=True)

    le_executable_driver_impact = sub.add_parser(
        "audit-labor-employment-executable-driver-impact",
        help=(
            "Map executable synthetic L&E driver bindings to candidate budget-impact "
            "policy without producing dollar amounts."
        ),
    )
    le_executable_driver_impact.add_argument(
        "--executable-driver-binding-report",
        required=True,
        help="Path to labor_employment_executable_driver_binding_report.json.",
    )
    le_executable_driver_impact.add_argument("--out-dir", required=True)

    le_driver_impact_review = sub.add_parser(
        "review-labor-employment-driver-impact-slice",
        help=(
            "Materialize a reviewed nonblocking synthetic L&E driver-impact slice "
            "for local budget-gate replay."
        ),
    )
    le_driver_impact_review.add_argument(
        "--review-spec",
        default=DEFAULT_LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_SPEC,
        help="Path to labor-employment-driver-impact-review.json.",
    )
    le_driver_impact_review.add_argument(
        "--driver-impact-report",
        required=True,
        help="Path to labor_employment_executable_driver_impact_report.json.",
    )
    le_driver_impact_review.add_argument("--out-dir", required=True)

    le_blocked_driver_impact_review = sub.add_parser(
        "review-labor-employment-blocked-driver-impacts",
        help=(
            "Build a synthetic review packet for L&E driver impacts that block "
            "amount-budget output."
        ),
    )
    le_blocked_driver_impact_review.add_argument(
        "--fact-binding-report",
        required=True,
        help="Path to labor_employment_executable_fact_binding_report.json.",
    )
    le_blocked_driver_impact_review.add_argument(
        "--driver-binding-report",
        required=True,
        help="Path to labor_employment_executable_driver_binding_report.json.",
    )
    le_blocked_driver_impact_review.add_argument(
        "--driver-impact-report",
        required=True,
        help="Path to labor_employment_executable_driver_impact_report.json.",
    )
    le_blocked_driver_impact_review.add_argument("--out-dir", required=True)

    le_budget_output_expectations = sub.add_parser(
        "audit-labor-employment-budget-output-expectations",
        help=(
            "Aggregate reviewed and blocked synthetic L&E driver impacts into "
            "candidate allowed budget-output expectations."
        ),
    )
    le_budget_output_expectations.add_argument(
        "--driver-impact-report",
        required=True,
        help="Path to labor_employment_executable_driver_impact_report.json.",
    )
    le_budget_output_expectations.add_argument(
        "--driver-impact-review-report",
        required=True,
        help="Path to labor_employment_driver_impact_review_report.json.",
    )
    le_budget_output_expectations.add_argument(
        "--blocked-driver-impact-review-report",
        required=True,
        help="Path to labor_employment_blocked_driver_impact_review_report.json.",
    )
    le_budget_output_expectations.add_argument("--out-dir", required=True)

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

    matter_linking_preflight = sub.add_parser(
        "audit-matter-linking-preflight",
        help=(
            "Audit an Upfront-like intake output for ambiguous matter/document linking "
            "without connector or Lake writes."
        ),
    )
    matter_linking_preflight.add_argument(
        "--input",
        required=True,
        help="Path to upfront-like-intake-output JSON.",
    )
    matter_linking_preflight.add_argument("--out-dir", required=True)
    matter_linking_preflight.add_argument(
        "--generated-at",
        help="Optional fixed timestamp for deterministic tests and replayed reports.",
    )

    public_data_cache = sub.add_parser(
        "audit-public-data-cache",
        help="Audit a local ignored public-data cache manifest before methodology review.",
    )
    public_data_cache.add_argument("--cache-root", required=True)
    public_data_cache.add_argument("--out-dir", required=True)
    public_data_cache.add_argument(
        "--manifest",
        help="Optional path to public_data_cache_manifest.json; defaults under --cache-root.",
    )
    public_data_cache.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to inspect; defaults to the current working directory.",
    )

    courtlistener_dataset_strategy = sub.add_parser(
        "audit-courtlistener-dataset-strategy",
        help="Audit the offline CourtListener early-case corpus and Rust shadow strategy.",
    )
    courtlistener_dataset_strategy.add_argument("--out-dir", required=True)
    courtlistener_dataset_strategy.add_argument(
        "--repo-root",
        default=".",
        help="Repository root to inspect; defaults to the current working directory.",
    )
    courtlistener_dataset_strategy.add_argument(
        "--strategy-config",
        help="Optional CourtListener dataset strategy YAML path.",
    )

    courtlistener_fixture_audit = sub.add_parser(
        "audit-courtlistener-fixture",
        help="Audit an offline CourtListener-style fixture manifest and source-bound labels.",
    )
    courtlistener_fixture_audit.add_argument(
        "--manifest",
        required=True,
        help="Path to courtlistener dataset manifest JSON.",
    )
    courtlistener_fixture_audit.add_argument("--out-dir", required=True)
    courtlistener_fixture_audit.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative fixture refs; defaults to current directory.",
    )

    labor_employment_budget_facts = sub.add_parser(
        "audit-labor-employment-budget-facts",
        help="Audit source-bound L&E budget fact coverage and missing budget blockers.",
    )
    labor_employment_budget_facts.add_argument(
        "--manifest",
        required=True,
        help="Path to courtlistener dataset manifest JSON.",
    )
    labor_employment_budget_facts.add_argument("--out-dir", required=True)
    labor_employment_budget_facts.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative fixture refs; defaults to current directory.",
    )
    labor_employment_budget_facts.add_argument(
        "--fact-policy",
        help="Optional L&E budget fact needs YAML path.",
    )

    labor_employment_budget_fact_gold = sub.add_parser(
        "validate-labor-employment-budget-fact-gold",
        help=("Replay L&E budget fact audits against reviewed synthetic gold expectations."),
    )
    labor_employment_budget_fact_gold.add_argument(
        "--gold",
        default="examples/synthetic/gold/labor-employment-budget-fact-gold.json",
        help="Path to labor-employment-budget-fact-gold.json.",
    )
    labor_employment_budget_fact_gold.add_argument("--out-dir", required=True)
    labor_employment_budget_fact_gold.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative fixture refs; defaults to current directory.",
    )
    labor_employment_budget_fact_gold.add_argument(
        "--fact-policy",
        help="Optional L&E budget fact needs YAML path.",
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

    budget_human_review_packet = sub.add_parser(
        "build-budget-human-review-packet",
        help="Build a consolidated human review packet for budget lifecycle evidence.",
    )
    budget_human_review_packet.add_argument("--out-dir", required=True)
    budget_human_review_packet.add_argument(
        "--budget-lifecycle-audit-report",
        required=True,
        help="Path to budget_lifecycle_audit_report.json.",
    )
    budget_human_review_packet.add_argument(
        "--budget-revision-report",
        help="Optional budget_revision_report.json.",
    )
    budget_human_review_packet.add_argument(
        "--budget-actual-comparison-report",
        help="Optional budget_actual_comparison_report.json.",
    )
    budget_human_review_packet.add_argument(
        "--carrier-rejection-review-packet",
        help="Optional carrier_rejection_review_packet.json.",
    )
    budget_human_review_packet.add_argument(
        "--carrier-rejection-learning-report",
        help="Optional carrier_rejection_learning_report.json.",
    )

    budget_human_review_outcome = sub.add_parser(
        "record-budget-human-review-outcome",
        help="Record append-only human decisions from a budget human review packet.",
    )
    budget_human_review_outcome.add_argument("--out-dir", required=True)
    budget_human_review_outcome.add_argument(
        "--budget-human-review-packet",
        required=True,
        help="Path to budget_human_review_packet.json.",
    )
    budget_human_review_outcome.add_argument(
        "--outcome",
        required=True,
        help="Path to a human-authored budget human review outcome record JSON.",
    )

    budget_human_review_outcome_owner_adoption = sub.add_parser(
        "build-budget-human-review-outcome-owner-adoption",
        help="Build owner-review packets from budget human review outcome evidence.",
    )
    budget_human_review_outcome_owner_adoption.add_argument("--out-dir", required=True)
    budget_human_review_outcome_owner_adoption.add_argument(
        "--budget-human-review-outcome-report",
        required=True,
        help="Path to budget_human_review_outcome_report.json.",
    )
    budget_human_review_outcome_owner_adoption.add_argument(
        "--budget-human-review-outcome-record",
        required=True,
        help="Path to budget_human_review_outcome_record.json.",
    )

    budget_actual_variance_owner_adoption = sub.add_parser(
        "build-budget-actual-variance-owner-adoption",
        help="Build owner-review packets from budget actual variance evidence.",
    )
    budget_actual_variance_owner_adoption.add_argument("--out-dir", required=True)
    budget_actual_variance_owner_adoption.add_argument(
        "--budget-actual-comparison-report",
        required=True,
        help="Path to budget_actual_comparison_report.json.",
    )
    budget_actual_variance_owner_adoption.add_argument(
        "--budget-actual-variance-ledger-report",
        required=True,
        help="Path to budget_actual_variance_ledger_report.json.",
    )

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

    orchestrator_owner_review_request = sub.add_parser(
        "build-orchestrator-owner-review-request",
        help="Build a local Orchestrator-compatible intake owner-review request.",
    )
    orchestrator_owner_review_request.add_argument("--preflight-packet", required=True)
    orchestrator_owner_review_request.add_argument("--confirmation", required=True)
    orchestrator_owner_review_request.add_argument("--budget", required=True)
    orchestrator_owner_review_request.add_argument("--out-dir", required=True)
    orchestrator_owner_review_request.add_argument("--budget-precondition-report")
    orchestrator_owner_review_request.add_argument("--budget-actual-comparison-report")
    orchestrator_owner_review_request.add_argument("--carrier-rejection-decision-ledger-report")
    orchestrator_owner_review_request.add_argument("--carrier-rejection-source-bundle")
    orchestrator_owner_review_request.add_argument(
        "--lake-handoff-mode",
        choices=["disabled", "validate_only"],
        default="disabled",
    )

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
    remaining_roadmap = sub.add_parser(
        "plan-remaining-roadmap",
        help="Build a local remaining-phase roadmap from readiness and closeout evidence.",
    )
    remaining_roadmap.add_argument(
        "--readiness-audit-report",
        required=True,
        help="Path to intake_vertical_readiness_audit_report.json.",
    )
    remaining_roadmap.add_argument(
        "--intake-local-closeout-report",
        required=True,
        help="Path to intake_local_closeout_report.json.",
    )
    remaining_roadmap.add_argument(
        "--pr-readiness-decision-report",
        help="Optional path to pr_readiness_decision_report.json.",
    )
    remaining_roadmap.add_argument("--out-dir", required=True)
    fixture_expansion = sub.add_parser(
        "audit-synthetic-fixture-expansion",
        help="Audit synthetic holdout fixture expansion against the remaining roadmap.",
    )
    fixture_expansion.add_argument(
        "--remaining-roadmap-report",
        required=True,
        help="Path to remaining_roadmap_report.json.",
    )
    fixture_expansion.add_argument(
        "--manifest",
        required=True,
        help="Path to synthetic fixture expansion manifest JSON.",
    )
    fixture_expansion.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative fixture/test refs.",
    )
    fixture_expansion.add_argument("--out-dir", required=True)
    fixture_depth = sub.add_parser(
        "audit-synthetic-fixture-depth",
        help="Audit synthetic holdout fixture depth against high-risk learning-loop gaps.",
    )
    fixture_depth.add_argument(
        "--manifest",
        required=True,
        help="Path to synthetic fixture expansion manifest JSON.",
    )
    fixture_depth.add_argument(
        "--repo-root",
        default=".",
        help="Repository root for relative fixture refs.",
    )
    fixture_depth.add_argument("--out-dir", required=True)
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
    owner_issue_draft_quality = sub.add_parser(
        "audit-owner-issue-draft-quality",
        help="Audit local owner issue draft text before manual issue creation.",
    )
    owner_issue_draft_quality.add_argument(
        "--issue-draft-report",
        required=True,
        help="Path to cross_repo_owner_issue_draft_report.json.",
    )
    owner_issue_draft_quality.add_argument("--out-dir", required=True)
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
        choices=["draft", "ready_for_review", "merged", "not_supplied"],
        default="not_supplied",
    )

    dad_review_issue = sub.add_parser(
        "record-dad-review-issue",
        help=(
            "Record a complex review finding as candidate DAD mail in "
            ".digital-asset/mail/outbox.jsonl."
        ),
    )
    dad_review_issue.add_argument(
        "--issue",
        required=True,
        help="Path to a dad-review-issue JSON record.",
    )
    dad_review_issue.add_argument(
        "--repo-root",
        default=".",
        help="Repo root whose .digital-asset/mail/outbox.jsonl should receive the record.",
    )
    dad_review_issue.add_argument(
        "--outbox",
        default=".digital-asset/mail/outbox.jsonl",
        help="Repo-local DAD outbox path. Must stay under .digital-asset/mail.",
    )
    dad_review_issue.add_argument(
        "--report-out",
        help="Optional path for dad_review_issue_outbox_report.json.",
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
                labor_employment_budget_fact_report=args.labor_employment_budget_fact_report,
                labor_employment_driver_impact_report=(args.labor_employment_driver_impact_report),
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
                    "labor_employment_budget_fact_report": args.labor_employment_budget_fact_report,
                    "labor_employment_driver_impact_report": (
                        args.labor_employment_driver_impact_report
                    ),
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

        if args.command == "validate-budget-artifact":
            report = validate_budget_artifacts(
                args.budget_proposal,
                carrier_projection_path=args.carrier_projection,
                report_out=args.report_out,
            )
            _print(report)
            return 0 if report["status"] == "passed" else 1

        if args.command == "build-ui-review-manifest":
            manifest = build_ui_review_manifest(
                run_root=args.run_root,
                out_path=args.out,
                generated_at=args.generated_at,
            )
            _print(
                {
                    "status": manifest["overallStatus"],
                    "manifest_id": manifest["manifestId"],
                    "out": args.out,
                    "artifact_count": len(manifest["artifacts"]),
                    "quality_gate_count": len(manifest["qualityGates"]),
                    "external_writes_performed": False,
                }
            )
            return 0 if manifest["overallStatus"] != "failed" else 1

        if args.command == "build-ui-review-data-bundle":
            bundle = build_ui_review_data_bundle(
                run_root=args.run_root,
                out_path=args.out,
                generated_at=args.generated_at,
            )
            _print(
                {
                    "status": bundle.status,
                    "ui_review_data_bundle_id": bundle.ui_review_data_bundle_id,
                    "out": args.out,
                    "detail_report_count": bundle.detail_report_count,
                    "missing_required_detail_report_count": (
                        bundle.missing_required_detail_report_count
                    ),
                    "external_write_report_count": bundle.external_write_report_count,
                    "external_writes_performed": False,
                    "lake_write_performed": False,
                    "sqlite_write_performed": False,
                }
            )
            return 0 if bundle.status == "ready_for_review" else 2

        if args.command == "build-synthetic-qa-bundle":
            report, run_dir, ui_manifest = run_synthetic_qa_bundle(
                run_root=args.run_root,
                out_dir=args.out_dir,
                budget_coherence_report_path=args.budget_coherence_report,
                fixture_depth_report_path=args.fixture_depth_report,
                fixture_depth_manifest_path=args.fixture_depth_manifest,
                repo_root=args.repo_root,
                budget_calibration_readiness_report_path=(args.budget_calibration_readiness_report),
                ui_manifest_out=args.ui_manifest_out,
                generated_at=args.generated_at,
            )
            ui_data_bundle = (
                load_json(Path(report.ui_data_bundle_ref))
                if report.ui_data_bundle_ref and Path(report.ui_data_bundle_ref).is_file()
                else None
            )
            _print(
                {
                    "status": report.status,
                    "synthetic_qa_bundle_report_id": (report.synthetic_qa_bundle_report_id),
                    "run_dir": str(run_dir),
                    "artifact_count": report.artifact_count,
                    "missing_required_artifact_count": (report.missing_required_artifact_count),
                    "blocked_artifact_count": report.blocked_artifact_count,
                    "pending_artifact_count": report.pending_artifact_count,
                    "ui_manifest_ref": report.ui_manifest_ref,
                    "ui_manifest_status": (ui_manifest["overallStatus"] if ui_manifest else None),
                    "ui_data_bundle_ref": report.ui_data_bundle_ref,
                    "ui_data_bundle_status": (ui_data_bundle["status"] if ui_data_bundle else None),
                    "external_writes_performed": False,
                    "lake_write_performed": False,
                    "sqlite_write_performed": False,
                }
            )
            return 0 if report.status in {"passed", "pending_review"} else 2

        if args.command == "build-synthetic-qa-review-run":
            report, run_dir = run_synthetic_qa_review_run(
                run_root=args.run_root,
                repo_root=args.repo_root,
                generated_at=args.generated_at,
            )
            _print(
                {
                    "status": report.status,
                    "synthetic_qa_review_run_report_id": (report.synthetic_qa_review_run_report_id),
                    "run_dir": str(run_dir),
                    "step_count": report.step_count,
                    "failed_step_count": report.failed_step_count,
                    "synthetic_qa_bundle_ref": report.synthetic_qa_bundle_ref,
                    "ui_manifest_ref": report.ui_manifest_ref,
                    "ui_data_bundle_ref": report.ui_data_bundle_ref,
                    "external_writes_performed": False,
                    "lake_write_performed": False,
                    "sqlite_write_performed": False,
                    "silent_learning_performed": False,
                }
            )
            return 0 if report.status == "synthetic_qa_review_run_ready" else 2

        if args.command == "build-budget-calibration-starter-pack":
            report, run_dir = run_budget_calibration_starter_pack(
                corpus_root=args.corpus_root,
                repo_root=args.repo_root,
                out_dir=args.out_dir,
                artifact_kind=args.artifact_kind,
                reviewed_at=args.reviewed_at,
            )
            _print(
                {
                    "status": report.status,
                    "starter_pack_report_id": report.starter_pack_report_id,
                    "selected_replay_case_id": report.selected_replay_case_id,
                    "selected_artifact_kind": report.selected_artifact_kind,
                    "budget_calibration_readiness_status": (
                        report.budget_calibration_readiness_status
                    ),
                    "budget_calibration_readiness_report_ref": (
                        report.budget_calibration_readiness_report_ref
                    ),
                    "run_dir": str(run_dir),
                    "fixture_files_mutated": report.fixture_files_mutated,
                    "fixture_binding_applied": report.fixture_binding_applied,
                    "calibration_applied": report.calibration_applied,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                }
            )
            return (
                0 if report.status == "starter_pack_ready_for_manual_fixture_update_review" else 2
            )

        if args.command == "build-labor-employment-qa-matrix":
            report, run_dir = run_labor_employment_qa_matrix(
                repo_root=args.repo_root,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "labor_employment_qa_matrix_report_id": (
                        report.labor_employment_qa_matrix_report_id
                    ),
                    "case_count": report.case_count,
                    "failed_case_count": report.failed_case_count,
                    "run_dir": str(run_dir),
                    "budget_amount_output_authorized": (report.budget_amount_output_authorized),
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                }
            )
            return 0 if report.status == "labor_employment_qa_matrix_ready_for_review" else 2

        if args.command == "audit-labor-employment-fixture-family-pack":
            report, run_dir = run_labor_employment_fixture_family_pack_audit(
                pack_path=args.pack,
                fact_needs_path=args.fact_needs,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "fixture_family_pack_report_id": (report.fixture_family_pack_report_id),
                    "pack_id": report.pack_id,
                    "case_count": report.case_count,
                    "missing_family_variant_count": report.missing_family_variant_count,
                    "missing_fact_need_ids": report.missing_fact_need_ids,
                    "missing_budget_driver_dimensions": (report.missing_budget_driver_dimensions),
                    "failed_checks": failed_checks,
                    "fixture_generation_authorized": report.fixture_generation_authorized,
                    "calibration_approved": report.calibration_approved,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0 if report.status == "labor_employment_fixture_family_pack_ready_for_review" else 2
            )

        if args.command == "audit-labor-employment-executable-fixtures":
            report, run_dir = run_labor_employment_executable_fixture_audit(
                manifest_path=args.manifest,
                pack_path=args.pack,
                repo_root=args.repo_root,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "executable_fixture_audit_report_id": (
                        report.executable_fixture_audit_report_id
                    ),
                    "manifest_id": report.manifest_id,
                    "fixture_count": report.fixture_count,
                    "preflight_executed_count": report.preflight_executed_count,
                    "failed_case_count": report.failed_case_count,
                    "missing_pack_link_count": report.missing_pack_link_count,
                    "missing_source_signal_count": report.missing_source_signal_count,
                    "missing_expected_exception_label_count": (
                        report.missing_expected_exception_label_count
                    ),
                    "failed_checks": failed_checks,
                    "budget_amount_output_authorized": (report.budget_amount_output_authorized),
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "fixture_generation_authorized": report.fixture_generation_authorized,
                    "calibration_approved": report.calibration_approved,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0 if report.status == "labor_employment_executable_fixtures_ready_for_review" else 2
            )

        if args.command == "audit-labor-employment-executable-coverage":
            report, run_dir = run_labor_employment_executable_coverage_audit(
                manifest_path=args.manifest,
                pack_path=args.pack,
                repo_root=args.repo_root,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "coverage_state": report.coverage_state,
                    "executable_coverage_report_id": report.executable_coverage_report_id,
                    "pack_id": report.pack_id,
                    "executable_manifest_id": report.executable_manifest_id,
                    "pack_case_count": report.pack_case_count,
                    "executable_fixture_count": report.executable_fixture_count,
                    "covered_pack_case_count": report.covered_pack_case_count,
                    "missing_executable_pack_case_count": (
                        report.missing_executable_pack_case_count
                    ),
                    "covered_family_variant_count": report.covered_family_variant_count,
                    "missing_family_variant_count": report.missing_family_variant_count,
                    "failed_checks": failed_checks,
                    "fixture_generation_authorized": report.fixture_generation_authorized,
                    "calibration_approved": report.calibration_approved,
                    "budget_amount_output_authorized": report.budget_amount_output_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0 if report.status == "labor_employment_executable_coverage_ready_for_review" else 2
            )

        if args.command == "audit-labor-employment-executable-fact-binding":
            report, run_dir = run_labor_employment_executable_fact_binding_audit(
                binding_manifest_path=args.binding_manifest,
                executable_fixture_report_path=args.executable_fixture_report,
                fact_policy_path=args.fact_policy,
                repo_root=args.repo_root,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "executable_budget_fact_binding_report_id": (
                        report.executable_budget_fact_binding_report_id
                    ),
                    "binding_manifest_id": report.binding_manifest_id,
                    "case_count": report.case_count,
                    "failed_case_count": report.failed_case_count,
                    "fact_binding_count": report.fact_binding_count,
                    "critical_fact_binding_count": report.critical_fact_binding_count,
                    "evidence_bound_fact_count": report.evidence_bound_fact_count,
                    "exception_bound_fact_count": report.exception_bound_fact_count,
                    "missing_policy_fact_count": report.missing_policy_fact_count,
                    "missing_source_signal_count": report.missing_source_signal_count,
                    "missing_exception_label_count": report.missing_exception_label_count,
                    "missing_source_id_count": report.missing_source_id_count,
                    "failed_checks": failed_checks,
                    "budget_amount_output_authorized": (report.budget_amount_output_authorized),
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0
                if report.status
                == "labor_employment_executable_budget_fact_bindings_ready_for_review"
                else 2
            )

        if args.command == "audit-labor-employment-executable-driver-binding":
            report, run_dir = run_labor_employment_executable_driver_binding_audit(
                executable_fixture_report_path=args.executable_fixture_report,
                executable_fact_binding_report_path=args.executable_fact_binding_report,
                pack_path=args.pack,
                repo_root=args.repo_root,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "executable_driver_binding_report_id": (
                        report.executable_driver_binding_report_id
                    ),
                    "case_count": report.case_count,
                    "failed_case_count": report.failed_case_count,
                    "driver_binding_count": report.driver_binding_count,
                    "source_bound_driver_count": report.source_bound_driver_count,
                    "unbound_driver_count": report.unbound_driver_count,
                    "critical_driver_block_count": report.critical_driver_block_count,
                    "covered_driver_dimensions": report.covered_driver_dimensions,
                    "missing_driver_dimensions": report.missing_driver_dimensions,
                    "failed_checks": failed_checks,
                    "budget_amount_output_authorized": (report.budget_amount_output_authorized),
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0
                if report.status == "labor_employment_executable_driver_bindings_ready_for_review"
                else 2
            )

        if args.command == "audit-labor-employment-executable-driver-impact":
            report, run_dir = run_labor_employment_executable_driver_impact_audit(
                executable_driver_binding_report_path=args.executable_driver_binding_report,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "executable_driver_impact_report_id": (
                        report.executable_driver_impact_report_id
                    ),
                    "case_count": report.case_count,
                    "failed_case_count": report.failed_case_count,
                    "impact_item_count": report.impact_item_count,
                    "source_bound_impact_count": report.source_bound_impact_count,
                    "block_amount_budget_impact_count": (report.block_amount_budget_impact_count),
                    "range_widening_impact_count": report.range_widening_impact_count,
                    "scenario_fork_impact_count": report.scenario_fork_impact_count,
                    "rate_guideline_review_impact_count": (
                        report.rate_guideline_review_impact_count
                    ),
                    "missing_impact_policy_dimensions": (report.missing_impact_policy_dimensions),
                    "failed_checks": failed_checks,
                    "budget_amount_output_authorized": (report.budget_amount_output_authorized),
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0
                if report.status == "labor_employment_executable_driver_impacts_ready_for_review"
                else 2
            )

        if args.command == "review-labor-employment-driver-impact-slice":
            report, run_dir = run_labor_employment_driver_impact_review(
                review_spec_path=args.review_spec,
                driver_impact_report_path=args.driver_impact_report,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            failed_cases = [
                result.executable_fixture_id
                for result in report.case_results
                if result.status == "failed"
            ]
            _print(
                {
                    "status": report.status,
                    "driver_impact_review_report_id": report.driver_impact_review_report_id,
                    "source_driver_impact_report_id": report.source_driver_impact_report_id,
                    "case_count": report.case_count,
                    "selected_case_count": report.selected_case_count,
                    "failed_case_count": report.failed_case_count,
                    "block_amount_budget_impact_count": (report.block_amount_budget_impact_count),
                    "range_widening_impact_count": report.range_widening_impact_count,
                    "scenario_fork_impact_count": report.scenario_fork_impact_count,
                    "rate_guideline_review_impact_count": (
                        report.rate_guideline_review_impact_count
                    ),
                    "reviewed_slice_report": report.reviewed_slice_report_ref,
                    "failed_cases": failed_cases,
                    "failed_checks": failed_checks,
                    "budget_amount_output_authorized": (report.budget_amount_output_authorized),
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0
                if report.status
                == "labor_employment_driver_impact_review_ready_for_budget_gate_replay"
                else 2
            )

        if args.command == "review-labor-employment-blocked-driver-impacts":
            report, run_dir = run_labor_employment_blocked_driver_impact_review(
                fact_binding_report_path=args.fact_binding_report,
                driver_binding_report_path=args.driver_binding_report,
                driver_impact_report_path=args.driver_impact_report,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "blocked_driver_impact_review_report_id": (
                        report.blocked_driver_impact_review_report_id
                    ),
                    "source_driver_impact_report_id": report.source_driver_impact_report_id,
                    "case_count": report.case_count,
                    "blocked_case_count": report.blocked_case_count,
                    "nonblocking_case_count": report.nonblocking_case_count,
                    "blocker_fact_count": report.blocker_fact_count,
                    "block_amount_budget_impact_count": (report.block_amount_budget_impact_count),
                    "candidate_exception_lake_labels": (report.candidate_exception_lake_labels),
                    "failed_checks": failed_checks,
                    "budget_amount_output_authorized": report.budget_amount_output_authorized,
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0
                if report.status == "labor_employment_blocked_driver_impacts_ready_for_review"
                else 2
            )

        if args.command == "audit-labor-employment-budget-output-expectations":
            report, run_dir = run_labor_employment_budget_output_expectations_audit(
                driver_impact_report_path=args.driver_impact_report,
                driver_impact_review_report_path=args.driver_impact_review_report,
                blocked_driver_impact_review_report_path=(args.blocked_driver_impact_review_report),
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            failed_cases = [
                case.executable_fixture_id for case in report.cases if case.status == "failed"
            ]
            _print(
                {
                    "status": report.status,
                    "budget_output_expectation_report_id": (
                        report.budget_output_expectation_report_id
                    ),
                    "source_driver_impact_report_id": report.source_driver_impact_report_id,
                    "source_driver_impact_review_report_id": (
                        report.source_driver_impact_review_report_id
                    ),
                    "source_blocked_driver_impact_review_report_id": (
                        report.source_blocked_driver_impact_review_report_id
                    ),
                    "case_count": report.case_count,
                    "failed_case_count": report.failed_case_count,
                    "blocked_amount_budget_case_count": (report.blocked_amount_budget_case_count),
                    "range_or_hours_only_case_count": report.range_or_hours_only_case_count,
                    "candidate_range_after_review_case_count": (
                        report.candidate_range_after_review_case_count
                    ),
                    "reviewed_nonblocking_case_count": (report.reviewed_nonblocking_case_count),
                    "blocked_review_case_count": report.blocked_review_case_count,
                    "candidate_exception_lake_labels": (report.candidate_exception_lake_labels),
                    "failed_cases": failed_cases,
                    "failed_checks": failed_checks,
                    "budget_amount_output_authorized": report.budget_amount_output_authorized,
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0
                if report.status == "labor_employment_budget_output_expectations_ready_for_review"
                else 2
            )

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

        if args.command == "audit-matter-linking-preflight":
            report, run_dir = run_matter_linking_preflight(
                input_path=args.input,
                out_dir=args.out_dir,
                generated_at=args.generated_at,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "matter_linking_preflight_report_id": (
                        report.matter_linking_preflight_report_id
                    ),
                    "source_artifact_id": report.source_artifact_id,
                    "overall_link_state": report.overall_link_state,
                    "official_matter_number_status": report.official_matter_number_status,
                    "cluster_count": report.cluster_count,
                    "weak_signal_count": report.weak_signal_count,
                    "strong_negative_signal_count": report.strong_negative_signal_count,
                    "failed_checks": failed_checks,
                    "required_next_gates": report.required_next_gates,
                    "upfront_connector_implemented": report.upfront_connector_implemented,
                    "vendor_api_called": report.vendor_api_called,
                    "external_write_performed": report.external_write_performed,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "matter_opening_authorized": report.matter_opening_authorized,
                    "budget_amount_output_authorized": (report.budget_amount_output_authorized),
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "conflict_conclusion_emitted": report.conflict_conclusion_emitted,
                    "screen_created": report.screen_created,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_matter_linking_preflight":
                return 2
            return 0

        if args.command == "audit-public-data-cache":
            report, run_dir = run_public_data_cache_audit(
                repo_root=args.repo_root,
                cache_root=args.cache_root,
                manifest_path=args.manifest,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status != "passed"]
            _print(
                {
                    "status": report.status,
                    "public_data_cache_audit_report_id": (report.public_data_cache_audit_report_id),
                    "manifest_entry_count": report.manifest_entry_count,
                    "valid_manifest_entry_count": report.valid_manifest_entry_count,
                    "cache_sample_count": report.cache_sample_count,
                    "failed_checks": failed_checks,
                    "unknown_source_ids": report.unknown_source_ids,
                    "failed_hash_source_ids": report.failed_hash_source_ids,
                    "missing_cache_file_source_ids": report.missing_cache_file_source_ids,
                    "blocked_path_refs": report.blocked_path_refs,
                    "direct_runtime_ingestion_allowed": (report.direct_runtime_ingestion_allowed),
                    "public_records_runtime_ingested": (report.public_records_runtime_ingested),
                    "raw_public_payload_committed": report.raw_public_payload_committed,
                    "tracked_public_payload_committed": (report.tracked_public_payload_committed),
                    "connector_implemented": report.connector_implemented,
                    "legal_knowledge_adapter_authorized": (
                        report.legal_knowledge_adapter_authorized
                    ),
                    "synthetic_fixtures_created": report.synthetic_fixtures_created,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_public_data_cache":
                return 2
            return 0

        if args.command == "audit-courtlistener-dataset-strategy":
            report, run_dir = run_courtlistener_dataset_strategy_audit(
                repo_root=args.repo_root,
                out_dir=args.out_dir,
                strategy_config_path=args.strategy_config,
            )
            failed_checks = [check.check_id for check in report.checks if check.status != "passed"]
            _print(
                {
                    "status": report.status,
                    "courtlistener_dataset_strategy_report_id": (
                        report.courtlistener_dataset_strategy_report_id
                    ),
                    "strategy_config_ref": report.strategy_config_ref,
                    "source_id": report.source_id,
                    "primary_practice_area": report.primary_practice_area,
                    "endpoint_count": len(report.endpoint_paths),
                    "starter_matter_family_count": len(report.starter_matter_families),
                    "failed_checks": failed_checks,
                    "offline_fixture_mode": report.offline_fixture_mode,
                    "allow_live_calls": report.allow_live_calls,
                    "pacer_purchase_allowed": report.pacer_purchase_allowed,
                    "recap_fetch_purchase_allowed": report.recap_fetch_purchase_allowed,
                    "rust_runtime_added": report.rust_runtime_added,
                    "rust_replacement_allowed": report.rust_replacement_allowed,
                    "training_pipeline_created": report.training_pipeline_created,
                    "public_records_ingested": report.public_records_ingested,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_courtlistener_dataset_strategy":
                return 2
            return 0

        if args.command == "audit-courtlistener-fixture":
            report, run_dir = run_courtlistener_fixture_audit(
                repo_root=args.repo_root,
                manifest_path=args.manifest,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status != "passed"]
            _print(
                {
                    "status": report.status,
                    "courtlistener_fixture_audit_report_id": (
                        report.courtlistener_fixture_audit_report_id
                    ),
                    "manifest_id": report.manifest_id,
                    "snapshot_count": report.snapshot_count,
                    "document_label_count": report.document_label_count,
                    "conflict_seed_label_count": report.conflict_seed_label_count,
                    "budget_driver_label_count": report.budget_driver_label_count,
                    "timeline_event_label_count": report.timeline_event_label_count,
                    "failed_checks": failed_checks,
                    "public_records_ingested": report.public_records_ingested,
                    "live_calls_performed": report.live_calls_performed,
                    "pacer_purchase_performed": report.pacer_purchase_performed,
                    "recap_fetch_purchase_performed": report.recap_fetch_purchase_performed,
                    "training_pipeline_created": report.training_pipeline_created,
                    "budget_accuracy_claimed": report.budget_accuracy_claimed,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_courtlistener_fixture":
                return 2
            return 0

        if args.command == "audit-labor-employment-budget-facts":
            report, run_dir = run_labor_employment_budget_fact_audit(
                repo_root=args.repo_root,
                manifest_path=args.manifest,
                policy_path=args.fact_policy,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status != "passed"]
            _print(
                {
                    "status": report.status,
                    "labor_employment_budget_fact_audit_report_id": (
                        report.labor_employment_budget_fact_audit_report_id
                    ),
                    "manifest_id": report.manifest_id,
                    "policy_ref": report.policy_ref,
                    "budget_readiness_state": report.budget_readiness_state,
                    "finding_count": report.finding_count,
                    "source_bound_finding_count": report.source_bound_finding_count,
                    "needs_review_finding_count": report.needs_review_finding_count,
                    "unknown_finding_count": report.unknown_finding_count,
                    "critical_gap_count": report.critical_gap_count,
                    "failed_checks": failed_checks,
                    "budget_amount_output_authorized": report.budget_amount_output_authorized,
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "conflict_conclusion_emitted": report.conflict_conclusion_emitted,
                    "matter_opening_authorized": report.matter_opening_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            if report.status == "blocked_labor_employment_budget_fact_audit":
                return 2
            return 0

        if args.command == "validate-labor-employment-budget-fact-gold":
            report, run_dir = run_labor_employment_budget_fact_gold_validation(
                gold_path=args.gold,
                repo_root=args.repo_root,
                policy_path=args.fact_policy,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status != "passed"]
            _print(
                {
                    "status": report.status,
                    "labor_employment_budget_fact_gold_report_id": (
                        report.labor_employment_budget_fact_gold_report_id
                    ),
                    "gold_id": report.gold_id,
                    "case_count": report.case_count,
                    "failed_case_count": report.failed_case_count,
                    "failed_check_count": report.failed_check_count,
                    "failed_checks": failed_checks,
                    "reviewed_gold": report.reviewed_gold,
                    "data_scope": report.data_scope,
                    "budget_amount_output_authorized": (report.budget_amount_output_authorized),
                    "budget_submission_authorized": report.budget_submission_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "passed" else 2

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

        if args.command == "build-budget-human-review-packet":
            report, run_dir = run_budget_human_review_packet(
                out_dir=args.out_dir,
                budget_lifecycle_audit_report_path=args.budget_lifecycle_audit_report,
                budget_revision_report_path=args.budget_revision_report,
                budget_actual_comparison_report_path=args.budget_actual_comparison_report,
                carrier_rejection_review_packet_path=args.carrier_rejection_review_packet,
                carrier_rejection_learning_report_path=args.carrier_rejection_learning_report,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "budget_human_review_packet_id": report.budget_human_review_packet_id,
                    "source_budget_lifecycle_audit_report_id": (
                        report.source_budget_lifecycle_audit_report_id
                    ),
                    "source_budget_lifecycle_audit_status": (
                        report.source_budget_lifecycle_audit_status
                    ),
                    "budget_proposal_id": report.budget_proposal_id,
                    "preflight_packet_id": report.preflight_packet_id,
                    "pending_human_decision_count": report.pending_human_decision_count,
                    "recommendation_count": len(report.recommendations),
                    "red_team_note_count": len(report.red_team_notes),
                    "decision_template_count": len(report.decision_templates),
                    "failed_checks": failed_checks,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "budget_submission_performed": report.budget_submission_performed,
                    "appeal_submission_performed": report.appeal_submission_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        report.carrier_guideline_mutation_performed
                    ),
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "ready_for_human_budget_review" else 2

        if args.command == "record-budget-human-review-outcome":
            report, run_dir = run_budget_human_review_outcome_record(
                budget_human_review_packet_path=args.budget_human_review_packet,
                outcome_path=args.outcome,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "budget_human_review_outcome_report_id": (
                        report.budget_human_review_outcome_report_id
                    ),
                    "budget_human_review_outcome_record_id": (
                        report.budget_human_review_outcome_record_id
                    ),
                    "budget_human_review_packet_id": report.budget_human_review_packet_id,
                    "source_budget_human_review_packet_status": (
                        report.source_budget_human_review_packet_status
                    ),
                    "overall_outcome": report.overall_outcome,
                    "decision_count": report.decision_count,
                    "appeal_decision_count": report.appeal_decision_count,
                    "write_off_decision_count": report.write_off_decision_count,
                    "correction_decision_count": report.correction_decision_count,
                    "route_to_owner_decision_count": report.route_to_owner_decision_count,
                    "no_learning_change_decision_count": (report.no_learning_change_decision_count),
                    "unresolved_followup_count": report.unresolved_followup_count,
                    "candidate_lake_event_labels": report.candidate_lake_event_labels,
                    "failed_checks": failed_checks,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "budget_submission_performed": report.budget_submission_performed,
                    "appeal_submission_performed": report.appeal_submission_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "carrier_guideline_mutation_performed": (
                        report.carrier_guideline_mutation_performed
                    ),
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "budget_human_review_outcome_recorded" else 2

        if args.command == "build-budget-human-review-outcome-owner-adoption":
            report, run_dir = run_budget_human_review_outcome_owner_adoption(
                budget_human_review_outcome_report_path=(args.budget_human_review_outcome_report),
                budget_human_review_outcome_record_path=(args.budget_human_review_outcome_record),
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "owner_adoption_report_id": report.owner_adoption_report_id,
                    "source_budget_human_review_outcome_status": (
                        report.source_budget_human_review_outcome_status
                    ),
                    "source_budget_human_review_outcome_report_id": (
                        report.source_budget_human_review_outcome_report_id
                    ),
                    "source_budget_human_review_outcome_record_id": (
                        report.source_budget_human_review_outcome_record_id
                    ),
                    "packet_count": report.packet_count,
                    "ready_packet_count": report.ready_packet_count,
                    "blocked_packet_count": report.blocked_packet_count,
                    "target_repos": report.target_repos,
                    "candidate_lake_event_labels": report.candidate_lake_event_labels,
                    "required_followup_count": len(report.required_followups),
                    "failed_checks": failed_checks,
                    "github_issue_created": report.github_issue_created,
                    "github_pr_created": report.github_pr_created,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "budget_submission_performed": report.budget_submission_performed,
                    "appeal_submission_performed": report.appeal_submission_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "budget_outcome_owner_adoption_packets_ready" else 2

        if args.command == "build-budget-actual-variance-owner-adoption":
            report, run_dir = run_budget_actual_variance_owner_adoption(
                budget_actual_comparison_report_path=(args.budget_actual_comparison_report),
                budget_actual_variance_ledger_report_path=(
                    args.budget_actual_variance_ledger_report
                ),
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "owner_adoption_report_id": report.owner_adoption_report_id,
                    "source_budget_actual_comparison_status": (
                        report.source_budget_actual_comparison_status
                    ),
                    "source_budget_actual_comparison_report_id": (
                        report.source_budget_actual_comparison_report_id
                    ),
                    "source_budget_actual_variance_ledger_status": (
                        report.source_budget_actual_variance_ledger_status
                    ),
                    "source_budget_actual_variance_ledger_report_id": (
                        report.source_budget_actual_variance_ledger_report_id
                    ),
                    "packet_count": report.packet_count,
                    "ready_packet_count": report.ready_packet_count,
                    "blocked_packet_count": report.blocked_packet_count,
                    "target_repos": report.target_repos,
                    "candidate_lake_event_labels": report.candidate_lake_event_labels,
                    "entry_count": report.entry_count,
                    "variance_review_event_count": report.variance_review_event_count,
                    "missing_actuals_event_count": report.missing_actuals_event_count,
                    "actuals_without_budget_event_count": (
                        report.actuals_without_budget_event_count
                    ),
                    "failed_checks": failed_checks,
                    "github_issue_created": report.github_issue_created,
                    "github_pr_created": report.github_pr_created,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "billing_connector_read_performed": report.billing_connector_read_performed,
                    "billing_connector_write_performed": report.billing_connector_write_performed,
                    "budget_mutation_performed": report.budget_mutation_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return (
                0 if report.status == "budget_actual_variance_owner_adoption_packets_ready" else 2
            )

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

        if args.command == "build-orchestrator-owner-review-request":
            request, run_dir = run_orchestrator_owner_review_request(
                preflight_packet_path=args.preflight_packet,
                confirmation_path=args.confirmation,
                budget_path=args.budget,
                budget_precondition_report_path=args.budget_precondition_report,
                budget_actual_comparison_report_path=args.budget_actual_comparison_report,
                carrier_rejection_decision_ledger_report_path=(
                    args.carrier_rejection_decision_ledger_report
                ),
                carrier_rejection_source_bundle_path=args.carrier_rejection_source_bundle,
                lake_handoff_mode=args.lake_handoff_mode,
                out_dir=args.out_dir,
            )
            pending_pauses = [
                key
                for key, value in request.human_confirmations.items()
                if value.status
                not in {
                    "confirmed",
                    "approved",
                    "human_only",
                    "declined_referred",
                }
            ]
            missing_preconditions = [
                key
                for key, value in request.budget_preconditions.model_dump(mode="json").items()
                if value is not True
            ]
            _print(
                {
                    "status": "orchestrator_owner_review_request_ready",
                    "request_id": request.request_id,
                    "schema_version": request.schema_version,
                    "workflow_label": request.workflow_label,
                    "source_ref_count": len(request.source_refs),
                    "budget_actual_line_count": len(request.budget_actual_lines),
                    "carrier_rejection_notice_count": len(request.carrier_rejection_notices),
                    "pending_human_pause_count": len(pending_pauses),
                    "pending_human_pauses": pending_pauses,
                    "missing_budget_preconditions": missing_preconditions,
                    "lake_handoff_mode": request.lake_handoff_mode,
                    "contains_real_firm_data": request.contains_real_firm_data,
                    "contains_real_client_data": request.contains_real_client_data,
                    "contains_real_matter_data": request.contains_real_matter_data,
                    "contains_privileged_data": request.contains_privileged_data,
                    "run_dir": str(run_dir),
                }
            )
            return 0

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

        if args.command == "plan-remaining-roadmap":
            report, run_dir = run_remaining_roadmap_plan(
                readiness_audit_report_path=args.readiness_audit_report,
                intake_local_closeout_report_path=args.intake_local_closeout_report,
                pr_readiness_decision_report_path=args.pr_readiness_decision_report,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "remaining_roadmap_report_id": report.remaining_roadmap_report_id,
                    "source_readiness_status": report.source_readiness_status,
                    "source_closeout_status": report.source_closeout_status,
                    "source_pr_readiness_decision_status": (
                        report.source_pr_readiness_decision_status
                    ),
                    "source_pr_readiness_decision": report.source_pr_readiness_decision,
                    "item_count": report.item_count,
                    "easy_item_count": report.easy_item_count,
                    "medium_item_count": report.medium_item_count,
                    "large_item_count": report.large_item_count,
                    "critical_item_count": report.critical_item_count,
                    "owner_gated_item_count": report.owner_gated_item_count,
                    "local_or_human_item_count": report.local_or_human_item_count,
                    "next_recommended_item_ids": report.next_recommended_item_ids,
                    "failed_checks": failed_checks,
                    "github_issue_created": report.github_issue_created,
                    "github_pr_created": report.github_pr_created,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "remaining_roadmap_ready_manual_execution_required" else 2

        if args.command == "audit-synthetic-fixture-expansion":
            report, run_dir = run_synthetic_fixture_expansion_audit(
                remaining_roadmap_report_path=args.remaining_roadmap_report,
                manifest_path=args.manifest,
                repo_root=args.repo_root,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "fixture_expansion_report_id": report.fixture_expansion_report_id,
                    "source_remaining_roadmap_status": (report.source_remaining_roadmap_status),
                    "source_remaining_roadmap_item_status": (
                        report.source_remaining_roadmap_item_status
                    ),
                    "manifest_id": report.manifest_id,
                    "required_family_count": report.required_family_count,
                    "holdout_count": report.holdout_count,
                    "family_counts": report.family_counts,
                    "missing_required_families": report.missing_required_families,
                    "failed_checks": failed_checks,
                    "calibration_approved": report.calibration_approved,
                    "fixture_files_mutated_by_audit": report.fixture_files_mutated_by_audit,
                    "github_issue_created": report.github_issue_created,
                    "github_pr_created": report.github_pr_created,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "synthetic_fixture_expansion_ready_for_review" else 2

        if args.command == "audit-synthetic-fixture-depth":
            report, run_dir = run_synthetic_fixture_depth_audit(
                manifest_path=args.manifest,
                repo_root=args.repo_root,
                out_dir=args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "fixture_depth_audit_report_id": report.fixture_depth_audit_report_id,
                    "manifest_id": report.manifest_id,
                    "holdout_count": report.holdout_count,
                    "dimension_count": report.dimension_count,
                    "covered_dimension_count": report.covered_dimension_count,
                    "missing_dimension_count": report.missing_dimension_count,
                    "missing_dimension_ids": report.missing_dimension_ids,
                    "boundary_violation_count": report.boundary_violation_count,
                    "calibration_approved": report.calibration_approved,
                    "fixture_files_mutated_by_audit": report.fixture_files_mutated_by_audit,
                    "github_issue_created": report.github_issue_created,
                    "github_pr_created": report.github_pr_created,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 2 if report.status == "blocked_by_depth_audit_boundary_violation" else 0

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

        if args.command == "audit-owner-issue-draft-quality":
            report, run_dir = run_owner_issue_draft_quality_audit(
                issue_draft_report_path=args.issue_draft_report,
                out_dir=args.out_dir,
            )
            failed_checks = [check.check_id for check in report.checks if check.status == "failed"]
            _print(
                {
                    "status": report.status,
                    "quality_report_id": report.quality_report_id,
                    "source_issue_draft_status": report.source_issue_draft_status,
                    "draft_count": report.draft_count,
                    "ready_item_count": report.ready_item_count,
                    "blocked_item_count": report.blocked_item_count,
                    "failed_item_count": report.failed_item_count,
                    "failed_checks": failed_checks,
                    "manual_creation_required": report.manual_creation_required,
                    "github_issue_created": report.github_issue_created,
                    "github_pr_created": report.github_pr_created,
                    "github_write_performed": report.github_write_performed,
                    "sibling_repo_write_performed": report.sibling_repo_write_performed,
                    "promotion_authorized": report.promotion_authorized,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0 if report.status == "owner_issue_draft_quality_ready_for_manual_review" else 2

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

        if args.command == "record-dad-review-issue":
            report, outbox = record_dad_review_issue_to_outbox(
                issue_path=args.issue,
                repo_root=args.repo_root,
                outbox_path=args.outbox,
                report_out=args.report_out,
            )
            _print(
                {
                    "status": report.status,
                    "dad_review_issue_outbox_report_id": (report.dad_review_issue_outbox_report_id),
                    "source_issue_id": report.source_issue_id,
                    "severity": report.severity,
                    "issue_classes": report.issue_classes,
                    "candidate_exception_labels": report.candidate_exception_labels,
                    "dad_mail_id": report.dad_mail_id,
                    "dad_thread_id": report.dad_thread_id,
                    "dedupe_key": report.dedupe_key,
                    "outbox_ref": str(outbox),
                    "outbox_append_performed": report.outbox_append_performed,
                    "outbox_duplicate_suppressed": report.outbox_duplicate_suppressed,
                    "candidate_only": report.candidate_only,
                    "dad_pickup_required": report.dad_pickup_required,
                    "hidden_chain_of_thought_included": report.hidden_chain_of_thought_included,
                    "raw_private_payload_included": report.raw_private_payload_included,
                    "lake_write_performed": report.lake_write_performed,
                    "sqlite_write_performed": report.sqlite_write_performed,
                    "external_writes_performed": report.external_writes_performed,
                    "silent_learning_performed": report.silent_learning_performed,
                    "report_out": args.report_out,
                }
            )
            return 0
    except (ValueError, OSError, json.JSONDecodeError, ValidationError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    return 2
