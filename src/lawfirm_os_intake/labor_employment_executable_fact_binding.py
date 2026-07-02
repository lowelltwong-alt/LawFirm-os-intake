from __future__ import annotations

from pathlib import Path
from typing import Any

from .labor_employment_budget_facts import load_labor_employment_budget_fact_policy
from .models import (
    EvidenceRef,
    IntakePreflightPacket,
    LaborEmploymentExecutableBudgetFactBindingCase,
    LaborEmploymentExecutableBudgetFactBindingCaseSpec,
    LaborEmploymentExecutableBudgetFactBindingCheck,
    LaborEmploymentExecutableBudgetFactBindingItem,
    LaborEmploymentExecutableBudgetFactBindingItemSpec,
    LaborEmploymentExecutableBudgetFactBindingManifest,
    LaborEmploymentExecutableBudgetFactBindingReport,
    LaborEmploymentExecutableFixtureAuditCase,
    LaborEmploymentExecutableFixtureAuditReport,
    Segment,
)
from .util import digest_text, load_json, now_iso, write_json


LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME = (
    "labor_employment_executable_fact_binding_report.json"
)
LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_NOTES_FILENAME = (
    "labor_employment_executable_fact_binding_report.md"
)

DEFAULT_BINDING_MANIFEST_REF = (
    "examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json"
)

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_fact_review",
    "build_labor_employment_budget_fact_audit_before_budget_precondition",
    "no_amount_budget_from_binding_report",
    "no_lake_or_sqlite_write_from_binding_report",
    "no_role_taxonomy_promotion_from_binding_report",
]


def run_labor_employment_executable_fact_binding_audit(
    *,
    binding_manifest_path: str | Path,
    executable_fixture_report_path: str | Path,
    repo_root: str | Path,
    out_dir: str | Path,
    fact_policy_path: str | Path | None = None,
) -> tuple[LaborEmploymentExecutableBudgetFactBindingReport, Path]:
    root = Path(repo_root).resolve()
    binding_manifest = LaborEmploymentExecutableBudgetFactBindingManifest.model_validate(
        load_json(binding_manifest_path)
    )
    fixture_report = LaborEmploymentExecutableFixtureAuditReport.model_validate(
        load_json(executable_fixture_report_path)
    )
    policy_ref = str(fact_policy_path or binding_manifest.fact_policy_ref)
    policy = load_labor_employment_budget_fact_policy(_resolve_repo_ref(root, policy_ref))
    fact_needs = {
        str(fact_need["fact_id"]): fact_need
        for fact_need in policy["fact_needs"]
        if isinstance(fact_need, dict) and "fact_id" in fact_need
    }
    fixture_cases = {case.executable_fixture_id: case for case in fixture_report.cases}

    cases = [
        _case_from_spec(
            root=root,
            spec=case_spec,
            executable_case=fixture_cases.get(case_spec.executable_fixture_id),
            fact_needs=fact_needs,
        )
        for case_spec in binding_manifest.bindings
    ]
    checks = _checks(
        binding_manifest=binding_manifest,
        fixture_report=fixture_report,
        cases=cases,
    )
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    report = LaborEmploymentExecutableBudgetFactBindingReport(
        executable_budget_fact_binding_report_id=_stable_id(
            "leexecfactbinding",
            "|".join(
                [
                    binding_manifest.manifest_id,
                    fixture_report.executable_fixture_audit_report_id,
                    *[
                        f"{case.executable_fixture_id}:{case.status}:{case.fact_binding_count}"
                        for case in cases
                    ],
                ]
            ),
        ),
        status=(
            "blocked_by_labor_employment_executable_budget_fact_bindings"
            if failed_cases or failed_checks
            else "labor_employment_executable_budget_fact_bindings_ready_for_review"
        ),
        binding_manifest_id=binding_manifest.manifest_id,
        binding_manifest_ref=str(binding_manifest_path),
        executable_fixture_report_ref=str(executable_fixture_report_path),
        fact_policy_ref=policy_ref,
        case_count=len(cases),
        failed_case_count=len(failed_cases),
        fact_binding_count=sum(case.fact_binding_count for case in cases),
        critical_fact_binding_count=sum(case.critical_fact_binding_count for case in cases),
        evidence_bound_fact_count=sum(case.evidence_bound_fact_count for case in cases),
        exception_bound_fact_count=sum(case.exception_bound_fact_count for case in cases),
        missing_policy_fact_count=sum(len(case.missing_policy_fact_ids) for case in cases),
        missing_source_signal_count=sum(
            len(binding.missing_source_signal_terms)
            for case in cases
            for binding in case.fact_bindings
        ),
        missing_exception_label_count=sum(
            len(binding.missing_exception_labels)
            for case in cases
            for binding in case.fact_bindings
        ),
        missing_source_id_count=sum(
            len(binding.missing_source_ids) for case in cases for binding in case.fact_bindings
        ),
        cases=cases,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FACT_BINDING_NOTES_FILENAME).write_text(
        render_labor_employment_executable_fact_binding_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_labor_employment_executable_fact_binding_report(
    report: LaborEmploymentExecutableBudgetFactBindingReport,
) -> str:
    lines = [
        "# Labor/Employment Executable Budget Fact Binding Report",
        "",
        f"**Report ID:** {report.executable_budget_fact_binding_report_id}",
        f"**Status:** {report.status}",
        f"**Binding manifest:** `{report.binding_manifest_ref}`",
        f"**Executable fixture report:** `{report.executable_fixture_report_ref}`",
        f"**Fact policy:** `{report.fact_policy_ref}`",
        "",
        "## Summary",
        "",
        f"- Cases: {report.case_count}",
        f"- Failed cases: {report.failed_case_count}",
        f"- Fact bindings: {report.fact_binding_count}",
        f"- Critical fact bindings: {report.critical_fact_binding_count}",
        f"- Evidence-bound facts: {report.evidence_bound_fact_count}",
        f"- Exception-bound facts: {report.exception_bound_fact_count}",
        f"- Missing source signals: {report.missing_source_signal_count}",
        "",
        "## Cases",
        "",
    ]
    for case in report.cases:
        lines.extend(
            [
                f"### {case.executable_fixture_id}",
                "",
                f"- Status: {case.status}",
                f"- Binding case: `{case.binding_case_id}`",
                f"- Preflight packet: `{case.preflight_packet_ref or 'missing'}`",
                f"- Expected readiness: {case.expected_budget_readiness_state}",
                f"- Expected gate: {case.expected_budget_gate_effect}",
                f"- Expected treatment: {case.expected_budget_treatment}",
                f"- Fact bindings: {case.fact_binding_count}",
                f"- Critical bindings: {case.critical_fact_binding_count}",
                f"- Evidence-bound facts: {case.evidence_bound_fact_count}",
                f"- Exception-bound facts: {case.exception_bound_fact_count}",
            ]
        )
        if case.failed_expectation_ids:
            lines.append(
                "- Failed expectations: "
                + ", ".join(f"`{item}`" for item in case.failed_expectation_ids)
            )
        for binding in case.fact_bindings:
            lines.append(
                f"- `{binding.fact_id}`: {binding.binding_state}; "
                f"level={binding.required_level}; "
                f"missing_terms={', '.join(binding.missing_source_signal_terms) or 'none'}; "
                f"missing_labels={', '.join(binding.missing_exception_labels) or 'none'}"
            )
        lines.extend(["- Notes:", *(f"  - {note}" for note in case.notes), ""])
    lines.extend(["## Checks", ""])
    for check in report.checks:
        blocking = (
            "; blocking refs=" + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
            if check.blocking_refs
            else ""
        )
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{blocking}")
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This report binds executable synthetic preflight fixtures to expected "
            "L&E budget fact gaps. It does not resolve those facts, generate an "
            "amount budget, write Lake/SQLite records, submit budgets, open matters, "
            "or promote role taxonomy.",
            "",
        ]
    )
    return "\n".join(lines)


def _case_from_spec(
    *,
    root: Path,
    spec: LaborEmploymentExecutableBudgetFactBindingCaseSpec,
    executable_case: LaborEmploymentExecutableFixtureAuditCase | None,
    fact_needs: dict[str, dict[str, Any]],
) -> LaborEmploymentExecutableBudgetFactBindingCase:
    failed_expectation_ids: list[str] = []
    notes = [
        "Binding report validates expected budget fact gaps against preflight evidence; it does not resolve facts.",
    ]
    if executable_case is None:
        failed_expectation_ids.append("executable_fixture_case_missing")
        packet = None
        packet_ref = None
    else:
        packet_ref = executable_case.preflight_packet_ref
        packet = _load_packet(root, packet_ref)
        if executable_case.status != "passed":
            failed_expectation_ids.append("executable_fixture_case_not_passed")
        if packet is None:
            failed_expectation_ids.append("preflight_packet_missing_or_invalid")
        if executable_case.expected_budget_readiness_state != spec.expected_budget_readiness_state:
            failed_expectation_ids.append("budget_readiness_expectation_drift")
        if executable_case.expected_budget_gate_effect != spec.expected_budget_gate_effect:
            failed_expectation_ids.append("budget_gate_expectation_drift")
        if executable_case.expected_budget_treatment != spec.expected_budget_treatment:
            failed_expectation_ids.append("budget_treatment_expectation_drift")

    fact_bindings: list[LaborEmploymentExecutableBudgetFactBindingItem] = []
    missing_policy_fact_ids: list[str] = []
    for binding_spec in spec.fact_bindings:
        fact_need = fact_needs.get(binding_spec.fact_id)
        if fact_need is None:
            missing_policy_fact_ids.append(binding_spec.fact_id)
            continue
        fact_bindings.append(
            _binding_item(
                packet=packet,
                executable_case=executable_case,
                binding_spec=binding_spec,
                fact_need=fact_need,
            )
        )

    failed_expectation_ids.extend(_binding_failures(fact_bindings))
    critical_fact_count = sum(
        1 for binding in fact_bindings if binding.required_level == "critical"
    )
    if (
        critical_fact_count
        and spec.expected_budget_readiness_state != "blocked_missing_critical_facts"
    ):
        failed_expectation_ids.append("critical_gap_without_blocked_readiness")
    if (
        critical_fact_count
        and spec.expected_budget_gate_effect != "block_amount_budget_before_proposal"
    ):
        failed_expectation_ids.append("critical_gap_without_amount_budget_block")
    status = "failed" if failed_expectation_ids or missing_policy_fact_ids else "passed"
    if critical_fact_count:
        notes.append(
            "At least one critical L&E budget fact is bound as a gap; amount budget stays blocked."
        )
    return LaborEmploymentExecutableBudgetFactBindingCase(
        binding_case_id=spec.binding_case_id,
        executable_fixture_id=spec.executable_fixture_id,
        status=status,
        preflight_packet_ref=packet_ref,
        executable_fixture_report_case_status=executable_case.status if executable_case else None,
        expected_budget_readiness_state=spec.expected_budget_readiness_state,
        executable_expected_budget_readiness_state=(
            executable_case.expected_budget_readiness_state if executable_case else None
        ),
        expected_budget_gate_effect=spec.expected_budget_gate_effect,
        executable_expected_budget_gate_effect=(
            executable_case.expected_budget_gate_effect if executable_case else None
        ),
        expected_budget_treatment=spec.expected_budget_treatment,
        executable_expected_budget_treatment=(
            executable_case.expected_budget_treatment if executable_case else None
        ),
        fact_binding_count=len(fact_bindings),
        critical_fact_binding_count=critical_fact_count,
        evidence_bound_fact_count=sum(1 for binding in fact_bindings if binding.evidence_refs),
        exception_bound_fact_count=sum(
            1 for binding in fact_bindings if binding.matched_exception_labels
        ),
        missing_policy_fact_ids=missing_policy_fact_ids,
        failed_expectation_ids=sorted(set(failed_expectation_ids)),
        fact_bindings=fact_bindings,
        notes=notes,
    )


def _binding_item(
    *,
    packet: IntakePreflightPacket | None,
    executable_case: LaborEmploymentExecutableFixtureAuditCase | None,
    binding_spec: LaborEmploymentExecutableBudgetFactBindingItemSpec,
    fact_need: dict[str, Any],
) -> LaborEmploymentExecutableBudgetFactBindingItem:
    evidence_refs: list[EvidenceRef] = []
    matched_terms: list[str] = []
    if packet is not None:
        for term in binding_spec.source_signal_terms:
            refs = _segment_refs_for_term(packet.segments, term)
            if refs:
                matched_terms.append(term)
                evidence_refs.extend(refs)
    evidence_refs = _dedup_refs(evidence_refs)
    exception_labels = set(executable_case.exception_labels if executable_case else [])
    matched_exception_labels = sorted(
        label for label in binding_spec.expected_exception_labels if label in exception_labels
    )
    source_ids = {item.source_id for item in packet.source_inventory} if packet else set()
    matched_source_ids = sorted(
        source_id for source_id in binding_spec.expected_source_ids if source_id in source_ids
    )
    source_inventory_refs = matched_source_ids[:]
    missing_terms = sorted(set(binding_spec.source_signal_terms) - set(matched_terms))
    missing_labels = sorted(
        set(binding_spec.expected_exception_labels) - set(matched_exception_labels)
    )
    missing_source_ids = sorted(set(binding_spec.expected_source_ids) - set(matched_source_ids))
    binding_state = _binding_state(
        evidence_refs=evidence_refs,
        matched_exception_labels=matched_exception_labels,
        source_inventory_refs=source_inventory_refs,
    )
    required_level = str(fact_need.get("required_level", "context"))
    return LaborEmploymentExecutableBudgetFactBindingItem(
        fact_id=binding_spec.fact_id,
        fact_category=fact_need["fact_category"],
        required_level=required_level,  # type: ignore[arg-type]
        question=str(fact_need["question"]),
        expected_gap_type=binding_spec.expected_gap_type,
        binding_state=binding_state,
        recommended_budget_treatment=fact_need.get(
            "recommended_budget_treatment",
            "hours_only_or_broad_range",
        ),
        budget_effects=[str(effect) for effect in fact_need.get("budget_effects", [])],
        source_signal_terms=binding_spec.source_signal_terms,
        matched_source_signal_terms=matched_terms,
        missing_source_signal_terms=missing_terms,
        expected_exception_labels=binding_spec.expected_exception_labels,
        matched_exception_labels=matched_exception_labels,
        missing_exception_labels=missing_labels,
        expected_source_ids=binding_spec.expected_source_ids,
        matched_source_ids=matched_source_ids,
        missing_source_ids=missing_source_ids,
        evidence_refs=evidence_refs,
        source_inventory_refs=source_inventory_refs,
        blocks_precise_budget=required_level == "critical",
        human_confirmation_required=bool(fact_need.get("human_confirmation_required", True)),
        reason=binding_spec.reason,
    )


def _binding_failures(
    fact_bindings: list[LaborEmploymentExecutableBudgetFactBindingItem],
) -> list[str]:
    failures: list[str] = []
    for binding in fact_bindings:
        prefix = binding.fact_id
        if binding.binding_state == "unbound_gap_candidate":
            failures.append(f"{prefix}:unbound_gap_candidate")
        if binding.missing_source_signal_terms:
            failures.append(f"{prefix}:missing_source_signal_terms")
        if binding.missing_exception_labels:
            failures.append(f"{prefix}:missing_exception_labels")
        if binding.missing_source_ids:
            failures.append(f"{prefix}:missing_source_ids")
    return failures


def _checks(
    *,
    binding_manifest: LaborEmploymentExecutableBudgetFactBindingManifest,
    fixture_report: LaborEmploymentExecutableFixtureAuditReport,
    cases: list[LaborEmploymentExecutableBudgetFactBindingCase],
) -> list[LaborEmploymentExecutableBudgetFactBindingCheck]:
    failed_cases = [case.executable_fixture_id for case in cases if case.status == "failed"]
    unbound = [
        f"{case.executable_fixture_id}:{binding.fact_id}"
        for case in cases
        for binding in case.fact_bindings
        if binding.binding_state == "unbound_gap_candidate"
    ]
    missing_policy = [
        f"{case.executable_fixture_id}:{fact_id}"
        for case in cases
        for fact_id in case.missing_policy_fact_ids
    ]
    side_effects = [
        flag
        for flag in [
            "budget_amount_output_authorized",
            "budget_submission_authorized",
            "conflict_conclusion_emitted",
            "matter_opening_authorized",
            "training_pipeline_created",
            "lake_write_performed",
            "sqlite_write_performed",
            "external_writes_performed",
            "silent_learning_performed",
        ]
        if getattr(binding_manifest, flag) is not False
        or getattr(fixture_report, flag) is not False
    ]
    return [
        _check(
            "binding_manifest_candidate_only",
            binding_manifest.synthetic_only
            and binding_manifest.candidate_only
            and not binding_manifest.external_writes_performed,
            "Binding manifest remains synthetic/candidate-only and no-write.",
            evidence_refs=[binding_manifest.manifest_id],
        ),
        _check(
            "executable_fixture_report_ready",
            fixture_report.status == "labor_employment_executable_fixtures_ready_for_review",
            "Executable fixture report is ready before fact binding is trusted.",
            evidence_refs=[fixture_report.executable_fixture_audit_report_id],
            blocking_refs=[]
            if fixture_report.status.endswith("ready_for_review")
            else [fixture_report.status],
        ),
        _check(
            "all_bound_facts_exist_in_policy",
            not missing_policy,
            "Every bound fact ID exists in the candidate L&E fact-needs policy.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=missing_policy,
        ),
        _check(
            "all_fact_bindings_have_preflight_anchors",
            not unbound,
            "Every fact binding is anchored by source text, exception labels, or source inventory.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=unbound,
        ),
        _check(
            "no_side_effect_boundaries_crossed",
            not side_effects,
            "Binding report did not authorize or perform budget, matter, Lake, SQLite, external, or learning actions.",
            evidence_refs=[
                binding_manifest.manifest_id,
                fixture_report.executable_fixture_audit_report_id,
            ],
            blocking_refs=side_effects,
        ),
        _check(
            "case_statuses_pass",
            not failed_cases,
            "Every executable budget-fact binding case matched deterministic expectations.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=failed_cases,
        ),
    ]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    evidence_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> LaborEmploymentExecutableBudgetFactBindingCheck:
    return LaborEmploymentExecutableBudgetFactBindingCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs or [],
        blocking_refs=blocking_refs or ([] if passed else evidence_refs or []),
    )


def _load_packet(root: Path, ref: str | None) -> IntakePreflightPacket | None:
    if ref is None:
        return None
    try:
        return IntakePreflightPacket.model_validate(load_json(_resolve_run_ref(root, ref)))
    except (OSError, ValueError):
        return None


def _segment_refs_for_term(segments: list[Segment], term: str) -> list[EvidenceRef]:
    lowered = term.casefold()
    return [_evidence_ref(segment) for segment in segments if lowered in segment.text.casefold()]


def _evidence_ref(segment: Segment) -> EvidenceRef:
    return EvidenceRef(
        source_id=segment.source_id,
        segment_id=segment.segment_id,
        start_offset=segment.start_offset,
        end_offset=segment.end_offset,
        sha256=segment.sha256,
    )


def _dedup_refs(refs: list[EvidenceRef]) -> list[EvidenceRef]:
    dedup: dict[tuple[str, str, int, int, str], EvidenceRef] = {}
    for ref in refs:
        dedup[(ref.source_id, ref.segment_id, ref.start_offset, ref.end_offset, ref.sha256)] = ref
    return list(dedup.values())


def _binding_state(
    *,
    evidence_refs: list[EvidenceRef],
    matched_exception_labels: list[str],
    source_inventory_refs: list[str],
) -> str:
    if evidence_refs and matched_exception_labels:
        return "source_and_exception_bound_gap_candidate"
    if evidence_refs:
        return "source_bound_gap_candidate"
    if matched_exception_labels:
        return "exception_bound_gap_candidate"
    if source_inventory_refs:
        return "inventory_bound_gap_candidate"
    return "unbound_gap_candidate"


def _resolve_repo_ref(root: Path, ref: str | Path) -> Path:
    path = Path(ref)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"repository reference escapes repo root: {ref}")
    return resolved


def _resolve_run_ref(root: Path, ref: str | Path) -> Path:
    path = Path(ref)
    return path if path.is_absolute() else root / path


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"
