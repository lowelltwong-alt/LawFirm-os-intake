from __future__ import annotations

from pathlib import Path

from .models import (
    LaborEmploymentExecutableFixtureAuditCase,
    LaborEmploymentExecutableFixtureAuditCheck,
    LaborEmploymentExecutableFixtureAuditReport,
    LaborEmploymentExecutableFixtureManifest,
    LaborEmploymentExecutableFixtureSpec,
    LaborEmploymentSyntheticFixtureCase,
    LaborEmploymentSyntheticFixtureFamilyPack,
    SourceBundle,
)
from .util import digest_text, load_json, load_jsonl, now_iso, write_json
from .workflow import run_preflight


LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME = (
    "labor_employment_executable_fixtures_report.json"
)
LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_NOTES_FILENAME = (
    "labor_employment_executable_fixtures_report.md"
)

REQUIRED_NEXT_GATES = [
    "human_labor_employment_budget_fact_review",
    "preflight_to_budget_fact_fixture_binding",
    "no_amount_budget_from_preflight_only",
    "no_real_public_payload_or_identity_reconstruction",
    "no_lake_or_sqlite_write_from_executable_fixtures",
]


def run_labor_employment_executable_fixture_audit(
    *,
    manifest_path: str | Path,
    repo_root: str | Path,
    out_dir: str | Path,
    pack_path: str | Path | None = None,
) -> tuple[LaborEmploymentExecutableFixtureAuditReport, Path]:
    root = Path(repo_root).resolve()
    manifest_ref = str(manifest_path)
    manifest = LaborEmploymentExecutableFixtureManifest.model_validate(load_json(manifest_path))
    resolved_pack_path = (
        _resolve_repo_ref(root, pack_path)
        if pack_path
        else _resolve_repo_ref(root, manifest.pack_ref)
    )
    pack = LaborEmploymentSyntheticFixtureFamilyPack.model_validate(load_json(resolved_pack_path))
    pack_cases = {case.case_id: case for case in pack.cases}
    profile_path = _resolve_repo_ref(root, manifest.practice_profile_ref)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    cases = [
        _audit_case(
            root=root,
            run_dir=run_dir,
            spec=spec,
            pack_cases=pack_cases,
            profile_path=profile_path,
        )
        for spec in manifest.fixtures
    ]
    checks = _checks(manifest=manifest, cases=cases)
    failed_cases = [case for case in cases if case.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    report = LaborEmploymentExecutableFixtureAuditReport(
        executable_fixture_audit_report_id=_stable_id(
            "leexecfixtures",
            "|".join(
                [
                    manifest.manifest_id,
                    *[
                        f"{case.executable_fixture_id}:{case.status}:{case.segment_count}"
                        for case in cases
                    ],
                ]
            ),
        ),
        status=(
            "blocked_by_labor_employment_executable_fixtures"
            if failed_cases or failed_checks
            else "labor_employment_executable_fixtures_ready_for_review"
        ),
        manifest_id=manifest.manifest_id,
        manifest_ref=manifest_ref,
        pack_ref=str(resolved_pack_path),
        practice_profile_ref=str(profile_path),
        fixture_count=len(cases),
        preflight_executed_count=sum(1 for case in cases if case.preflight_packet_ref),
        failed_case_count=len(failed_cases),
        missing_pack_link_count=sum(len(case.missing_pack_case_ids) for case in cases),
        missing_source_signal_count=sum(len(case.missing_source_signal_terms) for case in cases),
        missing_expected_exception_label_count=sum(
            len(case.missing_expected_exception_labels) for case in cases
        ),
        cases=cases,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    write_json(
        run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / LABOR_EMPLOYMENT_EXECUTABLE_FIXTURE_AUDIT_NOTES_FILENAME).write_text(
        render_labor_employment_executable_fixture_audit_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_labor_employment_executable_fixture_audit_report(
    report: LaborEmploymentExecutableFixtureAuditReport,
) -> str:
    lines = [
        "# Labor/Employment Executable Fixtures Report",
        "",
        f"**Report ID:** {report.executable_fixture_audit_report_id}",
        f"**Status:** {report.status}",
        f"**Manifest:** `{report.manifest_ref}`",
        f"**Pack:** `{report.pack_ref}`",
        f"**Practice profile:** `{report.practice_profile_ref}`",
        "",
        "## Summary",
        "",
        f"- Fixtures: {report.fixture_count}",
        f"- Preflights executed: {report.preflight_executed_count}",
        f"- Failed cases: {report.failed_case_count}",
        f"- Missing pack links: {report.missing_pack_link_count}",
        f"- Missing source signals: {report.missing_source_signal_count}",
        f"- Missing expected preflight exception labels: {report.missing_expected_exception_label_count}",
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
                f"- Source bundle: `{case.source_bundle_ref}`",
                f"- Pack case links: {', '.join(f'`{ref}`' for ref in case.linked_pack_case_ids)}",
                f"- Family/variant: {case.family}/{case.variant}",
                f"- Preflight packet: `{case.preflight_packet_ref or 'not executed'}`",
                f"- Sources/segments: {case.source_count}/{case.segment_count}",
                f"- Missing/duplicate sources: {case.missing_source_count}/{case.duplicate_source_count}",
                f"- Exception labels: {', '.join(case.exception_labels) if case.exception_labels else 'none'}",
                f"- Expected budget gate: {case.expected_budget_gate_effect}",
                f"- Expected budget treatment: {case.expected_budget_treatment}",
                f"- Budget fact audit required: {case.budget_fact_audit_required}",
            ]
        )
        if case.missing_expected_exception_labels:
            lines.append(
                "- Missing expected labels: "
                + ", ".join(f"`{label}`" for label in case.missing_expected_exception_labels)
            )
        if case.missing_source_signal_terms:
            lines.append(
                "- Missing source signals: "
                + ", ".join(f"`{term}`" for term in case.missing_source_signal_terms)
            )
        if case.failed_expectation_ids:
            lines.append(
                "- Failed expectations: "
                + ", ".join(f"`{item}`" for item in case.failed_expectation_ids)
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
            "This report proves only that selected synthetic L&E source bundles are "
            "runnable through deterministic preflight. It does not produce an amount "
            "budget, approve calibration, write Lake/SQLite records, open matters, "
            "submit budgets, or authorize learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _audit_case(
    *,
    root: Path,
    run_dir: Path,
    spec: LaborEmploymentExecutableFixtureSpec,
    pack_cases: dict[str, LaborEmploymentSyntheticFixtureCase],
    profile_path: Path,
) -> LaborEmploymentExecutableFixtureAuditCase:
    missing_pack_case_ids = [
        case_id for case_id in spec.linked_pack_case_ids if case_id not in pack_cases
    ]
    mismatches = _pack_family_variant_mismatches(spec, pack_cases)
    failed_expectation_ids: list[str] = []
    notes: list[str] = []

    try:
        bundle_path = _resolve_repo_ref(root, spec.source_bundle_ref)
        bundle = SourceBundle.model_validate(load_json(bundle_path))
    except Exception as exc:  # noqa: BLE001 - report validation failures as candidate QA.
        failed_expectation_ids.append("source_bundle_load_failed")
        return _failed_case_from_load_error(
            spec=spec,
            missing_pack_case_ids=missing_pack_case_ids,
            mismatches=mismatches,
            failed_expectation_ids=failed_expectation_ids,
            exc=exc,
        )

    if (
        bundle.data_origin != "synthetic"
        or bundle.contains_real_client_data
        or bundle.contains_real_matter_data
        or bundle.contains_privileged_data
    ):
        failed_expectation_ids.append("source_bundle_not_synthetic_only")

    preflight_packet_ref: str | None = None
    data_scope_gate_report_ref: str | None = None
    intake_review_form_ref: str | None = None
    exception_labels: list[str] = []
    source_count = 0
    segment_count = 0
    source_hash_count = 0
    missing_source_count = 0
    duplicate_source_count = 0
    party_candidate_count = 0
    matter_candidate_count = 0
    deadline_candidate_count = 0
    prohibited_next_step_count = 0

    try:
        packet, preflight_dir = run_preflight(
            input_path=bundle_path,
            profile_path=profile_path,
            out_dir=run_dir / "preflight" / _safe_dirname(spec.executable_fixture_id),
            adapter="deterministic",
            strict_evidence=True,
        )
        preflight_packet_ref = str(preflight_dir / "intake_preflight_packet.json")
        data_scope_gate_report_ref = str(preflight_dir / "data_scope_gate_report.json")
        intake_review_form_ref = str(preflight_dir / "intake_review_form.md")
        source_count = len(packet.source_inventory)
        segment_count = len(packet.segments)
        source_hash_count = len({item.source_sha256 for item in packet.source_inventory})
        missing_source_count = sum(
            1 for item in packet.source_inventory if item.read_state == "missing"
        )
        duplicate_source_count = sum(
            1 for item in packet.source_inventory if item.availability_state == "duplicate"
        )
        party_candidate_count = len(packet.party_candidates)
        matter_candidate_count = len(packet.matter_family_candidates)
        deadline_candidate_count = len(packet.deadline_candidates)
        prohibited_next_step_count = len(packet.prohibited_next_steps)
        exception_labels = sorted(
            {
                str(candidate.get("local_event_label"))
                for candidate in load_jsonl(preflight_dir / "exception_lake_candidates.jsonl")
                if isinstance(candidate, dict) and candidate.get("local_event_label")
            }
        )
        if packet.status != "human_intake_review_required":
            failed_expectation_ids.append("preflight_status_not_human_review_required")
    except Exception as exc:  # noqa: BLE001 - report validation failures as candidate QA.
        notes.append(f"Preflight execution failed: {exc}")
        failed_expectation_ids.append("preflight_execution_failed")

    if source_count < spec.expected_min_sources:
        failed_expectation_ids.append("source_count_below_expected")
    if segment_count < spec.expected_min_segments:
        failed_expectation_ids.append("segment_count_below_expected")
    if missing_source_count < spec.expected_min_missing_sources:
        failed_expectation_ids.append("missing_source_count_below_expected")
    if duplicate_source_count < spec.expected_min_duplicate_sources:
        failed_expectation_ids.append("duplicate_source_count_below_expected")

    missing_terms = _missing_terms(bundle, spec.expected_source_signal_terms)
    missing_expected_exception_labels = sorted(
        set(spec.expected_preflight_exception_labels) - set(exception_labels)
    )
    notes.extend(
        [
            "Preflight source mechanics only; L&E budget fact audit remains a required next gate.",
            f"Expected fact gaps: {', '.join(spec.expected_budget_fact_gap_ids) or 'none'}.",
        ]
    )
    if exception_labels:
        notes.append("Observed exception labels are dry-run candidates only.")

    failed = bool(
        failed_expectation_ids
        or missing_terms
        or missing_expected_exception_labels
        or missing_pack_case_ids
        or mismatches
    )
    return LaborEmploymentExecutableFixtureAuditCase(
        executable_fixture_id=spec.executable_fixture_id,
        source_bundle_ref=spec.source_bundle_ref,
        linked_pack_case_ids=spec.linked_pack_case_ids,
        family=spec.family,
        variant=spec.variant,
        status="failed" if failed else "passed",
        preflight_packet_ref=preflight_packet_ref,
        data_scope_gate_report_ref=data_scope_gate_report_ref,
        intake_review_form_ref=intake_review_form_ref,
        source_count=source_count,
        segment_count=segment_count,
        source_hash_count=source_hash_count,
        missing_source_count=missing_source_count,
        duplicate_source_count=duplicate_source_count,
        party_candidate_count=party_candidate_count,
        matter_candidate_count=matter_candidate_count,
        deadline_candidate_count=deadline_candidate_count,
        prohibited_next_step_count=prohibited_next_step_count,
        exception_labels=exception_labels,
        missing_expected_exception_labels=missing_expected_exception_labels,
        missing_source_signal_terms=missing_terms,
        missing_pack_case_ids=missing_pack_case_ids,
        pack_family_variant_mismatch_case_ids=mismatches,
        failed_expectation_ids=failed_expectation_ids,
        expected_budget_readiness_state=spec.expected_budget_readiness_state,
        expected_budget_gate_effect=spec.expected_budget_gate_effect,
        expected_budget_treatment=spec.expected_budget_treatment,
        expected_budget_fact_gap_ids=spec.expected_budget_fact_gap_ids,
        notes=notes,
    )


def _failed_case_from_load_error(
    *,
    spec: LaborEmploymentExecutableFixtureSpec,
    missing_pack_case_ids: list[str],
    mismatches: list[str],
    failed_expectation_ids: list[str],
    exc: Exception,
) -> LaborEmploymentExecutableFixtureAuditCase:
    return LaborEmploymentExecutableFixtureAuditCase(
        executable_fixture_id=spec.executable_fixture_id,
        source_bundle_ref=spec.source_bundle_ref,
        linked_pack_case_ids=spec.linked_pack_case_ids,
        family=spec.family,
        variant=spec.variant,
        status="failed",
        source_count=0,
        segment_count=0,
        source_hash_count=0,
        missing_source_count=0,
        duplicate_source_count=0,
        party_candidate_count=0,
        matter_candidate_count=0,
        deadline_candidate_count=0,
        prohibited_next_step_count=0,
        exception_labels=[],
        missing_expected_exception_labels=spec.expected_preflight_exception_labels,
        missing_source_signal_terms=spec.expected_source_signal_terms,
        missing_pack_case_ids=missing_pack_case_ids,
        pack_family_variant_mismatch_case_ids=mismatches,
        failed_expectation_ids=failed_expectation_ids,
        expected_budget_readiness_state=spec.expected_budget_readiness_state,
        expected_budget_gate_effect=spec.expected_budget_gate_effect,
        expected_budget_treatment=spec.expected_budget_treatment,
        expected_budget_fact_gap_ids=spec.expected_budget_fact_gap_ids,
        notes=[f"Source bundle could not be loaded or validated: {exc}"],
    )


def _checks(
    *,
    manifest: LaborEmploymentExecutableFixtureManifest,
    cases: list[LaborEmploymentExecutableFixtureAuditCase],
) -> list[LaborEmploymentExecutableFixtureAuditCheck]:
    failed_cases = [case.executable_fixture_id for case in cases if case.status == "failed"]
    missing_pack_links = [case_id for case in cases for case_id in case.missing_pack_case_ids]
    missing_exception_labels = [
        f"{case.executable_fixture_id}:{label}"
        for case in cases
        for label in case.missing_expected_exception_labels
    ]
    failed_expectations = [
        f"{case.executable_fixture_id}:{expectation}"
        for case in cases
        for expectation in case.failed_expectation_ids
    ]
    missing_terms = [
        f"{case.executable_fixture_id}:{term}"
        for case in cases
        for term in case.missing_source_signal_terms
    ]
    return [
        _check(
            "manifest_synthetic_only",
            manifest.synthetic_only
            and manifest.candidate_only
            and not manifest.external_writes_performed
            and not manifest.lake_write_performed
            and not manifest.sqlite_write_performed,
            "Executable fixture manifest remains synthetic/candidate-only and no-write.",
            evidence_refs=[manifest.manifest_id],
        ),
        _check(
            "pack_case_links_valid",
            not missing_pack_links,
            "Every executable fixture links to an existing L&E fixture-family pack case.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=missing_pack_links,
        ),
        _check(
            "preflight_execution_complete",
            all(case.preflight_packet_ref for case in cases),
            "Every executable fixture produced an intake_preflight_packet.json.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=[
                case.executable_fixture_id for case in cases if not case.preflight_packet_ref
            ],
        ),
        _check(
            "source_signals_observed",
            not missing_terms,
            "Expected L&E source terms are present in the synthetic source bundles.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=missing_terms,
        ),
        _check(
            "preflight_exception_labels_observed",
            not missing_exception_labels,
            "Expected deterministic preflight exception labels were emitted.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=missing_exception_labels,
        ),
        _check(
            "numeric_expectations_hold",
            not failed_expectations,
            "Source, segment, missing-source, and duplicate-source thresholds held.",
            evidence_refs=[case.executable_fixture_id for case in cases],
            blocking_refs=failed_expectations,
        ),
        _check(
            "no_side_effect_boundaries_crossed",
            all(
                not case.lake_write_performed
                and not case.sqlite_write_performed
                and not case.external_writes_performed
                and not case.budget_submission_authorized
                and not case.matter_opening_authorized
                and not case.training_pipeline_created
                for case in cases
            ),
            "Executable fixture audit did not write Lake/SQLite, submit budgets, open matters, or create training.",
            evidence_refs=[case.executable_fixture_id for case in cases],
        ),
        _check(
            "case_statuses_pass",
            not failed_cases,
            "Every executable fixture matched deterministic audit expectations.",
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
) -> LaborEmploymentExecutableFixtureAuditCheck:
    return LaborEmploymentExecutableFixtureAuditCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        evidence_refs=evidence_refs or [],
        blocking_refs=blocking_refs or ([] if passed else evidence_refs or []),
    )


def _pack_family_variant_mismatches(
    spec: LaborEmploymentExecutableFixtureSpec,
    pack_cases: dict[str, LaborEmploymentSyntheticFixtureCase],
) -> list[str]:
    linked_cases = [
        pack_cases[case_id] for case_id in spec.linked_pack_case_ids if case_id in pack_cases
    ]
    if not linked_cases:
        return []
    exact_match = any(
        case.family == spec.family and case.variant == spec.variant for case in linked_cases
    )
    if exact_match:
        return []
    return [case.case_id for case in linked_cases]


def _missing_terms(bundle: SourceBundle, terms: list[str]) -> list[str]:
    text = "\n".join(source.text for source in bundle.sources).casefold()
    return [term for term in terms if term.casefold() not in text]


def _resolve_repo_ref(root: Path, ref: str | Path) -> Path:
    path = Path(ref)
    resolved = path.resolve() if path.is_absolute() else (root / path).resolve()
    if not resolved.is_relative_to(root):
        raise ValueError(f"repository reference escapes repo root: {ref}")
    return resolved


def _safe_dirname(value: str) -> str:
    return "".join(
        character if character.isalnum() or character in {"-", "_"} else "-" for character in value
    )


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"
