from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    PublicSourceMethodologyCheck,
    PublicSourceMethodologyReport,
    PublicSourceMethodologySource,
)
from .public_data import (
    FORBIDDEN_CATALOG_FIELDS,
    PUBLIC_DATA_CATALOG_REF,
    PUBLIC_DATA_POLICY_REF,
    validate_public_data_boundary,
)
from .util import new_id, now_iso, write_json


PUBLIC_SOURCE_METHODOLOGY_REPORT_FILENAME = "public_source_methodology_report.json"
PUBLIC_SOURCE_METHODOLOGY_NOTES_FILENAME = "public_source_methodology_report.md"

REQUIRED_PHASE_2_SOURCE_IDS = [
    "courtlistener-recap",
    "fjc-idb",
    "cmu-enron-email",
]

REQUIRED_METHOD_FIELDS = [
    "methodology_role",
    "safe_use_classes",
    "prohibited_use_classes",
    "review_requirements",
    "synthetic_conversion_rules",
    "retention_policy",
    "privacy_posture",
    "adapter_status",
]

REQUIRED_REVIEW_GATES = {
    "source_license_review",
    "privacy_review",
    "retention_decision",
    "owner_approval_before_adapter",
    "no_raw_payload_commit",
}

REQUIRED_NEXT_GATES = [
    "human_public_source_methodology_review",
    "source_license_review",
    "privacy_review",
    "retention_decision",
    "synthetic_fixture_generation_review",
    "owner_approval_before_adapter",
]


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected YAML mapping: {path}")
    return payload


def _list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _source_from_catalog_entry(source: dict[str, Any]) -> PublicSourceMethodologySource:
    source_id = str(source.get("source_id", "unknown"))
    blocking_reasons: list[str] = []
    missing_fields = [
        field
        for field in REQUIRED_METHOD_FIELDS
        if field not in source or source.get(field) in (None, "", [])
    ]
    if missing_fields:
        blocking_reasons.extend(f"missing_methodology_field:{field}" for field in missing_fields)
    review_requirements = _list(source.get("review_requirements"))
    missing_review_gates = sorted(REQUIRED_REVIEW_GATES - set(review_requirements))
    if missing_review_gates:
        blocking_reasons.extend(f"missing_review_gate:{gate}" for gate in missing_review_gates)
    if source.get("direct_runtime_ingestion") is not False:
        blocking_reasons.append("direct_runtime_ingestion_not_false")
    if source.get("adapter_status") != "not_authorized":
        blocking_reasons.append("adapter_status_not_not_authorized")
    if FORBIDDEN_CATALOG_FIELDS.intersection(source):
        blocking_reasons.append("source_contains_payload_field")

    status = "blocked" if blocking_reasons else "ready_for_human_methodology_review"
    return PublicSourceMethodologySource(
        source_id=source_id,
        url=str(source.get("url", "")),
        methodology_role=str(source.get("methodology_role", "")),
        useful_for=_list(source.get("useful_for")),
        safe_use_classes=_list(source.get("safe_use_classes")),
        prohibited_use_classes=_list(source.get("prohibited_use_classes")),
        review_requirements=review_requirements,
        synthetic_conversion_rules=_list(source.get("synthetic_conversion_rules")),
        retention_policy=str(source.get("retention_policy", "")),
        privacy_posture=str(source.get("privacy_posture", "")),
        adapter_status=str(source.get("adapter_status", "")),
        direct_runtime_ingestion=bool(source.get("direct_runtime_ingestion", False)),
        status=status,  # type: ignore[arg-type]
        blocking_reasons=blocking_reasons,
    )


def build_public_source_methodology_report(
    *,
    repo_root: str | Path,
) -> PublicSourceMethodologyReport:
    root = Path(repo_root)
    catalog_path = root / PUBLIC_DATA_CATALOG_REF
    policy_path = root / PUBLIC_DATA_POLICY_REF
    catalog = _load_yaml(catalog_path)
    policy = _load_yaml(policy_path)
    boundary_ok, boundary_details = validate_public_data_boundary(root)
    sources_payload = catalog.get("sources")
    if not isinstance(sources_payload, list):
        sources_payload = []
    raw_sources = [source for source in sources_payload if isinstance(source, dict)]
    source_ids = {str(source.get("source_id", "")) for source in raw_sources}
    missing_required = sorted(set(REQUIRED_PHASE_2_SOURCE_IDS) - source_ids)
    sources = [_source_from_catalog_entry(source) for source in raw_sources]
    blocked_source_ids = [source.source_id for source in sources if source.status == "blocked"]

    checks = [
        PublicSourceMethodologyCheck(
            check_id="public_data_boundary_passes",
            status="passed" if boundary_ok else "failed",
            message=(
                "Existing metadata-only public data boundary passes."
                if boundary_ok
                else "Existing public data boundary failed: "
                + ", ".join(boundary_details.get("failures", []))
            ),
        ),
        PublicSourceMethodologyCheck(
            check_id="phase_2_required_sources_present",
            status="passed" if not missing_required else "blocked",
            message=(
                "CourtListener/RECAP, FJC IDB, and Enron structural sources are cataloged."
                if not missing_required
                else "Phase 2 required public methodology sources are missing."
            ),
            source_ids=missing_required,
        ),
        PublicSourceMethodologyCheck(
            check_id="catalog_sources_have_methodology_controls",
            status="passed" if not blocked_source_ids else "blocked",
            message=(
                "Every public source has methodology role, safe/prohibited use, review gates, "
                "synthetic conversion, retention, privacy, and adapter authorization fields."
                if not blocked_source_ids
                else "At least one public source is missing methodology controls."
            ),
            source_ids=blocked_source_ids,
        ),
        PublicSourceMethodologyCheck(
            check_id="policy_remains_synthetic_only",
            status="passed"
            if policy.get("runtime_mode") == "synthetic_only"
            and set(policy.get("allowed_data_origins", [])) == {"synthetic"}
            else "failed",
            message="Policy runtime mode remains synthetic-only with no public runtime origin.",
        ),
        PublicSourceMethodologyCheck(
            check_id="no_public_adapter_or_payload_authorized",
            status="passed",
            message=(
                "The methodology audit records no connector, no public-record ingestion, "
                "no raw payload commit, and no Legal Knowledge adapter authorization."
            ),
        ),
    ]
    status = (
        "ready_for_human_public_source_methodology_review"
        if all(check.status == "passed" for check in checks)
        else "blocked_public_source_methodology"
    )

    return PublicSourceMethodologyReport(
        public_source_methodology_report_id=new_id("publicsourcemethodology"),
        status=status,  # type: ignore[arg-type]
        source_catalog_ref=PUBLIC_DATA_CATALOG_REF,
        data_policy_ref=PUBLIC_DATA_POLICY_REF,
        source_count=len(sources),
        required_source_ids=REQUIRED_PHASE_2_SOURCE_IDS,
        missing_required_source_ids=missing_required,
        sources=sources,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_public_source_methodology_report(report: PublicSourceMethodologyReport) -> str:
    lines = [
        "# Public Source Methodology Report",
        "",
        f"**Report ID:** {report.public_source_methodology_report_id}",
        f"**Status:** {report.status}",
        f"**Source count:** {report.source_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Planning only: {report.planning_only}",
        f"- Metadata only: {report.metadata_only}",
        f"- Direct runtime ingestion allowed: {report.direct_runtime_ingestion_allowed}",
        f"- Public records ingested: {report.public_records_ingested}",
        f"- Raw public payload committed: {report.raw_public_payload_committed}",
        f"- Connector implemented: {report.connector_implemented}",
        f"- Legal Knowledge adapter authorized: {report.legal_knowledge_adapter_authorized}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
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
            lines.extend(f"  - {source_id}" for source_id in check.source_ids)
    lines.extend(["", "## Sources", ""])
    for source in report.sources:
        lines.extend(
            [
                f"- `{source.source_id}`: {source.status}",
                f"  Role: {source.methodology_role}",
                f"  Adapter status: {source.adapter_status}",
                f"  Retention: {source.retention_policy}",
                "  Safe uses:",
                *(f"  - {item}" for item in source.safe_use_classes),
                "  Prohibited uses:",
                *(f"  - {item}" for item in source.prohibited_use_classes),
            ]
        )
        if source.blocking_reasons:
            lines.extend(["  Blockers:", *(f"  - {item}" for item in source.blocking_reasons)])
    lines.extend(
        [
            "",
            "This report prepares public-source methodology review only. It does not ingest "
            "public records, commit public payloads, authorize adapters, or permit runtime use.",
            "",
        ]
    )
    return "\n".join(lines)


def run_public_source_methodology_audit(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
) -> tuple[PublicSourceMethodologyReport, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report = build_public_source_methodology_report(repo_root=repo_root)
    report_path = run_dir / PUBLIC_SOURCE_METHODOLOGY_REPORT_FILENAME
    notes_path = run_dir / PUBLIC_SOURCE_METHODOLOGY_NOTES_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_public_source_methodology_report(report), encoding="utf-8")
    return report, run_dir
