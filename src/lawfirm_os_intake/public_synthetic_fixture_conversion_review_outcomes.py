from __future__ import annotations

from pathlib import Path

from .models import (
    PublicSyntheticFixtureConversionReviewDecisionTemplate,
    PublicSyntheticFixtureConversionReviewOutcomeCheck,
    PublicSyntheticFixtureConversionReviewOutcomeReport,
    PublicSyntheticFixtureConversionReviewPacket,
    PublicSyntheticFixtureConversionReviewRecommendation,
    PublicSyntheticFixtureConversionReviewRecord,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_RECORD_FILENAME = (
    "public_synthetic_fixture_conversion_review_record.json"
)
PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_HISTORY_FILENAME = (
    "public_synthetic_fixture_conversion_review_history.jsonl"
)
PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_OUTCOME_REPORT_FILENAME = (
    "public_synthetic_fixture_conversion_review_outcome_report.json"
)
PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_OUTCOME_NOTES_FILENAME = (
    "public_synthetic_fixture_conversion_review_outcome_report.md"
)

READY_REVIEW_PACKET_STATUS = "ready_for_human_conversion_review"

ACCEPT_CONVERSION_REVIEW_OUTCOME = "approve_conversion_spec_for_separate_fixture_pr"

PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_REQUIRED_NEXT_GATES = [
    "append_only_conversion_review_outcome",
    "separate_synthetic_fixture_generation_pr_if_approved",
    "synthetic_fixture_gold_review",
    "red_team_identity_reconstruction_review",
    "legal_knowledge_runtime_owner_review_before_adapter",
    "no_public_payload_or_identity_contamination",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    source_ids: list[str] | None = None,
    conversion_spec_ids: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> PublicSyntheticFixtureConversionReviewOutcomeCheck:
    return PublicSyntheticFixtureConversionReviewOutcomeCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        source_ids=source_ids or [],
        conversion_spec_ids=conversion_spec_ids or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _record_boundary_clear(record: PublicSyntheticFixtureConversionReviewRecord) -> bool:
    return (
        record.fixture_generation_authorized is False
        and record.fixture_pr_created is False
        and record.fixture_files_mutated is False
        and record.public_records_ingested is False
        and record.raw_public_payload_committed is False
        and record.connector_implemented is False
        and record.legal_knowledge_adapter_authorized is False
        and record.lake_write_performed is False
        and record.sqlite_write_performed is False
        and record.external_writes_performed is False
        and record.silent_learning_performed is False
    )


def _packet_boundary_clear(packet: PublicSyntheticFixtureConversionReviewPacket) -> bool:
    return (
        packet.public_records_ingested is False
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


def _accepted(record: PublicSyntheticFixtureConversionReviewRecord) -> bool:
    return record.outcome == ACCEPT_CONVERSION_REVIEW_OUTCOME


def _find_recommendation(
    packet: PublicSyntheticFixtureConversionReviewPacket,
    record: PublicSyntheticFixtureConversionReviewRecord,
) -> PublicSyntheticFixtureConversionReviewRecommendation | None:
    return next(
        (
            rec
            for rec in packet.recommendations
            if rec.conversion_spec_id == record.conversion_spec_id
            and rec.source_id == record.source_id
        ),
        None,
    )


def _find_decision_template(
    packet: PublicSyntheticFixtureConversionReviewPacket,
    record: PublicSyntheticFixtureConversionReviewRecord,
) -> PublicSyntheticFixtureConversionReviewDecisionTemplate | None:
    return next(
        (
            template
            for template in packet.decision_templates
            if template.conversion_spec_id == record.conversion_spec_id
            and template.source_id == record.source_id
        ),
        None,
    )


def _bind_record_to_packet(
    *,
    record: PublicSyntheticFixtureConversionReviewRecord,
    packet: PublicSyntheticFixtureConversionReviewPacket,
) -> PublicSyntheticFixtureConversionReviewRecord:
    if record.review_packet_id != packet.review_packet_id:
        raise ValueError(
            "conversion review record review_packet_id does not match: "
            f"{record.review_packet_id} != {packet.review_packet_id}"
        )
    if record.conversion_plan_id != packet.conversion_plan_id:
        raise ValueError(
            "conversion review record conversion_plan_id does not match: "
            f"{record.conversion_plan_id} != {packet.conversion_plan_id}"
        )
    if _find_recommendation(packet, record) is None:
        raise ValueError(
            "conversion review record source/spec is not present in review packet: "
            f"{record.source_id} / {record.conversion_spec_id}"
        )
    template = _find_decision_template(packet, record)
    if template is None:
        raise ValueError(
            "conversion review record source/spec has no decision template: "
            f"{record.source_id} / {record.conversion_spec_id}"
        )
    if record.outcome not in template.allowed_outcomes:
        raise ValueError(
            "conversion review record outcome is not allowed by decision template: "
            f"{record.outcome}"
        )
    return record


def build_public_synthetic_fixture_conversion_review_outcome_report(
    *,
    review_packet: PublicSyntheticFixtureConversionReviewPacket,
    review_packet_ref: str,
    review_record: PublicSyntheticFixtureConversionReviewRecord,
    history_ref: str,
) -> PublicSyntheticFixtureConversionReviewOutcomeReport:
    recommendation = _find_recommendation(review_packet, review_record)
    decision_template = _find_decision_template(review_packet, review_record)
    template_evidence_refs = decision_template.required_evidence_refs if decision_template else []
    evidence_refs_bound = set(template_evidence_refs).issubset(set(review_record.evidence_refs))
    approved = _accepted(review_record)
    checks = [
        _check(
            "review_packet_ready_without_writes",
            review_packet.status == READY_REVIEW_PACKET_STATUS
            and _packet_boundary_clear(review_packet),
            "Source review packet is ready for human conversion review and has no side effects.",
            artifact_refs=[review_packet_ref],
        ),
        _check(
            "review_record_matches_packet",
            review_record.review_packet_id == review_packet.review_packet_id
            and review_record.conversion_plan_id == review_packet.conversion_plan_id
            and recommendation is not None
            and decision_template is not None,
            "Review record is bound to the supplied review packet source/spec/template.",
            artifact_refs=[review_packet_ref],
            source_ids=[review_record.source_id],
            conversion_spec_ids=[review_record.conversion_spec_id],
        ),
        _check(
            "decision_template_allows_outcome",
            decision_template is not None
            and review_record.outcome in decision_template.allowed_outcomes,
            "Review outcome is one of the decision template's allowed outcomes.",
            artifact_refs=[review_packet_ref],
            source_ids=[review_record.source_id],
            conversion_spec_ids=[review_record.conversion_spec_id],
        ),
        _check(
            "decision_evidence_refs_bound",
            bool(template_evidence_refs) and evidence_refs_bound,
            "Review decision cites the decision template's required evidence refs.",
            artifact_refs=review_record.evidence_refs,
            source_ids=[review_record.source_id],
            conversion_spec_ids=[review_record.conversion_spec_id],
            blocking_refs=template_evidence_refs,
        ),
        _check(
            "human_decision_record_complete",
            bool(
                review_record.reviewer_id.strip()
                and review_record.reviewed_at.strip()
                and review_record.decision_reason.strip()
            ),
            "Human conversion review decision includes reviewer, timestamp, and reason.",
        ),
        _check(
            "approved_review_has_required_gates",
            (not approved)
            or {
                "human_public_synthetic_conversion_review",
                "source_license_review",
                "privacy_review",
                "retention_decision",
                "separate_synthetic_fixture_generation_pr_if_approved",
                "synthetic_fixture_gold_review",
                "red_team_identity_reconstruction_review",
            }.issubset(set(review_record.accepted_required_gates)),
            "Approved conversion decisions include required human gates before fixture PR planning.",
            artifact_refs=review_record.accepted_required_gates,
        ),
        _check(
            "revision_or_rejection_has_reasons",
            review_record.outcome not in {"require_spec_revision", "reject_source_for_fixture_use"}
            or bool(review_record.rejected_or_revision_reasons),
            "Revision or rejection decisions include reviewer reasons.",
            artifact_refs=review_record.rejected_or_revision_reasons,
        ),
        _check(
            "needs_more_information_has_followups",
            review_record.outcome != "needs_more_information"
            or bool(review_record.required_followups),
            "Needs-more-information decisions include required followups.",
            artifact_refs=review_record.required_followups,
        ),
        _check(
            "no_side_effects_from_review_recording",
            _record_boundary_clear(review_record),
            "Recording the conversion review did not create fixtures, ingest records, authorize adapters, write Lake/SQLite records, or perform silent learning.",
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    if failed_checks:
        status = "conversion_review_blocked_by_review_evidence"
    elif approved:
        status = "conversion_review_recorded_separate_fixture_pr_required"
    elif review_record.outcome in {"require_spec_revision", "reject_source_for_fixture_use"}:
        status = "conversion_review_recorded_revision_or_rejection"
    elif review_record.outcome == "needs_more_information":
        status = "conversion_review_recorded_more_information_required"
    else:
        status = "conversion_review_recorded_human_only_hold"

    return PublicSyntheticFixtureConversionReviewOutcomeReport(
        review_outcome_report_id=_stable_id(
            "publicfixtureconvoutcome",
            "|".join(
                [
                    review_packet.review_packet_id,
                    review_record.conversion_review_id,
                    review_record.outcome,
                ]
            ),
        ),
        status=status,  # type: ignore[arg-type]
        source_review_packet_ref=review_packet_ref,
        review_packet_id=review_packet.review_packet_id,
        conversion_plan_id=review_packet.conversion_plan_id,
        conversion_review_id=review_record.conversion_review_id,
        conversion_spec_id=review_record.conversion_spec_id,
        source_id=review_record.source_id,
        outcome=review_record.outcome,
        decision_reason=review_record.decision_reason,
        source_review_packet_status=review_packet.status,
        target_fixture_family=recommendation.target_fixture_family if recommendation else None,
        source_recommendation_id=recommendation.recommendation_id if recommendation else None,
        source_recommended_action=recommendation.recommended_action if recommendation else None,
        source_recommended_outcome=decision_template.recommended_outcome
        if decision_template
        else None,
        source_decision_template_id=decision_template.decision_template_id
        if decision_template
        else None,
        accepted_required_gates=review_record.accepted_required_gates,
        rejected_or_revision_reasons=review_record.rejected_or_revision_reasons,
        required_followups=review_record.required_followups,
        evidence_refs=review_record.evidence_refs,
        append_only_history_ref=history_ref,
        checks=checks,
        required_next_gates=PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_REQUIRED_NEXT_GATES,
        accepted_for_separate_fixture_pr=approved and not failed_checks,
        separate_fixture_generation_pr_required=approved and not failed_checks,
        generated_at=now_iso(),
    )


def render_public_synthetic_fixture_conversion_review_outcome_report(
    report: PublicSyntheticFixtureConversionReviewOutcomeReport,
) -> str:
    lines = [
        "# Public Synthetic Fixture Conversion Review Outcome",
        "",
        f"**Report ID:** {report.review_outcome_report_id}",
        f"**Status:** {report.status}",
        f"**Outcome:** {report.outcome}",
        f"**Source:** `{report.source_id}`",
        f"**Conversion spec:** `{report.conversion_spec_id}`",
        f"**Review packet:** `{report.source_review_packet_ref}`",
        f"**Append-only history:** `{report.append_only_history_ref}`",
        "",
        "## Human Decision",
        "",
        f"- Decision reason: {report.decision_reason}",
        f"- Accepted gates: {len(report.accepted_required_gates)}",
        f"- Revision/rejection reasons: {len(report.rejected_or_revision_reasons)}",
        f"- Required followups: {len(report.required_followups)}",
        f"- Separate fixture-generation PR required: {report.separate_fixture_generation_pr_required}",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(
        [
            "",
            "## Required Next Gates",
            "",
            *(f"- {gate}" for gate in report.required_next_gates),
            "",
            "## Boundary",
            "",
            f"- Candidate only: {report.candidate_only}",
            f"- Non-authoritative: {report.non_authoritative}",
            f"- Planning only: {report.planning_only}",
            f"- Fixture generation authorized: {report.fixture_generation_authorized}",
            f"- Fixture PR created: {report.fixture_pr_created}",
            f"- Fixture files mutated: {report.fixture_files_mutated}",
            f"- Public records ingested: {report.public_records_ingested}",
            f"- Raw public payload committed: {report.raw_public_payload_committed}",
            f"- Connector implemented: {report.connector_implemented}",
            f"- Legal Knowledge adapter authorized: {report.legal_knowledge_adapter_authorized}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report records local append-only public fixture conversion review evidence only. It does not create fixtures, create a PR, ingest public records, authorize adapters, write Lake/SQLite records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_public_synthetic_fixture_conversion_review_outcome_record(
    *,
    review_packet_path: str | Path,
    review_path: str | Path,
    out_dir: str | Path,
) -> tuple[PublicSyntheticFixtureConversionReviewOutcomeReport, Path]:
    packet_path = Path(review_packet_path)
    review_decision_path = Path(review_path)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    packet = PublicSyntheticFixtureConversionReviewPacket.model_validate(load_json(packet_path))
    raw_record = PublicSyntheticFixtureConversionReviewRecord.model_validate(
        load_json(review_decision_path)
    )
    record = _bind_record_to_packet(record=raw_record, packet=packet)
    history_path = run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_HISTORY_FILENAME
    report = build_public_synthetic_fixture_conversion_review_outcome_report(
        review_packet=packet,
        review_packet_ref=str(packet_path),
        review_record=record,
        history_ref=str(history_path),
    )
    write_json(
        run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_RECORD_FILENAME,
        record.model_dump(mode="json"),
    )
    append_jsonl(history_path, record.model_dump(mode="json"))
    write_json(
        run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_OUTCOME_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / PUBLIC_SYNTHETIC_FIXTURE_CONVERSION_REVIEW_OUTCOME_NOTES_FILENAME).write_text(
        render_public_synthetic_fixture_conversion_review_outcome_report(report),
        encoding="utf-8",
    )
    return report, run_dir
