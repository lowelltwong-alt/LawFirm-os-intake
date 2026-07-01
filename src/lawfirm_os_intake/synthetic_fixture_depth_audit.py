from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
from typing import Any

from .models import (
    SyntheticFixtureDepthAuditReport,
    SyntheticFixtureDepthDimension,
    SyntheticFixtureDepthFamilySummary,
    SyntheticFixtureExpansionHoldoutSpec,
    SyntheticFixtureExpansionManifest,
)
from .util import digest_text, load_json, now_iso, write_json


SYNTHETIC_FIXTURE_DEPTH_AUDIT_REPORT_FILENAME = "synthetic_fixture_depth_audit_report.json"
SYNTHETIC_FIXTURE_DEPTH_AUDIT_NOTES_FILENAME = "synthetic_fixture_depth_audit_report.md"


@dataclass(frozen=True)
class DepthRequirement:
    dimension_id: str
    family: str
    danger_loop: str
    description: str
    required_term_groups: tuple[tuple[str, ...], ...]
    why_it_matters: str
    remediation_hint: str


DEPTH_REQUIREMENTS: tuple[DepthRequirement, ...] = (
    DepthRequirement(
        dimension_id="ambiguous_role_source_context_separation",
        family="ambiguous_roles",
        danger_loop="role_collapse",
        description="Ambiguous role holdouts preserve source-bound role alternatives and context separation.",
        required_term_groups=(
            ("carrier",),
            ("payer", "insured", "represented-client", "represented client"),
            ("unknown", "ambiguous", "ambiguity"),
            ("context", "practice context"),
            ("source-anchor", "source anchor", "observed evidence", "source-bound"),
        ),
        why_it_matters=(
            "Budgets can move materially when a carrier, payer, insured, sender, "
            "or represented client is collapsed into the wrong role."
        ),
        remediation_hint=(
            "Add or retain holdouts that force sender, payer, insured, adverse, "
            "and represented-client alternatives to remain separate until human review."
        ),
    ),
    DepthRequirement(
        dimension_id="missing_actuals_not_zero_or_connector_backfill",
        family="missing_actuals",
        danger_loop="actuals_backfill",
        description="Missing actual-cost holdouts do not treat absent billing evidence as zero spend.",
        required_term_groups=(
            ("missing actual", "actuals_not_available"),
            ("variance_ledger_no_actuals", "actuals_by_phase", "actuals_by_code"),
            ("billing connector", "connector", "billing_connector_read_performed"),
            (
                "no billing connector read",
                "no billing connector write",
                "no read or write",
                "billing_connector_write_performed",
            ),
        ),
        why_it_matters=(
            "Budget-to-actual comparison becomes misleading if unavailable actuals "
            "are interpreted as zero cost or silently fetched from billing systems."
        ),
        remediation_hint=(
            "Add missing-actuals fixtures that emit missing-actual ledger evidence "
            "while preserving the no billing connector read/write boundary."
        ),
    ),
    DepthRequirement(
        dimension_id="carrier_rejection_capture_completeness",
        family="carrier_rejection_variants",
        danger_loop="carrier_rejection_capture",
        description="Carrier rejection holdouts cover reconciliation completeness failures.",
        required_term_groups=(
            ("duplicate",),
            ("missing response", "missing-response", "missing responses", "missing_response_count"),
            ("unlinked", "unlinked_notice_count"),
            ("parser failure", "parse failure", "parse_failed", "parser_failure_count"),
            ("appeal",),
            ("duplicate_notice_count", "total_disputed_amount", "current_financial_exposure"),
        ),
        why_it_matters=(
            "The future production invariant is response-state completeness, not "
            "model confidence. Duplicate, missing, unlinked, malformed, and appeal "
            "states must all remain audit-visible."
        ),
        remediation_hint=(
            "Keep at least one rejection fixture that forces duplicate collapse, "
            "missing response follow-up, unlinked notice review, parse-failure review, "
            "and appeal financial outcome capture."
        ),
    ),
    DepthRequirement(
        dimension_id="carrier_partial_allowance_and_appeal_outcome_variety",
        family="carrier_rejection_variants",
        danger_loop="carrier_learning",
        description="Carrier rejection holdouts include partial allowances and non-success appeal outcomes.",
        required_term_groups=(
            ("partial allowance", "partial allowances", "partially_accepted", "partial rejection"),
            ("stale", "denied", "no_response", "no response"),
        ),
        why_it_matters=(
            "Partial allowances can inflate exposure if the full submitted amount is "
            "reused, and stale or denied appeals must not become silent guideline learning."
        ),
        remediation_hint=(
            "Add carrier rejection holdouts with partially accepted notices plus stale, "
            "denied, or no-response appeal results and explicit write-down evidence."
        ),
    ),
    DepthRequirement(
        dimension_id="budget_driver_unknown_and_counterfactual_intensity",
        family="budget_driver_edges",
        danger_loop="budget_driver_overfit",
        description="Budget-driver holdouts cover low, high, and unknown intensity without inventing facts.",
        required_term_groups=(
            ("low-intensity", "low intensity", "lower_intensity_projection", "soft_tissue"),
            (
                "high-intensity",
                "high intensity",
                "higher_intensity_projection",
                "catastrophic",
            ),
            ("unknown",),
            ("context", "profile-default", "profile_default"),
            ("not observed", "not observed facts", "not invent facts"),
        ),
        why_it_matters=(
            "Budget math should widen or route review when key drivers are unknown; "
            "it should not invent facts from practice context."
        ),
        remediation_hint=(
            "Keep budget-driver fixtures that compare low/high/unknown drivers and "
            "prove context stays separate from observed facts."
        ),
    ),
    DepthRequirement(
        dimension_id="labor_employment_budget_fact_gap_holdout",
        family="cross_family",
        danger_loop="labor_employment_budget_false_precision",
        description="Holdouts cover labor and employment budget fact gaps before L&E budget calibration.",
        required_term_groups=(
            ("labor", "employment", "employee", "employer", "wage", "harassment"),
            ("party", "plaintiff", "claimant", "class", "collective"),
            ("budget", "driver", "critical fact", "fact gap"),
        ),
        why_it_matters=(
            "The first serious matter-family push is labor and employment. Budgets "
            "need party counts, employee/entity roles, claim posture, and complexity "
            "facts before ranges can be responsibly narrowed."
        ),
        remediation_hint=(
            "Add L&E-specific critical-fact holdouts covering employee/employer roles, "
            "claimant or class posture, claims, venue posture, documents, witnesses, "
            "deadlines, and missing budget drivers."
        ),
    ),
    DepthRequirement(
        dimension_id="review_and_learning_guardrails_visible",
        family="cross_family",
        danger_loop="human_gate_bypass",
        description="Holdouts make human review, no-write, and no-silent-learning gates visible.",
        required_term_groups=(
            ("human", "review", "unknown"),
            ("no ", "not ", "must not"),
            ("learning", "calibration", "shadow eval", "mutate"),
            ("external", "connector", "lake", "sqlite", "submission"),
        ),
        why_it_matters=(
            "Fixture growth can accidentally turn candidate evidence into automatic "
            "calibration, profile mutation, or external workflow authority."
        ),
        remediation_hint=(
            "Keep each holdout family tied to human review, no external writes, no "
            "Lake/SQLite admission, and no silent learning or calibration approval."
        ),
    ),
)


@dataclass(frozen=True)
class HoldoutEvidence:
    holdout: SyntheticFixtureExpansionHoldoutSpec
    manifest_text: str
    fixture_text: str
    test_text: str
    fixture_term_pointers: dict[str, list[str]]
    fixture_test_binding_statuses: dict[str, str]
    verified_test_refs: tuple[str, ...]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _normalize_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold())


def _holdout_text(holdout: SyntheticFixtureExpansionHoldoutSpec) -> str:
    parts = [
        holdout.holdout_id,
        holdout.family,
        holdout.description,
        *holdout.fixture_refs,
        *holdout.test_refs,
        *holdout.expected_signals,
        *holdout.red_team_notes,
    ]
    return _normalize_text(" ".join(parts))


def _json_pointer_escape(value: str) -> str:
    return value.replace("~", "~0").replace("/", "~1")


def _json_scalar_text(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, bool):
        return str(value).lower()
    if value is None:
        return "null"
    if isinstance(value, (int, float)):
        return str(value)
    return ""


def _json_text_and_pointers(
    payload: Any,
    *,
    pointer: str = "",
) -> tuple[list[str], dict[str, list[str]]]:
    texts: list[str] = []
    pointers: dict[str, list[str]] = {}
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_pointer = (
                f"{pointer}/{_json_pointer_escape(str(key))}"
                if pointer
                else f"/{_json_pointer_escape(str(key))}"
            )
            texts.append(str(key))
            pointers.setdefault(str(key), []).append(child_pointer)
            child_texts, child_pointers = _json_text_and_pointers(
                value,
                pointer=child_pointer,
            )
            texts.extend(child_texts)
            for term, refs in child_pointers.items():
                pointers.setdefault(term, []).extend(refs)
        return texts, pointers
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            child_pointer = f"{pointer}/{index}" if pointer else f"/{index}"
            child_texts, child_pointers = _json_text_and_pointers(
                value,
                pointer=child_pointer,
            )
            texts.extend(child_texts)
            for term, refs in child_pointers.items():
                pointers.setdefault(term, []).extend(refs)
        return texts, pointers
    text = _json_scalar_text(payload)
    if text:
        texts.append(text)
        pointers.setdefault(text, []).append(pointer or "/")
    return texts, pointers


def _ref_path_part(ref: str) -> str:
    return ref.split("::", maxsplit=1)[0].split("#", maxsplit=1)[0]


def _test_name_part(ref: str) -> str | None:
    if "::" not in ref:
        return None
    name = ref.split("::", maxsplit=1)[1].split("[", maxsplit=1)[0]
    return name or None


def _resolve_repo_ref(repo_root: Path, ref: str) -> Path | None:
    path_part = _ref_path_part(ref)
    target = Path(path_part)
    resolved = target.resolve() if target.is_absolute() else (repo_root / target).resolve()
    try:
        resolved.relative_to(repo_root)
    except ValueError:
        return None
    return resolved


def _test_body_for_ref(test_path: Path, test_ref: str) -> str | None:
    test_name = _test_name_part(test_ref)
    if not test_name:
        return None
    text = test_path.read_text(encoding="utf-8")
    pattern = re.compile(rf"(?ms)^def\s+{re.escape(test_name)}\b.*?(?=^def\s+|^class\s+|\Z)")
    match = pattern.search(text)
    if not match:
        return None
    return match.group(0)


def _fixture_ref_terms(ref: str) -> tuple[str, ...]:
    path_part = _ref_path_part(ref)
    path = Path(path_part)
    terms = [path_part.replace("\\", "/"), path.name]
    if path.stem:
        terms.append(path.stem)
    return tuple(dict.fromkeys(terms))


FORBIDDEN_TRUE_FLAGS = {
    "contains_real_client_data",
    "contains_real_matter_data",
    "contains_privileged_data",
    "billing_connector_read_performed",
    "billing_connector_write_performed",
    "external_writes_performed",
    "lake_write_performed",
    "sqlite_write_performed",
    "silent_learning_performed",
    "calibration_approved",
}


def _json_boundary_violations(
    payload: Any,
    ref: str,
    *,
    pointer: str = "",
) -> list[str]:
    violations: list[str] = []
    if isinstance(payload, dict):
        for key, value in payload.items():
            child_pointer = (
                f"{pointer}/{_json_pointer_escape(str(key))}"
                if pointer
                else f"/{_json_pointer_escape(str(key))}"
            )
            if key == "data_origin" and value not in {None, "synthetic"}:
                violations.append(f"{ref}{child_pointer}: data_origin is not synthetic")
            if key in FORBIDDEN_TRUE_FLAGS and value is True:
                violations.append(f"{ref}{child_pointer}: {key}=true")
            violations.extend(_json_boundary_violations(value, ref, pointer=child_pointer))
        return violations
    if isinstance(payload, list):
        for index, value in enumerate(payload):
            child_pointer = f"{pointer}/{index}" if pointer else f"/{index}"
            violations.extend(_json_boundary_violations(value, ref, pointer=child_pointer))
    return violations


def _boundary_violations(
    *,
    manifest: SyntheticFixtureExpansionManifest,
    manifest_ref: str,
    repo_root: Path,
) -> list[str]:
    violations: list[str] = []
    if manifest.calibration_approved:
        violations.append(f"{manifest_ref}: calibration_approved=true")
    for flag in (
        "fixture_files_mutated_by_audit",
        "lake_write_performed",
        "sqlite_write_performed",
        "external_writes_performed",
        "silent_learning_performed",
    ):
        if getattr(manifest, flag):
            violations.append(f"{manifest_ref}: {flag}=true")
    for holdout in manifest.holdouts:
        if holdout.calibration_approved:
            violations.append(f"{holdout.holdout_id}: calibration_approved=true")
        test_paths: list[tuple[str, Path, str]] = []
        for test_ref in holdout.test_refs:
            resolved_test = _resolve_repo_ref(repo_root, test_ref)
            if resolved_test is None:
                violations.append(f"{test_ref}: test ref resolves outside repo root")
                continue
            if not resolved_test.exists():
                violations.append(f"{test_ref}: missing test file")
                continue
            body = _test_body_for_ref(resolved_test, test_ref)
            if body is None:
                violations.append(f"{test_ref}: named test function is missing")
                continue
            test_paths.append((test_ref, resolved_test, resolved_test.read_text(encoding="utf-8")))
        for ref in holdout.fixture_refs:
            resolved = _resolve_repo_ref(repo_root, ref)
            if resolved is None:
                violations.append(f"{ref}: resolves outside repo root")
                continue
            if not resolved.exists():
                violations.append(f"{ref}: missing")
                continue
            fixture_terms = _fixture_ref_terms(ref)
            if not any(
                any(term in test_text for term in fixture_terms)
                for _test_ref, _test_path, test_text in test_paths
            ):
                violations.append(
                    f"{holdout.holdout_id}: {ref} is not referenced by any named test ref"
                )
                continue
            if resolved.suffix.lower() != ".json":
                continue
            try:
                violations.extend(_json_boundary_violations(load_json(resolved), ref))
            except ValueError as exc:
                violations.append(f"{ref}: invalid JSON ({exc})")
    return violations


def _holdout_evidence(
    holdout: SyntheticFixtureExpansionHoldoutSpec,
    *,
    repo_root: Path,
) -> HoldoutEvidence:
    fixture_text_parts: list[str] = []
    fixture_term_pointers: dict[str, list[str]] = {}
    verified_test_refs: list[str] = []
    test_text_parts: list[str] = []
    test_file_texts: dict[str, str] = {}

    for ref in holdout.fixture_refs:
        resolved = _resolve_repo_ref(repo_root, ref)
        if resolved is None or not resolved.exists() or resolved.suffix.lower() != ".json":
            continue
        try:
            texts, pointers = _json_text_and_pointers(load_json(resolved))
        except ValueError:
            continue
        fixture_text_parts.extend(texts)
        for term, refs in pointers.items():
            fixture_term_pointers.setdefault(_normalize_text(term), []).extend(refs)

    for test_ref in holdout.test_refs:
        resolved = _resolve_repo_ref(repo_root, test_ref)
        if resolved is None or not resolved.exists():
            continue
        body = _test_body_for_ref(resolved, test_ref)
        if body is None:
            continue
        verified_test_refs.append(test_ref)
        test_text_parts.append(body)
        test_file_texts[test_ref] = resolved.read_text(encoding="utf-8")

    binding_statuses: dict[str, str] = {}
    if not verified_test_refs:
        default_status = "missing_test"
    else:
        default_status = "listed_only"
    for ref in holdout.fixture_refs:
        resolved = _resolve_repo_ref(repo_root, ref)
        if resolved is None or not resolved.exists():
            binding_statuses[ref] = "missing_fixture"
            continue
        fixture_terms = _fixture_ref_terms(ref)
        if any(
            any(term in test_text for term in fixture_terms)
            for test_text in test_file_texts.values()
        ):
            binding_statuses[ref] = "bound"
        else:
            binding_statuses[ref] = default_status

    return HoldoutEvidence(
        holdout=holdout,
        manifest_text=_holdout_text(holdout),
        fixture_text=_normalize_text(" ".join(fixture_text_parts)),
        test_text=_normalize_text(" ".join(test_text_parts)),
        fixture_term_pointers=fixture_term_pointers,
        fixture_test_binding_statuses=binding_statuses,
        verified_test_refs=tuple(sorted(verified_test_refs)),
    )


def _matching_terms(text: str, terms: tuple[str, ...]) -> list[str]:
    return [term for term in terms if term.casefold() in text]


def _source_json_pointers_for_terms(
    evidence: HoldoutEvidence,
    terms: list[str],
) -> list[str]:
    pointers: list[str] = []
    for needle in terms:
        normalized_needle = _normalize_text(needle)
        for candidate, refs in evidence.fixture_term_pointers.items():
            if normalized_needle in candidate:
                pointers.extend(refs)
    return sorted(set(pointers))


def _dimension_for_requirement(
    requirement: DepthRequirement,
    holdout_evidence: dict[str, HoldoutEvidence],
) -> SyntheticFixtureDepthDimension:
    matched_holdout_ids: list[str] = []
    matched_terms: list[str] = []
    fixture_evidence_refs: list[str] = []
    test_evidence_refs: list[str] = []
    source_json_pointers: list[str] = []
    fixture_test_binding_statuses: dict[str, str] = {}
    test_refs_verified: list[str] = []
    prose_only_match_count = 0
    for holdout_id, evidence in holdout_evidence.items():
        structural_text = " ".join([evidence.fixture_text, evidence.test_text])
        manifest_plus_structural = " ".join([evidence.manifest_text, structural_text])
        structural_group_matches = [
            _matching_terms(structural_text, group) for group in requirement.required_term_groups
        ]
        prose_group_matches = [
            _matching_terms(manifest_plus_structural, group)
            for group in requirement.required_term_groups
        ]
        if all(prose_group_matches) and not all(structural_group_matches):
            prose_only_match_count += 1
        fixture_group_matches = [
            _matching_terms(evidence.fixture_text, group)
            for group in requirement.required_term_groups
        ]
        test_group_matches = [
            _matching_terms(evidence.test_text, group) for group in requirement.required_term_groups
        ]
        fixture_terms = sorted({term for group in fixture_group_matches for term in group})
        test_terms = sorted({term for group in test_group_matches for term in group})
        if all(structural_group_matches) and fixture_terms and test_terms:
            matched_holdout_ids.append(holdout_id)
            matched_terms.extend(term for group in structural_group_matches for term in group)
            fixture_evidence_refs.extend(evidence.holdout.fixture_refs)
            test_evidence_refs.extend(evidence.verified_test_refs)
            source_json_pointers.extend(_source_json_pointers_for_terms(evidence, fixture_terms))
        fixture_test_binding_statuses.update(
            {
                f"{holdout_id}:{ref}": status
                for ref, status in evidence.fixture_test_binding_statuses.items()
            }
        )
        test_refs_verified.extend(evidence.verified_test_refs)
    unique_terms = sorted(set(matched_terms))
    unique_holdouts = sorted(set(matched_holdout_ids))
    return SyntheticFixtureDepthDimension(
        dimension_id=requirement.dimension_id,
        family=requirement.family,
        danger_loop=requirement.danger_loop,
        description=requirement.description,
        status="covered" if unique_holdouts else "missing",
        matched_holdout_ids=unique_holdouts,
        matched_terms=unique_terms,
        required_term_groups=[list(group) for group in requirement.required_term_groups],
        fixture_evidence_refs=sorted(set(fixture_evidence_refs)),
        test_evidence_refs=sorted(set(test_evidence_refs)),
        source_json_pointers=sorted(set(source_json_pointers)),
        fixture_test_binding_statuses=fixture_test_binding_statuses,
        test_refs_verified=sorted(set(test_refs_verified)),
        prose_only_match_count=prose_only_match_count,
        why_it_matters=requirement.why_it_matters,
        remediation_hint=requirement.remediation_hint,
    )


def _family_summaries(
    *,
    manifest: SyntheticFixtureExpansionManifest,
    dimensions: list[SyntheticFixtureDepthDimension],
) -> list[SyntheticFixtureDepthFamilySummary]:
    families = sorted({holdout.family for holdout in manifest.holdouts} | {"cross_family"})
    summaries: list[SyntheticFixtureDepthFamilySummary] = []
    for family in families:
        family_dimensions = [dimension for dimension in dimensions if dimension.family == family]
        missing = [
            dimension.dimension_id
            for dimension in family_dimensions
            if dimension.status == "missing"
        ]
        summaries.append(
            SyntheticFixtureDepthFamilySummary(
                family=family,
                holdout_count=sum(1 for holdout in manifest.holdouts if holdout.family == family),
                covered_dimension_count=sum(
                    1 for dimension in family_dimensions if dimension.status == "covered"
                ),
                missing_dimension_count=len(missing),
                missing_dimension_ids=missing,
            )
        )
    return summaries


def _next_actions(
    *,
    missing_dimensions: list[SyntheticFixtureDepthDimension],
    boundary_violations: list[str],
) -> list[str]:
    if boundary_violations:
        return [
            "Remove or quarantine boundary-violating fixtures before using this manifest for review.",
            "Rerun audit-synthetic-fixture-expansion and audit-synthetic-fixture-depth.",
        ]
    if not missing_dimensions:
        return [
            "Use this depth report as candidate review evidence only.",
            "Do not approve calibration or learning without reviewed outcomes and owner gates.",
        ]
    return [
        f"{dimension.dimension_id}: {dimension.remediation_hint}"
        for dimension in missing_dimensions
    ]


def build_synthetic_fixture_depth_audit_report(
    *,
    manifest: SyntheticFixtureExpansionManifest,
    manifest_ref: str,
    repo_root: Path,
) -> SyntheticFixtureDepthAuditReport:
    holdout_evidence = {
        holdout.holdout_id: _holdout_evidence(holdout, repo_root=repo_root)
        for holdout in manifest.holdouts
    }
    dimensions = [
        _dimension_for_requirement(requirement, holdout_evidence)
        for requirement in DEPTH_REQUIREMENTS
    ]
    missing_dimensions = [dimension for dimension in dimensions if dimension.status == "missing"]
    boundary_violations = _boundary_violations(
        manifest=manifest,
        manifest_ref=manifest_ref,
        repo_root=repo_root,
    )
    if boundary_violations:
        status = "blocked_by_depth_audit_boundary_violation"
    elif missing_dimensions:
        status = "synthetic_fixture_depth_gaps_identified"
    else:
        status = "synthetic_fixture_depth_ready_for_review"
    return SyntheticFixtureDepthAuditReport(
        fixture_depth_audit_report_id=_stable_id(
            "syntheticfixturedepth",
            "|".join([manifest.manifest_id, ",".join(sorted(holdout_evidence))]),
        ),
        status=status,
        manifest_id=manifest.manifest_id,
        manifest_ref=manifest_ref,
        holdout_count=len(manifest.holdouts),
        dimension_count=len(dimensions),
        covered_dimension_count=sum(1 for dimension in dimensions if dimension.status == "covered"),
        missing_dimension_count=len(missing_dimensions),
        boundary_violation_count=len(boundary_violations),
        missing_dimension_ids=[dimension.dimension_id for dimension in missing_dimensions],
        boundary_violations=boundary_violations,
        family_summaries=_family_summaries(manifest=manifest, dimensions=dimensions),
        dimensions=dimensions,
        required_next_actions=_next_actions(
            missing_dimensions=missing_dimensions,
            boundary_violations=boundary_violations,
        ),
        generated_at=now_iso(),
    )


def render_synthetic_fixture_depth_audit_report(
    report: SyntheticFixtureDepthAuditReport,
) -> str:
    lines = [
        "# Synthetic Fixture Depth Audit Report",
        "",
        f"**Report ID:** {report.fixture_depth_audit_report_id}",
        f"**Status:** {report.status}",
        f"**Manifest:** `{report.manifest_ref}`",
        "",
        "## Summary",
        "",
        f"- Holdouts: {report.holdout_count}",
        f"- Dimensions: {report.dimension_count}",
        f"- Covered dimensions: {report.covered_dimension_count}",
        f"- Missing dimensions: {report.missing_dimension_count}",
        f"- Boundary violations: {report.boundary_violation_count}",
        "",
        "## Families",
        "",
    ]
    for family in report.family_summaries:
        missing = (
            ", ".join(family.missing_dimension_ids) if family.missing_dimension_ids else "none"
        )
        lines.append(
            f"- {family.family}: holdouts={family.holdout_count}; "
            f"covered={family.covered_dimension_count}; "
            f"missing={family.missing_dimension_count}; missing IDs={missing}"
        )
    lines.extend(["", "## Dimensions", ""])
    for dimension in report.dimensions:
        lines.extend(
            [
                f"### {dimension.dimension_id}",
                "",
                f"- Family: {dimension.family}",
                f"- Danger loop: {dimension.danger_loop}",
                f"- Status: {dimension.status}",
                f"- Matched holdouts: {', '.join(dimension.matched_holdout_ids) if dimension.matched_holdout_ids else 'none'}",
                f"- Matched terms: {', '.join(dimension.matched_terms) if dimension.matched_terms else 'none'}",
                f"- Fixture evidence refs: {', '.join(dimension.fixture_evidence_refs) if dimension.fixture_evidence_refs else 'none'}",
                f"- Test evidence refs: {', '.join(dimension.test_evidence_refs) if dimension.test_evidence_refs else 'none'}",
                f"- Source JSON pointers: {', '.join(dimension.source_json_pointers) if dimension.source_json_pointers else 'none'}",
                f"- Prose-only matches: {dimension.prose_only_match_count}",
                f"- Why it matters: {dimension.why_it_matters}",
                f"- Remediation: {dimension.remediation_hint}",
                "",
            ]
        )
        if dimension.fixture_test_binding_statuses:
            lines.append("- Fixture/test binding statuses:")
            lines.extend(
                f"  - {ref}: {status}"
                for ref, status in sorted(dimension.fixture_test_binding_statuses.items())
            )
            lines.append("")
    lines.extend(["## Boundary", ""])
    if report.boundary_violations:
        lines.extend(f"- {violation}" for violation in report.boundary_violations)
    else:
        lines.append("- No boundary violations detected.")
    lines.extend(["", "## Required Next Actions", ""])
    lines.extend(f"- {action}" for action in report.required_next_actions)
    lines.extend(
        [
            "",
            "This depth audit is local candidate evidence. It does not approve calibration, "
            "create PRs or issues, write sibling repos, admit Lake/SQLite records, perform "
            "external writes, mutate fixtures, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_synthetic_fixture_depth_audit(
    *,
    manifest_path: str | Path,
    repo_root: str | Path,
    out_dir: str | Path,
) -> tuple[SyntheticFixtureDepthAuditReport, Path]:
    manifest_ref = str(manifest_path)
    manifest = SyntheticFixtureExpansionManifest.model_validate(load_json(manifest_path))
    report = build_synthetic_fixture_depth_audit_report(
        manifest=manifest,
        manifest_ref=manifest_ref,
        repo_root=Path(repo_root).resolve(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / SYNTHETIC_FIXTURE_DEPTH_AUDIT_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / SYNTHETIC_FIXTURE_DEPTH_AUDIT_NOTES_FILENAME).write_text(
        render_synthetic_fixture_depth_audit_report(report),
        encoding="utf-8",
    )
    return report, run_dir
