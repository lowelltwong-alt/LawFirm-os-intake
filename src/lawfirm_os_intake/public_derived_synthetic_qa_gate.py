from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    PublicDataCacheAuditReport,
    PublicDerivedSyntheticQAGateCheck,
    PublicDerivedSyntheticQAGateReport,
)
from .util import load_json, new_id, now_iso, write_json


PUBLIC_DERIVED_SYNTHETIC_QA_GATE_REPORT_FILENAME = "public_derived_synthetic_qa_gate_report.json"
PUBLIC_DERIVED_SYNTHETIC_QA_GATE_NOTES_FILENAME = "public_derived_synthetic_qa_gate_report.md"

READY_METHODOLOGY_STATUS = "ready_for_human_public_source_methodology_review"
READY_CONVERSION_PLAN_STATUS = "ready_for_human_conversion_review"
READY_CONVERSION_REVIEW_STATUS = "ready_for_human_conversion_review"
READY_CACHE_AUDIT_STATUS = "ready_for_human_public_data_cache_review"

REQUIRED_NEXT_GATES = [
    "human_public_source_methodology_review",
    "human_public_synthetic_conversion_review",
    "append_only_conversion_review_outcome",
    "separate_synthetic_fixture_generation_pr_if_approved",
    "synthetic_fixture_gold_review",
    "red_team_identity_reconstruction_review",
    "public_cache_custody_review_when_samples_exist",
    "legal_knowledge_runtime_owner_review_before_adapter",
]

BASE_EXCEPTION_LABELS = [
    "public_derived_synthetic_qa_gate_candidate",
    "public_source_methodology_review_pending",
    "public_synthetic_conversion_review_pending",
    "public_payload_ingestion_blocked",
    "fixture_generation_requires_separate_review",
]

METHODOLOGY_SIDE_EFFECT_FIELDS = [
    "direct_runtime_ingestion_allowed",
    "public_records_ingested",
    "raw_public_payload_committed",
    "real_party_records_committed",
    "real_matter_records_committed",
    "connector_implemented",
    "legal_knowledge_adapter_authorized",
    "lake_write_performed",
    "sqlite_write_performed",
    "external_writes_performed",
]

CONVERSION_PLAN_SIDE_EFFECT_FIELDS = [
    "public_records_ingested",
    "raw_public_payload_committed",
    "synthetic_fixtures_created",
    "fixture_files_mutated",
    "connector_implemented",
    "legal_knowledge_adapter_authorized",
    "lake_write_performed",
    "sqlite_write_performed",
    "external_writes_performed",
]

CONVERSION_REVIEW_SIDE_EFFECT_FIELDS = [
    "public_records_ingested",
    "raw_public_payload_committed",
    "synthetic_fixtures_created",
    "fixture_files_mutated",
    "fixture_pr_created",
    "connector_implemented",
    "legal_knowledge_adapter_authorized",
    "lake_write_performed",
    "sqlite_write_performed",
    "external_writes_performed",
    "silent_learning_performed",
]

CACHE_AUDIT_SIDE_EFFECT_FIELDS = [
    "direct_runtime_ingestion_allowed",
    "public_records_runtime_ingested",
    "raw_public_payload_committed",
    "tracked_public_payload_committed",
    "real_party_records_committed",
    "real_matter_records_committed",
    "connector_implemented",
    "legal_knowledge_adapter_authorized",
    "synthetic_fixtures_created",
    "fixture_files_mutated",
    "lake_write_performed",
    "sqlite_write_performed",
    "external_writes_performed",
]


def _load_mapping(path: str | Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _dicts(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _strings(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _int(value: Any, default: int = -1) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _side_effect_failures(
    *,
    artifact_name: str,
    payload: dict[str, Any],
    fields: list[str],
) -> list[str]:
    failures: list[str] = []
    for field in fields:
        if payload.get(field) is not False:
            failures.append(f"{artifact_name}.{field}")
    return failures


def _check(
    check_id: str,
    *,
    passed: bool,
    message_passed: str,
    message_failed: str,
    failure_status: str = "failed",
    artifact_refs: list[str] | None = None,
    source_ids: list[str] | None = None,
    conversion_spec_ids: list[str] | None = None,
    labels: list[str] | None = None,
) -> PublicDerivedSyntheticQAGateCheck:
    return PublicDerivedSyntheticQAGateCheck(
        check_id=check_id,
        status="passed" if passed else failure_status,  # type: ignore[arg-type]
        message=message_passed if passed else message_failed,
        artifact_refs=artifact_refs or [],
        source_ids=source_ids or [],
        conversion_spec_ids=conversion_spec_ids or [],
        candidate_exception_lake_labels=[] if passed else labels or [],
    )


def build_public_derived_synthetic_qa_gate_report(
    *,
    methodology_report_path: str | Path,
    conversion_plan_path: str | Path,
    conversion_review_packet_path: str | Path,
    public_data_cache_audit_report_path: str | Path | None = None,
) -> PublicDerivedSyntheticQAGateReport:
    methodology_path = Path(methodology_report_path)
    plan_path = Path(conversion_plan_path)
    packet_path = Path(conversion_review_packet_path)
    methodology = _load_mapping(methodology_path)
    plan = _load_mapping(plan_path)
    packet = _load_mapping(packet_path)
    cache_path = (
        Path(public_data_cache_audit_report_path) if public_data_cache_audit_report_path else None
    )
    cache = _load_mapping(cache_path) if cache_path else None

    sources = _dicts(methodology.get("sources"))
    specs = _dicts(plan.get("specs"))
    recommendations = _dicts(packet.get("recommendations"))
    decision_templates = _dicts(packet.get("decision_templates"))
    red_team_notes = _dicts(packet.get("red_team_notes"))

    source_ids = _unique(
        [str(source.get("source_id", "")) for source in sources if source.get("source_id")]
    )
    spec_ids = _unique(
        [
            str(spec.get("conversion_spec_id", ""))
            for spec in specs
            if spec.get("conversion_spec_id")
        ]
    )
    spec_source_ids = _unique(
        [str(spec.get("source_id", "")) for spec in specs if spec.get("source_id")]
    )
    recommendation_spec_ids = _unique(
        [
            str(rec.get("conversion_spec_id", ""))
            for rec in recommendations
            if rec.get("conversion_spec_id")
        ]
    )
    template_spec_ids = _unique(
        [
            str(template.get("conversion_spec_id", ""))
            for template in decision_templates
            if template.get("conversion_spec_id")
        ]
    )
    target_families = _unique(
        [
            str(spec.get("target_fixture_family", ""))
            for spec in specs
            if spec.get("target_fixture_family")
        ]
    )

    artifact_refs = [str(methodology_path), str(plan_path), str(packet_path)]
    if cache_path:
        artifact_refs.append(str(cache_path))

    checks: list[PublicDerivedSyntheticQAGateCheck] = []
    checks.append(
        _check(
            "source_methodology_ready",
            passed=methodology.get("status") == READY_METHODOLOGY_STATUS
            and _int(methodology.get("source_count")) == len(sources)
            and set(source_ids) >= set(_strings(methodology.get("required_source_ids"))),
            message_passed="Public-source methodology is ready and source counts match.",
            message_failed="Public-source methodology is not ready or source counts/required sources do not match.",
            failure_status="blocked",
            artifact_refs=[str(methodology_path)],
            source_ids=source_ids,
            labels=["public_methodology_not_ready"],
        )
    )
    checks.append(
        _check(
            "conversion_plan_matches_methodology",
            passed=plan.get("status") == READY_CONVERSION_PLAN_STATUS
            and plan.get("source_methodology_report_id")
            == methodology.get("public_source_methodology_report_id")
            and plan.get("source_catalog_ref") == methodology.get("source_catalog_ref")
            and _int(plan.get("spec_count")) == len(specs)
            and set(spec_source_ids) == set(source_ids),
            message_passed="Conversion plan points to the methodology report and covers every methodology source once.",
            message_failed="Conversion plan does not match the methodology report, source catalog, or spec/source coverage.",
            failure_status="failed",
            artifact_refs=[str(methodology_path), str(plan_path)],
            source_ids=sorted(set(source_ids).symmetric_difference(set(spec_source_ids))),
            conversion_spec_ids=spec_ids,
            labels=["public_conversion_plan_mismatch"],
        )
    )
    checks.append(
        _check(
            "conversion_review_packet_matches_plan",
            passed=packet.get("status") == READY_CONVERSION_REVIEW_STATUS
            and packet.get("conversion_plan_id") == plan.get("conversion_plan_id")
            and packet.get("conversion_plan_status") == plan.get("status")
            and _int(packet.get("spec_count")) == len(specs)
            and _int(packet.get("recommendation_count")) == len(recommendations)
            and _int(packet.get("decision_template_count")) == len(decision_templates)
            and set(recommendation_spec_ids) == set(spec_ids)
            and set(template_spec_ids) == set(spec_ids)
            and len(red_team_notes) > 0,
            message_passed="Conversion review packet matches the plan and has recommendations, decision templates, and red-team notes.",
            message_failed="Conversion review packet does not match the plan or is missing recommendations, decision templates, or red-team notes.",
            failure_status="blocked",
            artifact_refs=[str(plan_path), str(packet_path)],
            conversion_spec_ids=sorted(
                set(spec_ids)
                .symmetric_difference(set(recommendation_spec_ids))
                .union(set(spec_ids).symmetric_difference(set(template_spec_ids)))
            ),
            labels=["public_conversion_review_packet_mismatch"],
        )
    )

    cache_audit_present = cache is not None
    cache_audit_required = bool(cache and cache.get("public_cache_samples_present") is True)
    cache_custody_status = "not_required"
    if cache and cache_audit_required:
        cache_custody_status = str(cache.get("rust_custody_status", "not_run"))
    cache_ready = True
    if cache_audit_required:
        cache_ready = (
            cache is not None
            and cache.get("status") == READY_CACHE_AUDIT_STATUS
            and cache.get("rust_custody_status") == "passed"
            and _int(cache.get("rust_custody_failure_count")) == 0
        )
    checks.append(
        _check(
            "cache_custody_ready_when_samples_exist",
            passed=cache_ready,
            message_passed=(
                "No public-cache samples require custody validation."
                if not cache_audit_required
                else "Public-cache samples exist and the cache audit/Rust custody report passed."
            ),
            message_failed="Public-cache samples exist but cache audit or Rust custody failed.",
            failure_status="failed",
            artifact_refs=[str(cache_path)] if cache_path else [],
            source_ids=_strings(cache.get("approved_source_ids", [])) if cache else [],
            labels=["public_cache_custody_failed"],
        )
    )

    nested_failures: list[str] = []
    for index, spec in enumerate(specs):
        spec_id = str(spec.get("conversion_spec_id", index))
        expected_false = ["fixture_file_mutation_allowed", "external_writes_performed"]
        expected_true = [
            "no_public_payload_ingested",
            "no_real_party_records",
            "no_real_matter_records",
            "no_adapter_authorized",
        ]
        for field in expected_false:
            if spec.get(field) is not False:
                nested_failures.append(f"conversion_plan.spec.{spec_id}.{field}")
        for field in expected_true:
            if spec.get(field) is not True:
                nested_failures.append(f"conversion_plan.spec.{spec_id}.{field}")
    side_effect_failures = []
    side_effect_failures.extend(
        _side_effect_failures(
            artifact_name="methodology",
            payload=methodology,
            fields=METHODOLOGY_SIDE_EFFECT_FIELDS,
        )
    )
    side_effect_failures.extend(
        _side_effect_failures(
            artifact_name="conversion_plan",
            payload=plan,
            fields=CONVERSION_PLAN_SIDE_EFFECT_FIELDS,
        )
    )
    side_effect_failures.extend(
        _side_effect_failures(
            artifact_name="conversion_review_packet",
            payload=packet,
            fields=CONVERSION_REVIEW_SIDE_EFFECT_FIELDS,
        )
    )
    if cache:
        side_effect_failures.extend(
            _side_effect_failures(
                artifact_name="public_data_cache_audit",
                payload=cache,
                fields=CACHE_AUDIT_SIDE_EFFECT_FIELDS,
            )
        )
    side_effect_failures.extend(nested_failures)
    checks.append(
        _check(
            "no_public_payload_or_side_effects",
            passed=not side_effect_failures,
            message_passed="All linked artifacts remain metadata-only/candidate-only and record no prohibited side effects.",
            message_failed=(
                "At least one linked artifact claims a prohibited side effect: "
                + ", ".join(side_effect_failures)
            ),
            failure_status="failed",
            artifact_refs=artifact_refs,
            labels=["public_synthetic_side_effect_boundary_failed"],
        )
    )
    checks.append(
        _check(
            "human_review_still_required",
            passed=methodology.get("human_review_required") is True
            and plan.get("human_review_required") is True
            and packet.get("human_review_required") is True
            and packet.get("append_only_review_outcome_required") is True,
            message_passed="Human methodology and conversion review remain required; review outcomes must be append-only.",
            message_failed="Human review or append-only review outcome requirements are missing.",
            failure_status="blocked",
            artifact_refs=artifact_refs,
            labels=["human_review_gate_missing"],
        )
    )
    checks.append(
        _check(
            "synthetic_gold_and_red_team_checks_present",
            passed=all(
                spec.get("required_synthetic_gold_checks") and spec.get("required_red_team_checks")
                for spec in specs
            )
            and len(red_team_notes) > 0,
            message_passed="Every conversion spec has synthetic gold and red-team checks and the review packet has red-team notes.",
            message_failed="At least one conversion spec lacks synthetic gold/red-team checks or the review packet lacks red-team notes.",
            failure_status="blocked",
            artifact_refs=[str(plan_path), str(packet_path)],
            conversion_spec_ids=[
                str(spec.get("conversion_spec_id"))
                for spec in specs
                if not spec.get("required_synthetic_gold_checks")
                or not spec.get("required_red_team_checks")
            ],
            labels=["public_synthetic_red_team_gap"],
        )
    )

    failed_count = sum(1 for check in checks if check.status == "failed")
    blocked_count = sum(1 for check in checks if check.status == "blocked")
    warning_count = sum(1 for check in checks if check.status == "warning")
    status = (
        "public_derived_synthetic_qa_ready_for_review"
        if failed_count == 0 and blocked_count == 0
        else "blocked_by_public_derived_synthetic_qa_gate"
    )
    labels = list(BASE_EXCEPTION_LABELS)
    if cache_audit_required:
        labels.append("public_cache_custody_required")
    for check in checks:
        labels.extend(check.candidate_exception_lake_labels)

    return PublicDerivedSyntheticQAGateReport(
        public_derived_synthetic_qa_gate_report_id=new_id("publicderivedsyntheticqagate"),
        status=status,  # type: ignore[arg-type]
        source_methodology_report_ref=str(methodology_path),
        source_methodology_report_id=str(
            methodology.get("public_source_methodology_report_id", "")
        ),
        source_methodology_report_status=str(methodology.get("status", "")),
        conversion_plan_ref=str(plan_path),
        conversion_plan_id=str(plan.get("conversion_plan_id", "")),
        conversion_plan_status=str(plan.get("status", "")),
        conversion_review_packet_ref=str(packet_path),
        conversion_review_packet_id=str(packet.get("review_packet_id", "")),
        conversion_review_packet_status=str(packet.get("status", "")),
        public_data_cache_audit_report_ref=str(cache_path) if cache_path else None,
        public_data_cache_audit_report_id=(
            str(cache.get("public_data_cache_audit_report_id", "")) if cache else None
        ),
        public_data_cache_audit_status=str(cache.get("status", "")) if cache else None,
        cache_audit_present=cache_audit_present,
        cache_audit_required=cache_audit_required,
        cache_custody_status=cache_custody_status,  # type: ignore[arg-type]
        methodology_source_count=len(source_ids),
        conversion_spec_count=len(spec_ids),
        review_recommendation_count=len(recommendations),
        review_red_team_note_count=len(red_team_notes),
        failed_check_count=failed_count,
        blocked_check_count=blocked_count,
        warning_check_count=warning_count,
        source_ids=source_ids,
        conversion_spec_ids=spec_ids,
        target_fixture_families=target_families,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        candidate_exception_lake_labels=_unique(labels),
        generated_at=now_iso(),
    )


def render_public_derived_synthetic_qa_gate_report(
    report: PublicDerivedSyntheticQAGateReport,
) -> str:
    lines = [
        "# Public-Derived Synthetic QA Gate Report",
        "",
        f"**Report ID:** {report.public_derived_synthetic_qa_gate_report_id}",
        f"**Status:** {report.status}",
        f"**Sources:** {report.methodology_source_count}",
        f"**Conversion specs:** {report.conversion_spec_count}",
        f"**Review recommendations:** {report.review_recommendation_count}",
        f"**Red-team notes:** {report.review_red_team_note_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Metadata only: {report.metadata_only}",
        f"- Human review required: {report.human_review_required}",
        f"- Fixture generation authorized: {report.fixture_generation_authorized}",
        f"- Fixture files mutated: {report.fixture_files_mutated}",
        f"- GitHub PR created: {report.github_pr_created}",
        f"- Public records ingested: {report.public_records_ingested}",
        f"- Raw public payload committed: {report.raw_public_payload_committed}",
        f"- Connector implemented: {report.connector_implemented}",
        f"- Legal Knowledge adapter authorized: {report.legal_knowledge_adapter_authorized}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Inputs",
        "",
        f"- Methodology: `{report.source_methodology_report_ref}` ({report.source_methodology_report_status})",
        f"- Conversion plan: `{report.conversion_plan_ref}` ({report.conversion_plan_status})",
        f"- Conversion review: `{report.conversion_review_packet_ref}` ({report.conversion_review_packet_status})",
        f"- Cache audit required: {report.cache_audit_required}",
        f"- Cache custody status: {report.cache_custody_status}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in report.required_next_gates),
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.extend([f"- `{check.check_id}`: {check.status}", f"  {check.message}"])
        if check.source_ids:
            lines.append(f"  Sources: {', '.join(check.source_ids)}")
        if check.conversion_spec_ids:
            lines.append(f"  Specs: {', '.join(check.conversion_spec_ids)}")
    lines.extend(
        [
            "",
            "This report gates public-derived synthetic fixture QA evidence only. It does not approve fixture generation, ingest public records, create a PR, write Lake/SQLite records, authorize adapters, submit budgets, or open matters.",
            "",
        ]
    )
    return "\n".join(lines)


def run_public_derived_synthetic_qa_gate(
    *,
    methodology_report_path: str | Path,
    conversion_plan_path: str | Path,
    conversion_review_packet_path: str | Path,
    out_dir: str | Path,
    public_data_cache_audit_report_path: str | Path | None = None,
) -> tuple[PublicDerivedSyntheticQAGateReport, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report = build_public_derived_synthetic_qa_gate_report(
        methodology_report_path=methodology_report_path,
        conversion_plan_path=conversion_plan_path,
        conversion_review_packet_path=conversion_review_packet_path,
        public_data_cache_audit_report_path=public_data_cache_audit_report_path,
    )
    write_json(
        run_dir / PUBLIC_DERIVED_SYNTHETIC_QA_GATE_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / PUBLIC_DERIVED_SYNTHETIC_QA_GATE_NOTES_FILENAME).write_text(
        render_public_derived_synthetic_qa_gate_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def validate_public_derived_synthetic_qa_gate_report(
    path: str | Path,
) -> PublicDerivedSyntheticQAGateReport:
    return PublicDerivedSyntheticQAGateReport.model_validate(load_json(path))


def validate_public_data_cache_audit_report(path: str | Path) -> PublicDataCacheAuditReport:
    return PublicDataCacheAuditReport.model_validate(load_json(path))
