from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .models import UIDemoQARecipeFixtureRefreshReport, UIDemoQARecipeReport
from .ui_demo_fixture_refresh import refresh_ui_demo_fixtures
from .util import digest_json, load_json, now_iso, write_json


DEMO_UI_DEMO_QA_RECIPE_FIXTURE_FILENAME = "demo-ui-demo-qa-recipe-report.json"
UI_DEMO_QA_RECIPE_FIXTURE_REFRESH_REPORT_FILENAME = "ui_demo_qa_recipe_fixture_refresh_report.json"

_PATH_PLACEHOLDER_FIELDS = {
    "out_dir_ref": "<demo-recipe-out-dir>",
    "final_run_root_ref": "<demo-run-root>",
    "initial_run_root_ref": "<demo-initial-run-root>",
    "temp_fixtures_root_ref": "<demo-temp-fixtures-root>",
    "validation_suite_evidence_ref": "<validation-suite-evidence>",
}

_PROHIBITED_TRUE_KEYS = {
    "external_writes_performed",
    "lake_write_performed",
    "sqlite_write_performed",
    "budget_submission_authorized",
    "matter_opening_authorized",
    "silent_learning_performed",
    "conflict_conclusion_emitted",
    "training_pipeline_created",
    "fixture_files_mutated",
}


def refresh_ui_demo_qa_recipe_fixture(
    *,
    source_recipe_report_path: str | Path,
    fixtures_root: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    write_fixtures: bool,
    generated_at: str | None = None,
    timeout_seconds: int = 240,
) -> tuple[UIDemoQARecipeFixtureRefreshReport, Path]:
    source = Path(source_recipe_report_path)
    fixtures = Path(fixtures_root)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / UI_DEMO_QA_RECIPE_FIXTURE_REFRESH_REPORT_FILENAME
    target = fixtures / DEMO_UI_DEMO_QA_RECIPE_FIXTURE_FILENAME

    if not write_fixtures:
        report = _report(
            status="ui_demo_qa_recipe_fixture_refresh_blocked_write_flag_required",
            source=source,
            source_status="not_loaded",
            fixtures=fixtures,
            target=target,
            old_target_sha256=_sha256_file(target) if target.is_file() else None,
            new_target_sha256=None,
            source_sha256=None,
            sanitized_replacement_count=0,
            forbidden_path_leak_count=0,
            blocked_side_effect_count=0,
            wrapper_refresh_status="not_run",
            wrapper_refresh_report_ref=None,
            manifest_status="not_run",
            source_hash_gate_status="not_run",
            snapshot_gate_status="not_run",
            local_fixture_update_performed=False,
            rollback_performed=False,
            generated_at=generated_at,
            required_next_actions=["Recipe proof fixture refresh requires --write-fixtures."],
        )
        write_json(report_path, report.model_dump(mode="json"))
        return report, report_path

    old_files = _snapshot_files(
        [
            target,
            fixtures / "demo-ui-review-data-bundle.json",
            fixtures / "demo-rust-fixture-manifest-report.json",
        ]
    )
    old_target_sha256 = _sha256_file(target) if target.is_file() else None
    source_sha256 = _sha256_file(source) if source.is_file() else None
    try:
        source_payload = load_json(source)
        source_report = UIDemoQARecipeReport.model_validate(source_payload)
        replacements = _replacement_pairs(source_payload, source=source, fixtures=fixtures)
        sanitized, replacement_count = _sanitize_value(source_payload, replacements=replacements)
        if isinstance(sanitized, dict):
            sanitized["fixtures_root_ref"] = "apps/legal-intake-budget/src/fixtures"
            sanitized["ui_demo_qa_recipe_report_id"] = _sanitized_recipe_report_id(sanitized)
        UIDemoQARecipeReport.model_validate(sanitized)
        leak_count = _forbidden_path_leak_count(sanitized, replacements=replacements)
        side_effect_count = _blocked_side_effect_count(sanitized)
        if source_report.status != "ui_demo_qa_recipe_verified" or leak_count or side_effect_count:
            _restore_files(old_files)
            report = _report(
                status="ui_demo_qa_recipe_fixture_refresh_failed",
                source=source,
                source_status=source_report.status,
                fixtures=fixtures,
                target=target,
                old_target_sha256=old_target_sha256,
                new_target_sha256=None,
                source_sha256=source_sha256,
                sanitized_replacement_count=replacement_count,
                forbidden_path_leak_count=leak_count,
                blocked_side_effect_count=side_effect_count,
                wrapper_refresh_status="not_run",
                wrapper_refresh_report_ref=None,
                manifest_status="not_run",
                source_hash_gate_status="not_run",
                snapshot_gate_status="not_run",
                local_fixture_update_performed=False,
                rollback_performed=True,
                generated_at=generated_at,
                required_next_actions=[
                    "Resolve recipe status, path leak, or side-effect signals before refreshing the checked recipe proof fixture."
                ],
            )
            write_json(report_path, report.model_dump(mode="json"))
            return report, report_path

        write_json(target, sanitized)
        wrapper_report, wrapper_report_path = refresh_ui_demo_fixtures(
            fixtures_root=fixtures,
            out_dir=out / "wrapper-refresh",
            repo_root=repo_root,
            write_fixtures=True,
            generated_at=generated_at,
            timeout_seconds=timeout_seconds,
        )
        verified = wrapper_report.status == "ui_demo_fixture_refresh_verified"
        if not verified:
            _restore_files(old_files)
        report = _report(
            status=(
                "ui_demo_qa_recipe_fixture_refresh_verified"
                if verified
                else "ui_demo_qa_recipe_fixture_refresh_failed"
            ),
            source=source,
            source_status=source_report.status,
            fixtures=fixtures,
            target=target,
            old_target_sha256=old_target_sha256,
            new_target_sha256=_sha256_file(target) if verified and target.is_file() else None,
            source_sha256=source_sha256,
            sanitized_replacement_count=replacement_count,
            forbidden_path_leak_count=leak_count,
            blocked_side_effect_count=side_effect_count,
            wrapper_refresh_status=wrapper_report.status,
            wrapper_refresh_report_ref=str(wrapper_report_path),
            manifest_status=wrapper_report.manifest_status,
            source_hash_gate_status=wrapper_report.source_hash_gate_status,
            snapshot_gate_status=wrapper_report.snapshot_gate_status,
            local_fixture_update_performed=verified,
            rollback_performed=not verified,
            generated_at=generated_at,
            required_next_actions=(
                [
                    "Checked recipe proof fixture was refreshed and verified by UI wrapper Rust gates."
                ]
                if verified
                else [
                    "Inspect wrapper refresh and Rust gate reports before relying on the recipe proof fixture."
                ]
            ),
        )
        write_json(report_path, report.model_dump(mode="json"))
        return report, report_path
    except Exception as exc:
        _restore_files(old_files)
        report = _report(
            status="ui_demo_qa_recipe_fixture_refresh_failed",
            source=source,
            source_status="load_or_validation_failed",
            fixtures=fixtures,
            target=target,
            old_target_sha256=old_target_sha256,
            new_target_sha256=None,
            source_sha256=source_sha256,
            sanitized_replacement_count=0,
            forbidden_path_leak_count=0,
            blocked_side_effect_count=0,
            wrapper_refresh_status="not_run",
            wrapper_refresh_report_ref=None,
            manifest_status="not_run",
            source_hash_gate_status="not_run",
            snapshot_gate_status="not_run",
            local_fixture_update_performed=False,
            rollback_performed=True,
            generated_at=generated_at,
            required_next_actions=[
                f"Recipe proof fixture refresh failed before wrapper gates: {exc}"
            ],
        )
        write_json(report_path, report.model_dump(mode="json"))
        return report, report_path


def _report(
    *,
    status: str,
    source: Path,
    source_status: str,
    fixtures: Path,
    target: Path,
    old_target_sha256: str | None,
    new_target_sha256: str | None,
    source_sha256: str | None,
    sanitized_replacement_count: int,
    forbidden_path_leak_count: int,
    blocked_side_effect_count: int,
    wrapper_refresh_status: str,
    wrapper_refresh_report_ref: str | None,
    manifest_status: str,
    source_hash_gate_status: str,
    snapshot_gate_status: str,
    local_fixture_update_performed: bool,
    rollback_performed: bool,
    generated_at: str | None,
    required_next_actions: list[str],
) -> UIDemoQARecipeFixtureRefreshReport:
    report_core = {
        "status": status,
        "source_recipe_report_ref": str(source),
        "target_fixture_ref": str(target),
        "new_target_sha256": new_target_sha256,
        "wrapper_refresh_status": wrapper_refresh_status,
    }
    return UIDemoQARecipeFixtureRefreshReport(
        ui_demo_qa_recipe_fixture_refresh_report_id="ui_demo_qa_recipe_fixture_refresh_"
        + digest_json(report_core).removeprefix("sha256:")[:16],
        status=status,  # type: ignore[arg-type]
        source_recipe_report_ref=str(source),
        source_recipe_status=source_status,
        fixtures_root_ref=str(fixtures),
        target_fixture_ref=str(target),
        old_target_sha256=old_target_sha256,
        new_target_sha256=new_target_sha256,
        source_sha256=source_sha256,
        sanitized_replacement_count=sanitized_replacement_count,
        forbidden_path_leak_count=forbidden_path_leak_count,
        blocked_side_effect_count=blocked_side_effect_count,
        wrapper_refresh_status=wrapper_refresh_status,
        wrapper_refresh_report_ref=wrapper_refresh_report_ref,
        manifest_status=manifest_status,
        source_hash_gate_status=source_hash_gate_status,
        snapshot_gate_status=snapshot_gate_status,
        local_fixture_update_performed=local_fixture_update_performed,
        rollback_performed=rollback_performed,
        required_next_actions=required_next_actions,
        generated_at=generated_at or now_iso(),
    )


def _replacement_pairs(
    payload: dict[str, Any], *, source: Path, fixtures: Path
) -> list[tuple[str, str]]:
    pairs: list[tuple[str, str]] = []
    for field, placeholder in _PATH_PLACEHOLDER_FIELDS.items():
        value = payload.get(field)
        if isinstance(value, str):
            pairs.extend((variant, placeholder) for variant in _path_variants(value))
    pairs.extend(
        (variant, "<demo-recipe-out-dir>") for variant in _path_variants(str(source.parent))
    )
    pairs.extend(
        (variant, "apps/legal-intake-budget/src/fixtures")
        for variant in _path_variants(str(fixtures))
    )
    unique: dict[str, str] = {}
    for raw, placeholder in pairs:
        if raw and "<" not in raw and ">" not in raw:
            unique[raw] = placeholder
    return sorted(unique.items(), key=lambda item: len(item[0]), reverse=True)


def _path_variants(value: str) -> set[str]:
    variants = {value, value.replace("\\", "/"), value.replace("/", "\\")}
    try:
        path = Path(value)
        variants.update({str(path), path.as_posix()})
        resolved = path.resolve()
        variants.update({str(resolved), resolved.as_posix()})
    except OSError:
        pass
    return variants


def _sanitize_value(value: Any, *, replacements: list[tuple[str, str]]) -> tuple[Any, int]:
    if isinstance(value, dict):
        output = {}
        count = 0
        for key, child in value.items():
            sanitized, child_count = _sanitize_value(child, replacements=replacements)
            output[key] = sanitized
            count += child_count
        return output, count
    if isinstance(value, list):
        output_list = []
        count = 0
        for child in value:
            sanitized, child_count = _sanitize_value(child, replacements=replacements)
            output_list.append(sanitized)
            count += child_count
        return output_list, count
    if isinstance(value, str):
        output = value
        count = 0
        for raw, placeholder in replacements:
            if raw in output:
                replacement_count = output.count(raw)
                output = output.replace(raw, placeholder)
                count += replacement_count
        return output, count
    return value, 0


def _forbidden_path_leak_count(value: Any, *, replacements: list[tuple[str, str]]) -> int:
    if isinstance(value, dict):
        return sum(
            _forbidden_path_leak_count(child, replacements=replacements) for child in value.values()
        )
    if isinstance(value, list):
        return sum(_forbidden_path_leak_count(child, replacements=replacements) for child in value)
    if isinstance(value, str):
        raw_leaks = sum(1 for raw, _placeholder in replacements if raw and raw in value)
        generated_leaks = int(".lawfirm-os-intake" in value)
        temp_leaks = int("AppData\\Local\\Temp" in value or "AppData/Local/Temp" in value)
        return raw_leaks + generated_leaks + temp_leaks
    return 0


def _blocked_side_effect_count(value: Any) -> int:
    if isinstance(value, dict):
        count = sum(
            1 for key, child in value.items() if key in _PROHIBITED_TRUE_KEYS and child is True
        )
        return count + sum(_blocked_side_effect_count(child) for child in value.values())
    if isinstance(value, list):
        return sum(_blocked_side_effect_count(child) for child in value)
    return 0


def _sanitized_recipe_report_id(payload: dict[str, Any]) -> str:
    report_core = {
        "status": payload.get("status"),
        "steps": [
            {
                "step_id": step.get("step_id"),
                "status": step.get("status"),
                "observed_status": step.get("observed_status"),
            }
            for step in payload.get("steps", [])
            if isinstance(step, dict)
        ],
        "final_run_root_ref": payload.get("final_run_root_ref"),
        "fixtures_root_ref": payload.get("fixtures_root_ref"),
    }
    return "ui_demo_qa_recipe_" + digest_json(report_core).removeprefix("sha256:")[:16]


def _snapshot_files(paths: list[Path]) -> dict[Path, bytes | None]:
    return {path: path.read_bytes() if path.is_file() else None for path in paths}


def _restore_files(snapshot: dict[Path, bytes | None]) -> None:
    for path, content in snapshot.items():
        if content is None:
            if path.exists():
                path.unlink()
            continue
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)


def _sha256_file(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()
