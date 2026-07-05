from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
import subprocess

from .models import (
    RustFixtureManifestReport,
    UIDemoFixtureRefreshDetail,
    UIDemoFixtureRefreshReport,
    UIReviewDataBundle,
)
from .rust_fixture_snapshot_coherence import run_rust_fixture_snapshot_coherence_check
from .rust_ui_bundle_source_hash import run_rust_ui_bundle_source_hash_check
from .util import digest_json, load_json, now_iso, write_json


DEMO_UI_REVIEW_DATA_BUNDLE_FILENAME = "demo-ui-review-data-bundle.json"
DEMO_RUST_FIXTURE_MANIFEST_FILENAME = "demo-rust-fixture-manifest-report.json"
RUST_FIXTURE_MANIFEST_CARGO_MANIFEST_REF = "rust/fixture-boundary-checker/Cargo.toml"
UI_DEMO_FIXTURE_REFRESH_REPORT_FILENAME = "ui_demo_fixture_refresh_report.json"


@dataclass(frozen=True)
class ResolvedDetail:
    path: Path
    strategy: str


def refresh_ui_demo_fixtures(
    *,
    fixtures_root: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    write_fixtures: bool,
    generated_at: str | None = None,
    timeout_seconds: int = 240,
) -> tuple[UIDemoFixtureRefreshReport, Path]:
    fixtures = Path(fixtures_root)
    repo = Path(repo_root).resolve()
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    report_path = out / UI_DEMO_FIXTURE_REFRESH_REPORT_FILENAME
    bundle_path = fixtures / DEMO_UI_REVIEW_DATA_BUNDLE_FILENAME
    manifest_path = fixtures / DEMO_RUST_FIXTURE_MANIFEST_FILENAME

    if not write_fixtures:
        report = _blocked_report(
            fixtures_root=fixtures,
            bundle_path=bundle_path,
            manifest_path=manifest_path,
            generated_at=generated_at,
            message="refresh-ui-demo-fixtures requires --write-fixtures.",
        )
        write_json(report_path, report.model_dump(mode="json"))
        return report, report_path

    bundle_payload = load_json(bundle_path)
    UIReviewDataBundle.model_validate(bundle_payload)
    old_bundle_id = str(bundle_payload.get("ui_review_data_bundle_id") or "")
    old_bundle_sha256 = _sha256_file(bundle_path)
    manifest_old_sha256 = _sha256_file(manifest_path) if manifest_path.is_file() else None

    details = []
    missing_count = 0
    invalid_count = 0
    update_count = 0
    unchanged_count = 0

    for detail in bundle_payload.get("detail_reports", []):
        if not detail.get("present"):
            details.append(
                _detail(
                    detail=detail,
                    status="skipped_not_present",
                    old_sha=detail.get("source_sha256"),
                    new_sha=detail.get("source_sha256"),
                )
            )
            continue
        if detail.get("file_name") == "rust_fixture_manifest_report.json":
            details.append(
                _detail(
                    detail=detail,
                    status="deferred_manifest",
                    old_sha=detail.get("source_sha256"),
                    new_sha=detail.get("source_sha256"),
                )
            )
            continue

        resolved = _resolve_detail_source(fixtures, detail)
        if resolved is None:
            missing_count += 1
            details.append(
                _detail(
                    detail=detail,
                    status="missing_source",
                    old_sha=detail.get("source_sha256"),
                    new_sha=None,
                )
            )
            continue

        new_sha = _sha256_file(resolved.path)
        old_sha = detail.get("source_sha256")
        if old_sha is not None and not _is_sha256_ref(str(old_sha)):
            invalid_count += 1
        detail["source_sha256"] = new_sha
        status = "updated" if old_sha != new_sha else "unchanged"
        update_count += int(status == "updated")
        unchanged_count += int(status == "unchanged")
        details.append(
            _detail(
                detail=detail,
                status=status,
                old_sha=old_sha,
                new_sha=new_sha,
                resolved_path=_display_path(resolved.path, fixtures),
                resolution_strategy=resolved.strategy,
            )
        )

    if missing_count:
        report = _refresh_report(
            fixtures_root=fixtures,
            bundle_path=bundle_path,
            manifest_path=manifest_path,
            old_bundle_id=old_bundle_id,
            new_bundle_id=old_bundle_id,
            old_bundle_sha256=old_bundle_sha256,
            new_bundle_sha256=old_bundle_sha256,
            manifest_old_sha256=manifest_old_sha256,
            manifest_new_sha256=manifest_old_sha256,
            details=details,
            source_hash_update_count=update_count,
            source_hash_unchanged_count=unchanged_count,
            missing_source_count=missing_count,
            invalid_existing_hash_count=invalid_count,
            manifest_status="not_run",
            source_hash_gate_status="not_run",
            snapshot_gate_status="not_run",
            local_fixture_updates_performed=False,
            generated_at=generated_at,
            status="ui_demo_fixture_refresh_failed",
            required_next_actions=[
                "Resolve missing UI detail source files before refreshing checked demo fixtures."
            ],
        )
        write_json(report_path, report.model_dump(mode="json"))
        return report, report_path

    bundle_payload["ui_review_data_bundle_id"] = _bundle_id(bundle_payload)
    write_json(bundle_path, bundle_payload)
    manifest = _run_manifest_scanner_to_fixture(
        repo=repo,
        fixtures=fixtures,
        manifest_path=manifest_path,
        timeout_seconds=timeout_seconds,
    )
    manifest_new_sha256 = _sha256_file(manifest_path)

    manifest_detail = _find_detail(bundle_payload, "rust_fixture_manifest_report.json")
    if manifest_detail is not None:
        old_sha = manifest_detail.get("source_sha256")
        manifest_detail["source_sha256"] = manifest_new_sha256
        status = "updated" if old_sha != manifest_new_sha256 else "unchanged"
        update_count += int(status == "updated")
        unchanged_count += int(status == "unchanged")
        details = [
            item for item in details if item.file_name != "rust_fixture_manifest_report.json"
        ]
        details.append(
            _detail(
                detail=manifest_detail,
                status=status,
                old_sha=old_sha,
                new_sha=manifest_new_sha256,
                resolved_path=DEMO_RUST_FIXTURE_MANIFEST_FILENAME,
                resolution_strategy="refreshed_manifest",
            )
        )

    new_bundle_id = _bundle_id(bundle_payload)
    bundle_payload["ui_review_data_bundle_id"] = new_bundle_id
    if generated_at is not None:
        bundle_payload["generated_at"] = generated_at
    write_json(bundle_path, bundle_payload)
    new_bundle_sha256 = _sha256_file(bundle_path)

    source_hash_gate, _source_hash_gate_path = run_rust_ui_bundle_source_hash_check(
        root=fixtures,
        bundle=bundle_path,
        out_dir=out / "rust-ui-bundle-source-hash",
        repo_root=repo,
        timeout_seconds=timeout_seconds,
    )
    snapshot_gate, _snapshot_gate_path = run_rust_fixture_snapshot_coherence_check(
        root=fixtures,
        expected_manifest=manifest_path,
        out_dir=out / "rust-fixture-snapshot-coherence",
        repo_root=repo,
        timeout_seconds=timeout_seconds,
    )

    status = (
        "ui_demo_fixture_refresh_verified"
        if (
            manifest.status == "passed"
            and source_hash_gate.status == "passed"
            and snapshot_gate.status == "passed"
        )
        else "ui_demo_fixture_refresh_failed"
    )
    required_next_actions = (
        [
            "UI demo fixture wrappers are refreshed and verified by Rust source-hash and snapshot-coherence gates."
        ]
        if status == "ui_demo_fixture_refresh_verified"
        else ["Inspect failed Rust gate reports before relying on checked UI demo fixtures."]
    )
    report = _refresh_report(
        fixtures_root=fixtures,
        bundle_path=bundle_path,
        manifest_path=manifest_path,
        old_bundle_id=old_bundle_id,
        new_bundle_id=new_bundle_id,
        old_bundle_sha256=old_bundle_sha256,
        new_bundle_sha256=new_bundle_sha256,
        manifest_old_sha256=manifest_old_sha256,
        manifest_new_sha256=manifest_new_sha256,
        details=details,
        source_hash_update_count=update_count,
        source_hash_unchanged_count=unchanged_count,
        missing_source_count=missing_count,
        invalid_existing_hash_count=invalid_count,
        manifest_status=manifest.status,
        source_hash_gate_status=source_hash_gate.status,
        snapshot_gate_status=snapshot_gate.status,
        local_fixture_updates_performed=True,
        generated_at=generated_at,
        status=status,
        required_next_actions=required_next_actions,
    )
    write_json(report_path, report.model_dump(mode="json"))
    return report, report_path


def _run_manifest_scanner_to_fixture(
    *,
    repo: Path,
    fixtures: Path,
    manifest_path: Path,
    timeout_seconds: int,
) -> RustFixtureManifestReport:
    command = [
        "cargo",
        "run",
        "--quiet",
        "--manifest-path",
        str(repo / RUST_FIXTURE_MANIFEST_CARGO_MANIFEST_REF),
        "--bin",
        "fixture_manifest_scanner",
        "--",
        "--root",
        str(fixtures),
        "--out",
        str(manifest_path),
    ]
    completed = subprocess.run(
        command,
        cwd=repo,
        check=False,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout_seconds,
    )
    if not manifest_path.is_file():
        raise RuntimeError(
            "Rust fixture manifest scanner did not emit checked demo manifest; "
            f"return_code={completed.returncode}; stderr={completed.stderr.strip()}"
        )
    manifest = RustFixtureManifestReport.model_validate(load_json(manifest_path))
    if completed.returncode != 0 and manifest.status == "passed":
        raise RuntimeError(
            f"Rust fixture manifest scanner returned {completed.returncode} but report passed."
        )
    return manifest


def _resolve_detail_source(fixtures: Path, detail: dict) -> ResolvedDetail | None:
    artifact_ref = str(detail.get("artifact_ref") or "")
    if artifact_ref and "<" not in artifact_ref and ">" not in artifact_ref:
        candidate = Path(artifact_ref)
        candidates = [candidate] if candidate.is_absolute() else [fixtures / candidate, candidate]
        for item in candidates:
            if item.is_file() and _is_under_root(item, fixtures):
                return ResolvedDetail(path=item, strategy="artifact_ref")

    file_name = str(detail.get("file_name") or "")
    for candidate in [
        fixtures / file_name,
        fixtures / "budget" / file_name,
        fixtures / "quality" / file_name,
        fixtures / "qa" / file_name,
    ]:
        if candidate.is_file():
            return ResolvedDetail(path=candidate, strategy="run_root_file_name")

    demo_name = _demo_fixture_name(file_name)
    if demo_name:
        candidate = fixtures / demo_name
        if candidate.is_file():
            return ResolvedDetail(path=candidate, strategy="demo_fixture_name")
    return None


def _find_detail(bundle_payload: dict, file_name: str) -> dict | None:
    for detail in bundle_payload.get("detail_reports", []):
        if detail.get("file_name") == file_name:
            return detail
    return None


def _bundle_id(bundle_payload: dict) -> str:
    report_core = {
        "status": bundle_payload.get("status"),
        "run_root_ref": bundle_payload.get("run_root_ref"),
        "detail_reports": [
            {
                "detail_report_id": detail.get("detail_report_id"),
                "present": detail.get("present"),
                "source_sha256": detail.get("source_sha256"),
                "external_writes_performed": detail.get("external_writes_performed"),
            }
            for detail in bundle_payload.get("detail_reports", [])
        ],
    }
    return "ui_review_data_bundle_" + digest_json(report_core)[len("sha256:") : len("sha256:") + 12]


def _demo_fixture_name(file_name: str) -> str | None:
    if file_name == "ui_review_manifest.json":
        return "demo-run-manifest.json"
    if not file_name.endswith(".json"):
        return None
    return "demo-" + file_name[:-5].replace("_", "-") + ".json"


def _sha256_file(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _is_sha256_ref(value: str) -> bool:
    return (
        len(value) == len("sha256:") + 64
        and value.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in value[len("sha256:") :])
    )


def _is_under_root(candidate: Path, root: Path) -> bool:
    try:
        return candidate.resolve().is_relative_to(root.resolve())
    except OSError:
        return False


def _display_path(path: Path, root: Path) -> str:
    return str(path.relative_to(root) if path.is_relative_to(root) else path).replace("\\", "/")


def _detail(
    *,
    detail: dict,
    status: str,
    old_sha: str | None,
    new_sha: str | None,
    resolved_path: str | None = None,
    resolution_strategy: str | None = None,
) -> UIDemoFixtureRefreshDetail:
    return UIDemoFixtureRefreshDetail(
        detail_report_id=str(detail.get("detail_report_id") or ""),
        report_kind=str(detail.get("report_kind") or ""),
        file_name=str(detail.get("file_name") or ""),
        old_source_sha256=old_sha,
        new_source_sha256=new_sha,
        resolved_path=resolved_path,
        resolution_strategy=resolution_strategy,
        status=status,
    )


def _blocked_report(
    *,
    fixtures_root: Path,
    bundle_path: Path,
    manifest_path: Path,
    generated_at: str | None,
    message: str,
) -> UIDemoFixtureRefreshReport:
    return _refresh_report(
        fixtures_root=fixtures_root,
        bundle_path=bundle_path,
        manifest_path=manifest_path,
        old_bundle_id=None,
        new_bundle_id=None,
        old_bundle_sha256=None,
        new_bundle_sha256=None,
        manifest_old_sha256=None,
        manifest_new_sha256=None,
        details=[],
        source_hash_update_count=0,
        source_hash_unchanged_count=0,
        missing_source_count=0,
        invalid_existing_hash_count=0,
        manifest_status="not_run",
        source_hash_gate_status="not_run",
        snapshot_gate_status="not_run",
        local_fixture_updates_performed=False,
        generated_at=generated_at,
        status="ui_demo_fixture_refresh_blocked_write_flag_required",
        required_next_actions=[message],
    )


def _refresh_report(
    *,
    fixtures_root: Path,
    bundle_path: Path,
    manifest_path: Path,
    old_bundle_id: str | None,
    new_bundle_id: str | None,
    old_bundle_sha256: str | None,
    new_bundle_sha256: str | None,
    manifest_old_sha256: str | None,
    manifest_new_sha256: str | None,
    details: list[UIDemoFixtureRefreshDetail],
    source_hash_update_count: int,
    source_hash_unchanged_count: int,
    missing_source_count: int,
    invalid_existing_hash_count: int,
    manifest_status: str,
    source_hash_gate_status: str,
    snapshot_gate_status: str,
    local_fixture_updates_performed: bool,
    generated_at: str | None,
    status: str,
    required_next_actions: list[str],
) -> UIDemoFixtureRefreshReport:
    return UIDemoFixtureRefreshReport(
        status=status,
        fixtures_root_ref=str(fixtures_root),
        ui_bundle_ref=str(bundle_path),
        manifest_ref=str(manifest_path),
        old_ui_review_data_bundle_id=old_bundle_id,
        new_ui_review_data_bundle_id=new_bundle_id,
        old_ui_bundle_sha256=old_bundle_sha256,
        new_ui_bundle_sha256=new_bundle_sha256,
        old_manifest_sha256=manifest_old_sha256,
        new_manifest_sha256=manifest_new_sha256,
        detail_report_count=len(details),
        source_hash_update_count=source_hash_update_count,
        source_hash_unchanged_count=source_hash_unchanged_count,
        missing_source_count=missing_source_count,
        invalid_existing_hash_count=invalid_existing_hash_count,
        manifest_status=manifest_status,
        source_hash_gate_status=source_hash_gate_status,
        snapshot_gate_status=snapshot_gate_status,
        local_fixture_updates_performed=local_fixture_updates_performed,
        details=details,
        required_next_actions=required_next_actions,
        generated_at=generated_at or now_iso(),
    )
