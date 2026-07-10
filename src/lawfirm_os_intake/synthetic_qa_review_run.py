from __future__ import annotations

from pathlib import Path
from shutil import copy2

from .budget_actual_variance_ledger import BUDGET_ACTUAL_VARIANCE_LEDGER_REPORT_FILENAME
from .budget_actuals import (
    BUDGET_ACTUAL_COMPARISON_REPORT_FILENAME,
    run_budget_actual_comparison,
)
from .budget_calibration_starter_pack import run_budget_calibration_starter_pack
from .budget_learning_loop import (
    BUDGET_LEARNING_LOOP_REPORT_FILENAME,
    run_budget_learning_loop_report,
)
from .budget_revisions import BUDGET_REVISION_REPORT_FILENAME, run_budget_review_record
from .carrier_rejection_decision_ledger import CARRIER_REJECTION_DECISION_LEDGER_REPORT_FILENAME
from .carrier_rejection_learning import LEARNING_REPORT_FILENAME, run_carrier_rejection_learning
from .carrier_rejection_review import REVIEW_PACKET_FILENAME, run_carrier_rejection_review
from .carrier_rejections import run_carrier_rejection_capture
from .coherence import validate_budget_artifacts
from .confirmation import bind_confirmation_to_packet_evidence
from .labor_employment_blocked_driver_impact_review import (
    LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
    run_labor_employment_blocked_driver_impact_review,
)
from .labor_employment_budget_fact_gold import (
    LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_REPORT_FILENAME,
    run_labor_employment_budget_fact_gold_validation,
)
from .labor_employment_budget_output_expectations import (
    LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME,
    run_labor_employment_budget_output_expectations_audit,
)
from .labor_employment_budget_learning_fixtures import (
    LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME,
    run_labor_employment_budget_learning_fixture_audit,
)
from .labor_employment_budget_outcome_replay_readiness import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_readiness_audit,
)
from .labor_employment_budget_outcome_replay_execution import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_execution,
)
from .labor_employment_budget_outcome_replay_builder_binding import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_builder_binding_audit,
)
from .labor_employment_budget_outcome_replay_confidence_status import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_CONFIDENCE_STATUS_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_confidence_status,
)
from .labor_employment_budget_outcome_replay_input_pack import (
    LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME,
    run_labor_employment_budget_outcome_replay_input_pack_audit,
)
from .labor_employment_budget_qa_gate import (
    LABOR_EMPLOYMENT_BUDGET_QA_GATE_REPORT_FILENAME,
    run_labor_employment_budget_qa_gate,
)
from .labor_employment_driver_impact_review import (
    LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
    run_labor_employment_driver_impact_review,
)
from .labor_employment_executable_coverage import (
    LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME,
    run_labor_employment_executable_coverage_audit,
)
from .labor_employment_executable_driver_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_driver_binding_audit,
)
from .labor_employment_executable_driver_impact import (
    LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME,
    run_labor_employment_executable_driver_impact_audit,
)
from .labor_employment_executable_fact_binding import (
    LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME,
    run_labor_employment_executable_fact_binding_audit,
)
from .labor_employment_executable_fixtures import (
    LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME,
    run_labor_employment_executable_fixture_audit,
)
from .labor_employment_fixture_family_pack import (
    LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_REPORT_FILENAME,
    run_labor_employment_fixture_family_pack_audit,
)
from .labor_employment_qa_matrix import (
    LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME,
    run_labor_employment_qa_matrix,
)
from .models import (
    BudgetLearningLoopReport,
    HumanConfirmation,
    SyntheticQAReviewRunReport,
    SyntheticQAReviewRunStep,
)
from .matter_linking_preflight import (
    MATTER_LINKING_PREFLIGHT_REPORT_FILENAME,
    run_matter_linking_preflight,
)
from .matter_linking_qa_gate import (
    MATTER_LINKING_QA_GATE_REPORT_FILENAME,
    run_matter_linking_qa_gate,
)
from .matter_linking_review_outcomes import (
    MATTER_LINKING_REVIEW_OUTCOME_REPORT_FILENAME,
    run_matter_linking_review_outcome_record,
)
from .reviewed_learning_gate import (
    REVIEWED_LEARNING_GATE_REPORT_FILENAME,
    run_reviewed_learning_gate,
)
from .synthetic_confidence_summary import (
    SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME,
    run_synthetic_confidence_summary,
)
from .synthetic_qa_blocker_report import (
    SYNTHETIC_QA_BLOCKER_REPORT_FILENAME,
    run_synthetic_qa_blocker_report,
)
from .synthetic_qa_review_outcomes import (
    SYNTHETIC_QA_REVIEW_OUTCOME_REPORT_FILENAME,
    run_synthetic_qa_review_outcome_record,
)
from .synthetic_qa_bundle import SYNTHETIC_QA_BUNDLE_REPORT_FILENAME, run_synthetic_qa_bundle
from .poc_qa_triage import POC_QA_TRIAGE_REPORT_FILENAME, run_poc_qa_triage_report
from .public_derived_synthetic_qa_gate import (
    PUBLIC_DERIVED_SYNTHETIC_QA_GATE_REPORT_FILENAME,
    run_public_derived_synthetic_qa_gate,
)
from .public_source_methodology import (
    PUBLIC_SOURCE_METHODOLOGY_REPORT_FILENAME,
    run_public_source_methodology_audit,
)
from .public_synthetic_fixture_conversion import (
    PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_PLAN_FILENAME,
    run_public_synthetic_fixture_conversion_plan,
)
from .public_synthetic_fixture_conversion_review import (
    PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_PACKET_FILENAME,
    run_public_synthetic_fixture_conversion_review,
)
from .ui_review_data_bundle import UI_REVIEW_DATA_BUNDLE_FILENAME, build_ui_review_data_bundle
from .ui_review_manifest import build_ui_review_manifest
from .util import digest_json, load_json, now_iso, write_json
from .workflow import run_budget, run_preflight


SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME = "synthetic_qa_review_run_report.json"

DEMO_INPUT_REF = "examples/synthetic/inbound/carrier-assignment-medmal.json"
DEMO_PROFILE_REF = "context/synthetic-profiles/insurance-defense.yaml"
DEMO_CONFIRMATION_REF = (
    "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
)
DEMO_BUDGET_REVIEW_REF = "examples/synthetic/budget-review/medmal-human-budget-review-change.json"
DEMO_ACTUALS_REF = "examples/synthetic/actuals/medmal-phase-code-actuals.json"
DEMO_CARRIER_REJECTION_REF = (
    "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json"
)
FIXTURE_DEPTH_MANIFEST_REF = "examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json"
LE_PACK_REF = "examples/synthetic/labor-employment/labor-employment-budget-fixture-family-pack.json"
LE_FACT_NEEDS_REF = "config/labor-employment-budget-fact-needs.yaml"
LE_EXECUTABLE_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json"
)
LE_BINDING_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json"
)
LE_DRIVER_IMPACT_REVIEW_REF = "examples/synthetic/gold/labor-employment-driver-impact-review.json"
LE_BUDGET_FACT_GOLD_REF = "examples/synthetic/gold/labor-employment-budget-fact-gold.json"
LE_BUDGET_LEARNING_FIXTURES_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-learning-fixtures.json"
)
LE_BUDGET_OUTCOME_REPLAY_SEEDS_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-seeds.json"
)
LE_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REF = (
    "examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json"
)
UPFRONT_RESOLVED_FOLLOWUP_REF = (
    "examples/synthetic/upfront/upfront-like-intake-output.resolved-followup.example.json"
)
UPFRONT_WEAK_SINGLE_CANDIDATE_REF = (
    "examples/synthetic/upfront/upfront-like-intake-output.weak-single-candidate.example.json"
)
UPFRONT_MATTER_LINKING_CONFIRM_SPLIT_REF = (
    "examples/synthetic/upfront/matter-linking-review-confirm-split.outcome.json"
)


def run_synthetic_qa_review_run(
    *,
    run_root: str | Path,
    repo_root: str | Path = ".",
    fixture_boundary_report_path: str | Path | None = None,
    fixture_manifest_report_path: str | Path | None = None,
    validation_suite_evidence_report_path: str | Path | None = None,
    generated_at: str | None = None,
) -> tuple[SyntheticQAReviewRunReport, Path]:
    root = Path(repo_root).resolve()
    run_dir = Path(run_root).resolve()
    quality_dir = run_dir / "quality"
    budget_dir = run_dir / "budget"
    run_dir.mkdir(parents=True, exist_ok=True)
    quality_dir.mkdir(parents=True, exist_ok=True)
    budget_dir.mkdir(parents=True, exist_ok=True)

    steps: list[SyntheticQAReviewRunStep] = []

    budget_coherence_ref = _build_budget_coherence(
        repo_root=root,
        run_root=run_dir,
        budget_dir=budget_dir,
    )
    steps.append(
        _step(
            "budget_coherence",
            "Budget Coherence",
            "passed",
            budget_coherence_ref,
            load_json(budget_coherence_ref).get("status") == "passed",
            "Budget proposal coherence is generated from the synthetic demo budget.",
        )
    )

    matter_linking, matter_linking_dir = run_matter_linking_preflight(
        input_path=root / UPFRONT_RESOLVED_FOLLOWUP_REF,
        out_dir=quality_dir / "matter-linking-preflight",
        generated_at=generated_at,
    )
    matter_linking_ref = matter_linking_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME
    steps.append(
        _step(
            "matter_linking_preflight",
            "Matter-Linking Preflight",
            matter_linking.status,
            matter_linking_ref,
            matter_linking.status == "matter_linking_preflight_resolved_candidate_requires_review",
            "Resolved Upfront-like document clusters remain human-gated and no-write.",
        )
    )

    matter_linking_review_outcome, matter_linking_review_outcome_dir = (
        run_matter_linking_review_outcome_record(
            matter_linking_preflight_report_path=matter_linking_ref,
            outcome_path=root / UPFRONT_MATTER_LINKING_CONFIRM_SPLIT_REF,
            out_dir=quality_dir / "matter-linking-review-outcome",
            generated_at=generated_at,
        )
    )
    matter_linking_review_outcome_ref = (
        matter_linking_review_outcome_dir / MATTER_LINKING_REVIEW_OUTCOME_REPORT_FILENAME
    )
    steps.append(
        _step(
            "matter_linking_review_outcome",
            "Matter-Linking Review Outcome",
            matter_linking_review_outcome.status,
            matter_linking_review_outcome_ref,
            matter_linking_review_outcome.status == "matter_linking_review_outcome_recorded"
            and matter_linking_review_outcome.budget_amount_output_authorized is False
            and matter_linking_review_outcome.matter_opening_authorized is False,
            "Human split confirmation is recorded append-only without authorizing budgets, matters, Lake writes, or learning.",
        )
    )

    weak_matter_linking, weak_matter_linking_dir = run_matter_linking_preflight(
        input_path=root / UPFRONT_WEAK_SINGLE_CANDIDATE_REF,
        out_dir=quality_dir / "matter-linking-weak-only-holdout",
        generated_at=generated_at,
    )
    weak_matter_linking_ref = weak_matter_linking_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME
    steps.append(
        _step(
            "matter_linking_weak_only_holdout",
            "Matter-Linking Weak-Only Holdout",
            weak_matter_linking.status,
            weak_matter_linking_ref,
            weak_matter_linking.status == "blocked_matter_linking_preflight"
            and weak_matter_linking.weak_only_candidate_count > 0
            and weak_matter_linking.negative_split_evidence_required is False,
            "Weak sender/carrier/reference-only candidates must block rather than merge or budget.",
        )
    )

    matter_linking_qa_gate, matter_linking_qa_gate_dir = run_matter_linking_qa_gate(
        repo_root=root,
        out_dir=quality_dir / "matter-linking-qa-gate",
        generated_at=generated_at,
    )
    matter_linking_qa_gate_ref = matter_linking_qa_gate_dir / MATTER_LINKING_QA_GATE_REPORT_FILENAME
    steps.append(
        _step(
            "matter_linking_qa_gate",
            "Matter-Linking QA Gate",
            matter_linking_qa_gate.status,
            matter_linking_qa_gate_ref,
            matter_linking_qa_gate.status == "matter_linking_qa_gate_ready_for_review",
            "Aggregate Upfront-like fixture gate covers ambiguous, resolved, weak-only, and conflicting-identifier matter-linking states.",
        )
    )

    starter_pack, starter_dir = run_budget_calibration_starter_pack(
        corpus_root=root / "examples/synthetic",
        repo_root=root,
        out_dir=quality_dir / "calibration-starter",
        reviewed_at=generated_at,
    )
    steps.append(
        _step(
            "budget_calibration_starter_pack",
            "Budget Calibration Starter Pack",
            starter_pack.status,
            starter_dir / "budget_calibration_starter_pack_report.json",
            starter_pack.status == "starter_pack_ready_for_manual_fixture_update_review",
            "Calibration remains review-only and does not apply learning.",
        )
    )

    le_matrix, le_matrix_dir = run_labor_employment_qa_matrix(
        repo_root=root,
        out_dir=quality_dir / "le-qa-matrix",
    )
    steps.append(
        _step(
            "labor_employment_qa_matrix",
            "L&E QA Matrix",
            le_matrix.status,
            le_matrix_dir / LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME,
            le_matrix.status == "labor_employment_qa_matrix_ready_for_review",
            "Critical blockers and range-only review posture are visible.",
        )
    )

    family_pack, family_pack_dir = run_labor_employment_fixture_family_pack_audit(
        pack_path=root / LE_PACK_REF,
        fact_needs_path=root / LE_FACT_NEEDS_REF,
        out_dir=quality_dir / "le-fixture-family-pack",
    )
    steps.append(
        _step(
            "labor_employment_fixture_family_pack",
            "L&E Fixture Family Pack",
            family_pack.status,
            family_pack_dir / LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_REPORT_FILENAME,
            family_pack.status == "labor_employment_fixture_family_pack_ready_for_review",
            "Synthetic fixture family and variant coverage is reviewed.",
        )
    )

    executable_report, executable_dir = run_labor_employment_executable_fixture_audit(
        manifest_path=root / LE_EXECUTABLE_MANIFEST_REF,
        repo_root=root,
        out_dir=quality_dir / "le-executable-fixtures",
    )
    executable_report_ref = (
        executable_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME
    )
    steps.append(
        _step(
            "labor_employment_executable_fixtures",
            "L&E Executable Fixtures",
            executable_report.status,
            executable_report_ref,
            executable_report.status == "labor_employment_executable_fixtures_ready_for_review",
            "Selected source bundles execute through deterministic preflight.",
        )
    )

    coverage, coverage_dir = run_labor_employment_executable_coverage_audit(
        manifest_path=root / LE_EXECUTABLE_MANIFEST_REF,
        repo_root=root,
        out_dir=quality_dir / "le-executable-coverage",
    )
    steps.append(
        _step(
            "labor_employment_executable_coverage",
            "L&E Executable Coverage",
            coverage.status,
            coverage_dir / LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME,
            coverage.status == "labor_employment_executable_coverage_ready_for_review",
            "Executable coverage gaps stay visible for later fixture expansion.",
        )
    )

    fact_binding, fact_binding_dir = run_labor_employment_executable_fact_binding_audit(
        binding_manifest_path=root / LE_BINDING_MANIFEST_REF,
        executable_fixture_report_path=executable_report_ref,
        repo_root=root,
        out_dir=quality_dir / "le-executable-fact-binding",
    )
    fact_binding_ref = fact_binding_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME
    steps.append(
        _step(
            "labor_employment_executable_fact_binding",
            "L&E Executable Fact Binding",
            fact_binding.status,
            fact_binding_ref,
            fact_binding.status
            == "labor_employment_executable_budget_fact_bindings_ready_for_review",
            "Executable facts bind to expected L&E budget-fact gaps.",
        )
    )

    driver_binding, driver_binding_dir = run_labor_employment_executable_driver_binding_audit(
        executable_fixture_report_path=executable_report_ref,
        executable_fact_binding_report_path=fact_binding_ref,
        repo_root=root,
        out_dir=quality_dir / "le-executable-driver-binding",
    )
    driver_binding_ref = (
        driver_binding_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_BINDING_REPORT_FILENAME
    )
    steps.append(
        _step(
            "labor_employment_executable_driver_binding",
            "L&E Executable Driver Binding",
            driver_binding.status,
            driver_binding_ref,
            driver_binding.status == "labor_employment_executable_driver_bindings_ready_for_review",
            "Fact gaps map to budget-driver dimensions.",
        )
    )

    driver_impact, driver_impact_dir = run_labor_employment_executable_driver_impact_audit(
        executable_driver_binding_report_path=driver_binding_ref,
        out_dir=quality_dir / "le-executable-driver-impact",
    )
    driver_impact_ref = (
        driver_impact_dir / LABOR_EMPLOYMENT_EXECUTABLE_DRIVER_IMPACT_REPORT_FILENAME
    )
    steps.append(
        _step(
            "labor_employment_executable_driver_impact",
            "L&E Executable Driver Impact",
            driver_impact.status,
            driver_impact_ref,
            driver_impact.status == "labor_employment_executable_driver_impacts_ready_for_review",
            "Driver bindings declare blockers, ranges, scenario forks, and rate reviews.",
        )
    )

    driver_review, driver_review_dir = run_labor_employment_driver_impact_review(
        review_spec_path=root / LE_DRIVER_IMPACT_REVIEW_REF,
        driver_impact_report_path=driver_impact_ref,
        out_dir=quality_dir / "le-driver-impact-review",
    )
    steps.append(
        _step(
            "labor_employment_driver_impact_review",
            "L&E Driver Impact Review",
            driver_review.status,
            driver_review_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
            driver_review.status
            == "labor_employment_driver_impact_review_ready_for_budget_gate_replay",
            "Nonblocking driver impacts are reviewed for budget-gate replay.",
        )
    )

    blocked_review, blocked_review_dir = run_labor_employment_blocked_driver_impact_review(
        fact_binding_report_path=fact_binding_ref,
        driver_binding_report_path=driver_binding_ref,
        driver_impact_report_path=driver_impact_ref,
        out_dir=quality_dir / "le-blocked-driver-impact-review",
    )
    steps.append(
        _step(
            "labor_employment_blocked_driver_impact_review",
            "L&E Blocked Driver Impact Review",
            blocked_review.status,
            blocked_review_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
            blocked_review.status == "labor_employment_blocked_driver_impacts_ready_for_review",
            "Blocked amount-budget cases explain blocker facts and follow-up actions.",
        )
    )

    output_expectations, output_expectations_dir = (
        run_labor_employment_budget_output_expectations_audit(
            driver_impact_report_path=driver_impact_ref,
            driver_impact_review_report_path=(
                driver_review_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
            ),
            blocked_driver_impact_review_report_path=(
                blocked_review_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
            ),
            out_dir=quality_dir / "le-budget-output-expectations",
        )
    )
    output_expectations_ref = (
        output_expectations_dir / LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME
    )
    steps.append(
        _step(
            "labor_employment_budget_output_expectations",
            "L&E Budget Output Expectations",
            output_expectations.status,
            output_expectations_ref,
            output_expectations.status
            == "labor_employment_budget_output_expectations_ready_for_review",
            "Every executable L&E case has one allowed budget-output state and next gate.",
        )
    )

    budget_qa_gate, budget_qa_gate_dir = run_labor_employment_budget_qa_gate(
        budget_output_expectations_report_path=output_expectations_ref,
        blocked_driver_impact_review_report_path=(
            blocked_review_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME
        ),
        executable_coverage_report_path=(
            coverage_dir / LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME
        ),
        out_dir=quality_dir / "le-budget-qa-gate",
        generated_at=generated_at,
    )
    budget_qa_gate_ref = budget_qa_gate_dir / LABOR_EMPLOYMENT_BUDGET_QA_GATE_REPORT_FILENAME
    steps.append(
        _step(
            "labor_employment_budget_qa_gate",
            "L&E Budget QA Gate",
            budget_qa_gate.status,
            budget_qa_gate_ref,
            budget_qa_gate.status == "labor_employment_budget_qa_gate_ready_for_review",
            "L&E budget-output states are aggregated into a candidate-only QA gate.",
        )
    )

    budget_learning_fixtures, budget_learning_fixtures_dir = (
        run_labor_employment_budget_learning_fixture_audit(
            manifest_path=root / LE_BUDGET_LEARNING_FIXTURES_REF,
            budget_qa_gate_report_path=budget_qa_gate_ref,
            out_dir=quality_dir / "le-budget-learning-fixtures",
            generated_at=generated_at,
        )
    )
    budget_learning_fixtures_ref = (
        budget_learning_fixtures_dir / LABOR_EMPLOYMENT_BUDGET_LEARNING_FIXTURE_REPORT_FILENAME
    )
    steps.append(
        _step(
            "labor_employment_budget_learning_fixtures",
            "L&E Budget Learning Fixtures",
            budget_learning_fixtures.status,
            budget_learning_fixtures_ref,
            budget_learning_fixtures.status
            == "labor_employment_budget_learning_fixtures_ready_for_review",
            (
                "L&E actuals, carrier rejection, appeal, reviewed-learning, and "
                "blocked-budget guard fixture coverage is mapped for QA."
            ),
        )
    )

    outcome_replay, outcome_replay_dir = run_labor_employment_budget_outcome_replay_readiness_audit(
        seed_manifest_path=root / LE_BUDGET_OUTCOME_REPLAY_SEEDS_REF,
        learning_fixture_report_path=budget_learning_fixtures_ref,
        repo_root=root,
        out_dir=quality_dir / "le-budget-outcome-replay-readiness",
        generated_at=generated_at,
    )
    outcome_replay_ref = (
        outcome_replay_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_READINESS_REPORT_FILENAME
    )
    steps.append(
        _step(
            "labor_employment_budget_outcome_replay_readiness",
            "L&E Budget Outcome Replay Readiness",
            outcome_replay.status,
            outcome_replay_ref,
            outcome_replay.status == "labor_employment_budget_outcome_replay_ready_for_review",
            (
                "L&E actuals, carrier rejection, appeal, reviewed-learning, and blocked "
                "guard fixture intents have concrete synthetic replay seeds."
            ),
        )
    )

    outcome_execution, outcome_execution_dir = run_labor_employment_budget_outcome_replay_execution(
        seed_manifest_path=root / LE_BUDGET_OUTCOME_REPLAY_SEEDS_REF,
        readiness_report_path=outcome_replay_ref,
        out_dir=quality_dir / "le-budget-outcome-replay-execution",
        generated_at=generated_at,
    )
    outcome_execution_ref = (
        outcome_execution_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_EXECUTION_REPORT_FILENAME
    )
    steps.append(
        _step(
            "labor_employment_budget_outcome_replay_execution",
            "L&E Budget Outcome Replay Execution",
            outcome_execution.status,
            outcome_execution_ref,
            outcome_execution.status
            == "labor_employment_budget_outcome_replay_execution_ready_for_review",
            (
                "L&E outcome replay seeds are materialized as safe candidate artifact "
                "slots without runtime carrier, billing, Lake, SQLite, or learning writes."
            ),
        )
    )

    outcome_builder_binding, outcome_builder_binding_dir = (
        run_labor_employment_budget_outcome_replay_builder_binding_audit(
            execution_report_path=outcome_execution_ref,
            out_dir=quality_dir / "le-budget-outcome-replay-builder-binding",
            generated_at=generated_at,
        )
    )
    outcome_builder_binding_ref = (
        outcome_builder_binding_dir
        / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_BUILDER_BINDING_REPORT_FILENAME
    )
    steps.append(
        _step(
            "labor_employment_budget_outcome_replay_builder_binding",
            "L&E Budget Outcome Replay Builder Binding",
            outcome_builder_binding.status,
            outcome_builder_binding_ref,
            outcome_builder_binding.status
            == "labor_employment_budget_replay_builder_binding_ready_for_review",
            (
                "L&E outcome replay slots are mapped to deterministic local builders "
                "with explicit synthetic input gaps and no runtime artifact creation."
            ),
        )
    )

    outcome_input_pack, outcome_input_pack_dir = (
        run_labor_employment_budget_outcome_replay_input_pack_audit(
            builder_binding_report_path=outcome_builder_binding_ref,
            input_pack_manifest_path=root / LE_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REF,
            repo_root=root,
            out_dir=quality_dir / "le-budget-outcome-replay-input-pack",
            generated_at=generated_at,
        )
    )
    outcome_input_pack_ref = (
        outcome_input_pack_dir / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_INPUT_PACK_REPORT_FILENAME
    )
    outcome_confidence, outcome_confidence_dir = (
        run_labor_employment_budget_outcome_replay_confidence_status(
            readiness_report_path=outcome_replay_ref,
            execution_report_path=outcome_execution_ref,
            builder_binding_report_path=outcome_builder_binding_ref,
            input_pack_report_path=outcome_input_pack_ref,
            out_dir=quality_dir / "le-budget-outcome-replay-confidence-status",
            generated_at=generated_at,
        )
    )
    outcome_confidence_ref = (
        outcome_confidence_dir
        / LABOR_EMPLOYMENT_BUDGET_OUTCOME_REPLAY_CONFIDENCE_STATUS_REPORT_FILENAME
    )
    steps.append(
        _step(
            "labor_employment_budget_outcome_replay_confidence_status",
            "L&E Budget Outcome Replay Confidence Status",
            outcome_confidence.status,
            outcome_confidence_ref,
            outcome_confidence.status
            in {
                "labor_employment_budget_outcome_replay_confidence_ready_for_review",
                "labor_employment_budget_outcome_replay_confidence_pending_inputs",
            },
            (
                "L&E replay confidence aggregates readiness, execution, builder binding, "
                "and input-pack gaps without authorizing calibration, learning, Lake writes, "
                "or budget submission."
            ),
        )
    )
    _ = outcome_input_pack

    gold, gold_dir = run_labor_employment_budget_fact_gold_validation(
        gold_path=root / LE_BUDGET_FACT_GOLD_REF,
        repo_root=root,
        out_dir=quality_dir / "le-budget-fact-gold",
    )
    steps.append(
        _step(
            "labor_employment_budget_fact_gold",
            "L&E Budget Fact Gold",
            gold.status,
            gold_dir / LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_REPORT_FILENAME,
            gold.status == "passed",
            "Reviewed synthetic gold validates L&E budget-fact audit outputs.",
        )
    )

    budget_learning_loop, budget_learning_loop_dir = _build_budget_learning_loop(
        repo_root=root,
        budget_dir=budget_dir,
        quality_dir=quality_dir,
        generated_at=generated_at,
    )
    budget_learning_loop_ref = budget_learning_loop_dir / BUDGET_LEARNING_LOOP_REPORT_FILENAME
    steps.append(
        _step(
            "budget_learning_loop",
            "Budget Learning Loop",
            budget_learning_loop.status,
            budget_learning_loop_ref,
            _budget_learning_loop_qa_passed(budget_learning_loop),
            (
                "Budget actuals, carrier rejection, appeal outcome, and reviewed-learning "
                "candidates are summarized for QA; the expected proof-gate block is a "
                "passing fail-closed outcome without silent learning."
            ),
        )
    )

    public_methodology, public_methodology_dir = run_public_source_methodology_audit(
        repo_root=root,
        out_dir=quality_dir / "public-source-methodology",
    )
    public_methodology_ref = public_methodology_dir / PUBLIC_SOURCE_METHODOLOGY_REPORT_FILENAME
    public_conversion, public_conversion_dir = run_public_synthetic_fixture_conversion_plan(
        methodology_report_path=public_methodology_ref,
        out_dir=quality_dir / "public-synthetic-conversion",
    )
    public_conversion_ref = (
        public_conversion_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_PLAN_FILENAME
    )
    public_conversion_review, public_conversion_review_dir = (
        run_public_synthetic_fixture_conversion_review(
            conversion_plan_path=public_conversion_ref,
            out_dir=quality_dir / "public-synthetic-conversion-review",
        )
    )
    public_conversion_review_ref = (
        public_conversion_review_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_PACKET_FILENAME
    )
    public_derived_gate, public_derived_gate_dir = run_public_derived_synthetic_qa_gate(
        methodology_report_path=public_methodology_ref,
        conversion_plan_path=public_conversion_ref,
        conversion_review_packet_path=public_conversion_review_ref,
        out_dir=quality_dir / "public-derived-synthetic-qa-gate",
    )
    public_derived_gate_ref = (
        public_derived_gate_dir / PUBLIC_DERIVED_SYNTHETIC_QA_GATE_REPORT_FILENAME
    )
    steps.append(
        _step(
            "public_derived_synthetic_qa_gate",
            "Public-Derived Synthetic QA Gate",
            public_derived_gate.status,
            public_derived_gate_ref,
            public_methodology.status == "ready_for_human_public_source_methodology_review"
            and public_conversion.status == "ready_for_human_conversion_review"
            and public_conversion_review.status == "ready_for_human_conversion_review"
            and public_derived_gate.status == "public_derived_synthetic_qa_ready_for_review",
            (
                "Public-source methodology, conversion planning, conversion review, "
                "and cache-custody boundary checks are bound before public-derived "
                "synthetic fixtures are trusted for QA."
            ),
        )
    )

    for source_path in [
        starter_dir / "budget-calibration-readiness" / "budget_calibration_readiness_report.json",
        matter_linking_ref,
        matter_linking_review_outcome_ref,
        matter_linking_qa_gate_ref,
        le_matrix_dir / LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME,
        family_pack_dir / LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_REPORT_FILENAME,
        executable_report_ref,
        coverage_dir / LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME,
        fact_binding_ref,
        driver_binding_ref,
        driver_impact_ref,
        driver_review_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
        blocked_review_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
        output_expectations_ref,
        budget_qa_gate_ref,
        budget_learning_fixtures_ref,
        outcome_replay_ref,
        outcome_execution_ref,
        outcome_builder_binding_ref,
        outcome_confidence_ref,
        gold_dir / LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_REPORT_FILENAME,
        budget_learning_loop_ref,
        public_derived_gate_ref,
    ]:
        _stage_for_bundle(source_path, quality_dir)

    staged_fixture_boundary_ref: Path | None = None
    if fixture_boundary_report_path is not None:
        staged_fixture_boundary_ref = _stage_for_bundle(
            Path(fixture_boundary_report_path),
            quality_dir,
        )
        fixture_boundary_payload = load_json(staged_fixture_boundary_ref)
        steps.append(
            _step(
                "rust_fixture_boundary",
                "Rust Fixture Boundary",
                str(fixture_boundary_payload.get("status") or "missing"),
                staged_fixture_boundary_ref,
                fixture_boundary_payload.get("status") == "passed",
                (
                    "Prebuilt Rust fixture-boundary evidence validates local JSON flags "
                    "without making the synthetic QA run compile or execute Rust."
                ),
            )
        )

    staged_fixture_manifest_ref: Path | None = None
    if fixture_manifest_report_path is not None:
        staged_fixture_manifest_ref = _stage_for_bundle(
            Path(fixture_manifest_report_path),
            quality_dir,
        )
        fixture_manifest_payload = load_json(staged_fixture_manifest_ref)
        steps.append(
            _step(
                "rust_fixture_manifest",
                "Rust Fixture Manifest",
                str(fixture_manifest_payload.get("status") or "missing"),
                staged_fixture_manifest_ref,
                fixture_manifest_payload.get("status") == "passed",
                (
                    "Prebuilt Rust fixture-manifest evidence hash-binds local JSON "
                    "fixtures without making the synthetic QA run compile or execute Rust."
                ),
            )
        )

    staged_validation_suite_evidence_ref: Path | None = None
    if validation_suite_evidence_report_path is not None:
        staged_validation_suite_evidence_ref = _stage_for_bundle_as(
            Path(validation_suite_evidence_report_path),
            quality_dir,
            "validation_suite_evidence_report.json",
        )
        validation_suite_evidence_payload = load_json(staged_validation_suite_evidence_ref)
        steps.append(
            _step(
                "validation_suite_evidence",
                "Validation Suite Evidence",
                str(validation_suite_evidence_payload.get("status") or "missing"),
                staged_validation_suite_evidence_ref,
                validation_suite_evidence_payload.get("status") == "validation_suite_passed",
                (
                    "Prebuilt wrapper validation evidence is staged from "
                    "scripts/run_validation_suite.py output; the synthetic QA run "
                    "does not execute full pytest or smoke checks itself."
                ),
            )
        )

    bundle, _bundle_dir, ui_manifest = run_synthetic_qa_bundle(
        run_root=run_dir,
        out_dir=quality_dir,
        budget_coherence_report_path=budget_coherence_ref,
        fixture_depth_manifest_path=root / FIXTURE_DEPTH_MANIFEST_REF,
        repo_root=root,
        ui_manifest_out=run_dir / "ui_review_manifest.json",
        generated_at=generated_at,
    )
    synthetic_qa_bundle_ref = quality_dir / SYNTHETIC_QA_BUNDLE_REPORT_FILENAME
    ui_manifest_ref = run_dir / "ui_review_manifest.json"
    ui_data_bundle_ref = run_dir / UI_REVIEW_DATA_BUNDLE_FILENAME
    steps.append(
        _step(
            "synthetic_qa_bundle",
            "Synthetic QA Bundle",
            bundle.status,
            synthetic_qa_bundle_ref,
            bundle.status in {"pending_review", "passed"},
            "Synthetic QA artifacts are bundled for local review.",
        )
    )
    steps.append(
        _step(
            "ui_review_manifest",
            "UI Review Manifest",
            ui_manifest["overallStatus"] if ui_manifest else "missing",
            ui_manifest_ref,
            ui_manifest is not None and ui_manifest["overallStatus"] != "failed",
            "Read-only frontend manifest is generated from local artifacts.",
        )
    )
    report = _build_review_run_report(
        run_dir=run_dir,
        quality_dir=quality_dir,
        steps=steps,
        synthetic_qa_bundle_ref=synthetic_qa_bundle_ref,
        ui_manifest_ref=ui_manifest_ref,
        ui_data_bundle_ref=ui_data_bundle_ref,
        generated_at=generated_at,
    )
    write_json(run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME, report.model_dump(mode="json"))

    confidence_summary, confidence_summary_dir = run_synthetic_confidence_summary(
        synthetic_qa_review_run_report_path=run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
        synthetic_qa_bundle_report_path=synthetic_qa_bundle_ref,
        ui_manifest_path=ui_manifest_ref,
        ui_review_data_bundle_path=ui_data_bundle_ref,
        out_dir=quality_dir / "synthetic-confidence-summary",
        generated_at=generated_at,
    )
    confidence_summary_ref = confidence_summary_dir / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME
    _stage_for_bundle(confidence_summary_ref, quality_dir)
    steps.append(
        _step(
            "synthetic_confidence_summary",
            "Synthetic Confidence Summary",
            confidence_summary.status,
            confidence_summary_ref,
            confidence_summary.status == "synthetic_confidence_summary_ready_for_review",
            "Aggregate QA/UI readiness banner is generated without production authority.",
        )
    )
    build_ui_review_manifest(
        run_root=run_dir,
        out_path=ui_manifest_ref,
        generated_at=generated_at,
    )
    build_ui_review_data_bundle(
        run_root=run_dir,
        out_path=ui_data_bundle_ref,
        generated_at=generated_at,
    )
    ui_data_bundle = load_json(ui_data_bundle_ref) if ui_data_bundle_ref.is_file() else {}
    ui_data_bundle_step_index = len(steps)
    steps.append(
        _step(
            "ui_review_data_bundle",
            "UI Review Data Bundle",
            str(ui_data_bundle.get("status") or "missing"),
            ui_data_bundle_ref,
            ui_data_bundle.get("status") == "ready_for_review",
            "UI-renderable detail reports are hash-bound for local review.",
        )
    )
    report = _build_review_run_report(
        run_dir=run_dir,
        quality_dir=quality_dir,
        steps=steps,
        synthetic_qa_bundle_ref=synthetic_qa_bundle_ref,
        ui_manifest_ref=ui_manifest_ref,
        ui_data_bundle_ref=ui_data_bundle_ref,
        generated_at=generated_at,
    )
    write_json(run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME, report.model_dump(mode="json"))
    confidence_summary, confidence_summary_dir = run_synthetic_confidence_summary(
        synthetic_qa_review_run_report_path=run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
        synthetic_qa_bundle_report_path=synthetic_qa_bundle_ref,
        ui_manifest_path=ui_manifest_ref,
        ui_review_data_bundle_path=ui_data_bundle_ref,
        out_dir=quality_dir / "synthetic-confidence-summary",
        generated_at=generated_at,
    )
    _stage_for_bundle(
        confidence_summary_dir / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME,
        quality_dir,
    )
    build_ui_review_manifest(
        run_root=run_dir,
        out_path=ui_manifest_ref,
        generated_at=generated_at,
    )
    _blocker_report, blocker_report_dir = run_synthetic_qa_blocker_report(
        ui_manifest_path=ui_manifest_ref,
        synthetic_confidence_summary_path=(
            quality_dir / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME
        ),
        synthetic_qa_review_run_report_path=run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
        out_dir=quality_dir / "synthetic-qa-blocker-report",
        generated_at=generated_at,
    )
    _stage_for_bundle(
        blocker_report_dir / SYNTHETIC_QA_BLOCKER_REPORT_FILENAME,
        quality_dir,
    )
    synthetic_qa_outcome_path = write_json(
        quality_dir / "synthetic_qa_review_outcome_record.seed.json",
        _synthetic_qa_review_outcome_payload(
            blocker_report=load_json(quality_dir / SYNTHETIC_QA_BLOCKER_REPORT_FILENAME),
            generated_at=generated_at,
        ),
    )
    _synthetic_qa_review_outcome, synthetic_qa_review_outcome_dir = (
        run_synthetic_qa_review_outcome_record(
            synthetic_qa_blocker_report_path=quality_dir / SYNTHETIC_QA_BLOCKER_REPORT_FILENAME,
            outcome_path=synthetic_qa_outcome_path,
            out_dir=quality_dir / "synthetic-qa-review-outcome",
            generated_at=generated_at,
        )
    )
    _stage_for_bundle(
        synthetic_qa_review_outcome_dir / SYNTHETIC_QA_REVIEW_OUTCOME_REPORT_FILENAME,
        quality_dir,
    )
    build_ui_review_manifest(
        run_root=run_dir,
        out_path=ui_manifest_ref,
        generated_at=generated_at,
    )
    _blocker_report, blocker_report_dir = run_synthetic_qa_blocker_report(
        ui_manifest_path=ui_manifest_ref,
        synthetic_confidence_summary_path=(
            quality_dir / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME
        ),
        synthetic_qa_review_run_report_path=run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
        out_dir=quality_dir / "synthetic-qa-blocker-report",
        generated_at=generated_at,
    )
    _stage_for_bundle(
        blocker_report_dir / SYNTHETIC_QA_BLOCKER_REPORT_FILENAME,
        quality_dir,
    )
    build_ui_review_manifest(
        run_root=run_dir,
        out_path=ui_manifest_ref,
        generated_at=generated_at,
    )
    build_ui_review_data_bundle(
        run_root=run_dir,
        out_path=ui_data_bundle_ref,
        generated_at=generated_at,
    )
    final_confidence_summary, final_confidence_summary_dir = run_synthetic_confidence_summary(
        synthetic_qa_review_run_report_path=run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
        synthetic_qa_bundle_report_path=synthetic_qa_bundle_ref,
        ui_manifest_path=ui_manifest_ref,
        ui_review_data_bundle_path=ui_data_bundle_ref,
        out_dir=quality_dir / "synthetic-confidence-summary",
        generated_at=generated_at,
    )
    _stage_for_bundle(
        final_confidence_summary_dir / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME,
        quality_dir,
    )
    steps[ui_data_bundle_step_index] = _step(
        "ui_review_data_bundle",
        "UI Review Data Bundle",
        "ready_for_review",
        ui_data_bundle_ref,
        final_confidence_summary.status == "synthetic_confidence_summary_ready_for_review",
        "UI-renderable detail reports are hash-bound for local review.",
    )
    report = _build_review_run_report(
        run_dir=run_dir,
        quality_dir=quality_dir,
        steps=steps,
        synthetic_qa_bundle_ref=synthetic_qa_bundle_ref,
        ui_manifest_ref=ui_manifest_ref,
        ui_data_bundle_ref=ui_data_bundle_ref,
        generated_at=generated_at,
    )
    write_json(run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME, report.model_dump(mode="json"))
    build_ui_review_manifest(
        run_root=run_dir,
        out_path=ui_manifest_ref,
        generated_at=generated_at,
    )
    if staged_validation_suite_evidence_ref is not None:
        _poc_qa_triage, poc_qa_triage_dir = run_poc_qa_triage_report(
            ui_manifest_path=ui_manifest_ref,
            synthetic_confidence_summary_path=(
                quality_dir / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME
            ),
            synthetic_qa_review_run_path=run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
            synthetic_qa_blocker_report_path=quality_dir / SYNTHETIC_QA_BLOCKER_REPORT_FILENAME,
            ui_review_data_bundle_path=ui_data_bundle_ref,
            matter_linking_preflight_path=quality_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME,
            labor_employment_qa_matrix_path=quality_dir
            / LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME,
            blocked_driver_impact_review_path=quality_dir
            / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
            budget_output_expectations_path=quality_dir
            / LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME,
            budget_qa_gate_path=quality_dir / LABOR_EMPLOYMENT_BUDGET_QA_GATE_REPORT_FILENAME,
            validation_suite_evidence_path=staged_validation_suite_evidence_ref,
            out_dir=quality_dir / "poc-qa-triage",
            repo_root=root,
            generated_at=generated_at,
        )
        _stage_for_bundle(poc_qa_triage_dir / POC_QA_TRIAGE_REPORT_FILENAME, quality_dir)
        build_ui_review_manifest(
            run_root=run_dir,
            out_path=ui_manifest_ref,
            generated_at=generated_at,
        )
        run_poc_qa_triage_report(
            ui_manifest_path=ui_manifest_ref,
            synthetic_confidence_summary_path=(
                quality_dir / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME
            ),
            synthetic_qa_review_run_path=run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
            synthetic_qa_blocker_report_path=quality_dir / SYNTHETIC_QA_BLOCKER_REPORT_FILENAME,
            ui_review_data_bundle_path=ui_data_bundle_ref,
            matter_linking_preflight_path=quality_dir / MATTER_LINKING_PREFLIGHT_REPORT_FILENAME,
            labor_employment_qa_matrix_path=quality_dir
            / LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME,
            blocked_driver_impact_review_path=quality_dir
            / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
            budget_output_expectations_path=quality_dir
            / LABOR_EMPLOYMENT_BUDGET_OUTPUT_EXPECTATION_REPORT_FILENAME,
            budget_qa_gate_path=quality_dir / LABOR_EMPLOYMENT_BUDGET_QA_GATE_REPORT_FILENAME,
            validation_suite_evidence_path=staged_validation_suite_evidence_ref,
            out_dir=quality_dir / "poc-qa-triage",
            repo_root=root,
            generated_at=generated_at,
        )
        _stage_for_bundle(
            quality_dir / "poc-qa-triage" / POC_QA_TRIAGE_REPORT_FILENAME,
            quality_dir,
        )
        build_ui_review_manifest(
            run_root=run_dir,
            out_path=ui_manifest_ref,
            generated_at=generated_at,
        )
    build_ui_review_data_bundle(
        run_root=run_dir,
        out_path=ui_data_bundle_ref,
        generated_at=generated_at,
    )
    return report, run_dir


def _synthetic_qa_review_outcome_payload(
    *,
    blocker_report: dict,
    generated_at: str | None,
) -> dict:
    rows = blocker_report.get("rows", [])
    if len(rows) < 3:
        raise ValueError("synthetic QA review outcome seed requires at least three blocker rows")
    outcomes = ["accepted_for_poc_review", "needs_fix", "defer_to_roadmap"]
    decisions = [
        _synthetic_qa_review_decision(row=row, index=index, outcome=outcome)
        for index, (row, outcome) in enumerate(zip(rows[:3], outcomes), start=1)
    ]
    return {
        "schema_version": "0.1",
        "synthetic_qa_review_outcome_record_id": (
            "synthetic-qa-review-outcome-record.generated-review-run.v0_1"
        ),
        "synthetic_qa_blocker_report_id": blocker_report["synthetic_qa_blocker_report_id"],
        "reviewer_id": "synthetic-qa-reviewer",
        "reviewed_at": generated_at or now_iso(),
        "decision_reason": "Generated partial synthetic QA review outcome for local UI evidence.",
        "decisions": decisions,
    }


def _synthetic_qa_review_decision(*, row: dict, index: int, outcome: str) -> dict:
    followups: list[str] = []
    if outcome == "needs_fix":
        followups = [f"Fix or re-run QA evidence for {row['row_id']}."]
    if outcome == "defer_to_roadmap":
        followups = [f"Carry {row['row_id']} into the remaining roadmap."]
    return {
        "decision_id": f"synthetic-qa-review-decision-{index}",
        "row_id": row["row_id"],
        "outcome": outcome,
        "decision_reason": f"Synthetic QA reviewer decision for {row['label']}.",
        "evidence_refs": [row["row_id"], *row.get("evidence_refs", [])],
        "required_followups": followups,
        "red_team_notes": ["This is POC QA evidence only and does not prove production readiness."],
        "candidate_exception_lake_labels": [
            "synthetic_qa_review_decision_candidate",
            *row.get("candidate_exception_lake_labels", []),
        ],
    }


def _build_budget_coherence(*, repo_root: Path, run_root: Path, budget_dir: Path) -> Path:
    packet, preflight_dir = run_preflight(
        repo_root / DEMO_INPUT_REF,
        repo_root / DEMO_PROFILE_REF,
        run_root / "preflight",
    )
    confirmation_payload = load_json(repo_root / DEMO_CONFIRMATION_REF)
    confirmation_payload["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(confirmation_payload),
    )
    confirmation_path = write_json(
        run_root / "human_confirmation.json",
        confirmation.model_dump(mode="json"),
    )
    run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / DEMO_PROFILE_REF,
        budget_dir,
    )
    report_path = budget_dir / "budget_coherence_report.json"
    validate_budget_artifacts(
        budget_dir / "legal_budget_proposal.json",
        report_out=report_path,
    )
    return report_path


def _build_budget_learning_loop(
    *,
    repo_root: Path,
    budget_dir: Path,
    quality_dir: Path,
    generated_at: str | None,
) -> tuple[BudgetLearningLoopReport, Path]:
    budget_path = budget_dir / "legal_budget_proposal.json"
    _budget_review, budget_review_dir = run_budget_review_record(
        budget_path=budget_path,
        review_path=repo_root / DEMO_BUDGET_REVIEW_REF,
        out_dir=quality_dir / "budget-review",
    )
    _actuals, actuals_dir = run_budget_actual_comparison(
        budget_path=budget_path,
        actuals_path=repo_root / DEMO_ACTUALS_REF,
        budget_revision_report_path=budget_review_dir / BUDGET_REVISION_REPORT_FILENAME,
        out_dir=quality_dir / "budget-actuals",
    )
    _carrier_rejections, carrier_rejections_dir = run_carrier_rejection_capture(
        budget_path,
        repo_root / DEMO_CARRIER_REJECTION_REF,
        quality_dir / "carrier-rejections",
    )
    _carrier_review, carrier_review_dir = run_carrier_rejection_review(
        carrier_rejections_dir / "carrier_rejection_reconciliation_report.json",
        quality_dir / "carrier-rejection-review",
    )
    _carrier_learning, carrier_learning_dir = run_carrier_rejection_learning(
        carrier_review_dir / REVIEW_PACKET_FILENAME,
        quality_dir / "carrier-rejection-learning",
    )
    _reviewed_gate, reviewed_gate_dir = run_reviewed_learning_gate(
        out_dir=quality_dir / "reviewed-learning-gate",
        carrier_rejection_learning_report_path=(carrier_learning_dir / LEARNING_REPORT_FILENAME),
        budget_revision_report_path=budget_review_dir / BUDGET_REVISION_REPORT_FILENAME,
        budget_actual_comparison_report_path=(
            actuals_dir / BUDGET_ACTUAL_COMPARISON_REPORT_FILENAME
        ),
    )
    return run_budget_learning_loop_report(
        budget_actual_comparison_report_path=(
            actuals_dir / BUDGET_ACTUAL_COMPARISON_REPORT_FILENAME
        ),
        budget_actual_variance_ledger_report_path=(
            actuals_dir / BUDGET_ACTUAL_VARIANCE_LEDGER_REPORT_FILENAME
        ),
        carrier_rejection_reconciliation_report_path=(
            carrier_rejections_dir / "carrier_rejection_reconciliation_report.json"
        ),
        carrier_rejection_decision_ledger_report_path=(
            carrier_rejections_dir / CARRIER_REJECTION_DECISION_LEDGER_REPORT_FILENAME
        ),
        carrier_rejection_review_packet_path=carrier_review_dir / REVIEW_PACKET_FILENAME,
        carrier_rejection_learning_report_path=carrier_learning_dir / LEARNING_REPORT_FILENAME,
        reviewed_learning_gate_report_path=(
            reviewed_gate_dir / REVIEWED_LEARNING_GATE_REPORT_FILENAME
        ),
        out_dir=quality_dir / "budget-learning-loop",
        generated_at=generated_at,
    )


def _budget_learning_loop_qa_passed(report: BudgetLearningLoopReport) -> bool:
    if report.status == "budget_learning_loop_ready_for_review":
        return True
    return (
        report.status == "blocked_by_budget_learning_loop"
        and report.reviewed_learning_gate.status == "failed"
        and report.candidate_only
        and report.synthetic_only
        and not report.lake_write_performed
        and not report.sqlite_write_performed
        and not report.external_writes_performed
        and not report.silent_learning_performed
    )


def _stage_for_bundle(source_path: Path, quality_dir: Path) -> Path:
    destination = quality_dir / source_path.name
    if source_path.resolve() != destination.resolve():
        copy2(source_path, destination)
    return destination


def _stage_for_bundle_as(source_path: Path, quality_dir: Path, file_name: str) -> Path:
    destination = quality_dir / file_name
    if source_path.resolve() != destination.resolve():
        copy2(source_path, destination)
    return destination


def _build_review_run_report(
    *,
    run_dir: Path,
    quality_dir: Path,
    steps: list[SyntheticQAReviewRunStep],
    synthetic_qa_bundle_ref: Path,
    ui_manifest_ref: Path,
    ui_data_bundle_ref: Path,
    generated_at: str | None,
) -> SyntheticQAReviewRunReport:
    failed = [step for step in steps if step.status == "failed"]
    report_core = {
        "run_root_ref": str(run_dir),
        "steps": [
            {
                "step_id": step.step_id,
                "status": step.status,
                "observed_status": step.observed_status,
                "artifact_ref": step.artifact_ref,
            }
            for step in steps
        ],
    }
    return SyntheticQAReviewRunReport(
        synthetic_qa_review_run_report_id="syntheticqareviewrun_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=(
            "blocked_by_synthetic_qa_review_run" if failed else "synthetic_qa_review_run_ready"
        ),
        run_root_ref=str(run_dir),
        quality_dir_ref=str(quality_dir),
        step_count=len(steps),
        failed_step_count=len(failed),
        steps=steps,
        synthetic_qa_bundle_ref=str(synthetic_qa_bundle_ref),
        ui_manifest_ref=str(ui_manifest_ref),
        ui_data_bundle_ref=str(ui_data_bundle_ref),
        required_next_actions=_required_next_actions(failed),
        generated_at=generated_at or now_iso(),
    )


def _step(
    step_id: str,
    label: str,
    observed_status: str,
    artifact_ref: str | Path,
    passed: bool,
    note: str,
) -> SyntheticQAReviewRunStep:
    return SyntheticQAReviewRunStep(
        step_id=step_id,
        label=label,
        status="passed" if passed else "failed",
        observed_status=observed_status,
        artifact_ref=str(artifact_ref),
        notes=[note],
    )


def _required_next_actions(failed_steps: list[SyntheticQAReviewRunStep]) -> list[str]:
    if failed_steps:
        return [
            f"Repair synthetic QA recipe step before review: {step.step_id}"
            for step in failed_steps
        ]
    return [
        "Open the generated ui_review_data_bundle.json in the read-only review UI.",
        "Treat pending QA gates as review evidence only; do not apply calibration or learning.",
    ]
