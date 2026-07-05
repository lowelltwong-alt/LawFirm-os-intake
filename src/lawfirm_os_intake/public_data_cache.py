from __future__ import annotations

from hashlib import sha256
import json
from pathlib import Path
from typing import Any

import yaml

from .models import (
    PublicDataCacheAuditCheck,
    PublicDataCacheAuditReport,
    PublicDataCacheSourceManifest,
    RustPublicDataCacheCustodyReport,
)
from .public_data import (
    PUBLIC_DATA_CATALOG_REF,
    PUBLIC_DATA_POLICY_REF,
    validate_public_data_boundary,
)
from .util import new_id, now_iso, write_json
from .rust_public_data_cache_custody import run_rust_public_data_cache_custody_check


PUBLIC_DATA_CACHE_MANIFEST_FILENAME = "public_data_cache_manifest.json"
PUBLIC_DATA_CACHE_AUDIT_REPORT_FILENAME = "public_data_cache_audit_report.json"
PUBLIC_DATA_CACHE_AUDIT_NOTES_FILENAME = "public_data_cache_audit_report.md"

IGNORED_IN_REPO_CACHE_REF = ".lawfirm-os-intake/public-data-cache"

REQUIRED_NEXT_GATES = [
    "human_public_data_cache_review",
    "source_license_review",
    "privacy_review",
    "retention_decision",
    "public_source_methodology_review",
    "synthetic_fixture_generation_review",
    "owner_approval_before_adapter",
]


def _is_relative_to(path: Path, parent: Path) -> bool:
    try:
        path.relative_to(parent)
    except ValueError:
        return False
    return True


def _path_ref(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return str(path)


def _load_catalog_source_ids(repo_root: Path) -> set[str]:
    catalog_path = repo_root / PUBLIC_DATA_CATALOG_REF
    payload = yaml.safe_load(catalog_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        return set()
    sources = payload.get("sources")
    if not isinstance(sources, list):
        return set()
    return {
        str(source.get("source_id"))
        for source in sources
        if isinstance(source, dict) and source.get("source_id")
    }


def _load_manifest_entries(manifest_path: Path) -> tuple[list[dict[str, Any]], str | None]:
    if not manifest_path.is_file():
        return [], "manifest_missing"
    try:
        payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return [], "manifest_not_parseable_json"
    if isinstance(payload, list):
        raw_entries = payload
    elif isinstance(payload, dict):
        raw_entries = payload.get("sources", [])
    else:
        return [], "manifest_root_not_list_or_mapping"
    if not isinstance(raw_entries, list):
        return [], "manifest_sources_not_list"
    entries = [entry for entry in raw_entries if isinstance(entry, dict)]
    if len(entries) != len(raw_entries):
        return entries, "manifest_contains_non_mapping_entries"
    return entries, None


def _allowed_in_repo_cache_root(repo_root: Path, cache_root: Path) -> bool:
    if not _is_relative_to(cache_root, repo_root):
        return True
    cache_rel = cache_root.relative_to(repo_root).as_posix()
    return cache_rel == IGNORED_IN_REPO_CACHE_REF or cache_rel.startswith(
        f"{IGNORED_IN_REPO_CACHE_REF}/"
    )


def _resolve_cache_file(cache_root: Path, cache_ref: str) -> Path:
    return (cache_root / cache_ref).resolve()


def _hash_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_public_data_cache_audit_report(
    *,
    repo_root: str | Path,
    cache_root: str | Path,
    manifest_path: str | Path | None = None,
    rust_custody_report: RustPublicDataCacheCustodyReport | None = None,
    rust_custody_report_path: str | Path | None = None,
) -> PublicDataCacheAuditReport:
    root = Path(repo_root).resolve()
    cache = Path(cache_root).resolve()
    manifest = (
        Path(manifest_path).resolve()
        if manifest_path
        else cache / PUBLIC_DATA_CACHE_MANIFEST_FILENAME
    )
    catalog_source_ids = _load_catalog_source_ids(root)
    boundary_ok, boundary_details = validate_public_data_boundary(root)
    raw_entries, manifest_error = _load_manifest_entries(manifest)
    rust_custody_status = rust_custody_report.status if rust_custody_report else "not_run"
    rust_custody_failure_count = rust_custody_report.failure_count if rust_custody_report else 0
    rust_custody_report_ref = (
        _path_ref(Path(rust_custody_report_path).resolve(), root)
        if rust_custody_report_path
        else None
    )

    sources: list[PublicDataCacheSourceManifest] = []
    invalid_manifest_refs: list[str] = []
    for index, entry in enumerate(raw_entries):
        try:
            sources.append(PublicDataCacheSourceManifest.model_validate(entry))
        except ValueError:
            source_id = str(entry.get("source_id", f"entry-{index}"))
            invalid_manifest_refs.append(source_id)

    unknown_source_ids = sorted(
        {source.source_id for source in sources if source.source_id not in catalog_source_ids}
    )
    missing_cache_file_source_ids: list[str] = []
    failed_hash_source_ids: list[str] = []
    blocked_path_refs: list[str] = []
    present_sample_source_ids: list[str] = []
    total_bytes = 0

    cache_root_allowed = _allowed_in_repo_cache_root(root, cache)
    manifest_allowed = not _is_relative_to(manifest, root) or _allowed_in_repo_cache_root(
        root, manifest.parent
    )
    for source in sources:
        cache_file = _resolve_cache_file(cache, source.cache_ref)
        if not _is_relative_to(cache_file, cache):
            blocked_path_refs.append(_path_ref(cache_file, root))
            continue
        if _is_relative_to(cache_file, root) and not _allowed_in_repo_cache_root(
            root, cache_file.parent
        ):
            blocked_path_refs.append(_path_ref(cache_file, root))
            continue
        if not cache_file.is_file():
            missing_cache_file_source_ids.append(source.source_id)
            continue
        present_sample_source_ids.append(source.source_id)
        total_bytes += cache_file.stat().st_size
        actual_hash = _hash_file(cache_file)
        expected_hash = source.sha256.removeprefix("sha256:").lower()
        if actual_hash != expected_hash or cache_file.stat().st_size != source.byte_count:
            failed_hash_source_ids.append(source.source_id)

    checks = [
        PublicDataCacheAuditCheck(
            check_id="public_data_boundary_passes",
            status="passed" if boundary_ok else "failed",
            message=(
                "Metadata-only public catalog and synthetic-only data policy still pass."
                if boundary_ok
                else "Public data boundary failed: "
                + ", ".join(boundary_details.get("failures", []))
            ),
        ),
        PublicDataCacheAuditCheck(
            check_id="cache_root_is_ignored_or_external",
            status="passed" if cache_root_allowed and manifest_allowed else "blocked",
            message=(
                "Cache root is either outside the repo or under the ignored public-data cache."
                if cache_root_allowed and manifest_allowed
                else "Cache root or manifest path resolves into tracked repo payload space."
            ),
            path_refs=[
                _path_ref(cache, root),
                _path_ref(manifest, root),
            ],
        ),
        PublicDataCacheAuditCheck(
            check_id="rust_public_data_cache_custody_passes",
            status="passed" if rust_custody_status == "passed" else "failed",
            message=(
                "Rust public-data cache custody checker passed local path, presence, hash, and byte-count gates."
                if rust_custody_status == "passed"
                else (
                    "Rust public-data cache custody checker did not pass; "
                    f"status={rust_custody_status}, failures={rust_custody_failure_count}."
                )
            ),
            path_refs=[rust_custody_report_ref] if rust_custody_report_ref else [],
        ),
        PublicDataCacheAuditCheck(
            check_id="manifest_present_and_parseable",
            status="passed" if manifest_error is None else "failed",
            message=(
                "Public data cache manifest was present and parseable."
                if manifest_error is None
                else f"Public data cache manifest failed: {manifest_error}."
            ),
            path_refs=[_path_ref(manifest, root)],
        ),
        PublicDataCacheAuditCheck(
            check_id="manifest_entries_schema_valid",
            status="passed" if not invalid_manifest_refs else "failed",
            message=(
                "Every cache manifest entry has required source, hash, license, use, and retention fields."
                if not invalid_manifest_refs
                else "At least one cache manifest entry is not schema-valid."
            ),
            source_ids=sorted(invalid_manifest_refs),
        ),
        PublicDataCacheAuditCheck(
            check_id="manifest_sources_are_cataloged",
            status="passed" if not unknown_source_ids else "blocked",
            message=(
                "Every cache manifest source_id exists in the planning-only public source catalog."
                if not unknown_source_ids
                else "At least one cache manifest source_id is not cataloged."
            ),
            source_ids=unknown_source_ids,
        ),
        PublicDataCacheAuditCheck(
            check_id="cache_refs_stay_under_cache_root",
            status="passed" if not blocked_path_refs else "blocked",
            message=(
                "Every cache_ref resolves under the approved cache root and outside tracked payload paths."
                if not blocked_path_refs
                else "At least one cache_ref resolves outside the approved cache root or into tracked payload paths."
            ),
            path_refs=sorted(blocked_path_refs),
        ),
        PublicDataCacheAuditCheck(
            check_id="cache_files_present",
            status="passed" if not missing_cache_file_source_ids else "blocked",
            message=(
                "Every manifest entry has a local cache file for deterministic methodology review."
                if not missing_cache_file_source_ids
                else "At least one manifest entry is missing its local cache file."
            ),
            source_ids=sorted(missing_cache_file_source_ids),
        ),
        PublicDataCacheAuditCheck(
            check_id="cache_hashes_and_sizes_match",
            status="passed" if not failed_hash_source_ids else "failed",
            message=(
                "Every local cache file matches its manifest SHA-256 digest and byte count."
                if not failed_hash_source_ids
                else "At least one local cache file failed SHA-256 or byte-count validation."
            ),
            source_ids=sorted(failed_hash_source_ids),
        ),
        PublicDataCacheAuditCheck(
            check_id="no_runtime_ingestion_or_external_authority",
            status="passed",
            message=(
                "The cache audit authorizes no runtime ingestion, adapter, fixture creation, "
                "Lake/SQLite write, production connector, or external write."
            ),
        ),
        PublicDataCacheAuditCheck(
            check_id="human_review_required_before_conversion",
            status="passed",
            message=(
                "A passing cache audit is only ready for human public-data cache review before "
                "methodology/conversion review can produce synthetic fixtures."
            ),
        ),
    ]
    status = (
        "ready_for_human_public_data_cache_review"
        if all(check.status == "passed" for check in checks)
        else "blocked_public_data_cache"
    )
    return PublicDataCacheAuditReport(
        public_data_cache_audit_report_id=new_id("publicdatacacheaudit"),
        status=status,  # type: ignore[arg-type]
        source_catalog_ref=PUBLIC_DATA_CATALOG_REF,
        data_policy_ref=PUBLIC_DATA_POLICY_REF,
        cache_root_ref=_path_ref(cache, root),
        manifest_ref=_path_ref(manifest, root),
        manifest_entry_count=len(raw_entries),
        valid_manifest_entry_count=len(sources),
        cache_sample_count=len(present_sample_source_ids),
        total_cache_sample_bytes=total_bytes,
        approved_source_ids=sorted(catalog_source_ids),
        unknown_source_ids=unknown_source_ids,
        failed_hash_source_ids=sorted(failed_hash_source_ids),
        missing_cache_file_source_ids=sorted(missing_cache_file_source_ids),
        blocked_path_refs=sorted(blocked_path_refs),
        rust_custody_report_ref=rust_custody_report_ref,
        rust_custody_status=rust_custody_status,  # type: ignore[arg-type]
        rust_custody_failure_count=rust_custody_failure_count,
        rust_custody_checked_source_count=(
            rust_custody_report.checked_source_count if rust_custody_report else 0
        ),
        rust_custody_checked_sample_count=(
            rust_custody_report.checked_sample_count if rust_custody_report else 0
        ),
        rust_custody_total_checked_sample_bytes=(
            rust_custody_report.total_checked_sample_bytes if rust_custody_report else 0
        ),
        sources=sources,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        public_cache_samples_present=bool(present_sample_source_ids),
        generated_at=now_iso(),
    )


def render_public_data_cache_audit_report(report: PublicDataCacheAuditReport) -> str:
    lines = [
        "# Public Data Cache Audit Report",
        "",
        f"**Report ID:** {report.public_data_cache_audit_report_id}",
        f"**Status:** {report.status}",
        f"**Cache root:** `{report.cache_root_ref}`",
        f"**Manifest:** `{report.manifest_ref}`",
        f"**Manifest entries:** {report.manifest_entry_count}",
        f"**Cache sample count:** {report.cache_sample_count}",
        f"**Rust custody status:** {report.rust_custody_status}",
        f"**Rust custody failures:** {report.rust_custody_failure_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Planning only: {report.planning_only}",
        f"- Report payload metadata only: {report.report_payload_metadata_only}",
        f"- Public cache samples present: {report.public_cache_samples_present}",
        f"- Direct runtime ingestion allowed: {report.direct_runtime_ingestion_allowed}",
        f"- Public records runtime ingested: {report.public_records_runtime_ingested}",
        f"- Raw public payload committed: {report.raw_public_payload_committed}",
        f"- Tracked public payload committed: {report.tracked_public_payload_committed}",
        f"- Connector implemented: {report.connector_implemented}",
        f"- Legal Knowledge adapter authorized: {report.legal_knowledge_adapter_authorized}",
        f"- Synthetic fixtures created: {report.synthetic_fixtures_created}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Rust custody report: {report.rust_custody_report_ref}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in report.required_next_gates),
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.extend(
            [
                f"- `{check.check_id}`: {check.status}",
                f"  {check.message}",
            ]
        )
        if check.source_ids:
            lines.extend(f"  - source: `{source_id}`" for source_id in check.source_ids)
        if check.path_refs:
            lines.extend(f"  - path: `{path_ref}`" for path_ref in check.path_refs)
    lines.extend(["", "## Manifest Sources", ""])
    for source in report.sources:
        lines.extend(
            [
                f"- `{source.source_id}`",
                f"  Cache ref: `{source.cache_ref}`",
                f"  Source type: {source.source_type}",
                f"  SHA-256: `{source.sha256}`",
                f"  Byte count: {source.byte_count}",
                f"  Allowed use: {source.allowed_use}",
                f"  Prohibited use: {source.prohibited_use}",
                f"  Retention: {source.retention_posture}",
            ]
        )
    lines.extend(
        [
            "",
            "This report validates only local ignored-cache custody and deterministic hashes. "
            "It does not ingest public records into intake runtime, commit public payloads, "
            "authorize adapters, create fixtures, or write to the Exception Lake.",
            "",
        ]
    )
    return "\n".join(lines)


def run_public_data_cache_audit(
    *,
    repo_root: str | Path,
    cache_root: str | Path,
    out_dir: str | Path,
    manifest_path: str | Path | None = None,
    rust_timeout_seconds: int = 240,
) -> tuple[PublicDataCacheAuditReport, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    rust_custody_report, rust_custody_report_path = run_rust_public_data_cache_custody_check(
        repo_root=repo_root,
        cache_root=cache_root,
        manifest_path=manifest_path,
        out_dir=run_dir,
        timeout_seconds=rust_timeout_seconds,
    )
    report = build_public_data_cache_audit_report(
        repo_root=repo_root,
        cache_root=cache_root,
        manifest_path=manifest_path,
        rust_custody_report=rust_custody_report,
        rust_custody_report_path=rust_custody_report_path,
    )
    report_path = run_dir / PUBLIC_DATA_CACHE_AUDIT_REPORT_FILENAME
    notes_path = run_dir / PUBLIC_DATA_CACHE_AUDIT_NOTES_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_public_data_cache_audit_report(report), encoding="utf-8")
    return report, run_dir
