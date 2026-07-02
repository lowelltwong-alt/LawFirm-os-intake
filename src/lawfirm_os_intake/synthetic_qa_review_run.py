from __future__ import annotations

from pathlib import Path
from shutil import copy2

from .budget_calibration_starter_pack import run_budget_calibration_starter_pack
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
    HumanConfirmation,
    SyntheticQAReviewRunReport,
    SyntheticQAReviewRunStep,
)
from .synthetic_qa_bundle import SYNTHETIC_QA_BUNDLE_REPORT_FILENAME, run_synthetic_qa_bundle
from .ui_review_data_bundle import UI_REVIEW_DATA_BUNDLE_FILENAME
from .util import digest_json, load_json, now_iso, write_json
from .workflow import run_budget, run_preflight


SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME = "synthetic_qa_review_run_report.json"

DEMO_INPUT_REF = "examples/synthetic/inbound/carrier-assignment-medmal.json"
DEMO_PROFILE_REF = "context/synthetic-profiles/insurance-defense.yaml"
DEMO_CONFIRMATION_REF = (
    "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
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


def run_synthetic_qa_review_run(
    *,
    run_root: str | Path,
    repo_root: str | Path = ".",
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

    for source_path in [
        starter_dir / "budget-calibration-readiness" / "budget_calibration_readiness_report.json",
        le_matrix_dir / LABOR_EMPLOYMENT_QA_MATRIX_REPORT_FILENAME,
        family_pack_dir / LABOR_EMPLOYMENT_FIXTURE_FAMILY_PACK_REPORT_FILENAME,
        executable_report_ref,
        coverage_dir / LABOR_EMPLOYMENT_EXECUTABLE_COVERAGE_REPORT_FILENAME,
        fact_binding_ref,
        driver_binding_ref,
        driver_impact_ref,
        driver_review_dir / LABOR_EMPLOYMENT_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
        blocked_review_dir / LABOR_EMPLOYMENT_BLOCKED_DRIVER_IMPACT_REVIEW_REPORT_FILENAME,
        gold_dir / LABOR_EMPLOYMENT_BUDGET_FACT_GOLD_REPORT_FILENAME,
    ]:
        _stage_for_bundle(source_path, quality_dir)

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
    ui_data_bundle = load_json(ui_data_bundle_ref) if ui_data_bundle_ref.is_file() else {}
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
    report = SyntheticQAReviewRunReport(
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
    write_json(run_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME, report.model_dump(mode="json"))
    return report, run_dir


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


def _stage_for_bundle(source_path: Path, quality_dir: Path) -> Path:
    destination = quality_dir / source_path.name
    if source_path.resolve() != destination.resolve():
        copy2(source_path, destination)
    return destination


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
