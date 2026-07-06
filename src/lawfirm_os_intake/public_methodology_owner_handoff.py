from __future__ import annotations

from pathlib import Path

from .models import (
    PublicMethodologyOwnerHandoffCheck,
    PublicMethodologyOwnerHandoffPacket,
    PublicMethodologyOwnerHandoffReport,
    PublicMethodologyOwnerTargetRepo,
    PublicSourceMethodologyReport,
    PublicSyntheticFixtureConversionPlan,
    PublicSyntheticFixtureConversionReviewPacket,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


PUBLIC_METHODOLOGY_OWNER_HANDOFF_REPORT_FILENAME = "public_methodology_owner_handoff_report.json"
PUBLIC_METHODOLOGY_OWNER_HANDOFF_NOTES_FILENAME = "public_methodology_owner_handoff_report.md"
PUBLIC_METHODOLOGY_OWNER_HANDOFF_PACKETS_FILENAME = "public_methodology_owner_handoff_packets.jsonl"
PUBLIC_METHODOLOGY_OWNER_HANDOFF_DIRNAME = "public_methodology_owner_packets"

READY_METHODOLOGY_STATUS = "ready_for_human_public_source_methodology_review"
READY_CONVERSION_PLAN_STATUS = "ready_for_human_conversion_review"
READY_CONVERSION_REVIEW_STATUS = "ready_for_human_conversion_review"

TARGET_REPOS: list[PublicMethodologyOwnerTargetRepo] = [
    "LawFirm-os-intake",
    "LawFirm-os-legal-knowledge-runtime",
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
]

PUBLIC_METHODOLOGY_OWNER_REQUIRED_NEXT_GATES = [
    "human_public_methodology_owner_review",
    "manual_owner_issue_creation_if_desired",
    "owning_repo_triage",
    "owner_repo_implementation_pr_if_accepted",
    "source_license_privacy_retention_review",
    "legal_knowledge_runtime_owner_review_before_adapter",
    "no_intake_public_ingestion_or_adapter_authorization",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _owner_slug(owner: str) -> str:
    return owner.lower().replace("lawfirm-os-", "").replace("_", "-")


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> PublicMethodologyOwnerHandoffCheck:
    return PublicMethodologyOwnerHandoffCheck(
        check_id=check_id,
        status="passed" if passed else "blocked",
        message=message,
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _methodology_boundary_clear(report: PublicSourceMethodologyReport) -> bool:
    return (
        report.candidate_only is True
        and report.non_authoritative is True
        and report.planning_only is True
        and report.metadata_only is True
        and report.human_review_required is True
        and report.direct_runtime_ingestion_allowed is False
        and report.public_records_ingested is False
        and report.raw_public_payload_committed is False
        and report.real_party_records_committed is False
        and report.real_matter_records_committed is False
        and report.connector_implemented is False
        and report.legal_knowledge_adapter_authorized is False
        and report.lake_write_performed is False
        and report.sqlite_write_performed is False
        and report.external_writes_performed is False
    )


def _conversion_plan_boundary_clear(plan: PublicSyntheticFixtureConversionPlan) -> bool:
    return (
        plan.candidate_only is True
        and plan.non_authoritative is True
        and plan.planning_only is True
        and plan.human_review_required is True
        and plan.public_records_ingested is False
        and plan.raw_public_payload_committed is False
        and plan.synthetic_fixtures_created is False
        and plan.fixture_files_mutated is False
        and plan.connector_implemented is False
        and plan.legal_knowledge_adapter_authorized is False
        and plan.lake_write_performed is False
        and plan.sqlite_write_performed is False
        and plan.external_writes_performed is False
    )


def _review_packet_boundary_clear(packet: PublicSyntheticFixtureConversionReviewPacket) -> bool:
    return (
        packet.candidate_only is True
        and packet.non_authoritative is True
        and packet.planning_only is True
        and packet.human_review_required is True
        and packet.public_records_ingested is False
        and packet.raw_public_payload_committed is False
        and packet.synthetic_fixtures_created is False
        and packet.fixture_files_mutated is False
        and packet.fixture_pr_created is False
        and packet.connector_implemented is False
        and packet.legal_knowledge_adapter_authorized is False
        and packet.lake_write_performed is False
        and packet.sqlite_write_performed is False
        and packet.external_writes_performed is False
        and packet.silent_learning_performed is False
    )


def _source_artifact_refs(
    *,
    methodology_report: PublicSourceMethodologyReport,
    methodology_report_ref: str,
    conversion_plan: PublicSyntheticFixtureConversionPlan,
    conversion_plan_ref: str,
    review_packet: PublicSyntheticFixtureConversionReviewPacket,
    review_packet_ref: str,
) -> list[str]:
    refs = [
        methodology_report_ref,
        conversion_plan_ref,
        review_packet_ref,
        methodology_report.source_catalog_ref,
        methodology_report.data_policy_ref,
        conversion_plan.specs_output_ref,
        "schemas/public-source-methodology-report.schema.json",
        "schemas/public-synthetic-fixture-conversion-plan.schema.json",
        "schemas/public-synthetic-fixture-conversion-review-packet.schema.json",
    ]
    if review_packet.human_readable_review_ref:
        refs.append(review_packet.human_readable_review_ref)
    if review_packet.decision_template_ref:
        refs.append(review_packet.decision_template_ref)
    return refs


def _handoff_focus(owner: str) -> str:
    return {
        "LawFirm-os-intake": "local_intake_candidate_stewardship",
        "LawFirm-os-legal-knowledge-runtime": "legal_knowledge_public_adapter_boundary",
        "LawFirm-os-semantic-substrate": "public_data_governance_policy",
        "LawFirm-os-orchestrator": "runtime_public_source_gate",
        "LawFirm-os-exceptions-lake-runtime": "append_only_public_methodology_audit",
    }[owner]


def _candidate_contract_refs(owner: str) -> list[str]:
    return {
        "LawFirm-os-intake": [
            "intake://candidate/public-methodology-owner-handoff.v0_1",
            "intake://candidate/public-synthetic-fixture-conversion-review.v0_1",
            "intake://candidate/no-public-payload-or-adapter-authority.v0_1",
        ],
        "LawFirm-os-legal-knowledge-runtime": [
            "legal-knowledge-runtime://candidate/interfaces/public-source-preflight.v0_1",
            "legal-knowledge-runtime://candidate/interfaces/public-structure-retrieval-disabled.v0_1",
            "legal-knowledge-runtime://candidate/provenance/public-source-methodology-ref.v0_1",
        ],
        "LawFirm-os-semantic-substrate": [
            "semantic-substrate://candidate/data-scope/public-methodology.v0_1",
            "semantic-substrate://candidate/policy/public-structure-only-fixtures.v0_1",
            "semantic-substrate://candidate/review-gates/source-license-privacy-retention.v0_1",
        ],
        "LawFirm-os-orchestrator": [
            "orchestrator://candidate/workflows/public-source-methodology-review.v0_1",
            "orchestrator://candidate/gates/public-adapter-authorization.v0_1",
            "orchestrator://candidate/evidence-packets/public-methodology-owner-review.v0_1",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "exception-lake://candidate/admission/public-methodology-review.v0_1",
            "exception-lake://candidate/admission/public-fixture-conversion-decision.v0_1",
            "exception-lake://candidate/audit/public-adapter-denial-or-approval.v0_1",
        ],
    }[owner]


def _owner_actions(owner: str) -> list[str]:
    return {
        "LawFirm-os-intake": [
            "Keep public-source methodology artifacts local, candidate-only, metadata-only, and human-review gated.",
            "Confirm this handoff does not create owner issues, open PRs, mutate fixtures, ingest public payloads, authorize adapters, or write Lake records.",
            "Use owner feedback to prepare later implementation PRs without promoting local candidate contracts as canon.",
        ],
        "LawFirm-os-legal-knowledge-runtime": [
            "Review the future public-source preflight and structure-only adapter boundary before any lookup or retrieval helper is enabled.",
            "Define source provenance, public-methodology refs, retrieval trace constraints, and no-raw-payload storage guarantees.",
            "Keep public adapter status blocked until source-license, privacy, retention, Orchestrator gate, and Substrate policy decisions land.",
        ],
        "LawFirm-os-semantic-substrate": [
            "Review the public-source methodology, structure-only fixture, and no-payload policies against canonical data-scope doctrine.",
            "Decide which source-license, privacy, retention, and no-runtime-ingestion gates should become canonical review gates.",
            "Decide whether public methodology, conversion review, and fixture PR package labels need canonical schema or event-class promotion.",
        ],
        "LawFirm-os-orchestrator": [
            "Define the runtime workflow that pauses for source-license, privacy, retention, fixture-conversion, and adapter-authorization review.",
            "Require Legal Knowledge Runtime owner approval before any public-source lookup, retrieval, or adapter path can run.",
            "Assemble owner-reviewed evidence packets for future Lake admission without granting intake connector authority.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Review append-only record families for public methodology review, conversion decisions, fixture PR package review, and adapter authorization outcomes.",
            "Define idempotency, support hashes, record hashes, supersession, and SQLite ownership for public methodology audit records.",
            "Keep raw public payloads, public identities, and downloaded public records outside Lake records unless a future owner-approved contract allows them.",
        ],
    }[owner]


def _acceptance_checks(owner: str) -> list[str]:
    return {
        "LawFirm-os-intake": [
            "The handoff remains a local candidate artifact and does not create owner issues, PRs, fixtures, adapters, Lake records, or learned changes.",
            "Input artifacts are methodology/report artifacts only, not raw public records, downloaded payloads, public adapter output, or fixture files.",
            "Any later owner implementation uses separate reviewed PRs in the owning repo.",
        ],
        "LawFirm-os-legal-knowledge-runtime": [
            "Public-source helpers are disabled until owner-approved adapter contracts and Orchestrator gates exist.",
            "Public-source provenance is represented as methodology metadata, not raw payload or observed intake fact.",
            "Retrieval traces and Legal Context Bundles cannot include real public payloads in this starter path.",
        ],
        "LawFirm-os-semantic-substrate": [
            "No public-source policy, source class, route ID, event class, or review gate is canonical until promoted in substrate.",
            "Structure-only fixture rules forbid raw payload text, real party names, real case numbers, downloaded payloads, and record reconstruction.",
            "Adapter authorization remains a separate reviewed governance decision.",
        ],
        "LawFirm-os-orchestrator": [
            "Runtime workflow requires human source-license, privacy, retention, fixture, and adapter gates before public-source use.",
            "Public-source connectors and external writes remain impossible from intake.",
            "Evidence packets preserve methodology refs and no-payload/no-identity decisions.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Admission records are append-only and distinguish methodology decisions, conversion decisions, fixture package decisions, and adapter outcomes.",
            "SQLite schema and migrations remain owned by Exception Lake, not intake.",
            "Lake admission rejects raw public payloads and identity-bearing public records by default.",
        ],
    }[owner]


def _red_team_notes(owner: str) -> list[str]:
    return {
        "LawFirm-os-intake": [
            "A local handoff report can look like owner approval; it is only a request packet.",
            "Public methodology review can drift into fixture or adapter authorization unless every next gate stays explicit.",
        ],
        "LawFirm-os-legal-knowledge-runtime": [
            "A metadata-only source catalog can drift into raw public ingestion if adapter boundaries are not explicit.",
            "Public records must not be treated as source-bound intake evidence for conflicts, merits, party roles, or budgets.",
        ],
        "LawFirm-os-semantic-substrate": [
            "A local public methodology report can look like platform policy; it is not canon.",
            "Structure-only sources can still leak identity if rare field combinations are too specific.",
        ],
        "LawFirm-os-orchestrator": [
            "The highest-risk failure is accidentally enabling public lookup or retrieval without source-license, privacy, and retention gates.",
            "Fixture generation review is not adapter approval and must not be treated as runtime authorization.",
        ],
        "LawFirm-os-exceptions-lake-runtime": [
            "Public methodology evidence can become misleading if payload hashes or raw excerpts are admitted without an explicit owner contract.",
            "Corrections and supersessions are required because source-license decisions can change over time.",
        ],
    }[owner]


def _build_checks(
    *,
    methodology_report: PublicSourceMethodologyReport,
    methodology_report_ref: str,
    conversion_plan: PublicSyntheticFixtureConversionPlan,
    conversion_plan_ref: str,
    review_packet: PublicSyntheticFixtureConversionReviewPacket,
    review_packet_ref: str,
) -> list[PublicMethodologyOwnerHandoffCheck]:
    lineage_match = (
        conversion_plan.source_methodology_report_id
        == methodology_report.public_source_methodology_report_id
        and conversion_plan.source_methodology_report_ref == methodology_report_ref
        and review_packet.conversion_plan_id == conversion_plan.conversion_plan_id
        and review_packet.conversion_plan_ref == conversion_plan_ref
    )
    methodology_source_ids = {source.source_id for source in methodology_report.sources}
    conversion_source_ids = {spec.source_id for spec in conversion_plan.specs}
    conversion_spec_ids = {spec.conversion_spec_id for spec in conversion_plan.specs}
    recommendation_spec_ids = {rec.conversion_spec_id for rec in review_packet.recommendations}
    decision_template_spec_ids = {
        template.conversion_spec_id for template in review_packet.decision_templates
    }
    required_red_team_scopes = {
        "boundary",
        "identity_reconstruction",
        "payload_contamination",
        "legal_fact_misuse",
    }
    review_red_team_scopes = {note.scope for note in review_packet.red_team_notes}
    methodology_ready = (
        methodology_report.status == READY_METHODOLOGY_STATUS
        and _methodology_boundary_clear(methodology_report)
        and all(check.status == "passed" for check in methodology_report.checks)
        and all(
            source.status == "ready_for_human_methodology_review"
            and source.adapter_status == "not_authorized"
            and source.direct_runtime_ingestion is False
            for source in methodology_report.sources
        )
    )
    conversion_plan_ready = (
        conversion_plan.status == READY_CONVERSION_PLAN_STATUS
        and _conversion_plan_boundary_clear(conversion_plan)
        and all(check.status == "passed" for check in conversion_plan.checks)
        and conversion_plan.spec_count == methodology_report.source_count
        and conversion_source_ids == methodology_source_ids
    )
    review_packet_ready = (
        review_packet.status == READY_CONVERSION_REVIEW_STATUS
        and _review_packet_boundary_clear(review_packet)
        and review_packet.spec_count == conversion_plan.spec_count
        and review_packet.recommendation_count == conversion_plan.spec_count
        and review_packet.decision_template_count == conversion_plan.spec_count
        and recommendation_spec_ids == conversion_spec_ids
        and decision_template_spec_ids == conversion_spec_ids
    )
    return [
        _check(
            "public_methodology_ready_without_payloads",
            methodology_ready,
            "Public methodology report is ready and preserves metadata-only/no-public-ingestion boundaries.",
            artifact_refs=[methodology_report_ref],
        ),
        _check(
            "conversion_plan_ready_without_fixture_mutation",
            conversion_plan_ready,
            "Public synthetic conversion plan is ready and creates no fixtures or adapter authorization.",
            artifact_refs=[conversion_plan_ref],
        ),
        _check(
            "conversion_review_ready_without_adapter_or_learning",
            review_packet_ready,
            "Public conversion review packet is ready and creates no fixture PR, adapter authorization, Lake write, or learning.",
            artifact_refs=[review_packet_ref],
        ),
        _check(
            "public_methodology_lineage_matches",
            lineage_match,
            "Methodology, conversion plan, and conversion review packet IDs form one evidence chain.",
            artifact_refs=[methodology_report_ref, conversion_plan_ref, review_packet_ref],
        ),
        _check(
            "conversion_review_covers_sources",
            methodology_report.source_count == conversion_plan.spec_count
            and conversion_plan.spec_count == review_packet.recommendation_count,
            "Every public methodology source has a conversion spec and review recommendation.",
            artifact_refs=[methodology_report_ref, conversion_plan_ref, review_packet_ref],
        ),
        _check(
            "conversion_review_red_team_scope_covers_boundary_risks",
            required_red_team_scopes.issubset(review_red_team_scopes),
            "Conversion review red-team notes cover boundary, identity reconstruction, payload contamination, and legal fact misuse risks.",
            artifact_refs=[review_packet_ref],
        ),
    ]


def _ready_for_owner_packets(checks: list[PublicMethodologyOwnerHandoffCheck]) -> bool:
    return all(check.status == "passed" for check in checks)


def build_public_methodology_owner_handoff_packets(
    *,
    methodology_report: PublicSourceMethodologyReport,
    methodology_report_ref: str,
    conversion_plan: PublicSyntheticFixtureConversionPlan,
    conversion_plan_ref: str,
    review_packet: PublicSyntheticFixtureConversionReviewPacket,
    review_packet_ref: str,
    ready: bool,
) -> list[PublicMethodologyOwnerHandoffPacket]:
    source_ids = [source.source_id for source in methodology_report.sources]
    source_artifact_refs = _source_artifact_refs(
        methodology_report=methodology_report,
        methodology_report_ref=methodology_report_ref,
        conversion_plan=conversion_plan,
        conversion_plan_ref=conversion_plan_ref,
        review_packet=review_packet,
        review_packet_ref=review_packet_ref,
    )
    packets: list[PublicMethodologyOwnerHandoffPacket] = []
    for owner in TARGET_REPOS:
        packets.append(
            PublicMethodologyOwnerHandoffPacket(
                handoff_packet_id=_stable_id(
                    "publicmethodologyownerpacket",
                    "|".join(
                        [
                            methodology_report.public_source_methodology_report_id,
                            conversion_plan.conversion_plan_id,
                            review_packet.review_packet_id,
                            owner,
                        ]
                    ),
                ),
                target_repo=owner,
                handoff_focus=_handoff_focus(owner),  # type: ignore[arg-type]
                status=(
                    "ready_for_owner_review" if ready else "blocked_by_public_methodology_chain"
                ),
                source_public_methodology_report_id=(
                    methodology_report.public_source_methodology_report_id
                ),
                source_public_methodology_report_ref=methodology_report_ref,
                source_public_methodology_status=methodology_report.status,
                source_conversion_plan_id=conversion_plan.conversion_plan_id,
                source_conversion_plan_ref=conversion_plan_ref,
                source_conversion_plan_status=conversion_plan.status,
                source_conversion_review_packet_id=review_packet.review_packet_id,
                source_conversion_review_packet_ref=review_packet_ref,
                source_conversion_review_packet_status=review_packet.status,
                source_count=methodology_report.source_count,
                spec_count=conversion_plan.spec_count,
                recommendation_count=review_packet.recommendation_count,
                red_team_note_count=review_packet.red_team_note_count,
                source_ids=source_ids,
                source_artifact_refs=source_artifact_refs,
                candidate_contract_refs=_candidate_contract_refs(owner),
                required_owner_actions=_owner_actions(owner),
                acceptance_checks=_acceptance_checks(owner),
                red_team_notes=_red_team_notes(owner),
                required_next_gates=PUBLIC_METHODOLOGY_OWNER_REQUIRED_NEXT_GATES,
            )
        )
    return packets


def build_public_methodology_owner_handoff_report(
    *,
    methodology_report: PublicSourceMethodologyReport,
    methodology_report_ref: str,
    conversion_plan: PublicSyntheticFixtureConversionPlan,
    conversion_plan_ref: str,
    review_packet: PublicSyntheticFixtureConversionReviewPacket,
    review_packet_ref: str,
    packets: list[PublicMethodologyOwnerHandoffPacket],
    packet_output_refs: list[str],
    checks: list[PublicMethodologyOwnerHandoffCheck],
) -> PublicMethodologyOwnerHandoffReport:
    ready_count = sum(1 for packet in packets if packet.status == "ready_for_owner_review")
    blocked_count = len(packets) - ready_count
    return PublicMethodologyOwnerHandoffReport(
        owner_handoff_report_id=_stable_id(
            "publicmethodologyownerreport",
            "|".join(
                [
                    methodology_report.public_source_methodology_report_id,
                    conversion_plan.conversion_plan_id,
                    review_packet.review_packet_id,
                    methodology_report_ref,
                    conversion_plan_ref,
                    review_packet_ref,
                ]
            ),
        ),
        status=(
            "public_methodology_owner_handoff_packets_ready"
            if not blocked_count and all(check.status == "passed" for check in checks)
            else "blocked_by_public_methodology_chain"
        ),
        source_public_methodology_report_id=(
            methodology_report.public_source_methodology_report_id
        ),
        source_public_methodology_report_ref=methodology_report_ref,
        source_public_methodology_status=methodology_report.status,
        source_conversion_plan_id=conversion_plan.conversion_plan_id,
        source_conversion_plan_ref=conversion_plan_ref,
        source_conversion_plan_status=conversion_plan.status,
        source_conversion_review_packet_id=review_packet.review_packet_id,
        source_conversion_review_packet_ref=review_packet_ref,
        source_conversion_review_packet_status=review_packet.status,
        target_repo_count=len(TARGET_REPOS),
        packet_count=len(packets),
        ready_packet_count=ready_count,
        blocked_packet_count=blocked_count,
        target_repos=TARGET_REPOS,
        packets=packets,
        packet_output_refs=packet_output_refs,
        checks=checks,
        required_next_gates=PUBLIC_METHODOLOGY_OWNER_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_public_methodology_owner_handoff_packet(
    packet: PublicMethodologyOwnerHandoffPacket,
) -> str:
    lines = [
        "# Public Methodology Owner Handoff Packet",
        "",
        f"**Packet ID:** {packet.handoff_packet_id}",
        f"**Target repo:** {packet.target_repo}",
        f"**Focus:** {packet.handoff_focus}",
        f"**Status:** {packet.status}",
        "",
        "## Source Evidence",
        "",
        f"- Methodology report: `{packet.source_public_methodology_report_ref}`",
        f"- Methodology status: {packet.source_public_methodology_status}",
        f"- Conversion plan: `{packet.source_conversion_plan_ref}`",
        f"- Conversion plan status: {packet.source_conversion_plan_status}",
        f"- Conversion review packet: `{packet.source_conversion_review_packet_ref}`",
        f"- Conversion review status: {packet.source_conversion_review_packet_status}",
        f"- Sources: {packet.source_count}",
        f"- Specs: {packet.spec_count}",
        f"- Recommendations: {packet.recommendation_count}",
        "",
        "## Candidate Contract Refs",
        "",
        *(f"- `{ref}`" for ref in packet.candidate_contract_refs),
        "",
        "## Required Owner Actions",
        "",
        *(f"- [ ] {action}" for action in packet.required_owner_actions),
        "",
        "## Acceptance Checks",
        "",
        *(f"- [ ] {check}" for check in packet.acceptance_checks),
        "",
        "## Red-Team Notes",
        "",
        *(f"- {note}" for note in packet.red_team_notes),
        "",
        "## Source IDs",
        "",
        *(f"- `{source_id}`" for source_id in packet.source_ids),
        "",
        "## Source Artifact Refs",
        "",
        *(f"- `{ref}`" for ref in packet.source_artifact_refs),
        "",
        "## Boundary Flags",
        "",
        f"- Human review required: {packet.human_review_required}",
        f"- Owning repo review required: {packet.owning_repo_review_required}",
        f"- Direct runtime ingestion allowed: {packet.direct_runtime_ingestion_allowed}",
        f"- Direct promotion performed: {packet.direct_promotion_performed}",
        f"- Promotion authorized: {packet.promotion_authorized}",
        f"- Sibling repo write performed: {packet.sibling_repo_write_performed}",
        f"- GitHub issue created: {packet.github_issue_created}",
        f"- GitHub PR created: {packet.github_pr_created}",
        f"- Public records ingested: {packet.public_records_ingested}",
        f"- Raw public payload committed: {packet.raw_public_payload_committed}",
        f"- Real party records committed: {packet.real_party_records_committed}",
        f"- Real matter records committed: {packet.real_matter_records_committed}",
        f"- Synthetic fixtures created: {packet.synthetic_fixtures_created}",
        f"- Fixture files mutated: {packet.fixture_files_mutated}",
        f"- Fixture generation authorized: {packet.fixture_generation_authorized}",
        f"- Connector implemented: {packet.connector_implemented}",
        f"- Legal Knowledge adapter authorized: {packet.legal_knowledge_adapter_authorized}",
        f"- Lake write performed: {packet.lake_write_performed}",
        f"- SQLite write performed: {packet.sqlite_write_performed}",
        f"- External writes performed: {packet.external_writes_performed}",
        f"- Silent learning performed: {packet.silent_learning_performed}",
        "",
        "This packet is local owner-review evidence only. It does not create issues, open PRs, write sibling repos, promote canon, ingest public records, create fixtures, authorize adapters, admit Lake/SQLite records, or apply learning.",
        "",
    ]
    return "\n".join(lines)


def render_public_methodology_owner_handoff_report(
    report: PublicMethodologyOwnerHandoffReport,
) -> str:
    lines = [
        "# Public Methodology Owner Handoff Report",
        "",
        f"**Report ID:** {report.owner_handoff_report_id}",
        f"**Status:** {report.status}",
        f"**Methodology report:** `{report.source_public_methodology_report_ref}`",
        f"**Conversion plan:** `{report.source_conversion_plan_ref}`",
        f"**Conversion review packet:** `{report.source_conversion_review_packet_ref}`",
        f"**Ready packets:** {report.ready_packet_count}",
        f"**Blocked packets:** {report.blocked_packet_count}",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(["", "## Owner Packets", ""])
    for packet, output_ref in zip(report.packets, report.packet_output_refs, strict=True):
        lines.extend(
            [
                f"### {packet.target_repo}",
                "",
                f"- Status: {packet.status}",
                f"- Focus: {packet.handoff_focus}",
                f"- Packet ref: `{output_ref}`",
                "- First required action: "
                + (packet.required_owner_actions[0] if packet.required_owner_actions else "none"),
                "- First red-team note: "
                + (packet.red_team_notes[0] if packet.red_team_notes else "none"),
                "",
            ]
        )
    lines.extend(
        [
            "## Required Next Gates",
            "",
            *(f"- {gate}" for gate in report.required_next_gates),
            "",
            "## Boundary Flags",
            "",
            f"- Human review required: {report.human_review_required}",
            f"- Owning repo review required: {report.owning_repo_review_required}",
            f"- Direct runtime ingestion allowed: {report.direct_runtime_ingestion_allowed}",
            f"- Direct promotion performed: {report.direct_promotion_performed}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Sibling repo write performed: {report.sibling_repo_write_performed}",
            f"- GitHub issue created: {report.github_issue_created}",
            f"- GitHub PR created: {report.github_pr_created}",
            f"- Public records ingested: {report.public_records_ingested}",
            f"- Raw public payload committed: {report.raw_public_payload_committed}",
            f"- Real party records committed: {report.real_party_records_committed}",
            f"- Real matter records committed: {report.real_matter_records_committed}",
            f"- Synthetic fixtures created: {report.synthetic_fixtures_created}",
            f"- Fixture files mutated: {report.fixture_files_mutated}",
            f"- Fixture generation authorized: {report.fixture_generation_authorized}",
            f"- Connector implemented: {report.connector_implemented}",
            f"- Legal Knowledge adapter authorized: {report.legal_knowledge_adapter_authorized}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report is local owner-handoff planning evidence only. It does not create issues, open PRs, write sibling repos, promote canon, ingest public records, create fixtures, authorize adapters, admit Lake/SQLite records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_public_methodology_owner_handoff(
    *,
    methodology_report_path: str | Path,
    conversion_plan_path: str | Path,
    conversion_review_packet_path: str | Path,
    out_dir: str | Path,
) -> tuple[PublicMethodologyOwnerHandoffReport, Path]:
    methodology_path = Path(methodology_report_path)
    plan_path = Path(conversion_plan_path)
    review_path = Path(conversion_review_packet_path)
    methodology_report = PublicSourceMethodologyReport.model_validate(load_json(methodology_path))
    conversion_plan = PublicSyntheticFixtureConversionPlan.model_validate(load_json(plan_path))
    review_packet = PublicSyntheticFixtureConversionReviewPacket.model_validate(
        load_json(review_path)
    )
    checks = _build_checks(
        methodology_report=methodology_report,
        methodology_report_ref=str(methodology_path),
        conversion_plan=conversion_plan,
        conversion_plan_ref=str(plan_path),
        review_packet=review_packet,
        review_packet_ref=str(review_path),
    )
    ready = _ready_for_owner_packets(checks)
    packets = build_public_methodology_owner_handoff_packets(
        methodology_report=methodology_report,
        methodology_report_ref=str(methodology_path),
        conversion_plan=conversion_plan,
        conversion_plan_ref=str(plan_path),
        review_packet=review_packet,
        review_packet_ref=str(review_path),
        ready=ready,
    )

    run_dir = Path(out_dir)
    packet_dir = run_dir / PUBLIC_METHODOLOGY_OWNER_HANDOFF_DIRNAME
    packet_dir.mkdir(parents=True, exist_ok=True)
    packets_jsonl_path = run_dir / PUBLIC_METHODOLOGY_OWNER_HANDOFF_PACKETS_FILENAME
    if packets_jsonl_path.exists():
        packets_jsonl_path.unlink()

    packet_output_refs: list[str] = []
    for packet in packets:
        slug = _owner_slug(packet.target_repo)
        packet_path = packet_dir / f"{slug}.public_methodology_owner_packet.json"
        notes_path = packet_dir / f"{slug}.public_methodology_owner_packet.md"
        write_json(packet_path, packet.model_dump(mode="json"))
        notes_path.write_text(
            render_public_methodology_owner_handoff_packet(packet),
            encoding="utf-8",
        )
        append_jsonl(packets_jsonl_path, packet.model_dump(mode="json"))
        packet_output_refs.append(str(packet_path))

    report = build_public_methodology_owner_handoff_report(
        methodology_report=methodology_report,
        methodology_report_ref=str(methodology_path),
        conversion_plan=conversion_plan,
        conversion_plan_ref=str(plan_path),
        review_packet=review_packet,
        review_packet_ref=str(review_path),
        packets=packets,
        packet_output_refs=packet_output_refs,
        checks=checks,
    )
    write_json(
        run_dir / PUBLIC_METHODOLOGY_OWNER_HANDOFF_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / PUBLIC_METHODOLOGY_OWNER_HANDOFF_NOTES_FILENAME).write_text(
        render_public_methodology_owner_handoff_report(report),
        encoding="utf-8",
    )
    return report, run_dir
