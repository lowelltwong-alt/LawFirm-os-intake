from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .models import SyntheticQABlockerReport, SyntheticQABlockerRow
from .util import digest_json, load_json, now_iso, write_json


SYNTHETIC_QA_BLOCKER_REPORT_FILENAME = "synthetic_qa_blocker_report.json"


def run_synthetic_qa_blocker_report(
    *,
    ui_manifest_path: str | Path,
    synthetic_confidence_summary_path: str | Path,
    synthetic_qa_review_run_report_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[SyntheticQABlockerReport, Path]:
    output_dir = Path(out_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    manifest_ref = Path(ui_manifest_path)
    confidence_ref = Path(synthetic_confidence_summary_path)
    review_run_ref = Path(synthetic_qa_review_run_report_path)

    manifest = _load_object(manifest_ref)
    confidence = _load_object(confidence_ref)
    review_run = _load_object(review_run_ref)

    rows = _build_rows(
        manifest=manifest,
        confidence=confidence,
        review_run=review_run,
    )
    failed_count = sum(1 for row in rows if row.state == "failed")
    blocked_count = sum(1 for row in rows if row.state == "blocked")
    pending_count = sum(1 for row in rows if row.state == "pending_review")
    status = _status(
        failed_count=failed_count,
        blocked_count=blocked_count,
        confidence=confidence,
        review_run=review_run,
    )
    report_core = {
        "status": status,
        "source_ui_manifest_id": manifest.get("manifestId"),
        "source_synthetic_confidence_summary_report_id": confidence.get(
            "synthetic_confidence_summary_report_id"
        ),
        "source_synthetic_qa_review_run_report_id": review_run.get(
            "synthetic_qa_review_run_report_id"
        ),
        "rows": [row.model_dump(mode="json") for row in rows],
    }
    report = SyntheticQABlockerReport(
        synthetic_qa_blocker_report_id="synthetic_qa_blocker_report_"
        + digest_json(report_core)[len("sha256:") : len("sha256:") + 16],
        status=status,
        source_ui_manifest_ref=str(manifest_ref),
        source_ui_manifest_id=str(manifest.get("manifestId") or "missing"),
        source_ui_manifest_overall_status=str(manifest.get("overallStatus") or "missing"),
        source_synthetic_confidence_summary_ref=str(confidence_ref),
        source_synthetic_confidence_summary_report_id=str(
            confidence.get("synthetic_confidence_summary_report_id") or "missing"
        ),
        source_synthetic_confidence_summary_status=str(confidence.get("status") or "missing"),
        source_synthetic_qa_review_run_ref=str(review_run_ref),
        source_synthetic_qa_review_run_report_id=str(
            review_run.get("synthetic_qa_review_run_report_id") or "missing"
        ),
        source_synthetic_qa_review_run_status=str(review_run.get("status") or "missing"),
        row_count=len(rows),
        failed_row_count=failed_count,
        blocked_row_count=blocked_count,
        pending_review_row_count=pending_count,
        rows=rows,
        required_next_actions=_required_next_actions(
            status=status,
            rows=rows,
            confidence=confidence,
        ),
        generated_at=generated_at or now_iso(),
    )
    write_json(output_dir / SYNTHETIC_QA_BLOCKER_REPORT_FILENAME, report.model_dump(mode="json"))
    return report, output_dir


def _build_rows(
    *,
    manifest: dict[str, Any],
    confidence: dict[str, Any],
    review_run: dict[str, Any],
) -> list[SyntheticQABlockerRow]:
    rows: list[SyntheticQABlockerRow] = []
    for gate in _list(manifest.get("qualityGates")):
        gate_id = str(gate.get("gateId") or "missing_gate")
        status = str(gate.get("status") or "pending_review")
        if gate_id == "synthetic_qa_blocker_report" or status == "passed":
            continue
        rows.append(
            SyntheticQABlockerRow(
                row_id=f"quality_gate:{gate_id}",
                source="quality_gate",
                label=str(gate.get("label") or gate_id),
                state=_gate_state(status),
                owner=str(gate.get("owner") or "qa-reference"),
                evidence_refs=[str(gate.get("evidenceFile") or "missing evidence file")],
                notes=_notes(gate.get("notes")),
            )
        )

    for step in _list(review_run.get("steps")):
        step_id = str(step.get("step_id") or "missing_step")
        status = str(step.get("status") or "failed")
        if status == "passed":
            continue
        rows.append(
            SyntheticQABlockerRow(
                row_id=f"qa_step:{step_id}",
                source="qa_step",
                label=str(step.get("label") or step_id),
                state="failed",
                owner="synthetic_qa_review_run",
                evidence_refs=[str(step.get("artifact_ref") or "missing artifact ref")],
                notes=_dedupe(
                    [
                        str(step.get("observed_status") or "missing observed status"),
                        *_notes(step.get("notes")),
                    ]
                ),
            )
        )

    for item in _list(confidence.get("readiness_items")):
        item_id = str(item.get("item_id") or "missing_item")
        state = str(item.get("state") or "blocked")
        if state == "ready_for_review":
            continue
        rows.append(
            SyntheticQABlockerRow(
                row_id=f"readiness_item:{item_id}",
                source="readiness_item",
                label=str(item.get("label") or item_id),
                state=_readiness_state(state),
                owner=str(item.get("owner") or "qa-reference"),
                evidence_refs=_refs(item.get("evidence_refs")),
                notes=_notes(item.get("notes")),
            )
        )

    for index, blocker in enumerate(_text_list(confidence.get("top_blockers")), start=1):
        rows.append(
            SyntheticQABlockerRow(
                row_id=f"top_blocker:{index}",
                source="top_blocker",
                label=blocker,
                state="blocked",
                owner="synthetic_confidence_summary",
                evidence_refs=[
                    str(confidence.get("synthetic_confidence_summary_report_id") or "missing")
                ],
                notes=["Reported as a top blocker in the synthetic confidence summary."],
            )
        )

    return rows


def _status(
    *,
    failed_count: int,
    blocked_count: int,
    confidence: dict[str, Any],
    review_run: dict[str, Any],
) -> str:
    if _any_side_effect_boundary_failure(confidence, review_run):
        return "failed_synthetic_qa_blocker_boundary"
    if failed_count or blocked_count:
        return "blocked_by_synthetic_qa_blocker_report"
    return "synthetic_qa_blocker_report_ready_for_review"


def _required_next_actions(
    *,
    status: str,
    rows: list[SyntheticQABlockerRow],
    confidence: dict[str, Any],
) -> list[str]:
    if status == "failed_synthetic_qa_blocker_boundary":
        return [
            "Repair side-effect boundary failure before using this QA queue.",
            "Do not write to Exception Lake, SQLite, carrier portals, billing, or matter systems.",
        ]
    failed_or_blocked = [row for row in rows if row.state in {"failed", "blocked"}]
    if failed_or_blocked:
        return [f"Resolve {row.source}: {row.label}" for row in failed_or_blocked]
    actions = _text_list(confidence.get("required_next_actions"))
    if actions:
        return actions
    return [
        "Start manual synthetic QA review from the read-only UI.",
        "Keep this report candidate-only and do not use it for calibration or production readiness.",
    ]


def _gate_state(status: str) -> str:
    if status == "failed":
        return "failed"
    if status == "blocked":
        return "blocked"
    return "pending_review"


def _readiness_state(state: str) -> str:
    if state == "failed":
        return "failed"
    if state == "blocked":
        return "blocked"
    return "pending_review"


def _refs(value: object) -> list[str]:
    refs = _text_list(value)
    return refs or ["missing evidence ref"]


def _notes(value: object) -> list[str]:
    notes = _text_list(value)
    return notes or ["No note supplied."]


def _text_list(value: object) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value]
    return []


def _list(value: object) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return [item for item in value if isinstance(item, dict)]
    return []


def _load_object(path: Path) -> dict[str, Any]:
    payload = load_json(path)
    return payload if isinstance(payload, dict) else {}


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _any_side_effect_boundary_failure(*payloads: dict[str, Any]) -> bool:
    keys = [
        "external_writes_performed",
        "lake_write_performed",
        "sqlite_write_performed",
        "silent_learning_performed",
        "budget_submission_authorized",
        "matter_opening_authorized",
        "training_pipeline_created",
    ]
    return any(payload.get(key) is True for payload in payloads for key in keys)
