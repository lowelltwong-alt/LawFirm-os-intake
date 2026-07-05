from __future__ import annotations

from pathlib import Path
import shutil
import subprocess
import sys

from .models import UIDemoQARecipeReport, UIDemoQARecipeStep
from .rust_fixture_boundary import run_rust_fixture_boundary_check
from .rust_fixture_manifest import run_rust_fixture_manifest_scan
from .synthetic_qa_review_run import (
    SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
    run_synthetic_qa_review_run,
)
from .ui_demo_fixture_promotion import promote_ui_demo_run_fixtures
from .ui_review_data_bundle import UI_REVIEW_DATA_BUNDLE_FILENAME
from .util import digest_json, load_json, now_iso, write_json


UI_DEMO_QA_RECIPE_REPORT_FILENAME = "ui_demo_qa_recipe_report.json"

VALIDATION_STEP_ORDER = [
    "validate_repo",
    "export_schemas",
    "ruff_check",
    "ruff_format_check",
    "full_pytest",
    "smoke_demo",
    "validate_repo_final",
]


def run_ui_demo_qa_recipe(
    *,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    fixtures_root: str | Path = "apps/legal-intake-budget/src/fixtures",
    run_root: str | Path | None = None,
    validation_suite_evidence_report_path: str | Path | None = None,
    write_fixtures: bool = False,
    generated_at: str | None = None,
    timeout_seconds: int = 240,
    validation_timeout_seconds: int = 7200,
) -> tuple[UIDemoQARecipeReport, Path]:
    repo = Path(repo_root).resolve()
    out = Path(out_dir).resolve()
    fixtures = Path(fixtures_root)
    if not fixtures.is_absolute():
        fixtures = repo / fixtures
    fixtures = fixtures.resolve()
    final_run_root = (
        Path(run_root).resolve() if run_root is not None else out / "final-synthetic-qa-review"
    )
    initial_run_root = out / "initial-synthetic-qa-review"
    temp_fixtures = out / "temp-fixtures"
    temp_promotion_dir = out / "temp-promotion"
    rust_boundary_dir = out / "temp-rust-fixture-boundary"
    rust_manifest_dir = out / "temp-rust-fixture-manifest"
    final_promotion_dir = out / "final-promotion"
    report_path = out / UI_DEMO_QA_RECIPE_REPORT_FILENAME
    out.mkdir(parents=True, exist_ok=True)

    validation_ref = (
        Path(validation_suite_evidence_report_path).resolve()
        if validation_suite_evidence_report_path is not None
        else out / "validation" / "validation_suite_evidence_report.json"
    )
    _clean_recipe_paths(
        base=out,
        paths=[
            initial_run_root,
            final_run_root,
            temp_fixtures,
            temp_promotion_dir,
            rust_boundary_dir,
            rust_manifest_dir,
            final_promotion_dir,
        ],
        protected_paths=[validation_ref],
    )

    steps: list[UIDemoQARecipeStep] = []
    validation_mode = "provided" if validation_suite_evidence_report_path is not None else "ran"
    if validation_suite_evidence_report_path is None:
        validation_return_code = _run_validation_suite(
            repo=repo,
            report_out=validation_ref,
            generated_at=generated_at,
            timeout_seconds=validation_timeout_seconds,
        )
    else:
        validation_return_code = 0
    validation_payload = _load_object(validation_ref) if validation_ref.is_file() else {}
    validation_status = str(validation_payload.get("status") or "missing")
    validation_exact = _validation_exact_step_order_confirmed(validation_payload)
    validation_clean = validation_payload.get("working_tree_dirty") is False
    validation_passed = (
        validation_return_code == 0
        and validation_status == "validation_suite_passed"
        and validation_exact
        and validation_clean
    )
    steps.append(
        _step(
            step_id="validation_suite_evidence",
            label="Validation Suite Evidence",
            observed_status=validation_status,
            artifact_ref=validation_ref if validation_ref.is_file() else None,
            passed=validation_passed,
            notes=[
                "Validation evidence must be the exact wrapper step set, all passed, with clean worktree."
            ],
        )
    )
    if not validation_passed:
        return _finish_report(
            out=out,
            report_path=report_path,
            final_run_root=final_run_root,
            initial_run_root=initial_run_root,
            fixtures=fixtures,
            temp_fixtures=temp_fixtures,
            validation_mode=validation_mode,
            validation_ref=validation_ref,
            validation_status=validation_status,
            validation_exact=validation_exact,
            validation_clean=validation_clean,
            initial_status="not_run",
            temp_promotion_status="not_run",
            rust_boundary_status="not_run",
            rust_manifest_status="not_run",
            rust_boundary_root_matches=False,
            rust_manifest_root_matches=False,
            final_status="not_run",
            final_ui_bundle_status="not_run",
            final_poc_status="not_run",
            final_promotion_status="not_run",
            final_promotion_report_ref=None,
            final_ui_review_data_bundle_ref=None,
            final_poc_qa_triage_ref=None,
            temp_fixture_updates_performed=False,
            local_fixture_updates_performed=False,
            rollback_performed=False,
            steps=steps,
            generated_at=generated_at,
        )

    initial_report, initial_dir = run_synthetic_qa_review_run(
        run_root=initial_run_root,
        repo_root=repo,
        validation_suite_evidence_report_path=validation_ref,
        generated_at=generated_at,
    )
    initial_payload = _load_object(initial_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME)
    initial_status = str(initial_payload.get("status") or initial_report.status)
    steps.append(
        _step(
            step_id="initial_synthetic_qa_run",
            label="Initial Synthetic QA Run",
            observed_status=initial_status,
            artifact_ref=initial_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
            passed=(
                initial_status == "synthetic_qa_review_run_ready"
                and int(initial_payload.get("failed_step_count") or 0) == 0
                and _all_default_promotion_sources_exist(initial_dir)
            ),
            notes=["Initial run must emit every default UI demo promotion source at exact paths."],
        )
    )

    shutil.copytree(fixtures, temp_fixtures)
    temp_promotion, temp_promotion_path = promote_ui_demo_run_fixtures(
        run_root=initial_dir,
        fixtures_root=temp_fixtures,
        out_dir=temp_promotion_dir,
        repo_root=repo,
        write_fixtures=True,
        generated_at=generated_at,
        timeout_seconds=timeout_seconds,
    )
    temp_promotion_status = temp_promotion.status
    steps.append(
        _step(
            step_id="temp_fixture_promotion",
            label="Temporary Fixture Promotion",
            observed_status=temp_promotion_status,
            artifact_ref=temp_promotion_path,
            passed=temp_promotion_status == "ui_demo_fixture_promotion_verified",
            notes=[
                "Scratch fixture promotion builds wrapper evidence before checked fixtures are touched."
            ],
        )
    )

    rust_boundary, rust_boundary_path = run_rust_fixture_boundary_check(
        root=temp_fixtures,
        ui_bundle_path=temp_fixtures / "demo-ui-review-data-bundle.json",
        out_dir=rust_boundary_dir,
        repo_root=repo,
        timeout_seconds=timeout_seconds,
    )
    rust_boundary_root_matches = _same_path(rust_boundary.root, temp_fixtures)
    steps.append(
        _step(
            step_id="rust_fixture_boundary",
            label="Rust Fixture Boundary",
            observed_status=rust_boundary.status,
            artifact_ref=rust_boundary_path,
            passed=(
                rust_boundary.status == "passed"
                and rust_boundary.failure_count == 0
                and rust_boundary_root_matches
            ),
            notes=["Rust boundary evidence must be generated from the scratch fixture set."],
        )
    )

    rust_manifest, rust_manifest_path = run_rust_fixture_manifest_scan(
        root=temp_fixtures,
        out_dir=rust_manifest_dir,
        repo_root=repo,
        timeout_seconds=timeout_seconds,
    )
    rust_manifest_root_matches = _same_path(rust_manifest.root, temp_fixtures)
    steps.append(
        _step(
            step_id="rust_fixture_manifest",
            label="Rust Fixture Manifest",
            observed_status=rust_manifest.status,
            artifact_ref=rust_manifest_path,
            passed=(
                rust_manifest.status == "passed"
                and rust_manifest.failure_count == 0
                and rust_manifest_root_matches
            ),
            notes=["Rust manifest evidence must be generated from the scratch fixture set."],
        )
    )

    final_report, final_dir = run_synthetic_qa_review_run(
        run_root=final_run_root,
        repo_root=repo,
        validation_suite_evidence_report_path=validation_ref,
        fixture_boundary_report_path=rust_boundary_path,
        fixture_manifest_report_path=rust_manifest_path,
        generated_at=generated_at,
    )
    final_payload = _load_object(final_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME)
    final_status = str(final_payload.get("status") or final_report.status)
    final_ui_bundle_ref = final_dir / UI_REVIEW_DATA_BUNDLE_FILENAME
    final_ui_bundle_payload = _load_object(final_ui_bundle_ref)
    final_ui_bundle_status = str(final_ui_bundle_payload.get("status") or "missing")
    final_poc_ref = final_dir / "quality" / "poc_qa_triage_report.json"
    final_poc_payload = _load_object(final_poc_ref)
    final_poc_status = str(final_poc_payload.get("status") or "missing")
    steps.append(
        _step(
            step_id="final_synthetic_qa_run",
            label="Final Synthetic QA Run",
            observed_status=final_status,
            artifact_ref=final_dir / SYNTHETIC_QA_REVIEW_RUN_REPORT_FILENAME,
            passed=(
                final_status == "synthetic_qa_review_run_ready"
                and int(final_payload.get("failed_step_count") or 0) == 0
                and final_ui_bundle_status == "ready_for_review"
                and final_poc_status == "poc_qa_ready_for_review"
                and _all_default_promotion_sources_exist(final_dir)
            ),
            notes=["Final run is read back from disk after all generated wrapper passes finish."],
        )
    )

    final_promotion, final_promotion_path = promote_ui_demo_run_fixtures(
        run_root=final_dir,
        fixtures_root=fixtures,
        out_dir=final_promotion_dir,
        repo_root=repo,
        write_fixtures=write_fixtures,
        generated_at=generated_at,
        timeout_seconds=timeout_seconds,
    )
    final_promotion_status = final_promotion.status
    final_promotion_blocked_for_write = (
        final_promotion_status == "ui_demo_fixture_promotion_blocked_write_flag_required"
    )
    steps.append(
        _step(
            step_id="final_fixture_promotion",
            label="Final Checked Fixture Promotion",
            observed_status=final_promotion_status,
            artifact_ref=final_promotion_path,
            passed=final_promotion_status == "ui_demo_fixture_promotion_verified",
            blocked=final_promotion_blocked_for_write,
            notes=["Checked fixtures are updated only by this final explicit promotion step."],
        )
    )

    return _finish_report(
        out=out,
        report_path=report_path,
        final_run_root=final_dir,
        initial_run_root=initial_dir,
        fixtures=fixtures,
        temp_fixtures=temp_fixtures,
        validation_mode=validation_mode,
        validation_ref=validation_ref,
        validation_status=validation_status,
        validation_exact=validation_exact,
        validation_clean=validation_clean,
        initial_status=initial_status,
        temp_promotion_status=temp_promotion_status,
        rust_boundary_status=rust_boundary.status,
        rust_manifest_status=rust_manifest.status,
        rust_boundary_root_matches=rust_boundary_root_matches,
        rust_manifest_root_matches=rust_manifest_root_matches,
        final_status=final_status,
        final_ui_bundle_status=final_ui_bundle_status,
        final_poc_status=final_poc_status,
        final_promotion_status=final_promotion_status,
        final_promotion_report_ref=final_promotion_path,
        final_ui_review_data_bundle_ref=final_ui_bundle_ref,
        final_poc_qa_triage_ref=final_poc_ref,
        temp_fixture_updates_performed=temp_promotion.local_fixture_updates_performed,
        local_fixture_updates_performed=final_promotion.local_fixture_updates_performed,
        rollback_performed=final_promotion.rollback_performed,
        steps=steps,
        generated_at=generated_at,
    )


def _run_validation_suite(
    *,
    repo: Path,
    report_out: Path,
    generated_at: str | None,
    timeout_seconds: int,
) -> int:
    command = [
        sys.executable,
        "scripts/run_validation_suite.py",
        "--report-out",
        str(report_out),
    ]
    if generated_at is not None:
        command.extend(["--generated-at", generated_at])
    completed = subprocess.run(
        command,
        cwd=repo,
        check=False,
        timeout=timeout_seconds,
    )
    return completed.returncode


def _finish_report(
    *,
    out: Path,
    report_path: Path,
    final_run_root: Path,
    initial_run_root: Path,
    fixtures: Path,
    temp_fixtures: Path,
    validation_mode: str,
    validation_ref: Path,
    validation_status: str,
    validation_exact: bool,
    validation_clean: bool,
    initial_status: str,
    temp_promotion_status: str,
    rust_boundary_status: str,
    rust_manifest_status: str,
    rust_boundary_root_matches: bool,
    rust_manifest_root_matches: bool,
    final_status: str,
    final_ui_bundle_status: str,
    final_poc_status: str,
    final_promotion_status: str,
    final_promotion_report_ref: Path | None,
    final_ui_review_data_bundle_ref: Path | None,
    final_poc_qa_triage_ref: Path | None,
    temp_fixture_updates_performed: bool,
    local_fixture_updates_performed: bool,
    rollback_performed: bool,
    steps: list[UIDemoQARecipeStep],
    generated_at: str | None,
) -> tuple[UIDemoQARecipeReport, Path]:
    failed = [step for step in steps if step.status == "failed"]
    blocked = [step for step in steps if step.status == "blocked"]
    if final_promotion_status == "ui_demo_fixture_promotion_blocked_write_flag_required":
        status = "ui_demo_qa_recipe_blocked_write_flag_required"
    elif failed or blocked:
        status = "ui_demo_qa_recipe_failed"
    else:
        status = "ui_demo_qa_recipe_verified"
    report_core = {
        "status": status,
        "steps": [
            {
                "step_id": step.step_id,
                "status": step.status,
                "observed_status": step.observed_status,
            }
            for step in steps
        ],
        "final_run_root_ref": str(final_run_root),
        "fixtures_root_ref": str(fixtures),
    }
    report = UIDemoQARecipeReport(
        ui_demo_qa_recipe_report_id="ui_demo_qa_recipe_"
        + digest_json(report_core).removeprefix("sha256:")[:16],
        status=status,  # type: ignore[arg-type]
        out_dir_ref=str(out),
        final_run_root_ref=str(final_run_root),
        initial_run_root_ref=str(initial_run_root),
        fixtures_root_ref=str(fixtures),
        temp_fixtures_root_ref=str(temp_fixtures),
        validation_mode=validation_mode,  # type: ignore[arg-type]
        validation_suite_evidence_ref=str(validation_ref),
        validation_suite_status=validation_status,
        validation_exact_step_order_confirmed=validation_exact,
        validation_worktree_clean_confirmed=validation_clean,
        initial_synthetic_qa_status=initial_status,
        temp_promotion_status=temp_promotion_status,
        rust_boundary_status=rust_boundary_status,
        rust_manifest_status=rust_manifest_status,
        rust_boundary_root_matches_temp_fixtures=rust_boundary_root_matches,
        rust_manifest_root_matches_temp_fixtures=rust_manifest_root_matches,
        final_synthetic_qa_status=final_status,
        final_ui_bundle_status=final_ui_bundle_status,
        final_poc_qa_triage_status=final_poc_status,
        final_promotion_status=final_promotion_status,
        final_promotion_report_ref=(
            str(final_promotion_report_ref) if final_promotion_report_ref is not None else None
        ),
        final_ui_review_data_bundle_ref=(
            str(final_ui_review_data_bundle_ref)
            if final_ui_review_data_bundle_ref is not None
            else None
        ),
        final_poc_qa_triage_ref=(
            str(final_poc_qa_triage_ref) if final_poc_qa_triage_ref is not None else None
        ),
        step_count=len(steps),
        failed_step_count=len(failed),
        blocked_step_count=len(blocked),
        temp_fixture_updates_performed=temp_fixture_updates_performed,
        local_fixture_updates_performed=local_fixture_updates_performed,
        rollback_performed=rollback_performed,
        steps=steps,
        required_next_actions=_required_next_actions(status=status),
        generated_at=generated_at or now_iso(),
    )
    write_json(report_path, report.model_dump(mode="json"))
    return report, report_path


def _step(
    *,
    step_id: str,
    label: str,
    observed_status: str,
    artifact_ref: str | Path | None,
    passed: bool,
    notes: list[str],
    blocked: bool = False,
) -> UIDemoQARecipeStep:
    status = "passed" if passed else "blocked" if blocked else "failed"
    return UIDemoQARecipeStep(
        step_id=step_id,
        label=label,
        status=status,  # type: ignore[arg-type]
        observed_status=observed_status,
        artifact_ref=str(artifact_ref) if artifact_ref is not None else None,
        notes=notes,
    )


def _validation_exact_step_order_confirmed(payload: dict) -> bool:
    steps = payload.get("steps")
    if not isinstance(steps, list):
        return False
    step_ids = [step.get("step_id") for step in steps if isinstance(step, dict)]
    if step_ids != VALIDATION_STEP_ORDER:
        return False
    return all(
        isinstance(step, dict) and step.get("status") == "passed" and step.get("return_code") == 0
        for step in steps
    )


def _all_default_promotion_sources_exist(run_root: Path) -> bool:
    from .ui_demo_fixture_promotion import DEFAULT_UI_DEMO_FIXTURE_PROMOTION_SPECS

    return all(
        (run_root / spec.source_ref).is_file() for spec in DEFAULT_UI_DEMO_FIXTURE_PROMOTION_SPECS
    )


def _load_object(path: Path) -> dict:
    if not path.is_file():
        return {}
    payload = load_json(path)
    return payload if isinstance(payload, dict) else {}


def _same_path(left: str | Path, right: str | Path) -> bool:
    try:
        return Path(left).resolve() == Path(right).resolve()
    except OSError:
        return False


def _clean_recipe_paths(*, base: Path, paths: list[Path], protected_paths: list[Path]) -> None:
    protected = {path.resolve() for path in protected_paths}
    for path in paths:
        resolved = path.resolve()
        if resolved in protected:
            raise ValueError(f"recipe cleanup path would remove protected input: {resolved}")
        if not _is_under_root(resolved, base):
            if path.exists():
                raise ValueError(
                    "run-ui-demo-qa-recipe only cleans existing generated paths under out-dir; "
                    f"refusing to clean {resolved}"
                )
            continue
        if resolved.exists():
            if resolved.is_dir():
                shutil.rmtree(resolved)
            else:
                resolved.unlink()


def _is_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def _required_next_actions(*, status: str) -> list[str]:
    if status == "ui_demo_qa_recipe_verified":
        return [
            "UI demo QA recipe completed; checked fixtures were promoted and verified by Rust gates."
        ]
    if status == "ui_demo_qa_recipe_blocked_write_flag_required":
        return [
            "Rerun with --write-fixtures to update checked UI demo fixtures after reviewing the generated recipe report."
        ]
    return [
        "Inspect the failed UI demo QA recipe step before relying on checked frontend fixtures."
    ]
