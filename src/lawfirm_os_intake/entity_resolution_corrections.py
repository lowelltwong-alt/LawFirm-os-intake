from __future__ import annotations

from pathlib import Path

from .models import (
    EntityResolutionCorrectionCheck,
    EntityResolutionCorrectionRecord,
    EntityResolutionCorrectionReport,
    EvidenceRef,
    ExceptionLakeCandidate,
    SourceBundle,
)
from .util import append_jsonl, digest_json, digest_text, load_json, now_iso, write_json


RECORD_FILENAME = "entity_resolution_correction_record.json"
REPORT_FILENAME = "entity_resolution_correction_report.json"
EXCEPTION_CANDIDATES_FILENAME = "entity_resolution_exception_candidates.jsonl"
DAD_DRAFT_FILENAME = "entity_resolution_dad_lesson_draft.json"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    correction_ids: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> EntityResolutionCorrectionCheck:
    return EntityResolutionCorrectionCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        correction_ids=correction_ids or [],
        blocking_refs=blocking_refs or ([] if passed else correction_ids or []),
    )


def _ref_is_exact(bundle: SourceBundle, ref: EvidenceRef, expected: str) -> bool:
    source = next((item for item in bundle.sources if item.source_id == ref.source_id), None)
    if source is None or source.text is None or ref.segment_id != f"{ref.source_id}:source_text":
        return False
    snippet = source.text[ref.start_offset : ref.end_offset]
    return snippet == expected and ref.sha256 == digest_text(snippet)


def build_entity_resolution_correction_report(
    *,
    bundle: SourceBundle,
    source_bundle_ref: str,
    record: EntityResolutionCorrectionRecord,
    generated_at: str | None = None,
) -> tuple[EntityResolutionCorrectionReport, list[ExceptionLakeCandidate], dict[str, object]]:
    source_bound_ids = [
        decision.correction_id
        for decision in record.decisions
        if not all(
            _ref_is_exact(bundle, ref, decision.comparison.left.raw_value)
            for ref in decision.left_evidence_refs
        )
        or not all(
            _ref_is_exact(bundle, ref, decision.comparison.right.raw_value)
            for ref in decision.right_evidence_refs
        )
    ]
    bundle_matches = record.source_bundle_id == bundle.bundle_id
    exceptions: list[ExceptionLakeCandidate] = []
    for decision in record.decisions:
        if decision.outcome == "needs_more_information":
            label, lake_class = "entity_resolution_ambiguity_requires_review", "workflow_escalation"
        elif decision.outcome == "correct_declared_edge":
            label, lake_class = (
                "entity_resolution_declared_edge_correction",
                "authority_conflict_override",
            )
        else:
            label, lake_class = "human_entity_resolution_correction", "workflow_escalation"
        exceptions.append(
            ExceptionLakeCandidate(
                candidate_id="entitycorrection_"
                + digest_json(
                    {
                        "record": record.entity_resolution_correction_record_id,
                        "decision": decision.correction_id,
                    }
                )[7:27],
                run_id=record.run_id,
                preflight_packet_id=record.preflight_packet_id,
                local_event_label=label,
                canonical_lake_class=lake_class,  # type: ignore[arg-type]
                reason=decision.decision_reason,
                evidence_refs=[*decision.left_evidence_refs, *decision.right_evidence_refs],
                structured_refs=[
                    "docs/fable/entity-resolution-boundary.md#6-how-dad-learns-entity-resolution-mistakes-without-creating-canon",
                    f"entity_resolution_correction:{decision.correction_id}",
                ],
                blocked_state="entity_resolution_requires_human_review"
                if decision.outcome == "needs_more_information"
                else None,
            )
        )
    checks = [
        _check(
            "source_bundle_is_synthetic",
            bundle.data_origin == "synthetic"
            and not bundle.contains_real_client_data
            and not bundle.contains_real_matter_data
            and not bundle.contains_privileged_data,
            "Source bundle remains synthetic-only.",
        ),
        _check(
            "correction_record_matches_source_bundle",
            bundle_matches,
            "Correction record is bound to the supplied source bundle.",
        ),
        _check(
            "all_correction_evidence_is_exact_and_hash_bound",
            not source_bound_ids,
            "Every decision preserves both observed entity spans and hashes.",
            correction_ids=source_bound_ids,
        ),
        _check(
            "no_alias_table_mutation_or_persistent_identity_assertion",
            record.no_alias_table_mutation
            and record.no_persistent_identity_assertion
            and record.no_lake_admission_performed
            and record.no_dad_mail_emitted,
            "Corrections only propose reviewed local table changes and never persist identity or emit external writes.",
        ),
    ]
    status = (
        "blocked_entity_resolution_corrections"
        if any(item.status == "failed" for item in checks)
        else "entity_resolution_corrections_ready_for_review"
    )
    labels = sorted({item.local_event_label for item in exceptions})
    report_core = {
        "record": record.entity_resolution_correction_record_id,
        "status": status,
        "labels": labels,
    }
    report = EntityResolutionCorrectionReport(
        entity_resolution_correction_report_id="entityresolutioncorrection_"
        + digest_json(report_core)[7:27],
        status=status,
        source_bundle_ref=source_bundle_ref,
        entity_resolution_correction_record_id=record.entity_resolution_correction_record_id,
        decision_count=len(record.decisions),
        alias_table_candidate_count=sum(
            item.outcome == "confirm_alias_table_candidate" for item in record.decisions
        ),
        declared_edge_correction_count=sum(
            item.outcome == "correct_declared_edge" for item in record.decisions
        ),
        needs_more_information_count=sum(
            item.outcome == "needs_more_information" for item in record.decisions
        ),
        candidate_lake_event_labels=labels,
        candidate_dad_lesson_draft_status="not_emitted_requires_thresholded_human_review",
        candidate_exception_count=len(exceptions),
        checks=checks,
        required_next_gates=[
            "human_review_of_candidate_table_diff",
            "orchestrator_owned_persistent_identity_before_cross_bundle_use",
            "exception_lake_owner_review_before_admission",
            "thresholded_human_review_before_dad_lesson_draft_emission",
            "no_matcher_mutation_from_corrections",
        ],
        generated_at=generated_at or now_iso(),
    )
    dad_draft = {
        "status": report.candidate_dad_lesson_draft_status,
        "candidate_only": True,
        "emitted_to_outbox": False,
        "reason": "Corrections require thresholded human review before any DAD lesson is drafted or mailed.",
        "candidate_pattern_keys": sorted(
            {
                f"{decision.comparison.comparison_rung}:{decision.outcome}"
                for decision in record.decisions
            }
        ),
        "source_record_ref": record.entity_resolution_correction_record_id,
    }
    return report, exceptions, dad_draft


def run_entity_resolution_correction_audit(
    *,
    source_bundle_path: str | Path,
    correction_record_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[EntityResolutionCorrectionReport, Path]:
    source_path, record_path, run_dir = (
        Path(source_bundle_path),
        Path(correction_record_path),
        Path(out_dir),
    )
    bundle = SourceBundle.model_validate(load_json(source_path))
    record = EntityResolutionCorrectionRecord.model_validate(load_json(record_path))
    run_dir.mkdir(parents=True, exist_ok=True)
    report, exceptions, dad_draft = build_entity_resolution_correction_report(
        bundle=bundle,
        source_bundle_ref=str(source_path),
        record=record,
        generated_at=generated_at,
    )
    write_json(run_dir / RECORD_FILENAME, record.model_dump(mode="json"))
    (run_dir / EXCEPTION_CANDIDATES_FILENAME).touch()
    for candidate in exceptions:
        append_jsonl(run_dir / EXCEPTION_CANDIDATES_FILENAME, candidate.model_dump(mode="json"))
    write_json(run_dir / REPORT_FILENAME, report.model_dump(mode="json"))
    write_json(run_dir / DAD_DRAFT_FILENAME, dad_draft)
    return report, run_dir
