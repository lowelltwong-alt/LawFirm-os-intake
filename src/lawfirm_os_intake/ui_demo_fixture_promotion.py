from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import shutil
from typing import Any

from .models import UIDemoFixturePromotionItem, UIDemoFixturePromotionReport
from .rust_fixture_boundary import run_rust_fixture_boundary_check
from .ui_demo_fixture_refresh import refresh_ui_demo_fixtures
from .util import load_json, now_iso, write_json


DEMO_RUN_ROOT_PLACEHOLDER = "<demo-run-root>"
UI_DEMO_FIXTURE_PROMOTION_REPORT_FILENAME = "ui_demo_fixture_promotion_report.json"
DEMO_UI_REVIEW_DATA_BUNDLE_FILENAME = "demo-ui-review-data-bundle.json"
DEMO_RUST_FIXTURE_BOUNDARY_FILENAME = "demo-rust-fixture-boundary-report.json"

PROHIBITED_TRUE_KEYS = {
    "external_writes_performed",
    "lake_write_performed",
    "sqlite_write_performed",
    "budget_submission_authorized",
    "matter_opening_authorized",
    "appeal_submission_performed",
    "runtime_artifacts_created",
    "silent_learning_performed",
    "connector_implemented",
    "public_records_ingested",
    "client_submission_performed",
    "carrier_submission_performed",
    "billing_handoff_performed",
    "conflict_conclusion_emitted",
    "budget_amount_output_authorized",
    "fixture_files_mutated",
    "github_pr_created",
    "training_pipeline_created",
    "rust_runtime_added",
    "rust_replacement_allowed",
    "externalWritesPerformed",
    "networkCallsAllowed",
    "mutationCommandsAllowed",
    "exceptionLakeWritesAllowed",
    "sqliteWritesAllowed",
    "publicRuntimeIngestionAllowed",
    "budgetSubmissionAllowed",
    "matterOpeningAllowed",
}


@dataclass(frozen=True)
class UIDemoFixturePromotionSpec:
    source_ref: str
    fixture_name: str
    required: bool = True


@dataclass(frozen=True)
class PlannedPromotion:
    spec: UIDemoFixturePromotionSpec
    source_path: Path | None
    target_path: Path
    payload: dict[str, Any] | None
    old_target_sha256: str | None
    planned_target_sha256: str | None
    source_sha256: str | None
    sanitized_replacement_count: int
    forbidden_run_root_leak_count: int
    blocked_side_effect_count: int
    status: str
    message: str


DEFAULT_UI_DEMO_FIXTURE_PROMOTION_SPECS: tuple[UIDemoFixturePromotionSpec, ...] = (
    UIDemoFixturePromotionSpec("ui_review_manifest.json", "demo-run-manifest.json"),
    UIDemoFixturePromotionSpec(
        "synthetic_qa_review_run_report.json",
        "demo-synthetic-qa-review-run-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/synthetic_confidence_summary_report.json",
        "demo-synthetic-confidence-summary-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/poc_qa_triage_report.json",
        "demo-poc-qa-triage-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/synthetic_qa_blocker_report.json",
        "demo-synthetic-qa-blocker-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/synthetic_qa_bundle_report.json",
        "demo-synthetic-qa-bundle-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/synthetic_qa_review_outcome_report.json",
        "demo-synthetic-qa-review-outcome-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/validation_suite_evidence_report.json",
        "demo-validation-suite-evidence-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/matter_linking_preflight_report.json",
        "demo-matter-linking-preflight-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/matter_linking_qa_gate_report.json",
        "demo-matter-linking-qa-gate-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/matter_linking_review_outcome_report.json",
        "demo-matter-linking-review-outcome-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_qa_matrix_report.json",
        "demo-labor-employment-qa-matrix-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_executable_coverage_report.json",
        "demo-labor-employment-executable-coverage-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_blocked_driver_impact_review_report.json",
        "demo-labor-employment-blocked-driver-impact-review-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_budget_output_expectations_report.json",
        "demo-labor-employment-budget-output-expectations-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_budget_qa_gate_report.json",
        "demo-labor-employment-budget-qa-gate-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_budget_learning_fixtures_report.json",
        "demo-labor-employment-budget-learning-fixtures-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_budget_outcome_replay_readiness_report.json",
        "demo-labor-employment-budget-outcome-replay-readiness-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_budget_outcome_replay_execution_report.json",
        "demo-labor-employment-budget-outcome-replay-execution-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_budget_outcome_replay_builder_binding_report.json",
        "demo-labor-employment-budget-outcome-replay-builder-binding-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/labor_employment_budget_outcome_replay_confidence_status_report.json",
        "demo-labor-employment-budget-outcome-replay-confidence-status-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/budget_learning_loop_report.json",
        "demo-budget-learning-loop-report.json",
    ),
    UIDemoFixturePromotionSpec(
        "quality/public_derived_synthetic_qa_gate_report.json",
        "demo-public-derived-synthetic-qa-gate-report.json",
    ),
)


def promote_ui_demo_run_fixtures(
    *,
    run_root: str | Path,
    fixtures_root: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    write_fixtures: bool,
    generated_at: str | None = None,
    timeout_seconds: int = 240,
    promotion_specs: tuple[
        UIDemoFixturePromotionSpec, ...
    ] = DEFAULT_UI_DEMO_FIXTURE_PROMOTION_SPECS,
) -> tuple[UIDemoFixturePromotionReport, Path]:
    run = Path(run_root)
    fixtures = Path(fixtures_root)
    out = Path(out_dir)
    repo = Path(repo_root).resolve()
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / UI_DEMO_FIXTURE_PROMOTION_REPORT_FILENAME
    if not write_fixtures:
        report = _promotion_report(
            status="ui_demo_fixture_promotion_blocked_write_flag_required",
            run_root=run,
            fixtures=fixtures,
            items=[],
            rust_boundary_status="not_run",
            wrapper_refresh_status="not_run",
            manifest_status="not_run",
            source_hash_gate_status="not_run",
            snapshot_gate_status="not_run",
            wrapper_refresh_report_ref=None,
            old_ui_review_data_bundle_id=None,
            new_ui_review_data_bundle_id=None,
            local_fixture_updates_performed=False,
            rollback_performed=False,
            generated_at=generated_at,
            required_next_actions=["promote-ui-demo-run-fixtures requires --write-fixtures."],
        )
        write_json(report_path, report.model_dump(mode="json"))
        return report, report_path

    planned = _build_plan(run=run, fixtures=fixtures, promotion_specs=promotion_specs)
    planning_items = [_planned_item(item) for item in planned]
    if _plan_has_failures(planned):
        report = _promotion_report(
            status="ui_demo_fixture_promotion_failed",
            run_root=run,
            fixtures=fixtures,
            items=planning_items,
            rust_boundary_status="not_run",
            wrapper_refresh_status="not_run",
            manifest_status="not_run",
            source_hash_gate_status="not_run",
            snapshot_gate_status="not_run",
            wrapper_refresh_report_ref=None,
            old_ui_review_data_bundle_id=_current_bundle_id(fixtures),
            new_ui_review_data_bundle_id=_current_bundle_id(fixtures),
            local_fixture_updates_performed=False,
            rollback_performed=False,
            generated_at=generated_at,
            required_next_actions=[
                "Resolve missing, ambiguous, leaking, or side-effecting source artifacts before "
                "promoting generated run fixtures."
            ],
        )
        write_json(report_path, report.model_dump(mode="json"))
        return report, report_path

    fixture_backup = _snapshot_json_fixtures(fixtures)
    old_bundle_id = _current_bundle_id(fixtures)
    rollback_performed = False
    try:
        for item in planned:
            if item.payload is None:
                continue
            write_json(item.target_path, item.payload)

        boundary_report, boundary_report_path = run_rust_fixture_boundary_check(
            root=fixtures,
            ui_bundle_path=fixtures / DEMO_UI_REVIEW_DATA_BUNDLE_FILENAME,
            out_dir=out / "rust-fixture-boundary",
            repo_root=repo,
            timeout_seconds=timeout_seconds,
        )
        shutil.copy2(boundary_report_path, fixtures / DEMO_RUST_FIXTURE_BOUNDARY_FILENAME)

        refresh_report, refresh_report_path = refresh_ui_demo_fixtures(
            fixtures_root=fixtures,
            out_dir=out / "ui-demo-fixture-refresh",
            repo_root=repo,
            write_fixtures=True,
            generated_at=generated_at,
            timeout_seconds=timeout_seconds,
        )
        final_items = _final_items(
            planned=planned,
            fixtures=fixtures,
            boundary_report_path=fixtures / DEMO_RUST_FIXTURE_BOUNDARY_FILENAME,
        )
        status = (
            "ui_demo_fixture_promotion_verified"
            if (
                boundary_report.status == "passed"
                and refresh_report.status == "ui_demo_fixture_refresh_verified"
            )
            else "ui_demo_fixture_promotion_failed"
        )
        if status != "ui_demo_fixture_promotion_verified":
            _restore_json_fixtures(fixtures=fixtures, snapshot=fixture_backup)
            rollback_performed = True
            final_items = planning_items

        report = _promotion_report(
            status=status,
            run_root=run,
            fixtures=fixtures,
            items=final_items,
            rust_boundary_status=boundary_report.status,
            wrapper_refresh_status=refresh_report.status,
            manifest_status=refresh_report.manifest_status,
            source_hash_gate_status=refresh_report.source_hash_gate_status,
            snapshot_gate_status=refresh_report.snapshot_gate_status,
            wrapper_refresh_report_ref=str(refresh_report_path),
            old_ui_review_data_bundle_id=old_bundle_id,
            new_ui_review_data_bundle_id=refresh_report.new_ui_review_data_bundle_id,
            local_fixture_updates_performed=not rollback_performed
            and status == "ui_demo_fixture_promotion_verified",
            rollback_performed=rollback_performed,
            generated_at=generated_at,
            required_next_actions=_required_next_actions(status=status),
        )
        write_json(report_path, report.model_dump(mode="json"))
        return report, report_path
    except Exception:
        _restore_json_fixtures(fixtures=fixtures, snapshot=fixture_backup)
        rollback_performed = True
        raise


def _build_plan(
    *,
    run: Path,
    fixtures: Path,
    promotion_specs: tuple[UIDemoFixturePromotionSpec, ...],
) -> list[PlannedPromotion]:
    variants = _run_root_variants(run)
    planned = []
    for spec in promotion_specs:
        target_path = fixtures / spec.fixture_name
        source_path, source_status, message = _resolve_source(run=run, spec=spec)
        if source_path is None:
            planned.append(
                PlannedPromotion(
                    spec=spec,
                    source_path=None,
                    target_path=target_path,
                    payload=None,
                    old_target_sha256=_sha256_file(target_path) if target_path.is_file() else None,
                    planned_target_sha256=None,
                    source_sha256=None,
                    sanitized_replacement_count=0,
                    forbidden_run_root_leak_count=0,
                    blocked_side_effect_count=0,
                    status=source_status,
                    message=message,
                )
            )
            continue
        payload = load_json(source_path)
        if not isinstance(payload, dict):
            planned.append(
                PlannedPromotion(
                    spec=spec,
                    source_path=source_path,
                    target_path=target_path,
                    payload=None,
                    old_target_sha256=_sha256_file(target_path) if target_path.is_file() else None,
                    planned_target_sha256=None,
                    source_sha256=_sha256_file(source_path),
                    sanitized_replacement_count=0,
                    forbidden_run_root_leak_count=0,
                    blocked_side_effect_count=0,
                    status="blocked_side_effect",
                    message="Promotion source must be a JSON object report.",
                )
            )
            continue
        sanitized, replacement_count = _sanitize_value(payload, variants=variants)
        leak_count = _forbidden_run_root_leak_count(sanitized, variants=variants)
        side_effect_count = _blocked_side_effect_count(sanitized)
        old_hash = _sha256_file(target_path) if target_path.is_file() else None
        planned_hash = _sha256_json_payload(sanitized)
        status = "unchanged" if old_hash == planned_hash else "promoted"
        item_message = "Promoted sanitized generated artifact into checked UI fixture."
        if leak_count:
            status = "blocked_side_effect"
            item_message = "Sanitized artifact still contains a generated run-root reference."
        elif side_effect_count:
            status = "blocked_side_effect"
            item_message = "Source artifact contains prohibited write or authority signals."
        planned.append(
            PlannedPromotion(
                spec=spec,
                source_path=source_path,
                target_path=target_path,
                payload=sanitized,
                old_target_sha256=old_hash,
                planned_target_sha256=planned_hash,
                source_sha256=_sha256_file(source_path),
                sanitized_replacement_count=replacement_count,
                forbidden_run_root_leak_count=leak_count,
                blocked_side_effect_count=side_effect_count,
                status=status,
                message=item_message,
            )
        )
    return planned


def _resolve_source(*, run: Path, spec: UIDemoFixturePromotionSpec) -> tuple[Path | None, str, str]:
    source_ref = Path(spec.source_ref)
    if source_ref.is_absolute() or ".." in source_ref.parts:
        return (
            None,
            "missing_source",
            f"Generated artifact source_ref must stay under run root: {spec.source_ref}",
        )
    direct = run / spec.source_ref
    if direct.is_file() and _is_under_root(direct, run):
        return direct, "promoted", "Resolved by static source_ref."

    file_name = Path(spec.source_ref).name
    matches = sorted(
        [path for path in run.rglob(file_name) if path.is_file() and _is_under_root(path, run)],
        key=lambda path: (len(path.parts), str(path)),
    )
    if not matches:
        return None, "missing_source", f"Missing generated artifact: {spec.source_ref}"
    if len(matches) > 1:
        return (
            None,
            "ambiguous_source",
            f"Multiple generated artifacts match {file_name}; static source_ref is required.",
        )
    return matches[0], "promoted", "Resolved by unique generated artifact filename."


def _sanitize_value(value: Any, *, variants: tuple[str, ...]) -> tuple[Any, int]:
    if isinstance(value, dict):
        output = {}
        count = 0
        for key, child in value.items():
            sanitized_child, child_count = _sanitize_value(child, variants=variants)
            output[key] = sanitized_child
            count += child_count
        return output, count
    if isinstance(value, list):
        output_list = []
        count = 0
        for child in value:
            sanitized_child, child_count = _sanitize_value(child, variants=variants)
            output_list.append(sanitized_child)
            count += child_count
        return output_list, count
    if isinstance(value, str):
        sanitized = value
        count = 0
        for variant in variants:
            if variant and variant in sanitized:
                replacement_count = sanitized.count(variant)
                sanitized = sanitized.replace(variant, DEMO_RUN_ROOT_PLACEHOLDER)
                count += replacement_count
        return sanitized, count
    return value, 0


def _forbidden_run_root_leak_count(value: Any, *, variants: tuple[str, ...]) -> int:
    if isinstance(value, dict):
        return sum(
            _forbidden_run_root_leak_count(child, variants=variants) for child in value.values()
        )
    if isinstance(value, list):
        return sum(_forbidden_run_root_leak_count(child, variants=variants) for child in value)
    if isinstance(value, str):
        variant_leaks = sum(1 for variant in variants if variant and variant in value)
        return variant_leaks + int(".lawfirm-os-intake" in value)
    return 0


def _blocked_side_effect_count(value: Any) -> int:
    if isinstance(value, dict):
        count = sum(
            1 for key, child in value.items() if key in PROHIBITED_TRUE_KEYS and child is True
        )
        return count + sum(_blocked_side_effect_count(child) for child in value.values())
    if isinstance(value, list):
        return sum(_blocked_side_effect_count(child) for child in value)
    return 0


def _run_root_variants(run: Path) -> tuple[str, ...]:
    resolved = run.resolve()
    variants = {str(run), str(resolved), run.as_posix(), resolved.as_posix()}
    for candidate in [run, resolved]:
        parts = candidate.parts
        if ".lawfirm-os-intake" in parts:
            start = parts.index(".lawfirm-os-intake")
            suffix = Path(*parts[start:])
            variants.update({str(suffix), suffix.as_posix()})
    return tuple(sorted(variants, key=len, reverse=True))


def _plan_has_failures(planned: list[PlannedPromotion]) -> bool:
    return any(
        item.status in {"missing_source", "ambiguous_source", "blocked_side_effect"}
        or item.forbidden_run_root_leak_count
        or item.blocked_side_effect_count
        for item in planned
    )


def _planned_item(item: PlannedPromotion) -> UIDemoFixturePromotionItem:
    return UIDemoFixturePromotionItem(
        fixture_name=item.spec.fixture_name,
        source_ref=item.spec.source_ref,
        target_ref=str(item.target_path),
        old_target_sha256=item.old_target_sha256,
        new_target_sha256=item.planned_target_sha256,
        source_sha256=item.source_sha256,
        sanitized_replacement_count=item.sanitized_replacement_count,
        forbidden_run_root_leak_count=item.forbidden_run_root_leak_count,
        blocked_side_effect_count=item.blocked_side_effect_count,
        status=item.status,
        message=item.message,
    )


def _final_items(
    *,
    planned: list[PlannedPromotion],
    fixtures: Path,
    boundary_report_path: Path,
) -> list[UIDemoFixturePromotionItem]:
    items = []
    for item in planned:
        new_hash = _sha256_file(item.target_path)
        status = "unchanged" if item.old_target_sha256 == new_hash else "promoted"
        items.append(
            UIDemoFixturePromotionItem(
                fixture_name=item.spec.fixture_name,
                source_ref=item.spec.source_ref,
                target_ref=str(item.target_path),
                old_target_sha256=item.old_target_sha256,
                new_target_sha256=new_hash,
                source_sha256=item.source_sha256,
                sanitized_replacement_count=item.sanitized_replacement_count,
                forbidden_run_root_leak_count=0,
                blocked_side_effect_count=0,
                status=status,
                message=item.message,
            )
        )
    for fixture_name in [
        DEMO_RUST_FIXTURE_BOUNDARY_FILENAME,
        "demo-rust-fixture-manifest-report.json",
        DEMO_UI_REVIEW_DATA_BUNDLE_FILENAME,
    ]:
        path = fixtures / fixture_name
        if path.is_file():
            items.append(
                UIDemoFixturePromotionItem(
                    fixture_name=fixture_name,
                    source_ref=None,
                    target_ref=str(path),
                    old_target_sha256=None,
                    new_target_sha256=_sha256_file(path),
                    source_sha256=(
                        _sha256_file(boundary_report_path)
                        if fixture_name == DEMO_RUST_FIXTURE_BOUNDARY_FILENAME
                        else None
                    ),
                    sanitized_replacement_count=0,
                    forbidden_run_root_leak_count=0,
                    blocked_side_effect_count=0,
                    status="generated_wrapper",
                    message="Generated checked wrapper/gate artifact after promotion.",
                )
            )
    return items


def _promotion_report(
    *,
    status: str,
    run_root: Path,
    fixtures: Path,
    items: list[UIDemoFixturePromotionItem],
    rust_boundary_status: str,
    wrapper_refresh_status: str,
    manifest_status: str,
    source_hash_gate_status: str,
    snapshot_gate_status: str,
    wrapper_refresh_report_ref: str | None,
    old_ui_review_data_bundle_id: str | None,
    new_ui_review_data_bundle_id: str | None,
    local_fixture_updates_performed: bool,
    rollback_performed: bool,
    generated_at: str | None,
    required_next_actions: list[str],
) -> UIDemoFixturePromotionReport:
    return UIDemoFixturePromotionReport(
        status=status,
        run_root_ref=str(run_root),
        fixtures_root_ref=str(fixtures),
        promotion_item_count=len(items),
        promoted_item_count=len([item for item in items if item.status == "promoted"]),
        unchanged_item_count=len([item for item in items if item.status == "unchanged"]),
        generated_wrapper_count=len([item for item in items if item.status == "generated_wrapper"]),
        missing_source_count=len([item for item in items if item.status == "missing_source"]),
        ambiguous_source_count=len([item for item in items if item.status == "ambiguous_source"]),
        blocked_side_effect_count=sum(item.blocked_side_effect_count for item in items),
        sanitized_replacement_count=sum(item.sanitized_replacement_count for item in items),
        forbidden_run_root_leak_count=sum(item.forbidden_run_root_leak_count for item in items),
        rust_boundary_status=rust_boundary_status,
        wrapper_refresh_status=wrapper_refresh_status,
        manifest_status=manifest_status,
        source_hash_gate_status=source_hash_gate_status,
        snapshot_gate_status=snapshot_gate_status,
        wrapper_refresh_report_ref=wrapper_refresh_report_ref,
        old_ui_review_data_bundle_id=old_ui_review_data_bundle_id,
        new_ui_review_data_bundle_id=new_ui_review_data_bundle_id,
        local_fixture_updates_performed=local_fixture_updates_performed,
        rollback_performed=rollback_performed,
        items=items,
        required_next_actions=required_next_actions,
        generated_at=generated_at or now_iso(),
    )


def _required_next_actions(*, status: str) -> list[str]:
    if status == "ui_demo_fixture_promotion_verified":
        return [
            "Checked UI demo fixtures were promoted, sanitized, and verified by Rust boundary, source-hash, and snapshot gates."
        ]
    return [
        "Inspect promotion, sanitizer, and Rust gate failures before relying on checked UI demo fixtures."
    ]


def _current_bundle_id(fixtures: Path) -> str | None:
    bundle_path = fixtures / DEMO_UI_REVIEW_DATA_BUNDLE_FILENAME
    if not bundle_path.is_file():
        return None
    payload = load_json(bundle_path)
    return str(payload.get("ui_review_data_bundle_id") or "") if isinstance(payload, dict) else None


def _snapshot_json_fixtures(fixtures: Path) -> dict[Path, bytes]:
    if not fixtures.exists():
        return {}
    return {path: path.read_bytes() for path in fixtures.glob("*.json") if path.is_file()}


def _restore_json_fixtures(*, fixtures: Path, snapshot: dict[Path, bytes]) -> None:
    fixtures.mkdir(parents=True, exist_ok=True)
    for current in list(fixtures.glob("*.json")):
        if current not in snapshot:
            current.unlink()
    for path, content in snapshot.items():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _sha256_file(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _sha256_json_payload(payload: dict[str, Any]) -> str:
    import json

    return (
        "sha256:"
        + sha256(
            (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
        ).hexdigest()
    )


def _is_under_root(candidate: Path, root: Path) -> bool:
    try:
        return candidate.resolve().is_relative_to(root.resolve())
    except OSError:
        return False
