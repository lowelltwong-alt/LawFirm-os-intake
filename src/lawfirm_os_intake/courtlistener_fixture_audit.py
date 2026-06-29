from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import (
    BudgetDriverLabel,
    ConflictSeedLabel,
    CourtListenerDatasetManifest,
    CourtListenerDocketSnapshot,
    CourtListenerFixtureAuditCheck,
    CourtListenerFixtureAuditReport,
    CourtListenerLabelSourceRef,
    IntakeStageDocumentLabel,
    PersonTimelineEventLabel,
)
from .util import digest_text, load_json, new_id, now_iso, write_json


COURTLISTENER_FIXTURE_AUDIT_REPORT_FILENAME = "courtlistener_fixture_audit_report.json"
COURTLISTENER_FIXTURE_AUDIT_NOTES_FILENAME = "courtlistener_fixture_audit_report.md"

POSITIVE_CASE_STAGES = {
    "intake_stage",
    "pre_answer",
    "answer_filed",
    "early_motion",
    "initial_scheduling",
}

PROHIBITED_POSITIVE_DOCUMENT_TYPES = {
    "interrogatories",
    "requests_for_production",
    "requests_for_admission",
    "deposition_notices",
    "deposition_transcripts",
    "expert_reports",
    "summary_judgment_records",
    "trial_exhibits",
    "trial_transcripts",
    "fee_petitions",
    "appellate_briefs",
}

REQUIRED_CONFLICT_ROLES = {
    "employee",
    "employer",
    "opposing_counsel",
    "law_firm",
}

REQUIRED_BUDGET_DRIVERS = {
    "matter_family",
    "representation_posture",
    "forum",
    "procedural_stage",
    "number_of_parties",
    "class_or_collective_indicator",
}


DatasetLabel = (
    IntakeStageDocumentLabel | ConflictSeedLabel | BudgetDriverLabel | PersonTimelineEventLabel
)


def _check(
    check_id: str,
    passed: bool,
    message: str,
    details: dict[str, Any] | None = None,
) -> CourtListenerFixtureAuditCheck:
    return CourtListenerFixtureAuditCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        details=details or {},
    )


def _resolve_ref(base: Path, ref: str) -> Path:
    path = Path(ref)
    if path.is_absolute():
        return path
    return base / path


def _load_snapshots(
    *,
    repo_root: Path,
    manifest: CourtListenerDatasetManifest,
) -> list[CourtListenerDocketSnapshot]:
    snapshots: list[CourtListenerDocketSnapshot] = []
    for snapshot_ref in manifest.fixture_snapshot_refs:
        snapshots.append(
            CourtListenerDocketSnapshot.model_validate(
                load_json(_resolve_ref(repo_root, snapshot_ref))
            )
        )
    return snapshots


def _labels(manifest: CourtListenerDatasetManifest) -> list[DatasetLabel]:
    return [
        *manifest.intake_stage_document_labels,
        *manifest.conflict_seed_labels,
        *manifest.budget_driver_labels,
        *manifest.person_timeline_event_labels,
    ]


def _label_source_ref(label: DatasetLabel) -> CourtListenerLabelSourceRef:
    return label.source_ref


def _snapshot_segment_index(
    snapshots: list[CourtListenerDocketSnapshot],
) -> dict[tuple[str, str], tuple[CourtListenerDocketSnapshot, Any]]:
    index: dict[tuple[str, str], tuple[CourtListenerDocketSnapshot, Any]] = {}
    for snapshot in snapshots:
        for document in snapshot.documents:
            for segment in document.segments:
                index[(document.source_document_id, segment.segment_id)] = (snapshot, segment)
    return index


def _snapshot_document_index(
    snapshots: list[CourtListenerDocketSnapshot],
) -> dict[str, Any]:
    return {
        document.source_document_id: document
        for snapshot in snapshots
        for document in snapshot.documents
    }


def _side_effect_check(
    manifest: CourtListenerDatasetManifest,
    snapshots: list[CourtListenerDocketSnapshot],
) -> CourtListenerFixtureAuditCheck:
    unsafe_manifest_flags = [
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
    manifest_unsafe = [
        flag for flag in unsafe_manifest_flags if getattr(manifest, flag) is not False
    ]
    snapshot_unsafe: list[str] = []
    for snapshot in snapshots:
        for flag in [
            "public_records_ingested",
            "live_calls_performed",
            "pacer_purchase_performed",
            "recap_fetch_purchase_performed",
            "uploads_performed",
            "court_writes_performed",
            "external_writes_performed",
        ]:
            if getattr(snapshot, flag) is not False:
                snapshot_unsafe.append(f"{snapshot.snapshot_id}:{flag}")
    return _check(
        "offline_fixture_has_no_live_or_external_side_effects",
        not manifest_unsafe and not snapshot_unsafe,
        "Manifest and snapshots record no live calls, public ingestion, purchases, uploads, court writes, training pipeline, budget accuracy claim, or external writes.",
        {
            "manifest_unsafe_flags": manifest_unsafe,
            "snapshot_unsafe_flags": snapshot_unsafe,
        },
    )


def _snapshot_scope_check(
    snapshots: list[CourtListenerDocketSnapshot],
) -> CourtListenerFixtureAuditCheck:
    scope_issues: list[str] = []
    for snapshot in snapshots:
        if snapshot.source_access_mode != "offline_fixture":
            scope_issues.append(f"{snapshot.snapshot_id}:source_access_mode")
        if snapshot.public_data_sensitivity_level != "synthetic_no_real_public_identity":
            scope_issues.append(f"{snapshot.snapshot_id}:public_data_sensitivity_level")
        if snapshot.real_person_data_present is not False:
            scope_issues.append(f"{snapshot.snapshot_id}:real_person_data_present")
        if snapshot.fixture_redaction_status != "synthetic_no_real_identity":
            scope_issues.append(f"{snapshot.snapshot_id}:fixture_redaction_status")
        if not (90 <= snapshot.first_docket_day_count <= 120):
            scope_issues.append(f"{snapshot.snapshot_id}:first_docket_day_count")
    return _check(
        "snapshot_scope_is_offline_synthetic_and_early_case",
        not scope_issues,
        "Snapshots are offline synthetic/public-derived fixtures with no real public identity and a first 90-120 day corpus window.",
        {"scope_issues": scope_issues},
    )


def _source_ref_check(
    manifest: CourtListenerDatasetManifest,
    snapshots: list[CourtListenerDocketSnapshot],
) -> CourtListenerFixtureAuditCheck:
    index = _snapshot_segment_index(snapshots)
    issues: list[dict[str, Any]] = []
    for label in _labels(manifest):
        ref = _label_source_ref(label)
        indexed = index.get((ref.source_document_id, ref.source_segment_id))
        if indexed is None:
            issues.append({"label_id": label.label_id, "issue": "missing_segment"})
            continue
        snapshot, segment = indexed
        expected_hash = digest_text(segment.text)
        if ref.docket_id != snapshot.federal_docket_id:
            issues.append({"label_id": label.label_id, "issue": "docket_id_mismatch"})
        if ref.start_offset != segment.start_offset or ref.end_offset != segment.end_offset:
            issues.append({"label_id": label.label_id, "issue": "offset_mismatch"})
        if ref.sha256 != segment.sha256 or segment.sha256 != expected_hash:
            issues.append(
                {
                    "label_id": label.label_id,
                    "issue": "hash_mismatch",
                    "expected_sha256": expected_hash,
                    "ref_sha256": ref.sha256,
                    "segment_sha256": segment.sha256,
                }
            )
    return _check(
        "all_labels_have_resolving_source_refs_and_hashes",
        not issues,
        "Every document, conflict, budget-driver, and timeline label resolves to a snapshot segment with exact offsets and hashes.",
        {"issues": issues},
    )


def _early_case_label_check(
    manifest: CourtListenerDatasetManifest,
    snapshots: list[CourtListenerDocketSnapshot],
) -> CourtListenerFixtureAuditCheck:
    documents = _snapshot_document_index(snapshots)
    issues: list[dict[str, str]] = []
    for label in manifest.intake_stage_document_labels:
        document = documents.get(label.source_ref.source_document_id)
        if document is None:
            continue
        if document.case_stage in POSITIVE_CASE_STAGES:
            if document.filed_day > 120:
                issues.append({"label_id": label.label_id, "issue": "positive_stage_after_day_120"})
            if (
                label.label_type == "document_type"
                and label.value in PROHIBITED_POSITIVE_DOCUMENT_TYPES
            ):
                issues.append(
                    {
                        "label_id": label.label_id,
                        "issue": "prohibited_document_type_in_positive_corpus",
                    }
                )
    return _check(
        "positive_document_labels_stay_early_case",
        not issues,
        "Positive intake-stage document labels stay in the first 120 days and exclude post-discovery/trial/appellate document types.",
        {"issues": issues},
    )


def _required_label_family_check(
    manifest: CourtListenerDatasetManifest,
) -> CourtListenerFixtureAuditCheck:
    conflict_roles = {label.observed_role for label in manifest.conflict_seed_labels} | {
        label.inferred_role
        for label in manifest.conflict_seed_labels
        if label.inferred_role is not None
    }
    budget_drivers = {label.driver_id for label in manifest.budget_driver_labels}
    missing_conflict_roles = sorted(REQUIRED_CONFLICT_ROLES - conflict_roles)
    missing_budget_drivers = sorted(REQUIRED_BUDGET_DRIVERS - budget_drivers)
    has_document_types = any(
        label.label_type == "document_type" for label in manifest.intake_stage_document_labels
    )
    has_case_stage_labels = any(
        label.label_type == "case_stage" for label in manifest.intake_stage_document_labels
    )
    passed = (
        has_document_types
        and has_case_stage_labels
        and not missing_conflict_roles
        and not missing_budget_drivers
        and bool(manifest.person_timeline_event_labels)
    )
    return _check(
        "required_label_families_present",
        passed,
        "Manifest includes document type/stage, conflict seed, budget driver, and person timeline labels needed for the starter dataset.",
        {
            "has_document_type_labels": has_document_types,
            "has_case_stage_labels": has_case_stage_labels,
            "missing_conflict_roles": missing_conflict_roles,
            "missing_budget_drivers": missing_budget_drivers,
            "timeline_event_label_count": len(manifest.person_timeline_event_labels),
        },
    )


def _no_conclusion_or_training_check(
    manifest: CourtListenerDatasetManifest,
) -> CourtListenerFixtureAuditCheck:
    issues: list[str] = []
    for label in manifest.conflict_seed_labels:
        if label.conflict_conclusion_emitted or label.matter_opening_authorized:
            issues.append(f"{label.label_id}:conflict_or_matter_authority")
    for label in manifest.budget_driver_labels:
        if label.budget_amount_inferred or label.rate_inferred or label.guideline_inferred:
            issues.append(f"{label.label_id}:budget_amount_rate_or_guideline_inferred")
    for label in manifest.person_timeline_event_labels:
        if label.legal_or_factual_impossibility_claimed:
            issues.append(f"{label.label_id}:impossibility_claimed")
    if manifest.synthetic_intake_wrapper.observed_facts_manufactured:
        issues.append("synthetic_wrapper:observed_facts_manufactured")
    return _check(
        "labels_do_not_emit_legal_budget_or_training_authority",
        not issues
        and manifest.training_pipeline_created is False
        and manifest.budget_accuracy_claimed is False,
        "Labels remain candidates and do not clear conflicts, open matters, infer rates/guidelines/budget amounts, claim impossibility, create training, or claim budget accuracy.",
        {"issues": issues},
    )


def build_courtlistener_fixture_audit_report(
    *,
    repo_root: str | Path,
    manifest_path: str | Path,
) -> CourtListenerFixtureAuditReport:
    root = Path(repo_root)
    manifest_ref = str(manifest_path)
    manifest_file = _resolve_ref(root, manifest_ref)
    manifest = CourtListenerDatasetManifest.model_validate(load_json(manifest_file))
    snapshots = _load_snapshots(repo_root=root, manifest=manifest)
    checks = [
        _side_effect_check(manifest, snapshots),
        _snapshot_scope_check(snapshots),
        _source_ref_check(manifest, snapshots),
        _early_case_label_check(manifest, snapshots),
        _required_label_family_check(manifest),
        _no_conclusion_or_training_check(manifest),
    ]
    status = (
        "blocked_courtlistener_fixture"
        if any(check.status == "failed" for check in checks)
        else "courtlistener_fixture_ready_for_review"
    )
    return CourtListenerFixtureAuditReport(
        courtlistener_fixture_audit_report_id=new_id("courtlistenerfixture"),
        status=status,
        manifest_ref=manifest_ref,
        manifest_id=manifest.manifest_id,
        snapshot_refs=manifest.fixture_snapshot_refs,
        snapshot_count=len(snapshots),
        document_label_count=len(manifest.intake_stage_document_labels),
        conflict_seed_label_count=len(manifest.conflict_seed_labels),
        budget_driver_label_count=len(manifest.budget_driver_labels),
        timeline_event_label_count=len(manifest.person_timeline_event_labels),
        checks=checks,
        generated_at=now_iso(),
    )


def render_courtlistener_fixture_audit_report(
    report: CourtListenerFixtureAuditReport,
) -> str:
    lines = [
        "# CourtListener Fixture Audit Report",
        "",
        f"**Report ID:** {report.courtlistener_fixture_audit_report_id}",
        f"**Status:** {report.status}",
        f"**Manifest:** `{report.manifest_ref}`",
        f"**Snapshot count:** {report.snapshot_count}",
        "",
        "## Counts",
        "",
        f"- Document labels: {report.document_label_count}",
        f"- Conflict seed labels: {report.conflict_seed_label_count}",
        f"- Budget driver labels: {report.budget_driver_label_count}",
        f"- Timeline event labels: {report.timeline_event_label_count}",
        "",
        "## Boundary",
        "",
        f"- Public records ingested: {report.public_records_ingested}",
        f"- Live calls performed: {report.live_calls_performed}",
        f"- PACER purchase performed: {report.pacer_purchase_performed}",
        f"- RECAP Fetch purchase performed: {report.recap_fetch_purchase_performed}",
        f"- Training pipeline created: {report.training_pipeline_created}",
        f"- Budget accuracy claimed: {report.budget_accuracy_claimed}",
        f"- External writes performed: {report.external_writes_performed}",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.extend([f"- `{check.check_id}`: {check.status}", f"  {check.message}"])
        non_empty_details = {
            key: value for key, value in check.details.items() if value not in (None, "", [], {})
        }
        for key, value in non_empty_details.items():
            lines.append(f"  - {key}: {value}")
    lines.extend(
        [
            "",
            "This report validates a synthetic/offline fixture shape only. It does not "
            "authorize public-record ingestion, live API calls, scraping, purchases, uploads, "
            "training, conflict clearance, matter opening, budget approval, or learning promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def run_courtlistener_fixture_audit(
    *,
    repo_root: str | Path,
    manifest_path: str | Path,
    out_dir: str | Path,
) -> tuple[CourtListenerFixtureAuditReport, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report = build_courtlistener_fixture_audit_report(
        repo_root=repo_root,
        manifest_path=manifest_path,
    )
    report_path = run_dir / COURTLISTENER_FIXTURE_AUDIT_REPORT_FILENAME
    notes_path = run_dir / COURTLISTENER_FIXTURE_AUDIT_NOTES_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_courtlistener_fixture_audit_report(report), encoding="utf-8")
    return report, run_dir
