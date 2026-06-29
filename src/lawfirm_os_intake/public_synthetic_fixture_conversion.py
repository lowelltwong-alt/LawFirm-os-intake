from __future__ import annotations

from pathlib import Path

from .models import (
    PublicSourceMethodologyReport,
    PublicSourceMethodologySource,
    PublicSyntheticFixtureConversionCheck,
    PublicSyntheticFixtureConversionPlan,
    PublicSyntheticFixtureConversionSpec,
    PublicSyntheticFixtureFamily,
)
from .util import append_jsonl, load_json, new_id, now_iso, write_json


PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_PLAN_FILENAME = "public_synthetic_fixture_conversion_plan.json"
PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_NOTES_FILENAME = "public_synthetic_fixture_conversion_plan.md"
PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_SPECS_FILENAME = (
    "public_synthetic_fixture_conversion_specs.jsonl"
)

READY_METHODOLOGY_STATUS = "ready_for_human_public_source_methodology_review"

TARGET_FAMILY_BY_SOURCE_ID: dict[str, PublicSyntheticFixtureFamily] = {
    "courtlistener-recap": "docket_structure",
    "fjc-idb": "aggregate_case_metadata",
    "cmu-enron-email": "messy_email_structure",
    "sec-edgar": "public_filing_structure",
    "nhtsa-public-crash-data": "auto_liability_distribution",
    "npdb-public-use-data": "medical_malpractice_distribution",
}

REQUIRED_FORBIDDEN_INPUTS = [
    "real_party_names",
    "real_case_numbers",
    "raw_public_payloads",
    "downloaded_public_payloads",
    "privileged_or_confidential_material",
]

REQUIRED_NEXT_GATES = [
    "human_public_source_methodology_review",
    "human_public_synthetic_conversion_review",
    "source_license_review",
    "privacy_review",
    "retention_decision",
    "separate_synthetic_fixture_generation_pr",
    "synthetic_fixture_gold_review",
    "red_team_identity_reconstruction_review",
    "legal_knowledge_runtime_owner_review_before_adapter",
]


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _identity_rules(target_family: PublicSyntheticFixtureFamily) -> list[str]:
    rules = [
        "replace_party_person_entity_and_attorney_names",
        "synthesize_case_docket_source_and_message_identifiers",
        "synthesize_dates_locations_domains_contacts_and_account_numbers",
        "preserve_structure_distribution_and_field_shape_only",
        "exclude_real_payload_text_and_unique_fact_patterns",
    ]
    if target_family == "messy_email_structure":
        rules.extend(
            [
                "replace_senders_recipients_domains_subjects_and_message_bodies",
                "synthesize_attachment_refs_and_attachment_names",
            ]
        )
    if target_family == "docket_structure":
        rules.append("replace_docket_numbers_party_names_attorney_names_and_court_specific_ids")
    if target_family in {
        "aggregate_case_metadata",
        "auto_liability_distribution",
        "medical_malpractice_distribution",
    }:
        rules.extend(
            [
                "aggregate_or_bucket_fields_before_fixture_design",
                "avoid_reconstructing_any_single_public_record",
            ]
        )
    return rules


def _field_rules(
    source: PublicSourceMethodologySource,
    target_family: PublicSyntheticFixtureFamily,
) -> list[str]:
    rules = list(source.synthetic_conversion_rules)
    if target_family == "docket_structure":
        rules.extend(
            [
                "map_docket_rows_to_synthetic_filing_events_only",
                "map_party_attorney_fields_to_synthetic_role_placeholders_only",
            ]
        )
    elif target_family == "aggregate_case_metadata":
        rules.extend(
            [
                "convert_codebook_fields_to_synthetic_schema_candidates",
                "bucket_dates_and_postures_before_fixture_design",
            ]
        )
    elif target_family == "messy_email_structure":
        rules.extend(
            [
                "map_headers_threading_quoted_history_and_signatures_without_payload_text",
                "preserve_prompt_injection_as_untrusted_synthetic_data",
            ]
        )
    elif target_family == "public_filing_structure":
        rules.extend(
            [
                "map_section_shape_without_accession_numbers_or_public_entity_identifiers",
                "replace_filing_text_with_synthetic_legal_intake_style_content",
            ]
        )
    elif target_family == "auto_liability_distribution":
        rules.extend(
            [
                "use_aggregate_vehicle_date_location_patterns_only",
                "do_not_encode_real_crash_or_liability_fact_patterns",
            ]
        )
    elif target_family == "medical_malpractice_distribution":
        rules.extend(
            [
                "use_aggregate_provider_claim_payment_patterns_only",
                "do_not_encode_real_provider_claimant_or_claim_identifiers",
            ]
        )
    return _unique(rules)


def _synthetic_gold_checks(target_family: PublicSyntheticFixtureFamily) -> list[str]:
    checks = [
        "source_methodology_ref_present",
        "no_public_payload_text",
        "no_real_party_identity",
        "no_real_matter_identity",
        "synthetic_source_refs_only",
        "review_gate_refs_present",
        "fixture_generation_remains_separate_pr",
    ]
    if target_family == "docket_structure":
        checks.extend(["docket_id_is_synthetic", "party_and_attorney_names_are_synthetic"])
    elif target_family == "aggregate_case_metadata":
        checks.append("no_record_level_reconstruction")
    elif target_family == "messy_email_structure":
        checks.extend(["prompt_injection_treated_as_data", "quoted_history_boundary_check"])
    elif target_family == "public_filing_structure":
        checks.append("no_accession_or_public_entity_identifier")
    elif target_family == "auto_liability_distribution":
        checks.append("no_real_crash_reconstruction")
    elif target_family == "medical_malpractice_distribution":
        checks.append("no_provider_or_claimant_identity")
    return checks


def _red_team_checks(target_family: PublicSyntheticFixtureFamily) -> list[str]:
    checks = [
        "could_this_reconstruct_a_real_public_case",
        "could_identity_be_enriched_from_external_sources",
        "could_public_structure_be_misused_as_observed_intake_fact",
        "does_any_output_imply_conflict_merits_budget_or_legal_conclusion",
        "does_plan_authorize_adapter_connector_lake_or_sqlite_write",
        "does_plan_create_or_mutate_fixture_files",
    ]
    if target_family == "messy_email_structure":
        checks.append("could_synthetic_message_text_be_misread_as_instructions")
    if target_family in {
        "aggregate_case_metadata",
        "auto_liability_distribution",
        "medical_malpractice_distribution",
    }:
        checks.append("could_aggregate_patterns_be_joined_back_to_real_records")
    return checks


def _spec_for_source(
    *,
    source: PublicSourceMethodologySource,
    methodology_report_path: Path,
) -> PublicSyntheticFixtureConversionSpec:
    target_family = TARGET_FAMILY_BY_SOURCE_ID.get(source.source_id, "public_structure_review")
    return PublicSyntheticFixtureConversionSpec(
        conversion_spec_id=new_id("publicsyntheticfixturespec"),
        source_id=source.source_id,
        source_methodology_ref=f"{methodology_report_path}#source:{source.source_id}",
        methodology_role=source.methodology_role,
        target_fixture_family=target_family,
        allowed_structure_inputs=_unique(source.safe_use_classes + source.useful_for),
        forbidden_inputs=_unique(source.prohibited_use_classes + REQUIRED_FORBIDDEN_INPUTS),
        identity_replacement_rules=_identity_rules(target_family),
        field_transformation_rules=_field_rules(source, target_family),
        required_synthetic_gold_checks=_synthetic_gold_checks(target_family),
        required_red_team_checks=_red_team_checks(target_family),
        review_status="planned_for_human_conversion_review",
    )


def build_public_synthetic_fixture_conversion_plan(
    *,
    methodology_report_path: str | Path,
    specs_output_ref: str,
) -> PublicSyntheticFixtureConversionPlan:
    report_path = Path(methodology_report_path)
    methodology_report = PublicSourceMethodologyReport.model_validate(load_json(report_path))
    if methodology_report.status != READY_METHODOLOGY_STATUS:
        checks = [
            PublicSyntheticFixtureConversionCheck(
                check_id="source_methodology_report_ready",
                status="blocked",
                message=(
                    "Public-source methodology report is not ready; synthetic conversion "
                    "planning is blocked."
                ),
                source_ids=methodology_report.missing_required_source_ids,
            ),
            PublicSyntheticFixtureConversionCheck(
                check_id="no_payload_or_fixture_side_effects",
                status="passed",
                message=(
                    "Blocked conversion planning still performs no public ingestion, no "
                    "fixture mutation, no adapter authorization, and no Lake/SQLite writes."
                ),
            ),
        ]
        return PublicSyntheticFixtureConversionPlan(
            conversion_plan_id=new_id("publicsyntheticfixtureplan"),
            status="blocked_public_methodology_not_ready",
            source_methodology_report_id=(methodology_report.public_source_methodology_report_id),
            source_methodology_report_ref=str(report_path),
            source_catalog_ref=methodology_report.source_catalog_ref,
            specs_output_ref=specs_output_ref,
            spec_count=0,
            specs=[],
            checks=checks,
            required_next_gates=REQUIRED_NEXT_GATES,
            generated_at=now_iso(),
        )

    specs = [
        _spec_for_source(source=source, methodology_report_path=report_path)
        for source in methodology_report.sources
    ]
    checks = [
        PublicSyntheticFixtureConversionCheck(
            check_id="source_methodology_report_ready",
            status="passed",
            message="Public-source methodology report is ready for human review.",
        ),
        PublicSyntheticFixtureConversionCheck(
            check_id="conversion_specs_cover_sources",
            status="passed" if len(specs) == methodology_report.source_count else "failed",
            message="Every methodology source has a synthetic conversion planning spec.",
            source_ids=[source.source_id for source in methodology_report.sources],
        ),
        PublicSyntheticFixtureConversionCheck(
            check_id="all_specs_have_review_and_red_team_controls",
            status="passed"
            if all(
                spec.required_red_team_checks and spec.required_synthetic_gold_checks
                for spec in specs
            )
            else "failed",
            message="Every conversion spec includes synthetic gold and red-team checks.",
            source_ids=[spec.source_id for spec in specs],
        ),
        PublicSyntheticFixtureConversionCheck(
            check_id="no_payload_or_fixture_side_effects",
            status="passed",
            message=(
                "Conversion planning performs no public ingestion, no fixture mutation, "
                "no adapter authorization, and no Lake/SQLite writes."
            ),
        ),
    ]
    return PublicSyntheticFixtureConversionPlan(
        conversion_plan_id=new_id("publicsyntheticfixtureplan"),
        status="ready_for_human_conversion_review",
        source_methodology_report_id=methodology_report.public_source_methodology_report_id,
        source_methodology_report_ref=str(report_path),
        source_catalog_ref=methodology_report.source_catalog_ref,
        specs_output_ref=specs_output_ref,
        spec_count=len(specs),
        specs=specs,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_public_synthetic_fixture_conversion_plan(
    plan: PublicSyntheticFixtureConversionPlan,
) -> str:
    lines = [
        "# Public Synthetic Fixture Conversion Plan",
        "",
        f"**Plan ID:** {plan.conversion_plan_id}",
        f"**Status:** {plan.status}",
        f"**Source methodology report:** `{plan.source_methodology_report_ref}`",
        f"**Spec count:** {plan.spec_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {plan.candidate_only}",
        f"- Planning only: {plan.planning_only}",
        f"- Public records ingested: {plan.public_records_ingested}",
        f"- Raw public payload committed: {plan.raw_public_payload_committed}",
        f"- Synthetic fixtures created: {plan.synthetic_fixtures_created}",
        f"- Fixture files mutated: {plan.fixture_files_mutated}",
        f"- Connector implemented: {plan.connector_implemented}",
        f"- Legal Knowledge adapter authorized: {plan.legal_knowledge_adapter_authorized}",
        f"- Lake write performed: {plan.lake_write_performed}",
        f"- SQLite write performed: {plan.sqlite_write_performed}",
        f"- External writes performed: {plan.external_writes_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in plan.required_next_gates),
        "",
        "## Checks",
        "",
    ]
    for check in plan.checks:
        lines.append(f"- `{check.check_id}`: {check.status} - {check.message}")
    lines.extend(["", "## Conversion Specs", ""])
    for spec in plan.specs:
        lines.extend(
            [
                f"### {spec.source_id}",
                "",
                f"- Target fixture family: `{spec.target_fixture_family}`",
                f"- Why allowed: {', '.join(spec.allowed_structure_inputs)}",
                f"- Forbidden inputs: {', '.join(spec.forbidden_inputs)}",
                "- Identity replacement:",
                *(f"  - {rule}" for rule in spec.identity_replacement_rules),
                "- Synthetic gold checks:",
                *(f"  - {check}" for check in spec.required_synthetic_gold_checks),
                "- Red-team checks:",
                *(f"  - {check}" for check in spec.required_red_team_checks),
                "",
            ]
        )
    lines.extend(
        [
            "This plan is a human-review artifact only. It does not create fixtures, "
            "ingest public records, authorize adapters, write Lake/SQLite records, "
            "or permit runtime public-data use.",
            "",
        ]
    )
    return "\n".join(lines)


def run_public_synthetic_fixture_conversion_plan(
    *,
    methodology_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[PublicSyntheticFixtureConversionPlan, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    specs_path = run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_SPECS_FILENAME
    plan = build_public_synthetic_fixture_conversion_plan(
        methodology_report_path=methodology_report_path,
        specs_output_ref=str(specs_path),
    )
    specs_path.write_text("", encoding="utf-8")
    for spec in plan.specs:
        append_jsonl(specs_path, spec.model_dump(mode="json"))
    plan_path = run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_PLAN_FILENAME
    notes_path = run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_NOTES_FILENAME
    write_json(plan_path, plan.model_dump(mode="json"))
    notes_path.write_text(
        render_public_synthetic_fixture_conversion_plan(plan),
        encoding="utf-8",
    )
    return plan, run_dir
