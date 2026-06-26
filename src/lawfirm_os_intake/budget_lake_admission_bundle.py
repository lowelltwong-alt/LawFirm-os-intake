from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .budget_actual_variance_ledger import BUDGET_ACTUAL_VARIANCE_LEDGER_FILENAME
from .budget_change_ledger import BUDGET_CHANGE_LEDGER_FILENAME
from .carrier_rejection_decision_ledger import CARRIER_REJECTION_DECISION_LEDGER_FILENAME
from .models import (
    BudgetActualVarianceLedgerReport,
    BudgetChangeLedgerReport,
    BudgetLakeAdmissionBundleCheck,
    BudgetLakeAdmissionBundleReport,
    BudgetLakeCandidateRecordFamily,
    BudgetLakeEvidenceArtifact,
    CarrierRejectionDecisionLedgerReport,
)
from .util import digest_text, load_json, load_jsonl, now_iso, write_json


BUDGET_EVENT_LAKE_BUNDLE_REPORT_FILENAME = "budget_event_lake_admission_bundle_report.json"
BUDGET_EVENT_LAKE_BUNDLE_NOTES_FILENAME = "budget_event_lake_admission_bundle.md"

BUDGET_EVENT_LAKE_BUNDLE_REQUIRED_NEXT_GATES = [
    "human_budget_event_lake_bundle_review",
    "orchestrator_evidence_packet_assembly",
    "exception_lake_runtime_admission_validation",
    "exception_lake_record_hash_assignment",
    "exception_lake_append_only_storage",
    "semantic_substrate_event_class_promotion_if_needed",
    "no_intake_sqlite_lake_or_learning_write",
]

PROHIBITED_FALSE_FLAGS = {
    "lake_write_performed",
    "sqlite_write_performed",
    "external_writes_performed",
    "billing_connector_read_performed",
    "billing_connector_write_performed",
    "carrier_portal_write_performed",
    "email_send_performed",
    "appeal_submission_performed",
    "budget_submission_authorized",
    "carrier_submission_authorized",
    "budget_mutation_performed",
    "profile_mutation_performed",
    "template_mutation_performed",
    "carrier_guideline_mutation_performed",
    "silent_learning_performed",
    "raw_payload_included",
}

REQUIRED_TRUE_FLAGS = {
    "candidate_only",
    "non_authoritative",
    "synthetic_only",
    "append_only",
}


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _sha256(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _check(
    check_id: str,
    passed: bool,
    message: str,
    artifact_refs: list[str] | None = None,
) -> BudgetLakeAdmissionBundleCheck:
    return BudgetLakeAdmissionBundleCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
    )


def _event_id_field(artifact_kind: str) -> str:
    if artifact_kind.startswith("budget_change"):
        return "budget_change_ledger_event_id"
    if artifact_kind.startswith("budget_actual"):
        return "budget_actual_variance_ledger_event_id"
    return "decision_ledger_event_id"


def _report_id(report: Any) -> str:
    if isinstance(report, BudgetChangeLedgerReport):
        return report.budget_change_ledger_report_id
    if isinstance(report, BudgetActualVarianceLedgerReport):
        return report.budget_actual_variance_ledger_report_id
    return report.decision_ledger_report_id


def _ledger_id(report: Any) -> str:
    if isinstance(report, BudgetChangeLedgerReport):
        return report.ledger_id
    if isinstance(report, BudgetActualVarianceLedgerReport):
        return report.ledger_id
    return report.decision_ledger_id


def _event_kind_counts(events: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        kind = str(event.get("event_kind", "unknown"))
        counts[kind] = counts.get(kind, 0) + 1
    return counts


def _local_labels(events: list[dict[str, Any]]) -> list[str]:
    labels = set()
    for event in events:
        if event.get("exception_lake_local_event_label"):
            labels.add(str(event["exception_lake_local_event_label"]))
        if event.get("local_event_label"):
            labels.add(str(event["local_event_label"]))
    return sorted(labels)


def _budget_change_families(events: list[dict[str, Any]]) -> list[BudgetLakeCandidateRecordFamily]:
    return ["budget_human_change_record"] if events else []


def _actual_variance_families(
    events: list[dict[str, Any]],
) -> list[BudgetLakeCandidateRecordFamily]:
    families: set[BudgetLakeCandidateRecordFamily] = set()
    for event in events:
        if event.get("decision_status") == "actuals_missing_pending_source":
            families.add("budget_actual_missing_source_record")
        else:
            families.add("budget_actual_variance_record")
    return sorted(families)


def _carrier_decision_families(
    events: list[dict[str, Any]],
) -> list[BudgetLakeCandidateRecordFamily]:
    families: set[BudgetLakeCandidateRecordFamily] = set()
    for event in events:
        kind = event.get("event_kind")
        if kind == "carrier_appeal_result_received":
            families.add("carrier_appeal_result_record")
        elif kind == "carrier_financial_outcome_recorded":
            families.add("carrier_financial_outcome_record")
        else:
            families.add("carrier_rejection_decision_record")
    return sorted(families)


def _families_for_kind(
    artifact_kind: str,
    events: list[dict[str, Any]],
) -> list[BudgetLakeCandidateRecordFamily]:
    if artifact_kind.startswith("budget_change"):
        return _budget_change_families(events)
    if artifact_kind.startswith("budget_actual"):
        return _actual_variance_families(events)
    return _carrier_decision_families(events)


def _event_dicts(report: Any) -> list[dict[str, Any]]:
    return [event.model_dump(mode="json") for event in report.events]


def _report_artifact(
    *,
    artifact_kind: str,
    path: Path,
    report: Any,
) -> BudgetLakeEvidenceArtifact:
    events = _event_dicts(report)
    return BudgetLakeEvidenceArtifact(
        artifact_id=_stable_id("budgetlakeartifact", f"{artifact_kind}|{path}|report"),
        artifact_kind=artifact_kind,  # type: ignore[arg-type]
        artifact_ref=str(path),
        sha256=_sha256(path),
        report_id=_report_id(report),
        ledger_id=_ledger_id(report),
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        event_count=report.entry_count,
        row_event_count=0,
        event_kind_counts=dict(report.event_kind_counts),
        local_event_labels=_local_labels(events),
        candidate_record_families=_families_for_kind(artifact_kind, events),
    )


def _jsonl_artifact(
    *,
    artifact_kind: str,
    path: Path,
    report: Any,
    rows: list[dict[str, Any]],
) -> BudgetLakeEvidenceArtifact:
    return BudgetLakeEvidenceArtifact(
        artifact_id=_stable_id("budgetlakeartifact", f"{artifact_kind}|{path}|jsonl"),
        artifact_kind=artifact_kind,  # type: ignore[arg-type]
        artifact_ref=str(path),
        sha256=_sha256(path),
        report_id=_report_id(report),
        ledger_id=_ledger_id(report),
        run_id=report.run_id,
        preflight_packet_id=report.preflight_packet_id,
        budget_proposal_id=report.budget_proposal_id,
        event_count=0,
        row_event_count=len(rows),
        event_kind_counts=_event_kind_counts(rows),
        local_event_labels=_local_labels(rows),
        candidate_record_families=_families_for_kind(artifact_kind, rows),
    )


def _flag_violations(payload: dict[str, Any]) -> list[str]:
    violations = []
    to_scan = [payload, *payload.get("events", [])]
    for item in to_scan:
        for field in PROHIBITED_FALSE_FLAGS:
            if field in item and item[field] is not False:
                violations.append(f"{field}={item[field]}")
        for field in REQUIRED_TRUE_FLAGS:
            if field in item and item[field] is not True:
                violations.append(f"{field}={item[field]}")
    return sorted(set(violations))


def _load_report(
    *,
    report_path: str | Path | None,
    model: type,
    missing_refs: list[str],
) -> tuple[Any | None, Path | None, dict[str, Any] | None]:
    if report_path is None:
        return None, None, None
    path = Path(report_path)
    if not path.exists():
        missing_refs.append(str(path))
        return None, path, None
    payload = load_json(path)
    return model.model_validate(payload), path, payload


def _default_jsonl_path(report_path: Path, filename: str) -> Path:
    return report_path.parent / filename


def _process_pair(
    *,
    report: Any | None,
    report_path: Path | None,
    report_payload: dict[str, Any] | None,
    report_kind: str,
    jsonl_kind: str,
    jsonl_path: str | Path | None,
    default_jsonl_filename: str,
    artifacts: list[BudgetLakeEvidenceArtifact],
    missing_refs: list[str],
    count_mismatches: list[str],
    id_mismatches: list[str],
    flag_violations: list[str],
) -> None:
    if report is None or report_path is None or report_payload is None:
        return
    artifacts.append(_report_artifact(artifact_kind=report_kind, path=report_path, report=report))
    flag_violations.extend(
        f"{report_path}:{violation}" for violation in _flag_violations(report_payload)
    )
    rows_path = (
        Path(jsonl_path)
        if jsonl_path is not None
        else _default_jsonl_path(
            report_path,
            default_jsonl_filename,
        )
    )
    if not rows_path.exists():
        missing_refs.append(str(rows_path))
        return
    rows = load_jsonl(rows_path)
    artifacts.append(
        _jsonl_artifact(
            artifact_kind=jsonl_kind,
            path=rows_path,
            report=report,
            rows=rows,
        )
    )
    if len(rows) != report.entry_count:
        count_mismatches.append(
            f"{rows_path}: rows={len(rows)} report_entry_count={report.entry_count}"
        )
    event_id_field = _event_id_field(report_kind)
    report_ids = {event.get(event_id_field) for event in _event_dicts(report)}
    row_ids = {row.get(event_id_field) for row in rows}
    if report_ids != row_ids:
        id_mismatches.append(str(rows_path))
    for row in rows:
        flag_violations.extend(
            f"{rows_path}:{violation}" for violation in _flag_violations({"events": [row]})
        )


def _status(
    *,
    missing_refs: list[str],
    failed_count: int,
) -> str:
    if missing_refs:
        return "blocked_missing_artifacts"
    if failed_count:
        return "blocked_inconsistent_evidence"
    return "ready_for_exception_lake_review"


def build_budget_event_lake_admission_bundle(
    *,
    budget_change_ledger_report_path: str | Path | None = None,
    budget_change_ledger_jsonl_path: str | Path | None = None,
    budget_actual_variance_ledger_report_path: str | Path | None = None,
    budget_actual_variance_ledger_jsonl_path: str | Path | None = None,
    carrier_rejection_decision_ledger_report_path: str | Path | None = None,
    carrier_rejection_decision_ledger_jsonl_path: str | Path | None = None,
) -> BudgetLakeAdmissionBundleReport:
    missing_refs: list[str] = []
    count_mismatches: list[str] = []
    id_mismatches: list[str] = []
    flag_violations: list[str] = []
    artifacts: list[BudgetLakeEvidenceArtifact] = []

    budget_change_report, budget_change_path, budget_change_payload = _load_report(
        report_path=budget_change_ledger_report_path,
        model=BudgetChangeLedgerReport,
        missing_refs=missing_refs,
    )
    actual_report, actual_path, actual_payload = _load_report(
        report_path=budget_actual_variance_ledger_report_path,
        model=BudgetActualVarianceLedgerReport,
        missing_refs=missing_refs,
    )
    carrier_report, carrier_path, carrier_payload = _load_report(
        report_path=carrier_rejection_decision_ledger_report_path,
        model=CarrierRejectionDecisionLedgerReport,
        missing_refs=missing_refs,
    )

    _process_pair(
        report=budget_change_report,
        report_path=budget_change_path,
        report_payload=budget_change_payload,
        report_kind="budget_change_ledger_report",
        jsonl_kind="budget_change_ledger_jsonl",
        jsonl_path=budget_change_ledger_jsonl_path,
        default_jsonl_filename=BUDGET_CHANGE_LEDGER_FILENAME,
        artifacts=artifacts,
        missing_refs=missing_refs,
        count_mismatches=count_mismatches,
        id_mismatches=id_mismatches,
        flag_violations=flag_violations,
    )
    _process_pair(
        report=actual_report,
        report_path=actual_path,
        report_payload=actual_payload,
        report_kind="budget_actual_variance_ledger_report",
        jsonl_kind="budget_actual_variance_ledger_jsonl",
        jsonl_path=budget_actual_variance_ledger_jsonl_path,
        default_jsonl_filename=BUDGET_ACTUAL_VARIANCE_LEDGER_FILENAME,
        artifacts=artifacts,
        missing_refs=missing_refs,
        count_mismatches=count_mismatches,
        id_mismatches=id_mismatches,
        flag_violations=flag_violations,
    )
    _process_pair(
        report=carrier_report,
        report_path=carrier_path,
        report_payload=carrier_payload,
        report_kind="carrier_rejection_decision_ledger_report",
        jsonl_kind="carrier_rejection_decision_ledger_jsonl",
        jsonl_path=carrier_rejection_decision_ledger_jsonl_path,
        default_jsonl_filename=CARRIER_REJECTION_DECISION_LEDGER_FILENAME,
        artifacts=artifacts,
        missing_refs=missing_refs,
        count_mismatches=count_mismatches,
        id_mismatches=id_mismatches,
        flag_violations=flag_violations,
    )

    budget_ids = sorted({item.budget_proposal_id for item in artifacts if item.budget_proposal_id})
    preflight_ids = sorted(
        {item.preflight_packet_id for item in artifacts if item.preflight_packet_id}
    )
    run_ids = sorted({item.run_id for item in artifacts if item.run_id})
    families = sorted(
        {family for artifact in artifacts for family in artifact.candidate_record_families}
    )
    labels = sorted({label for artifact in artifacts for label in artifact.local_event_labels})
    duplicate_refs = sorted(
        ref
        for ref in {artifact.artifact_ref for artifact in artifacts}
        if sum(1 for artifact in artifacts if artifact.artifact_ref == ref) > 1
    )
    no_artifacts = not artifacts
    inconsistent_budget_refs = len(budget_ids) > 1
    inconsistent_preflight_refs = len(preflight_ids) > 1
    missing_record_families = not families
    checks = [
        _check(
            "at_least_one_ledger_report_provided",
            not no_artifacts,
            "At least one local budget/rejection ledger report was provided.",
        ),
        _check(
            "artifact_files_exist",
            not missing_refs,
            "Every declared ledger report and JSONL artifact exists.",
            missing_refs,
        ),
        _check(
            "artifact_hashes_present",
            all(artifact.sha256.startswith("sha256:") for artifact in artifacts),
            "Every declared artifact has a sha256 hash.",
            [artifact.artifact_ref for artifact in artifacts if not artifact.sha256],
        ),
        _check(
            "jsonl_rows_match_report_events",
            not count_mismatches,
            "Each ledger JSONL row count matches its paired report entry count.",
            count_mismatches,
        ),
        _check(
            "jsonl_event_ids_match_reports",
            not id_mismatches,
            "Each ledger JSONL event ID set matches its paired report event ID set.",
            id_mismatches,
        ),
        _check(
            "budget_proposal_id_consistent",
            not inconsistent_budget_refs,
            "All provided ledgers refer to the same budget proposal.",
            budget_ids,
        ),
        _check(
            "preflight_packet_id_consistent",
            not inconsistent_preflight_refs,
            "All provided ledgers refer to the same preflight packet.",
            preflight_ids,
        ),
        _check(
            "candidate_record_families_present",
            not missing_record_families,
            "Ledger events map to candidate Lake record families for owner review.",
        ),
        _check(
            "no_duplicate_artifact_refs",
            not duplicate_refs,
            "The bundle does not declare the same artifact path more than once.",
            duplicate_refs,
        ),
        _check(
            "no_prohibited_writes_or_silent_learning",
            not flag_violations,
            "Ledger reports and rows preserve no-write, no-submission, and no-silent-learning boundaries.",
            flag_violations,
        ),
    ]
    failed_count = sum(1 for check in checks if check.status == "failed")
    return BudgetLakeAdmissionBundleReport(
        bundle_report_id=_stable_id(
            "budgetlakebundle",
            "|".join(sorted(artifact.sha256 for artifact in artifacts)) or "empty",
        ),
        status=_status(missing_refs=missing_refs, failed_count=failed_count),  # type: ignore[arg-type]
        artifact_count=len(artifacts),
        ledger_report_count=sum(
            1 for artifact in artifacts if artifact.artifact_kind.endswith("_report")
        ),
        jsonl_row_count=sum(artifact.row_event_count for artifact in artifacts),
        total_event_count=sum(artifact.event_count for artifact in artifacts),
        budget_proposal_ids=budget_ids,
        preflight_packet_ids=preflight_ids,
        run_ids=run_ids,
        candidate_record_families=families,
        local_event_labels=labels,
        artifacts=artifacts,
        checks=checks,
        required_next_gates=BUDGET_EVENT_LAKE_BUNDLE_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_event_lake_admission_bundle(
    report: BudgetLakeAdmissionBundleReport,
) -> str:
    lines = [
        "# Budget Event Lake Admission Bundle",
        "",
        f"**Bundle ID:** {report.bundle_report_id}",
        f"**Status:** {report.status}",
        f"**Target repo:** {report.target_repo}",
        f"**Admission state:** {report.admission_state}",
        "",
        "## Summary",
        "",
        f"- Artifact count: {report.artifact_count}",
        f"- Ledger report count: {report.ledger_report_count}",
        f"- JSONL row count: {report.jsonl_row_count}",
        f"- Total report event count: {report.total_event_count}",
        f"- Budget proposal IDs: {', '.join(report.budget_proposal_ids) or 'none'}",
        f"- Preflight packet IDs: {', '.join(report.preflight_packet_ids) or 'none'}",
        f"- Candidate record families: {', '.join(report.candidate_record_families) or 'none'}",
        f"- Local event labels: {', '.join(report.local_event_labels) or 'none'}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Artifacts",
        "",
    ]
    for artifact in report.artifacts:
        lines.extend(
            [
                f"- `{artifact.artifact_kind}`",
                f"  - ref: `{artifact.artifact_ref}`",
                f"  - sha256: `{artifact.sha256}`",
                f"  - report id: {artifact.report_id or 'none'}",
                f"  - ledger id: {artifact.ledger_id or 'none'}",
                f"  - events: {artifact.event_count}; rows: {artifact.row_event_count}",
                f"  - families: {', '.join(artifact.candidate_record_families) or 'none'}",
            ]
        )
    lines.extend(["", "## Checks", ""])
    for check in report.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
        if check.artifact_refs:
            lines.append(f"  - refs: {', '.join(check.artifact_refs)}")
    lines.extend(["", "## Required Next Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This bundle is candidate-only review evidence. It does not admit Exception Lake records, write SQLite, assign record hashes, create canonical event classes, submit appeals or budgets, read billing, write billing, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_event_lake_admission_bundle(
    *,
    out_dir: str | Path,
    budget_change_ledger_report_path: str | Path | None = None,
    budget_change_ledger_jsonl_path: str | Path | None = None,
    budget_actual_variance_ledger_report_path: str | Path | None = None,
    budget_actual_variance_ledger_jsonl_path: str | Path | None = None,
    carrier_rejection_decision_ledger_report_path: str | Path | None = None,
    carrier_rejection_decision_ledger_jsonl_path: str | Path | None = None,
) -> tuple[BudgetLakeAdmissionBundleReport, Path]:
    report = build_budget_event_lake_admission_bundle(
        budget_change_ledger_report_path=budget_change_ledger_report_path,
        budget_change_ledger_jsonl_path=budget_change_ledger_jsonl_path,
        budget_actual_variance_ledger_report_path=budget_actual_variance_ledger_report_path,
        budget_actual_variance_ledger_jsonl_path=budget_actual_variance_ledger_jsonl_path,
        carrier_rejection_decision_ledger_report_path=(
            carrier_rejection_decision_ledger_report_path
        ),
        carrier_rejection_decision_ledger_jsonl_path=(carrier_rejection_decision_ledger_jsonl_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / BUDGET_EVENT_LAKE_BUNDLE_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_EVENT_LAKE_BUNDLE_NOTES_FILENAME).write_text(
        render_budget_event_lake_admission_bundle(report),
        encoding="utf-8",
    )
    return report, run_dir
