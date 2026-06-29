from __future__ import annotations

from pathlib import Path

from .models import (
    PublicSyntheticFixtureConversionPlan,
    PublicSyntheticFixtureConversionReviewDecisionTemplate,
    PublicSyntheticFixtureConversionReviewPacket,
    PublicSyntheticFixtureConversionReviewRecommendation,
    PublicSyntheticFixtureConversionReviewRedTeamNote,
    PublicSyntheticFixtureConversionSpec,
    PublicSyntheticFixtureReviewAction,
    PublicSyntheticFixtureReviewOutcome,
    PublicSyntheticFixtureReviewPriority,
)
from .util import digest_text, load_json, now_iso, write_json


PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_PACKET_FILENAME = (
    "public_synthetic_fixture_conversion_review_packet.json"
)
PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_NOTES_FILENAME = (
    "public_synthetic_fixture_conversion_review_packet.md"
)
PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_DECISION_TEMPLATE_FILENAME = (
    "public_synthetic_fixture_conversion_review_decision_template.json"
)

READY_CONVERSION_PLAN_STATUS = "ready_for_human_conversion_review"

REQUIRED_NEXT_GATES = [
    "human_public_synthetic_conversion_review",
    "append_only_conversion_review_outcome",
    "separate_synthetic_fixture_generation_pr_if_approved",
    "synthetic_fixture_gold_review",
    "red_team_identity_reconstruction_review",
    "legal_knowledge_runtime_owner_review_before_adapter",
]

ALLOWED_REVIEWER_OUTCOMES: list[PublicSyntheticFixtureReviewOutcome] = [
    "approve_conversion_spec_for_separate_fixture_pr",
    "require_spec_revision",
    "reject_source_for_fixture_use",
    "needs_more_information",
    "human_only_hold",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _priority_for_spec(
    spec: PublicSyntheticFixtureConversionSpec,
) -> PublicSyntheticFixtureReviewPriority:
    if spec.source_id in {"npdb-public-use-data", "courtlistener-recap"}:
        return "critical"
    if spec.source_id in {"cmu-enron-email", "fjc-idb"}:
        return "high"
    return "medium"


def _recommended_action(
    spec: PublicSyntheticFixtureConversionSpec,
) -> PublicSyntheticFixtureReviewAction:
    if spec.source_id in {"npdb-public-use-data", "cmu-enron-email"}:
        return "hold_for_privacy_or_license_review"
    if spec.review_status != "planned_for_human_conversion_review":
        return "revise_conversion_spec_before_fixture_pr"
    return "approve_for_separate_fixture_pr_after_required_reviews"


def _recommended_outcome(
    action: PublicSyntheticFixtureReviewAction,
) -> PublicSyntheticFixtureReviewOutcome:
    if action == "approve_for_separate_fixture_pr_after_required_reviews":
        return "approve_conversion_spec_for_separate_fixture_pr"
    if action == "hold_for_privacy_or_license_review":
        return "needs_more_information"
    if action == "reject_source_for_fixture_use":
        return "reject_source_for_fixture_use"
    if action == "human_only_hold":
        return "human_only_hold"
    return "require_spec_revision"


def _why_notes(spec: PublicSyntheticFixtureConversionSpec) -> list[str]:
    notes = [
        f"Conversion spec `{spec.conversion_spec_id}` targets `{spec.target_fixture_family}`.",
        "The source is limited to structure-only use and cannot supply observed intake facts.",
        "The spec forbids real party names, real case numbers, raw public payloads, downloaded payloads, and privileged material.",
        "Identity replacement and synthetic gold checks are present before any fixture PR can be considered.",
    ]
    if spec.source_id == "courtlistener-recap":
        notes.append(
            "Court docket structures are real public matters; reviewer must check that no docket, party, attorney, or filing identity can be reconstructed."
        )
    elif spec.source_id == "fjc-idb":
        notes.append(
            "Aggregate case metadata can shape distributions, but reviewer must check that buckets cannot join back to individual records."
        )
    elif spec.source_id == "cmu-enron-email":
        notes.append(
            "The email corpus has privacy history and instruction-like message text risk; reviewer should hold until privacy/license posture is explicitly accepted."
        )
    elif spec.source_id == "sec-edgar":
        notes.append(
            "Public filing section shape may be useful, but real entity identifiers and accession-style references must stay out of fixtures."
        )
    elif spec.source_id == "nhtsa-public-crash-data":
        notes.append(
            "Crash data can shape synthetic auto-liability fields only at aggregate/pattern level, not real incident facts."
        )
    elif spec.source_id == "npdb-public-use-data":
        notes.append(
            "Healthcare public-use data needs heightened privacy review and must not identify providers, claimants, or claims."
        )
    return notes


def _human_decisions(spec: PublicSyntheticFixtureConversionSpec) -> list[str]:
    decisions = [
        "confirm source license, privacy, and retention review posture",
        "confirm target fixture family is appropriate",
        "confirm forbidden inputs are complete",
        "confirm identity replacement rules are sufficient",
        "confirm synthetic gold and red-team checks are sufficient",
        "decide whether a separate fixture-generation PR may be prepared",
    ]
    if spec.source_id in {"npdb-public-use-data", "cmu-enron-email"}:
        decisions.append("record explicit privacy/license acceptance or hold the source")
    return decisions


def _red_team_focus(spec: PublicSyntheticFixtureConversionSpec) -> list[str]:
    focus = [
        "identity_reconstruction",
        "payload_contamination",
        "legal_fact_misuse",
        "fixture_pr_boundary",
    ]
    if spec.target_fixture_family in {
        "aggregate_case_metadata",
        "auto_liability_distribution",
        "medical_malpractice_distribution",
    }:
        focus.append("aggregate_reidentification")
    if spec.target_fixture_family == "messy_email_structure":
        focus.append("prompt_injection_as_data")
    if spec.source_id in {"npdb-public-use-data", "cmu-enron-email"}:
        focus.append("privacy_license_retention")
    return focus


def _recommendation(
    plan: PublicSyntheticFixtureConversionPlan,
    spec: PublicSyntheticFixtureConversionSpec,
) -> PublicSyntheticFixtureConversionReviewRecommendation:
    action = _recommended_action(spec)
    return PublicSyntheticFixtureConversionReviewRecommendation(
        recommendation_id=_stable_id(
            "publicfixtureconvrec", f"{plan.conversion_plan_id}|{spec.conversion_spec_id}"
        ),
        conversion_spec_id=spec.conversion_spec_id,
        source_id=spec.source_id,
        target_fixture_family=spec.target_fixture_family,
        recommended_action=action,
        priority=_priority_for_spec(spec),
        why=_why_notes(spec),
        required_human_decisions=_human_decisions(spec),
        required_evidence_refs=[
            plan.conversion_plan_id,
            spec.conversion_spec_id,
            spec.source_methodology_ref,
        ],
        red_team_focus=_red_team_focus(spec),
    )


def _decision_template(
    plan: PublicSyntheticFixtureConversionPlan,
    rec: PublicSyntheticFixtureConversionReviewRecommendation,
) -> PublicSyntheticFixtureConversionReviewDecisionTemplate:
    return PublicSyntheticFixtureConversionReviewDecisionTemplate(
        decision_template_id=_stable_id(
            "publicfixtureconvdecision",
            f"{plan.conversion_plan_id}|{rec.conversion_spec_id}",
        ),
        conversion_spec_id=rec.conversion_spec_id,
        source_id=rec.source_id,
        recommended_action=rec.recommended_action,
        allowed_outcomes=ALLOWED_REVIEWER_OUTCOMES,
        recommended_outcome=_recommended_outcome(rec.recommended_action),
        required_fields=[
            "conversion_review_id",
            "review_packet_id",
            "conversion_plan_id",
            "conversion_spec_id",
            "source_id",
            "reviewer_id",
            "reviewed_at",
            "outcome",
            "decision_reason",
            "accepted_required_gates",
            "rejected_or_revision_reasons",
            "required_followups",
            "evidence_refs",
            "supersedes_review_outcome_id",
        ],
        required_evidence_refs=rec.required_evidence_refs,
    )


def _red_team_notes(
    plan: PublicSyntheticFixtureConversionPlan,
    recommendations: list[PublicSyntheticFixtureConversionReviewRecommendation],
) -> list[PublicSyntheticFixtureConversionReviewRedTeamNote]:
    all_sources = [rec.source_id for rec in recommendations]
    notes = [
        PublicSyntheticFixtureConversionReviewRedTeamNote(
            note_id=_stable_id("publicfixtureconvrt", f"{plan.conversion_plan_id}|boundary"),
            severity="critical",
            scope="boundary",
            source_ids=all_sources,
            message=(
                "This packet is not approval to create fixtures, ingest public records, "
                "authorize adapters, write Lake/SQLite records, or use public data at runtime."
            ),
            recommended_check=(
                "Confirm fixture_files_mutated=false, fixture_pr_created=false, "
                "public_records_ingested=false, and legal_knowledge_adapter_authorized=false."
            ),
        ),
        PublicSyntheticFixtureConversionReviewRedTeamNote(
            note_id=_stable_id("publicfixtureconvrt", f"{plan.conversion_plan_id}|identity"),
            severity="critical",
            scope="identity_reconstruction",
            source_ids=all_sources,
            message="Public records are real matters and must not be reconstructable from synthetic fixtures.",
            recommended_check=(
                "Check docket/source IDs, party names, dates, locations, entity identifiers, "
                "and unique fact patterns for reconstruction risk."
            ),
        ),
        PublicSyntheticFixtureConversionReviewRedTeamNote(
            note_id=_stable_id("publicfixtureconvrt", f"{plan.conversion_plan_id}|payload"),
            severity="high",
            scope="payload_contamination",
            source_ids=all_sources,
            message="Structure-only planning must not smuggle raw public text into fixtures.",
            recommended_check=(
                "Confirm no public payload text, accession numbers, docket numbers, message bodies, "
                "or downloaded public records appear in any proposed fixture."
            ),
        ),
        PublicSyntheticFixtureConversionReviewRedTeamNote(
            note_id=_stable_id("publicfixtureconvrt", f"{plan.conversion_plan_id}|facts"),
            severity="high",
            scope="legal_fact_misuse",
            source_ids=all_sources,
            message="Public-source structure cannot become observed intake fact, conflict evidence, legal merits evidence, or budget evidence.",
            recommended_check=(
                "Confirm downstream fixtures use synthetic evidence refs and do not drive conflict, "
                "merits, matter, role, or budget conclusions from public records."
            ),
        ),
    ]
    aggregate_sources = [
        rec.source_id
        for rec in recommendations
        if "aggregate_reidentification" in rec.red_team_focus
    ]
    if aggregate_sources:
        notes.append(
            PublicSyntheticFixtureConversionReviewRedTeamNote(
                note_id=_stable_id("publicfixtureconvrt", f"{plan.conversion_plan_id}|aggregate"),
                severity="high",
                scope="aggregate_reidentification",
                source_ids=aggregate_sources,
                message="Aggregate/public distributions can become identifying when overfit to rare combinations.",
                recommended_check=(
                    "Bucket, perturb, or generalize fields before fixture design and avoid one-record reconstruction."
                ),
            )
        )
    prompt_sources = [
        rec.source_id for rec in recommendations if "prompt_injection_as_data" in rec.red_team_focus
    ]
    if prompt_sources:
        notes.append(
            PublicSyntheticFixtureConversionReviewRedTeamNote(
                note_id=_stable_id("publicfixtureconvrt", f"{plan.conversion_plan_id}|prompt"),
                severity="high",
                scope="prompt_injection",
                source_ids=prompt_sources,
                message="Email-style fixtures must preserve instruction-like text only as untrusted synthetic data.",
                recommended_check=(
                    "Include prompt-injection-as-data gold checks and ensure no worker treats message text as instructions."
                ),
            )
        )
    privacy_sources = [
        rec.source_id
        for rec in recommendations
        if "privacy_license_retention" in rec.red_team_focus
    ]
    if privacy_sources:
        notes.append(
            PublicSyntheticFixtureConversionReviewRedTeamNote(
                note_id=_stable_id("publicfixtureconvrt", f"{plan.conversion_plan_id}|privacy"),
                severity="critical",
                scope="privacy_license_retention",
                source_ids=privacy_sources,
                message="Privacy, license, and retention concerns must be decided before fixture generation.",
                recommended_check=(
                    "Record explicit reviewer acceptance, required limitations, or source hold before any fixture PR."
                ),
            )
        )
    return notes


def build_public_synthetic_fixture_conversion_review_packet(
    *,
    conversion_plan_path: str | Path,
    human_readable_review_ref: str | None,
    decision_template_ref: str | None,
) -> PublicSyntheticFixtureConversionReviewPacket:
    plan_path = Path(conversion_plan_path)
    plan = PublicSyntheticFixtureConversionPlan.model_validate(load_json(plan_path))
    if plan.status != READY_CONVERSION_PLAN_STATUS:
        notes = [
            PublicSyntheticFixtureConversionReviewRedTeamNote(
                note_id=_stable_id(
                    "publicfixtureconvrt", f"{plan.conversion_plan_id}|blocked-boundary"
                ),
                severity="critical",
                scope="boundary",
                message="Conversion review is blocked because the conversion plan is not ready.",
                recommended_check="Resolve blocked conversion-plan checks before human conversion review.",
            )
        ]
        return PublicSyntheticFixtureConversionReviewPacket(
            review_packet_id=_stable_id(
                "publicfixtureconvreview", f"{plan.conversion_plan_id}|blocked"
            ),
            conversion_plan_id=plan.conversion_plan_id,
            conversion_plan_ref=str(plan_path),
            conversion_plan_status=plan.status,
            status="blocked_by_conversion_plan",
            spec_count=plan.spec_count,
            recommendation_count=0,
            red_team_note_count=len(notes),
            decision_template_count=0,
            recommendations=[],
            red_team_notes=notes,
            decision_templates=[],
            allowed_reviewer_outcomes=ALLOWED_REVIEWER_OUTCOMES,
            required_next_gates=REQUIRED_NEXT_GATES,
            human_readable_review_ref=human_readable_review_ref,
            decision_template_ref=decision_template_ref,
            generated_at=now_iso(),
        )

    recommendations = [_recommendation(plan, spec) for spec in plan.specs]
    decision_templates = [_decision_template(plan, rec) for rec in recommendations]
    red_team_notes = _red_team_notes(plan, recommendations)
    status = "ready_for_human_conversion_review" if recommendations else "no_specs_to_review"
    return PublicSyntheticFixtureConversionReviewPacket(
        review_packet_id=_stable_id(
            "publicfixtureconvreview", f"{plan.conversion_plan_id}|human-review"
        ),
        conversion_plan_id=plan.conversion_plan_id,
        conversion_plan_ref=str(plan_path),
        conversion_plan_status=plan.status,
        status=status,
        spec_count=plan.spec_count,
        recommendation_count=len(recommendations),
        red_team_note_count=len(red_team_notes),
        decision_template_count=len(decision_templates),
        recommendations=recommendations,
        red_team_notes=red_team_notes,
        decision_templates=decision_templates,
        allowed_reviewer_outcomes=ALLOWED_REVIEWER_OUTCOMES,
        required_next_gates=REQUIRED_NEXT_GATES,
        human_readable_review_ref=human_readable_review_ref,
        decision_template_ref=decision_template_ref,
        generated_at=now_iso(),
    )


def render_public_synthetic_fixture_conversion_review_packet(
    packet: PublicSyntheticFixtureConversionReviewPacket,
) -> str:
    lines = [
        "# Public Synthetic Fixture Conversion Review Packet",
        "",
        f"**Review packet ID:** {packet.review_packet_id}",
        f"**Status:** {packet.status}",
        f"**Conversion plan:** `{packet.conversion_plan_ref}`",
        f"**Conversion plan status:** {packet.conversion_plan_status}",
        f"**Specs:** {packet.spec_count}",
        f"**Recommendations:** {packet.recommendation_count}",
        f"**Decision templates:** {packet.decision_template_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {packet.candidate_only}",
        f"- Human review required: {packet.human_review_required}",
        f"- Append-only review outcome required: {packet.append_only_review_outcome_required}",
        f"- Public records ingested: {packet.public_records_ingested}",
        f"- Raw public payload committed: {packet.raw_public_payload_committed}",
        f"- Synthetic fixtures created: {packet.synthetic_fixtures_created}",
        f"- Fixture files mutated: {packet.fixture_files_mutated}",
        f"- Fixture PR created: {packet.fixture_pr_created}",
        f"- Connector implemented: {packet.connector_implemented}",
        f"- Legal Knowledge adapter authorized: {packet.legal_knowledge_adapter_authorized}",
        f"- Lake write performed: {packet.lake_write_performed}",
        f"- SQLite write performed: {packet.sqlite_write_performed}",
        f"- External writes performed: {packet.external_writes_performed}",
        f"- Silent learning performed: {packet.silent_learning_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in packet.required_next_gates),
        "",
        "## Recommendations",
        "",
    ]
    if not packet.recommendations:
        lines.append("- none")
    for rec in packet.recommendations:
        lines.append(
            f"- `{rec.source_id}` -> `{rec.target_fixture_family}`: "
            f"{rec.recommended_action}; priority={rec.priority}"
        )
        lines.append("  Why:")
        lines.extend(f"  - {item}" for item in rec.why)
        lines.append("  Required human decisions:")
        lines.extend(f"  - {item}" for item in rec.required_human_decisions)
        lines.append("  Red-team focus:")
        lines.extend(f"  - {item}" for item in rec.red_team_focus)
    lines.extend(["", "## Red-Team Notes", ""])
    for note in packet.red_team_notes:
        source_text = ", ".join(note.source_ids) if note.source_ids else "packet"
        lines.extend(
            [
                f"- [{note.severity}] {note.scope} ({source_text}): {note.message}",
                f"  Check: {note.recommended_check}",
            ]
        )
    lines.extend(["", "## Decision Templates", ""])
    if not packet.decision_templates:
        lines.append("- none")
    for template in packet.decision_templates:
        lines.extend(
            [
                f"- `{template.source_id}`",
                f"  Recommended outcome: {template.recommended_outcome}",
                f"  Allowed outcomes: {', '.join(template.allowed_outcomes)}",
                f"  Required fields: {', '.join(template.required_fields)}",
                f"  Fixture generation authorized: {template.fixture_generation_authorized}",
                f"  Fixture files mutated: {template.fixture_files_mutated}",
                f"  Silent learning allowed: {template.silent_learning_allowed}",
            ]
        )
    lines.extend(
        [
            "",
            "This packet is a review aid only. It does not approve fixture generation, create a fixture PR, ingest public records, authorize adapters, write Lake/SQLite records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_public_synthetic_fixture_conversion_review(
    *,
    conversion_plan_path: str | Path,
    out_dir: str | Path,
) -> tuple[PublicSyntheticFixtureConversionReviewPacket, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    notes_path = run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_NOTES_FILENAME
    decision_template_path = (
        run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_DECISION_TEMPLATE_FILENAME
    )
    packet = build_public_synthetic_fixture_conversion_review_packet(
        conversion_plan_path=conversion_plan_path,
        human_readable_review_ref=str(notes_path),
        decision_template_ref=str(decision_template_path),
    )
    write_json(
        run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_PACKET_FILENAME,
        packet.model_dump(mode="json"),
    )
    write_json(
        decision_template_path,
        [item.model_dump(mode="json") for item in packet.decision_templates],
    )
    notes_path.write_text(
        render_public_synthetic_fixture_conversion_review_packet(packet),
        encoding="utf-8",
    )
    return packet, run_dir
