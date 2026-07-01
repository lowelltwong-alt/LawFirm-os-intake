from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    BudgetDriverLabel,
    BudgetDriverValue,
    ConflictSeedLabel,
    CourtListenerDatasetManifest,
    IntakeStageDocumentLabel,
    LaborEmploymentBudgetFactAuditCheck,
    LaborEmploymentBudgetFactAuditReport,
    LaborEmploymentBudgetFactFinding,
    LaborEmploymentBudgetFactGap,
    LaborEmploymentBudgetFactSource,
    LaborEmploymentBudgetFactState,
    LaborEmploymentRelationshipCoverage,
    LaborEmploymentRelationshipTopologySummary,
    PersonTimelineEventLabel,
)
from .util import load_json, new_id, now_iso, write_json


LABOR_EMPLOYMENT_BUDGET_FACT_REPORT_FILENAME = "labor_employment_budget_fact_audit_report.json"
LABOR_EMPLOYMENT_BUDGET_FACT_NOTES_FILENAME = "labor_employment_budget_fact_audit_report.md"
DEFAULT_FACT_POLICY_REF = "config/labor-employment-budget-fact-needs.yaml"

RELATIONSHIP_FACT_BUCKETS = {
    "employee_claimant_identity": "employee_or_claimant_person",
    "employer_or_defendant_identity": "employer_or_defendant_entity",
    "prospective_client_payer_carrier_posture": "prospective_client_payer_or_carrier_posture",
    "individual_supervisor_or_manager_defendants": "individual_actor_or_defendant",
    "joint_employer_or_affiliate_structure": "joint_employer_affiliate_or_staffing_structure",
}
PERSON_RELATIONSHIP_ROLES = {
    "employee",
    "claimant",
    "supervisor",
    "manager",
    "hr_representative",
    "individual_defendant",
}
ORGANIZATION_RELATIONSHIP_ROLES = {
    "employer",
    "parent_entity",
    "subsidiary",
    "affiliate",
    "joint_employer",
    "staffing_agency",
    "peo",
    "franchise_entity",
    "insurer",
    "payer",
    "carrier",
}


DatasetFactLabel = (
    BudgetDriverLabel | ConflictSeedLabel | IntakeStageDocumentLabel | PersonTimelineEventLabel
)


def _resolve_ref(base: Path, ref: str | Path) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    return base / path


def load_labor_employment_budget_fact_policy(path: str | Path) -> dict[str, Any]:
    policy = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        raise ValueError("labor/employment budget fact policy must be a mapping")
    if policy.get("contains_real_firm_data", False):
        raise ValueError("real firm L&E budget fact policies are prohibited")
    if policy.get("primary_practice_area") != "labor_employment":
        raise ValueError("L&E budget fact policy must target labor_employment")
    if not isinstance(policy.get("fact_needs"), list) or not policy["fact_needs"]:
        raise ValueError("L&E budget fact policy requires fact_needs")
    return policy


def _list_match(value: str | None, candidates: Any) -> bool:
    if value is None or not isinstance(candidates, list):
        return False
    return value in {str(candidate) for candidate in candidates}


def _budget_driver_sources(
    manifest: CourtListenerDatasetManifest,
    match: dict[str, Any],
) -> list[LaborEmploymentBudgetFactSource]:
    sources: list[LaborEmploymentBudgetFactSource] = []
    for label in manifest.budget_driver_labels:
        if not _list_match(label.driver_id, match.get("budget_driver_ids")):
            continue
        sources.append(
            LaborEmploymentBudgetFactSource(
                label_family="budget_driver_label",
                label_id=label.label_id,
                value=label.value,
                value_status=label.value_status,
                review_status=label.review_status,
                uncertainty=label.uncertainty,
                source_ref=label.source_ref,
            )
        )
    return sources


def _conflict_seed_sources(
    manifest: CourtListenerDatasetManifest,
    match: dict[str, Any],
) -> list[LaborEmploymentBudgetFactSource]:
    sources: list[LaborEmploymentBudgetFactSource] = []
    for label in manifest.conflict_seed_labels:
        observed_match = _list_match(label.observed_role, match.get("conflict_observed_roles"))
        inferred_match = _list_match(label.inferred_role, match.get("conflict_inferred_roles"))
        if not observed_match and not inferred_match:
            continue
        sources.append(
            LaborEmploymentBudgetFactSource(
                label_family="conflict_seed_label",
                label_id=label.label_id,
                value=label.name,
                observed_role=label.observed_role,
                inferred_role=label.inferred_role,
                review_status=label.review_status,
                uncertainty=label.uncertainty,
                source_ref=label.source_ref,
            )
        )
    return sources


def _document_label_sources(
    manifest: CourtListenerDatasetManifest,
    match: dict[str, Any],
) -> list[LaborEmploymentBudgetFactSource]:
    sources: list[LaborEmploymentBudgetFactSource] = []
    for label in manifest.intake_stage_document_labels:
        if not _list_match(label.value, match.get("intake_document_values")):
            continue
        sources.append(
            LaborEmploymentBudgetFactSource(
                label_family="intake_stage_document_label",
                label_id=label.label_id,
                value=label.value,
                review_status=label.review_status,
                uncertainty=label.uncertainty,
                source_ref=label.source_ref,
            )
        )
    return sources


def _timeline_label_sources(
    manifest: CourtListenerDatasetManifest,
    match: dict[str, Any],
) -> list[LaborEmploymentBudgetFactSource]:
    sources: list[LaborEmploymentBudgetFactSource] = []
    for label in manifest.person_timeline_event_labels:
        if not _list_match(label.event_type, match.get("timeline_event_types")):
            continue
        value: BudgetDriverValue = label.normalized_datetime_candidate or label.event_datetime_text
        sources.append(
            LaborEmploymentBudgetFactSource(
                label_family="person_timeline_event_label",
                label_id=label.label_id,
                value=value,
                review_status=label.review_status,
                uncertainty=label.uncertainty,
                source_ref=label.source_ref,
            )
        )
    return sources


def _sources_for_fact(
    manifest: CourtListenerDatasetManifest,
    fact_need: dict[str, Any],
) -> list[LaborEmploymentBudgetFactSource]:
    match = fact_need.get("match", {})
    if not isinstance(match, dict):
        return []
    sources = [
        *_budget_driver_sources(manifest, match),
        *_conflict_seed_sources(manifest, match),
        *_document_label_sources(manifest, match),
        *_timeline_label_sources(manifest, match),
    ]
    return sorted(sources, key=lambda source: (source.label_family, source.label_id))


def _fact_state(sources: list[LaborEmploymentBudgetFactSource]) -> LaborEmploymentBudgetFactState:
    if not sources:
        return "unknown_missing"
    if any(source.value_status == "synthetic_context_wrapper" for source in sources):
        return "synthetic_context_requires_confirmation"
    if any(source.review_status == "needs_review" for source in sources):
        return "source_bound_needs_review"
    if any(source.uncertainty == "high" for source in sources):
        return "source_bound_needs_review"
    return "source_bound_observed_candidate"


def _gap_for_finding(
    finding: LaborEmploymentBudgetFactFinding,
    fact_need: dict[str, Any],
) -> LaborEmploymentBudgetFactGap | None:
    if finding.current_state == "source_bound_observed_candidate":
        return None
    required_level = str(fact_need.get("required_level", "context"))
    if required_level == "context" and finding.current_state != "unknown_missing":
        return None
    severity = "critical" if required_level == "critical" else "warning"
    if required_level == "context":
        severity = "info"
    if finding.current_state == "unknown_missing":
        gap_type = "missing_evidence"
        risk_prefix = "Missing source-bound facts"
    elif finding.current_state == "synthetic_context_requires_confirmation":
        gap_type = "human_confirmation_required"
        risk_prefix = "Synthetic context cannot be treated as observed fact"
    else:
        gap_type = "uncertain_candidate"
        risk_prefix = "Candidate evidence still needs human review"
    source_refs = [source.source_ref for source in finding.sources]
    return LaborEmploymentBudgetFactGap(
        gap_id=f"lefactgap-{finding.fact_id}",
        fact_id=finding.fact_id,
        severity=severity,
        gap_type=gap_type,
        budget_risk=(
            f"{risk_prefix}; budget effects: {', '.join(finding.budget_effects) or 'unspecified'}."
        ),
        recommended_question=finding.question,
        blocks_precise_budget=severity == "critical",
        source_refs=source_refs,
    )


def _finding_for_need(
    manifest: CourtListenerDatasetManifest,
    fact_need: dict[str, Any],
) -> LaborEmploymentBudgetFactFinding:
    sources = _sources_for_fact(manifest, fact_need)
    state = _fact_state(sources)
    fact_id = str(fact_need["fact_id"])
    return LaborEmploymentBudgetFactFinding(
        fact_id=fact_id,
        fact_category=fact_need["fact_category"],
        required_level=fact_need["required_level"],
        question=str(fact_need["question"]),
        current_state=state,
        budget_effects=[str(effect) for effect in fact_need.get("budget_effects", [])],
        sources=sources,
        reviewer_action=(
            "Confirm this fact and correct entity/relationship roles before budget math."
            if state != "source_bound_observed_candidate"
            else "Review source-bound candidate evidence before relying on budget math."
        ),
        recommended_budget_treatment=fact_need.get(
            "recommended_budget_treatment",
            "hours_only_or_broad_range",
        ),
        source_bound=bool(sources),
        human_confirmation_required=bool(fact_need.get("human_confirmation_required", True)),
    )


def _check(
    check_id: str,
    passed: bool,
    message: str,
    details: dict[str, Any] | None = None,
) -> LaborEmploymentBudgetFactAuditCheck:
    return LaborEmploymentBudgetFactAuditCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        details=details or {},
    )


def _relationship_roles(
    sources: list[LaborEmploymentBudgetFactSource],
) -> tuple[list[str], list[str]]:
    observed = sorted(
        {
            source.observed_role
            for source in sources
            if source.label_family == "conflict_seed_label" and source.observed_role
        }
    )
    inferred = sorted(
        {
            source.inferred_role
            for source in sources
            if source.label_family == "conflict_seed_label" and source.inferred_role
        }
    )
    return observed, inferred


def _relationship_candidate_counts(
    coverage: list[LaborEmploymentRelationshipCoverage],
) -> tuple[int, int]:
    person_ids: set[str] = set()
    organization_ids: set[str] = set()
    for item in coverage:
        roles = set(item.observed_roles)
        if roles & PERSON_RELATIONSHIP_ROLES:
            person_ids.update(item.source_label_ids)
        if roles & ORGANIZATION_RELATIONSHIP_ROLES:
            organization_ids.update(item.source_label_ids)
    return len(person_ids), len(organization_ids)


def _build_relationship_topology(
    findings: list[LaborEmploymentBudgetFactFinding],
    gaps: list[LaborEmploymentBudgetFactGap],
) -> LaborEmploymentRelationshipTopologySummary:
    gap_by_fact = {gap.fact_id: gap for gap in gaps}
    coverage: list[LaborEmploymentRelationshipCoverage] = []
    for finding in findings:
        if finding.fact_category != "entity_relationship":
            continue
        bucket = RELATIONSHIP_FACT_BUCKETS.get(finding.fact_id)
        if bucket is None:
            continue
        observed_roles, inferred_roles = _relationship_roles(finding.sources)
        gap = gap_by_fact.get(finding.fact_id)
        coverage.append(
            LaborEmploymentRelationshipCoverage(
                fact_id=finding.fact_id,
                relationship_bucket=bucket,  # type: ignore[arg-type]
                current_state=finding.current_state,
                required_level=finding.required_level,
                question=finding.question,
                observed_roles=observed_roles,
                inferred_roles=inferred_roles,
                source_label_ids=sorted({source.label_id for source in finding.sources}),
                source_refs=[source.source_ref for source in finding.sources],
                budget_effects=finding.budget_effects,
                blocks_precise_budget=gap.blocks_precise_budget if gap else False,
                human_confirmation_required=finding.human_confirmation_required,
            )
        )
    person_count, organization_count = _relationship_candidate_counts(coverage)
    critical_gap_count = sum(
        1
        for item in coverage
        if item.required_level == "critical"
        and item.current_state != "source_bound_observed_candidate"
    )
    missing_or_review_count = sum(
        1 for item in coverage if item.current_state != "source_bound_observed_candidate"
    )
    if critical_gap_count:
        treatment = "block_amount_budget"
    elif missing_or_review_count:
        treatment = "hours_only_or_broad_range"
    else:
        treatment = "candidate_range_budget_after_review"
    return LaborEmploymentRelationshipTopologySummary(
        coverage=coverage,
        source_bound_relationship_count=sum(1 for item in coverage if item.source_refs),
        missing_or_review_relationship_count=missing_or_review_count,
        critical_relationship_gap_count=critical_gap_count,
        person_candidate_count=person_count,
        organization_candidate_count=organization_count,
        unresolved_relationship_fact_ids=[
            item.fact_id
            for item in coverage
            if item.current_state != "source_bound_observed_candidate"
        ],
        required_human_relationship_questions=[
            item.question
            for item in coverage
            if item.current_state != "source_bound_observed_candidate"
        ],
        budget_treatment=treatment,  # type: ignore[arg-type]
    )


def _build_checks(
    manifest: CourtListenerDatasetManifest,
    policy: dict[str, Any],
    findings: list[LaborEmploymentBudgetFactFinding],
    relationship_topology: LaborEmploymentRelationshipTopologySummary,
) -> list[LaborEmploymentBudgetFactAuditCheck]:
    side_effect_flags = [
        "public_records_ingested",
        "live_calls_performed",
        "pacer_purchase_performed",
        "recap_fetch_purchase_performed",
        "uploads_performed",
        "court_writes_performed",
        "training_pipeline_created",
        "budget_accuracy_claimed",
        "external_writes_performed",
    ]
    unsafe_flags = [flag for flag in side_effect_flags if getattr(manifest, flag) is not False]
    non_source_bound = [
        finding.fact_id
        for finding in findings
        if finding.current_state != "unknown_missing" and not finding.sources
    ]
    critical_fact_ids = {
        str(fact["fact_id"])
        for fact in policy.get("fact_needs", [])
        if fact.get("required_level") == "critical"
    }
    represented = {"employee_claimant_identity", "employer_or_defendant_identity"}
    relationship_fact_ids = {
        finding.fact_id for finding in findings if finding.fact_category == "entity_relationship"
    }
    topology_fact_ids = {item.fact_id for item in relationship_topology.coverage}
    critical_relationship_gap_ids = {
        finding.fact_id
        for finding in findings
        if finding.fact_category == "entity_relationship"
        and finding.required_level == "critical"
        and finding.current_state != "source_bound_observed_candidate"
    }
    return [
        _check(
            "practice_area_is_labor_employment",
            manifest.primary_practice_area == "labor_employment",
            "Manifest is scoped to the labor/employment starter corpus.",
            {"primary_practice_area": manifest.primary_practice_area},
        ),
        _check(
            "no_live_public_or_external_side_effects",
            not unsafe_flags,
            "Fact audit input records no public ingestion, live calls, purchases, uploads, court writes, training, budget accuracy claim, or external writes.",
            {"unsafe_flags": unsafe_flags},
        ),
        _check(
            "critical_entity_relationship_questions_present",
            represented.issubset(critical_fact_ids),
            "Policy includes employee/claimant and employer/defendant identity as critical budget questions.",
            {"missing": sorted(represented - critical_fact_ids)},
        ),
        _check(
            "source_bound_findings_keep_source_refs",
            not non_source_bound,
            "Every non-unknown fact finding keeps source label refs with offsets and hashes.",
            {"non_source_bound_fact_ids": non_source_bound},
        ),
        _check(
            "relationship_topology_includes_entity_relationship_findings",
            relationship_fact_ids == topology_fact_ids,
            "Relationship topology covers every entity-relationship fact need in the local policy.",
            {
                "missing_from_topology": sorted(relationship_fact_ids - topology_fact_ids),
                "extra_topology_fact_ids": sorted(topology_fact_ids - relationship_fact_ids),
            },
        ),
        _check(
            "relationship_topology_blocks_unresolved_critical_relationships",
            relationship_topology.critical_relationship_gap_count
            == len(critical_relationship_gap_ids)
            and (
                relationship_topology.budget_treatment == "block_amount_budget"
                if critical_relationship_gap_ids
                else True
            ),
            "Unresolved critical relationship facts remain visible as amount-budget blockers.",
            {
                "critical_relationship_gap_ids": sorted(critical_relationship_gap_ids),
                "budget_treatment": relationship_topology.budget_treatment,
            },
        ),
        _check(
            "relationship_topology_preserves_candidate_boundary",
            relationship_topology.canonical_role_promotion_authorized is False
            and relationship_topology.relationship_classification_authoritative is False,
            "Relationship topology is candidate-only and does not promote canonical roles.",
            {},
        ),
    ]


def build_labor_employment_budget_fact_audit_report(
    *,
    repo_root: str | Path,
    manifest_path: str | Path,
    policy_path: str | Path | None = None,
) -> LaborEmploymentBudgetFactAuditReport:
    root = Path(repo_root)
    manifest_ref = str(manifest_path)
    policy_ref = str(policy_path or DEFAULT_FACT_POLICY_REF)
    manifest = CourtListenerDatasetManifest.model_validate(
        load_json(_resolve_ref(root, manifest_ref))
    )
    policy = load_labor_employment_budget_fact_policy(_resolve_ref(root, policy_ref))
    findings = [
        _finding_for_need(manifest, fact_need)
        for fact_need in policy["fact_needs"]
        if isinstance(fact_need, dict)
    ]
    gaps = [
        gap
        for finding, fact_need in zip(findings, policy["fact_needs"], strict=True)
        if (gap := _gap_for_finding(finding, fact_need)) is not None
    ]
    relationship_topology = _build_relationship_topology(findings, gaps)
    checks = _build_checks(manifest, policy, findings, relationship_topology)
    critical_gap_count = sum(1 for gap in gaps if gap.severity == "critical")
    if critical_gap_count:
        budget_readiness_state = "blocked_missing_critical_facts"
    elif any(
        finding.current_state
        in {"source_bound_needs_review", "synthetic_context_requires_confirmation"}
        for finding in findings
    ):
        budget_readiness_state = "range_only_pending_human_review"
    else:
        budget_readiness_state = "candidate_ready_for_budget_review"
    status = (
        "blocked_labor_employment_budget_fact_audit"
        if any(check.status == "failed" for check in checks)
        else "labor_employment_budget_facts_ready_for_review"
    )
    return LaborEmploymentBudgetFactAuditReport(
        labor_employment_budget_fact_audit_report_id=new_id("lebudgetfacts"),
        status=status,
        manifest_ref=manifest_ref,
        manifest_id=manifest.manifest_id,
        policy_ref=policy_ref,
        primary_practice_area=manifest.primary_practice_area,
        budget_readiness_state=budget_readiness_state,
        finding_count=len(findings),
        source_bound_finding_count=sum(1 for finding in findings if finding.source_bound),
        needs_review_finding_count=sum(
            1
            for finding in findings
            if finding.current_state
            in {"source_bound_needs_review", "synthetic_context_requires_confirmation"}
        ),
        unknown_finding_count=sum(
            1 for finding in findings if finding.current_state == "unknown_missing"
        ),
        gap_count=len(gaps),
        critical_gap_count=critical_gap_count,
        relationship_topology=relationship_topology,
        findings=findings,
        gaps=gaps,
        required_human_questions=[gap.recommended_question for gap in gaps],
        checks=checks,
        generated_at=now_iso(),
    )


def render_labor_employment_budget_fact_audit_report(
    report: LaborEmploymentBudgetFactAuditReport,
) -> str:
    lines = [
        "# Labor/Employment Budget Fact Audit Report",
        "",
        f"**Report ID:** {report.labor_employment_budget_fact_audit_report_id}",
        f"**Status:** {report.status}",
        f"**Budget readiness:** {report.budget_readiness_state}",
        f"**Manifest:** `{report.manifest_ref}`",
        f"**Policy:** `{report.policy_ref}`",
        "",
        "## Summary",
        "",
        f"- Findings: {report.finding_count}",
        f"- Source-bound findings: {report.source_bound_finding_count}",
        f"- Needs-review findings: {report.needs_review_finding_count}",
        f"- Unknown findings: {report.unknown_finding_count}",
        f"- Critical gaps: {report.critical_gap_count}",
        "",
        "## Relationship Topology",
        "",
        f"- Source-bound relationship facts: {report.relationship_topology.source_bound_relationship_count}",
        f"- Missing/review relationship facts: {report.relationship_topology.missing_or_review_relationship_count}",
        f"- Critical relationship gaps: {report.relationship_topology.critical_relationship_gap_count}",
        f"- Person candidates: {report.relationship_topology.person_candidate_count}",
        f"- Organization candidates: {report.relationship_topology.organization_candidate_count}",
        f"- Budget treatment: {report.relationship_topology.budget_treatment}",
        "",
    ]
    for item in report.relationship_topology.coverage:
        lines.append(
            f"- `{item.fact_id}` ({item.relationship_bucket}): {item.current_state}; "
            f"roles={', '.join(item.observed_roles) or 'none'}; "
            f"blocks_precise_budget={item.blocks_precise_budget}"
        )
    lines.extend(
        [
            "",
            "## Human Relationship Questions",
            "",
        ]
    )
    for question in report.relationship_topology.required_human_relationship_questions:
        lines.append(f"- {question}")
    lines.extend(
        [
            "",
            "## Human Questions",
            "",
        ]
    )
    for question in report.required_human_questions:
        lines.append(f"- {question}")
    lines.extend(["", "## Findings", ""])
    for finding in report.findings:
        lines.append(
            f"- `{finding.fact_id}`: {finding.current_state}; "
            f"treatment={finding.recommended_budget_treatment}; "
            f"effects={', '.join(finding.budget_effects)}"
        )
        for source in finding.sources:
            lines.append(
                f"  - {source.label_family}:{source.label_id} "
                f"review={source.review_status} uncertainty={source.uncertainty}"
            )
    lines.extend(["", "## Boundary", ""])
    lines.extend(
        [
            f"- Budget amount output authorized: {report.budget_amount_output_authorized}",
            f"- Budget submission authorized: {report.budget_submission_authorized}",
            f"- Conflict conclusion emitted: {report.conflict_conclusion_emitted}",
            f"- Matter opening authorized: {report.matter_opening_authorized}",
            f"- Training pipeline created: {report.training_pipeline_created}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            "",
            "This report is a candidate fact-gap review surface only. It does not classify "
            "platform-canonical roles, approve a budget, submit a budget, open a matter, "
            "clear conflicts, write to the Exception Lake, or learn from reviewer changes.",
            "",
        ]
    )
    return "\n".join(lines)


def run_labor_employment_budget_fact_audit(
    *,
    repo_root: str | Path,
    manifest_path: str | Path,
    out_dir: str | Path,
    policy_path: str | Path | None = None,
) -> tuple[LaborEmploymentBudgetFactAuditReport, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report = build_labor_employment_budget_fact_audit_report(
        repo_root=repo_root,
        manifest_path=manifest_path,
        policy_path=policy_path,
    )
    write_json(
        run_dir / LABOR_EMPLOYMENT_BUDGET_FACT_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / LABOR_EMPLOYMENT_BUDGET_FACT_NOTES_FILENAME).write_text(
        render_labor_employment_budget_fact_audit_report(report),
        encoding="utf-8",
    )
    return report, run_dir
