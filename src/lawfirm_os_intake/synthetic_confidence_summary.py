from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from .models import SyntheticConfidenceSummaryItem, SyntheticConfidenceSummaryReport
from .util import digest_json, load_json, now_iso, write_json


SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME = "synthetic_confidence_summary_report.json"
SYNTHETIC_CONFIDENCE_SUMMARY_NOTES_FILENAME = "synthetic_confidence_summary_report.md"


def run_synthetic_confidence_summary(
    *,
    synthetic_qa_review_run_report_path: str | Path,
    synthetic_qa_bundle_report_path: str | Path,
    ui_manifest_path: str | Path,
    ui_review_data_bundle_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[SyntheticConfidenceSummaryReport, Path]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    review_run_ref = Path(synthetic_qa_review_run_report_path)
    bundle_ref = Path(synthetic_qa_bundle_report_path)
    manifest_ref = Path(ui_manifest_path)
    ui_bundle_ref = Path(ui_review_data_bundle_path)

    review_run = _load_object(review_run_ref)
    bundle = _load_object(bundle_ref)
    manifest = _load_object(manifest_ref)
    ui_bundle = _load_object(ui_bundle_ref)

    steps = _list(review_run.get("steps"))
    artifacts = _list(bundle.get("artifacts"))
    detail_reports = _list(ui_bundle.get("detail_reports"))
    quality_gates = _list(manifest.get("qualityGates"))

    qa_failed_step_count = _count_status(steps, "failed")
    qa_missing_required_artifact_count = int(bundle.get("missing_required_artifact_count") or 0)
    qa_blocked_artifact_count = int(bundle.get("blocked_artifact_count") or 0)
    qa_failed_artifact_count = int(bundle.get("failed_artifact_count") or 0)
    raw_ui_missing_required_detail_report_count = int(
        ui_bundle.get("missing_required_detail_report_count") or 0
    )
    ui_self_missing_required_detail_report_count = _self_missing_required_detail_count(
        detail_reports
    )
    ui_missing_required_detail_report_count = max(
        raw_ui_missing_required_detail_report_count - ui_self_missing_required_detail_report_count,
        0,
    )
    ui_external_write_report_count = int(ui_bundle.get("external_write_report_count") or 0)
    quality_gate_counts = _quality_gate_counts(quality_gates)

    readiness_items = _readiness_items(
        review_run_ref=review_run_ref,
        bundle_ref=bundle_ref,
        manifest_ref=manifest_ref,
        ui_bundle_ref=ui_bundle_ref,
        review_run=review_run,
        bundle=bundle,
        ui_bundle=ui_bundle,
        detail_reports=detail_reports,
        quality_gate_counts=quality_gate_counts,
    )
    top_blockers = _top_blockers(
        qa_failed_step_count=qa_failed_step_count,
        qa_missing_required_artifact_count=qa_missing_required_artifact_count,
        qa_blocked_artifact_count=qa_blocked_artifact_count,
        qa_failed_artifact_count=qa_failed_artifact_count,
        ui_missing_required_detail_report_count=ui_missing_required_detail_report_count,
        ui_external_write_report_count=ui_external_write_report_count,
        quality_gate_counts=quality_gate_counts,
        readiness_items=readiness_items,
    )
    status, readiness_state = _status_and_state(
        top_blockers=top_blockers,
        ui_external_write_report_count=ui_external_write_report_count,
    )
    display_banner = {
        "candidate_only": True,
        "synthetic_only": True,
        "local_json_only": True,
        "not_production_ready": True,
        "human_review_required": True,
        "testing_readiness_state": readiness_state,
        "budget_submission_authorized": False,
        "matter_opening_authorized": False,
        "lake_write_performed": False,
        "sqlite_write_performed": False,
        "external_writes_performed": False,
        "summary": _banner_summary(status=status, readiness_state=readiness_state),
    }
    report_core = {
        "status": status,
        "testing_readiness_state": readiness_state,
        "source_synthetic_qa_review_run_report_id": review_run.get(
            "synthetic_qa_review_run_report_id"
        ),
        "source_synthetic_qa_bundle_report_id": bundle.get("synthetic_qa_bundle_report_id"),
        "source_ui_manifest_id": manifest.get("manifestId"),
        "source_ui_review_data_bundle_id": ui_bundle.get("ui_review_data_bundle_id"),
        "top_blockers": top_blockers,
        "readiness_items": [
            {
                "item_id": item.item_id,
                "state": item.state,
                "evidence_refs": item.evidence_refs,
            }
            for item in readiness_items
        ],
    }
    report = SyntheticConfidenceSummaryReport(
        synthetic_confidence_summary_report_id="synthetic_confidence_summary_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=status,
        testing_readiness_state=readiness_state,
        source_synthetic_qa_review_run_ref=str(review_run_ref),
        source_synthetic_qa_review_run_report_id=str(
            review_run.get("synthetic_qa_review_run_report_id") or "missing"
        ),
        source_synthetic_qa_review_run_status=str(review_run.get("status") or "missing"),
        source_synthetic_qa_bundle_ref=str(bundle_ref),
        source_synthetic_qa_bundle_report_id=str(
            bundle.get("synthetic_qa_bundle_report_id") or "missing"
        ),
        source_synthetic_qa_bundle_status=str(bundle.get("status") or "missing"),
        source_ui_manifest_ref=str(manifest_ref),
        source_ui_manifest_id=str(manifest.get("manifestId") or "missing"),
        source_ui_manifest_overall_status=str(manifest.get("overallStatus") or "missing"),
        source_ui_review_data_bundle_ref=str(ui_bundle_ref),
        source_ui_review_data_bundle_id=str(ui_bundle.get("ui_review_data_bundle_id") or "missing"),
        source_ui_review_data_bundle_status=str(ui_bundle.get("status") or "missing"),
        qa_step_count=len(steps),
        qa_passed_step_count=_count_status(steps, "passed"),
        qa_failed_step_count=qa_failed_step_count,
        qa_artifact_count=int(bundle.get("artifact_count") or len(artifacts)),
        qa_missing_required_artifact_count=qa_missing_required_artifact_count,
        qa_blocked_artifact_count=qa_blocked_artifact_count,
        qa_pending_artifact_count=int(bundle.get("pending_artifact_count") or 0),
        qa_failed_artifact_count=qa_failed_artifact_count,
        ui_detail_report_count=int(ui_bundle.get("detail_report_count") or len(detail_reports)),
        ui_present_detail_report_count=int(ui_bundle.get("present_detail_report_count") or 0),
        ui_missing_required_detail_report_count=ui_missing_required_detail_report_count,
        ui_external_write_report_count=ui_external_write_report_count,
        quality_gate_count=len(quality_gates),
        quality_gate_passed_count=quality_gate_counts["passed"],
        quality_gate_pending_count=quality_gate_counts["pending"],
        quality_gate_blocked_count=quality_gate_counts["blocked"],
        quality_gate_failed_count=quality_gate_counts["failed"],
        readiness_item_count=len(readiness_items),
        readiness_items=readiness_items,
        top_blockers=top_blockers,
        display_banner=display_banner,
        required_next_actions=_required_next_actions(
            status=status,
            readiness_state=readiness_state,
            top_blockers=top_blockers,
        ),
        generated_at=generated_at or now_iso(),
    )
    write_json(
        output_dir / SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME, report.model_dump(mode="json")
    )
    (output_dir / SYNTHETIC_CONFIDENCE_SUMMARY_NOTES_FILENAME).write_text(
        render_synthetic_confidence_summary(report),
        encoding="utf-8",
        newline="\n",
    )
    return report, output_dir


def render_synthetic_confidence_summary(report: SyntheticConfidenceSummaryReport) -> str:
    lines = [
        "# Synthetic Confidence Summary",
        "",
        f"**Report ID:** {report.synthetic_confidence_summary_report_id}",
        f"**Status:** {report.status}",
        f"**Testing readiness:** {report.testing_readiness_state}",
        "",
        "## Display Banner",
        "",
        f"- Summary: {report.display_banner['summary']}",
        f"- Candidate only: {report.display_banner['candidate_only']}",
        f"- Synthetic only: {report.display_banner['synthetic_only']}",
        f"- Production ready: {not report.display_banner['not_production_ready']}",
        f"- Budget submission authorized: {report.display_banner['budget_submission_authorized']}",
        "",
        "## Evidence Counts",
        "",
        f"- QA steps: {report.qa_passed_step_count}/{report.qa_step_count} passed",
        f"- QA artifacts: {report.qa_artifact_count}",
        f"- Pending QA artifacts: {report.qa_pending_artifact_count}",
        f"- UI details: {report.ui_present_detail_report_count}/{report.ui_detail_report_count} present",
        f"- Quality gates blocked/failed: {report.quality_gate_blocked_count}/{report.quality_gate_failed_count}",
        "",
        "## Readiness Items",
        "",
    ]
    for item in report.readiness_items:
        lines.extend(
            [
                f"### {item.label}",
                "",
                f"- State: {item.state}",
                f"- Owner: {item.owner}",
                f"- Evidence: {', '.join(item.evidence_refs)}",
                f"- Notes: {' '.join(item.notes)}",
                "",
            ]
        )
    lines.extend(["## Top Blockers", ""])
    if report.top_blockers:
        lines.extend(f"- {blocker}" for blocker in report.top_blockers)
    else:
        lines.append("- None for synthetic QA review; pending review still required.")
    lines.extend(
        [
            "",
            "This report is candidate-only local QA evidence. It is not a production "
            "readiness claim, does not authorize budget amounts, and does not write "
            "Lake/SQLite records or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def _readiness_items(
    *,
    review_run_ref: Path,
    bundle_ref: Path,
    manifest_ref: Path,
    ui_bundle_ref: Path,
    review_run: dict[str, Any],
    bundle: dict[str, Any],
    ui_bundle: dict[str, Any],
    detail_reports: list[dict[str, Any]],
    quality_gate_counts: Counter[str],
) -> list[SyntheticConfidenceSummaryItem]:
    return [
        SyntheticConfidenceSummaryItem(
            item_id="synthetic_qa_recipe",
            label="Synthetic QA Recipe",
            owner="qa-reference",
            state=(
                "ready_for_review"
                if review_run.get("status") == "synthetic_qa_review_run_ready"
                else "blocked"
            ),
            evidence_refs=[str(review_run_ref)],
            notes=[
                f"{review_run.get('failed_step_count', 0)} failed steps out of "
                f"{review_run.get('step_count', 0)}."
            ],
        ),
        SyntheticConfidenceSummaryItem(
            item_id="required_qa_artifacts",
            label="Required QA Artifacts",
            owner="qa-reference",
            state=_artifact_item_state(bundle),
            evidence_refs=[str(bundle_ref)],
            notes=[
                f"{bundle.get('missing_required_artifact_count', 0)} missing required, "
                f"{bundle.get('blocked_artifact_count', 0)} blocked, "
                f"{bundle.get('pending_artifact_count', 0)} pending review."
            ],
        ),
        SyntheticConfidenceSummaryItem(
            item_id="ui_review_surface",
            label="Read-Only UI Review Surface",
            owner="frontend-review",
            state=_ui_surface_state(ui_bundle=ui_bundle, detail_reports=detail_reports),
            evidence_refs=[str(ui_bundle_ref), str(manifest_ref)],
            notes=[
                f"{ui_bundle.get('present_detail_report_count', 0)} detail reports present; "
                f"{ui_bundle.get('external_write_report_count', 0)} write-boundary failures."
            ],
        ),
        SyntheticConfidenceSummaryItem(
            item_id="authority_boundaries",
            label="Authority Boundaries",
            owner="governance-review",
            state=(
                "failed"
                if _any_side_effect_boundary_failure(review_run, bundle, ui_bundle)
                else "ready_for_review"
            ),
            evidence_refs=[str(review_run_ref), str(bundle_ref), str(ui_bundle_ref)],
            notes=[
                "No budget submission, matter opening, Lake/SQLite write, external write, "
                "or silent learning is authorized by these artifacts."
            ],
        ),
        SyntheticConfidenceSummaryItem(
            item_id="owner_review_backlog",
            label="Owner Review Backlog",
            owner="human-or-owner-review",
            state=(
                "blocked"
                if quality_gate_counts["blocked"] or quality_gate_counts["failed"]
                else "pending_review"
            ),
            evidence_refs=[str(manifest_ref)],
            notes=[
                f"{quality_gate_counts['pending']} pending gates remain; pending is expected "
                "until human/owner review accepts candidate QA evidence."
            ],
        ),
    ]


def _artifact_item_state(bundle: dict[str, Any]) -> str:
    if bundle.get("failed_artifact_count") or bundle.get("missing_required_artifact_count"):
        return "blocked"
    if bundle.get("blocked_artifact_count"):
        return "blocked"
    if bundle.get("pending_artifact_count"):
        return "pending_review"
    return "ready_for_review"


def _ui_surface_state(
    *,
    ui_bundle: dict[str, Any],
    detail_reports: list[dict[str, Any]],
) -> str:
    if ui_bundle.get("status") == "ready_for_review":
        return "ready_for_review"
    missing_required = int(ui_bundle.get("missing_required_detail_report_count") or 0)
    if missing_required and missing_required == _self_missing_required_detail_count(detail_reports):
        return "ready_for_review"
    return "blocked"


def _self_missing_required_detail_count(detail_reports: list[dict[str, Any]]) -> int:
    return sum(
        1
        for report in detail_reports
        if report.get("required") is True
        and report.get("present") is False
        and report.get("file_name") == SYNTHETIC_CONFIDENCE_SUMMARY_REPORT_FILENAME
    )


def _status_and_state(
    *,
    top_blockers: list[str],
    ui_external_write_report_count: int,
) -> tuple[str, str]:
    if ui_external_write_report_count:
        return (
            "failed_synthetic_confidence_summary_boundary",
            "failed_side_effect_boundary",
        )
    if top_blockers:
        return (
            "blocked_by_synthetic_confidence_summary",
            "blocked_missing_or_failed_evidence",
        )
    return (
        "synthetic_confidence_summary_ready_for_review",
        "synthetic_qa_ready_pending_review",
    )


def _top_blockers(
    *,
    qa_failed_step_count: int,
    qa_missing_required_artifact_count: int,
    qa_blocked_artifact_count: int,
    qa_failed_artifact_count: int,
    ui_missing_required_detail_report_count: int,
    ui_external_write_report_count: int,
    quality_gate_counts: Counter[str],
    readiness_items: list[SyntheticConfidenceSummaryItem],
) -> list[str]:
    blockers: list[str] = []
    if qa_failed_step_count:
        blockers.append(f"{qa_failed_step_count} synthetic QA recipe steps failed")
    if qa_missing_required_artifact_count:
        blockers.append(f"{qa_missing_required_artifact_count} required QA artifacts missing")
    if qa_blocked_artifact_count:
        blockers.append(f"{qa_blocked_artifact_count} QA artifacts blocked")
    if qa_failed_artifact_count:
        blockers.append(f"{qa_failed_artifact_count} QA artifacts failed")
    if ui_missing_required_detail_report_count:
        blockers.append(
            f"{ui_missing_required_detail_report_count} required UI detail reports missing"
        )
    if ui_external_write_report_count:
        blockers.append(
            f"{ui_external_write_report_count} UI detail reports show write side effects"
        )
    if quality_gate_counts["blocked"]:
        blockers.append(f"{quality_gate_counts['blocked']} UI quality gates blocked")
    if quality_gate_counts["failed"]:
        blockers.append(f"{quality_gate_counts['failed']} UI quality gates failed")
    blockers.extend(
        f"{item.label} is {item.state}"
        for item in readiness_items
        if item.state in {"blocked", "failed"}
    )
    return _dedupe(blockers)


def _required_next_actions(
    *,
    status: str,
    readiness_state: str,
    top_blockers: list[str],
) -> list[str]:
    if status == "failed_synthetic_confidence_summary_boundary":
        return [
            "Repair side-effect boundary failure before using the UI review surface.",
            "Do not route artifacts to Exception Lake, calibration, matter opening, or budget submission.",
        ]
    if status == "blocked_by_synthetic_confidence_summary":
        return [f"Resolve blocker: {blocker}" for blocker in top_blockers]
    return [
        "Start manual synthetic QA review from the read-only UI.",
        "Treat this as candidate-only synthetic readiness, not production readiness.",
        "Expand reviewed gold and fixture families before calibration or real-data pilot work.",
    ]


def _banner_summary(*, status: str, readiness_state: str) -> str:
    if status == "synthetic_confidence_summary_ready_for_review":
        return (
            "Synthetic QA cockpit is ready for review; outputs remain candidate-only, "
            "non-authoritative, and blocked from submission."
        )
    if readiness_state == "failed_side_effect_boundary":
        return "Synthetic QA cockpit is blocked by a side-effect boundary failure."
    return "Synthetic QA cockpit is blocked by missing or failed evidence."


def _quality_gate_counts(gates: list[dict[str, Any]]) -> Counter[str]:
    counts: Counter[str] = Counter({"passed": 0, "pending": 0, "blocked": 0, "failed": 0})
    for gate in gates:
        status = str(gate.get("status") or "pending_review")
        if status == "passed":
            counts["passed"] += 1
        elif status == "failed":
            counts["failed"] += 1
        elif status == "blocked":
            counts["blocked"] += 1
        else:
            counts["pending"] += 1
    return counts


def _any_side_effect_boundary_failure(*payloads: dict[str, Any]) -> bool:
    keys = [
        "external_writes_performed",
        "lake_write_performed",
        "sqlite_write_performed",
        "silent_learning_performed",
        "budget_submission_performed",
        "matter_opening_performed",
        "budget_submission_authorized",
        "matter_opening_authorized",
        "training_pipeline_created",
    ]
    return any(payload.get(key) is True for payload in payloads for key in keys)


def _count_status(rows: list[dict[str, Any]], status: str) -> int:
    return sum(1 for row in rows if row.get("status") == status)


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    if not isinstance(payload, dict):
        raise ValueError(f"expected JSON object: {path}")
    return payload


def _list(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _dedupe(values: list[str]) -> list[str]:
    seen: set[str] = set()
    deduped: list[str] = []
    for value in values:
        if value in seen:
            continue
        seen.add(value)
        deduped.append(value)
    return deduped
