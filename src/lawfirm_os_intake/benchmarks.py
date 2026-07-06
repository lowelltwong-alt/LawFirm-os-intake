from __future__ import annotations

from copy import deepcopy
from datetime import date, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import (
    BenchmarkEffectiveGrade,
    BenchmarkReplayBudgetLineCheck,
    BenchmarkReplayCellCheck,
    BenchmarkReplayCheck,
    BenchmarkReplayReport,
    BenchmarkSnapshotManifest,
    BudgetProposal,
    RateBenchmarkCell,
)
from .util import digest_json, load_json, now_iso, write_json


BENCHMARK_REPLAY_REPORT_FILENAME = "benchmark_replay_report.json"
BENCHMARK_REPLAY_NOTES_FILENAME = "benchmark_replay_report.md"
BENCHMARK_EFFECTIVE_GRADE_METHOD = "benchmark_effective_grade.v0_1"

AUTHORIZED_RATE_SOURCES = {
    "synthetic_profile",
    "authorized_profile",
    "synthetic_named_timekeeper_override",
}
SUCCESS_LABELS = [
    "benchmark_replay_candidate",
    "budget_rate_trace_review_candidate",
]
FAILURE_LABELS = SUCCESS_LABELS + [
    "benchmark_snapshot_invalid",
    "benchmark_rate_laundering_attempt",
]
REQUIRED_NEXT_GATES = [
    "human_budget_benchmark_context_review",
    "no_benchmark_cell_as_rate_authority",
    "legal_knowledge_runtime_owns_public_retrieval",
    "no_lake_or_sqlite_write_from_benchmark_replay",
]


def validate_benchmark_snapshot(payload: dict) -> BenchmarkSnapshotManifest:
    manifest = BenchmarkSnapshotManifest.model_validate(payload)
    seen = {cell.benchmark_cell_id for cell in manifest.cells}
    if len(seen) != len(manifest.cells):
        raise ValueError("benchmark snapshot contains duplicate benchmark_cell_id values")
    for cell in manifest.cells:
        if not cell.page_sha256.startswith("sha256:"):
            raise ValueError(f"benchmark cell {cell.benchmark_cell_id} is missing sha256 hash")
    return manifest


def replay_budget_benchmark_refs(
    budget: BudgetProposal,
    manifest: BenchmarkSnapshotManifest,
) -> list[str]:
    available = {cell.benchmark_cell_id for cell in manifest.cells}
    missing: list[str] = []
    for line in budget.lines:
        if line.estimate_basis != "benchmark_cell":
            continue
        for ref in line.estimate_basis_refs:
            if ref not in available:
                missing.append(ref)
    return sorted(set(missing))


def run_benchmark_replay_audit(
    *,
    budget_proposal_path: str | Path,
    benchmark_snapshot_path: str | Path,
    out_dir: str | Path,
    as_of_date: str | None = None,
) -> tuple[BenchmarkReplayReport, Path]:
    snapshot_payload = load_json(benchmark_snapshot_path)
    budget_payload = load_json(budget_proposal_path)
    as_of = _parse_date(as_of_date or now_iso())
    manifest, snapshot_checks = _load_snapshot(snapshot_payload)
    budget, budget_checks = _load_budget(budget_payload)
    cell_checks = _cell_checks(manifest, as_of) if manifest is not None else []
    valid_cell_ids = {
        check.benchmark_cell_id for check in cell_checks if _cell_can_satisfy_context_ref(check)
    }
    line_checks = _line_checks(budget_payload, budget=budget, valid_cell_ids=valid_cell_ids)
    checks = [
        *_snapshot_hash_checks(snapshot_payload),
        *snapshot_checks,
        *budget_checks,
        _no_benchmark_rate_source_check(budget_payload, line_checks),
    ]
    failed_cells = [check for check in cell_checks if check.status == "failed"]
    ignored_cells = [check for check in cell_checks if check.status == "ignored"]
    failed_lines = [check for check in line_checks if check.status == "failed"]
    failed_checks = [check for check in checks if check.status == "failed"]
    snapshot_hash = (
        snapshot_payload.get("pinned_hash") if isinstance(snapshot_payload, dict) else None
    )
    expected_hash = (
        _expected_snapshot_hash(snapshot_payload) if isinstance(snapshot_payload, dict) else None
    )
    core = {
        "budget": _budget_id(budget_payload, budget),
        "snapshot": _snapshot_id(snapshot_payload, manifest),
        "failed_cells": [check.benchmark_cell_id for check in failed_cells],
        "failed_lines": [check.line_ref for check in failed_lines],
        "failed_checks": [check.check_id for check in failed_checks],
        "expected_hash": expected_hash,
    }
    report = BenchmarkReplayReport(
        benchmark_replay_report_id="benchmarkreplay_"
        + digest_json(core)[len("sha256:") : len("sha256:") + 20],
        status=(
            "blocked_by_benchmark_replay"
            if failed_cells or failed_lines or failed_checks
            else "benchmark_replay_ready_for_review"
        ),
        budget_proposal_ref=str(budget_proposal_path),
        budget_proposal_id=_budget_id(budget_payload, budget),
        benchmark_snapshot_ref=str(benchmark_snapshot_path),
        benchmark_snapshot_id=_snapshot_id(snapshot_payload, manifest),
        benchmark_snapshot_hash=snapshot_hash,
        expected_benchmark_snapshot_hash=expected_hash,
        as_of_date=as_of.isoformat(),
        snapshot_cell_count=len(manifest.cells) if manifest is not None else 0,
        cell_check_count=len(cell_checks),
        failed_cell_check_count=len(failed_cells),
        ignored_cell_check_count=len(ignored_cells),
        budget_line_check_count=len(line_checks),
        failed_budget_line_check_count=len(failed_lines),
        missing_benchmark_ref_count=sum(len(line.missing_benchmark_refs) for line in line_checks),
        rate_laundering_attempt_count=sum(
            1 for line in line_checks if line.rate_trace_status == "benchmark_launder_attempt"
        ),
        cells=cell_checks,
        budget_lines=line_checks,
        checks=checks,
        candidate_exception_lake_labels=(
            FAILURE_LABELS if failed_cells or failed_lines or failed_checks else SUCCESS_LABELS
        ),
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / BENCHMARK_REPLAY_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / BENCHMARK_REPLAY_NOTES_FILENAME).write_text(
        render_benchmark_replay_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_benchmark_replay_report(report: BenchmarkReplayReport) -> str:
    failed_checks = [check for check in report.checks if check.status == "failed"]
    failed_lines = [line for line in report.budget_lines if line.status == "failed"]
    failed_cells = [cell for cell in report.cells if cell.status == "failed"]
    lines = [
        "# Benchmark Replay Report",
        "",
        f"**Report ID:** {report.benchmark_replay_report_id}",
        f"**Status:** {report.status}",
        f"**Budget:** `{report.budget_proposal_ref}`",
        f"**Benchmark snapshot:** `{report.benchmark_snapshot_ref}`",
        "",
        "## Boundary",
        "",
        "- Candidate-only and synthetic-only.",
        "- Benchmark cells are context, not rate authority.",
        "- Legal Knowledge Runtime owns public retrieval and benchmark grading.",
        "- No Lake/SQLite write, budget submission, matter opening, or calibration is authorized.",
        "",
        "## Summary",
        "",
        f"- Snapshot cells: {report.snapshot_cell_count}",
        f"- Failed cell checks: {report.failed_cell_check_count}",
        f"- Ignored cell checks: {report.ignored_cell_check_count}",
        f"- Budget line checks: {report.budget_line_check_count}",
        f"- Failed budget line checks: {report.failed_budget_line_check_count}",
        f"- Missing benchmark refs: {report.missing_benchmark_ref_count}",
        f"- Rate laundering attempts: {report.rate_laundering_attempt_count}",
        "",
        "## Failures",
        "",
    ]
    if not (failed_checks or failed_lines or failed_cells):
        lines.append("- None.")
    for check in failed_checks:
        lines.append(f"- `{check.check_id}`: {check.message}")
    for cell in failed_cells:
        lines.append(f"- Cell `{cell.benchmark_cell_id}`: {cell.message}")
    for line in failed_lines:
        lines.append(f"- Line `{line.line_ref}`: {line.message}")
    lines.extend(
        [
            "",
            "## Required Next Gates",
            "",
            *(f"- `{gate}`" for gate in report.required_next_gates),
            "",
        ]
    )
    return "\n".join(lines)


def _load_snapshot(
    payload: Any,
) -> tuple[BenchmarkSnapshotManifest | None, list[BenchmarkReplayCheck]]:
    checks: list[BenchmarkReplayCheck] = []
    if not isinstance(payload, dict):
        return None, [
            _failed_check(
                "benchmark_snapshot_payload_mapping",
                "Benchmark snapshot payload must be a JSON object.",
            )
        ]
    if payload.get("contains_real_negotiated_rates") is True:
        checks.append(
            _failed_check(
                "benchmark_snapshot_real_rates_refused",
                "Benchmark snapshot declares real negotiated rates; intake must refuse it.",
            )
        )
    try:
        manifest = validate_benchmark_snapshot(payload)
    except (ValidationError, ValueError) as exc:
        checks.append(
            _failed_check(
                "benchmark_snapshot_schema_valid",
                f"Benchmark snapshot schema/hash validation failed: {exc}",
            )
        )
        return None, checks
    checks.append(
        _passed_check(
            "benchmark_snapshot_schema_valid",
            "Benchmark snapshot validates against local candidate schema.",
            evidence_refs=[manifest.benchmark_snapshot_id],
        )
    )
    return manifest, checks


def _load_budget(payload: Any) -> tuple[BudgetProposal | None, list[BenchmarkReplayCheck]]:
    if not isinstance(payload, dict):
        return None, [
            _failed_check(
                "budget_proposal_payload_mapping",
                "Budget proposal payload must be a JSON object.",
            )
        ]
    try:
        budget = BudgetProposal.model_validate(payload)
    except ValidationError as exc:
        return None, [
            _failed_check(
                "budget_proposal_schema_valid",
                f"Budget proposal schema validation failed: {exc}",
            )
        ]
    return budget, [
        _passed_check(
            "budget_proposal_schema_valid",
            "Budget proposal validates against local schema.",
            evidence_refs=[budget.budget_proposal_id],
        )
    ]


def _snapshot_hash_checks(payload: Any) -> list[BenchmarkReplayCheck]:
    if not isinstance(payload, dict):
        return []
    expected = _expected_snapshot_hash(payload)
    actual = payload.get("pinned_hash")
    if actual != expected:
        return [
            _failed_check(
                "benchmark_snapshot_hash_matches_content",
                "Benchmark snapshot pinned_hash must equal sha256 of snapshot content without pinned_hash.",
                evidence_refs=[expected],
                blocking_refs=[str(actual)],
            )
        ]
    return [
        _passed_check(
            "benchmark_snapshot_hash_matches_content",
            "Benchmark snapshot pinned_hash matches canonical content hash.",
            evidence_refs=[expected],
        )
    ]


def _expected_snapshot_hash(payload: dict[str, Any]) -> str:
    body = deepcopy(payload)
    body.pop("pinned_hash", None)
    return digest_json(body)


def _cell_checks(
    manifest: BenchmarkSnapshotManifest,
    as_of: date,
) -> list[BenchmarkReplayCellCheck]:
    return [_cell_check(cell, as_of) for cell in manifest.cells]


def _cell_check(cell: RateBenchmarkCell, as_of: date) -> BenchmarkReplayCellCheck:
    issue_codes: list[str] = []
    status = "passed"
    if not _valid_sha256(cell.page_sha256):
        issue_codes.append("benchmark_cell_missing_valid_sha256")
        status = "failed"
    if not cell.source_url.strip():
        issue_codes.append("benchmark_cell_missing_source_url")
        status = "failed"
    if not cell.quote_span.strip():
        issue_codes.append("benchmark_cell_missing_quote_span")
        status = "failed"
    if not cell.license_note.strip():
        issue_codes.append("benchmark_cell_missing_license_note")
        status = "failed"
    if not cell.proxy_bias_note.strip():
        issue_codes.append("benchmark_cell_missing_proxy_bias_note")
        status = "failed"
    if cell.benchmark_type == "carrier_panel_candidate":
        issue_codes.append("benchmark_cell_carrier_panel_candidate_refused")
        status = "failed"
    effective_grade, staleness_months = effective_benchmark_grade(cell, as_of)
    if cell.human_grading_status == "rejected":
        issue_codes.append("benchmark_cell_rejected")
        status = "ignored" if status == "passed" else status
    elif cell.human_grading_status != "reviewed":
        issue_codes.append("benchmark_cell_not_human_reviewed")
        status = "ignored" if status == "passed" else status
    elif effective_grade not in {"A", "B"}:
        issue_codes.append("benchmark_cell_low_confidence_context_only")
        status = "ignored" if status == "passed" else status
    band_flag_authorized = (
        status == "passed"
        and effective_grade in {"A", "B"}
        and cell.human_grading_status == "reviewed"
    )
    if status == "passed":
        message = "Benchmark cell may be used as reviewed context only, not rate authority."
    elif status == "ignored":
        message = "Benchmark cell is ignored for band pressure but may remain context evidence."
    else:
        message = "Benchmark cell is malformed and cannot be used as context."
    return BenchmarkReplayCellCheck(
        benchmark_cell_id=cell.benchmark_cell_id,
        status=status,  # type: ignore[arg-type]
        original_grade=cell.grade,
        effective_grade=effective_grade,
        human_grading_status=cell.human_grading_status,
        staleness_months=staleness_months,
        band_flag_authorized=band_flag_authorized,
        issue_codes=issue_codes,
        message=message,
    )


def effective_benchmark_grade(
    cell: RateBenchmarkCell,
    as_of: date | str,
) -> tuple[BenchmarkEffectiveGrade, int]:
    as_of_date = _parse_date(as_of) if isinstance(as_of, str) else as_of
    if cell.human_grading_status == "rejected":
        return "rejected", _staleness_months(cell, as_of_date)
    if cell.grade in {"proxy_only", "ungraded"}:
        return cell.grade, _staleness_months(cell, as_of_date)
    staleness_months = _staleness_months(cell, as_of_date)
    if cell.grade == "C":
        return "C", staleness_months
    order = ["A", "B", "C"]
    downgrade_steps = max(0, (max(staleness_months - 24, 0) + 23) // 24)
    index = min(order.index(cell.grade) + downgrade_steps, len(order) - 1)
    return order[index], staleness_months  # type: ignore[return-value]


def _line_checks(
    budget_payload: dict[str, Any],
    *,
    budget: BudgetProposal | None,
    valid_cell_ids: set[str],
) -> list[BenchmarkReplayBudgetLineCheck]:
    raw_lines = [line for line in budget_payload.get("lines") or [] if isinstance(line, dict)]
    pricing_status = (
        budget.pricing_status
        if budget is not None
        else str(budget_payload.get("pricing_status", "unknown"))
    )
    checks = [
        _line_check(
            index=index,
            line=line,
            pricing_status=pricing_status,
            valid_cell_ids=valid_cell_ids,
        )
        for index, line in enumerate(raw_lines)
    ]
    rate_sources = []
    calculation_report = budget_payload.get("calculation_report")
    if isinstance(calculation_report, dict):
        rate_sources = [str(source) for source in calculation_report.get("rate_sources") or []]
    if "benchmark_cell" in rate_sources:
        checks.append(
            BenchmarkReplayBudgetLineCheck(
                line_ref="$.calculation_report.rate_sources",
                status="failed",
                pricing_status=_pricing_status_literal(pricing_status),
                rate_source="benchmark_cell",
                rate_trace_status="benchmark_launder_attempt",
                issue_codes=["benchmark_cell_listed_as_rate_source"],
                message="Calculation report attempts to list benchmark_cell as a rate source.",
            )
        )
    return checks


def _cell_can_satisfy_context_ref(check: BenchmarkReplayCellCheck) -> bool:
    if check.status == "passed":
        return True
    return check.status == "ignored" and check.issue_codes == [
        "benchmark_cell_low_confidence_context_only"
    ]


def _line_check(
    *,
    index: int,
    line: dict[str, Any],
    pricing_status: str,
    valid_cell_ids: set[str],
) -> BenchmarkReplayBudgetLineCheck:
    line_ref = f"$.lines[{index}]"
    rate_source = line.get("rate_source")
    estimate_basis = line.get("estimate_basis")
    benchmark_refs = [str(ref) for ref in line.get("estimate_basis_refs") or []]
    missing_refs = [
        ref
        for ref in benchmark_refs
        if estimate_basis == "benchmark_cell" and ref not in valid_cell_ids
    ]
    if rate_source == "benchmark_cell":
        return BenchmarkReplayBudgetLineCheck(
            line_ref=line_ref,
            status="failed",
            pricing_status=_pricing_status_literal(pricing_status),
            rate_source=str(rate_source),
            rate_trace_status="benchmark_launder_attempt",
            benchmark_refs=benchmark_refs,
            issue_codes=["benchmark_cell_used_as_rate_source"],
            message="Benchmark cells cannot be used as rate authority.",
        )
    if estimate_basis == "benchmark_cell" and missing_refs:
        return BenchmarkReplayBudgetLineCheck(
            line_ref=line_ref,
            status="failed",
            pricing_status=_pricing_status_literal(pricing_status),
            rate_source=str(rate_source) if rate_source is not None else None,
            rate_trace_status="benchmark_context_missing",
            benchmark_refs=benchmark_refs,
            missing_benchmark_refs=missing_refs,
            issue_codes=["benchmark_context_ref_missing"],
            message="Budget line cites benchmark context refs not present in the pinned snapshot.",
        )
    if pricing_status == "priced" and line.get("hourly_rate") is not None:
        if rate_source not in AUTHORIZED_RATE_SOURCES:
            return BenchmarkReplayBudgetLineCheck(
                line_ref=line_ref,
                status="failed",
                pricing_status="priced",
                rate_source=str(rate_source) if rate_source is not None else None,
                rate_trace_status="unknown_or_invalid_rate_source",
                benchmark_refs=benchmark_refs,
                issue_codes=["priced_line_missing_authorized_rate_source"],
                message="Priced budget line must trace to an authorized rate source.",
            )
        if estimate_basis == "benchmark_cell":
            return BenchmarkReplayBudgetLineCheck(
                line_ref=line_ref,
                status="passed",
                pricing_status="priced",
                rate_source=str(rate_source),
                rate_trace_status="benchmark_context_ref_valid",
                benchmark_refs=benchmark_refs,
                message="Priced line uses authorized rates and valid benchmark context.",
            )
        return BenchmarkReplayBudgetLineCheck(
            line_ref=line_ref,
            status="passed",
            pricing_status="priced",
            rate_source=str(rate_source),
            rate_trace_status="authorized_rate_source",
            benchmark_refs=benchmark_refs,
            message="Priced line traces to authorized rate source; no benchmark context required.",
        )
    return BenchmarkReplayBudgetLineCheck(
        line_ref=line_ref,
        status="passed",
        pricing_status=_pricing_status_literal(pricing_status),
        rate_source=str(rate_source) if rate_source is not None else None,
        rate_trace_status="hours_only_no_rate",
        benchmark_refs=benchmark_refs,
        message="Line is not priced or has no hourly rate; benchmark cells are not used as rates.",
    )


def _no_benchmark_rate_source_check(
    budget_payload: dict[str, Any],
    line_checks: list[BenchmarkReplayBudgetLineCheck],
) -> BenchmarkReplayCheck:
    laundering_refs = [
        check.line_ref
        for check in line_checks
        if check.rate_trace_status == "benchmark_launder_attempt"
    ]
    if laundering_refs:
        return _failed_check(
            "no_benchmark_cell_as_rate_source",
            "Benchmark cells appeared as rate authority in the budget artifact.",
            blocking_refs=laundering_refs,
        )
    return _passed_check(
        "no_benchmark_cell_as_rate_source",
        "Benchmark cells were not used as rate authority.",
        evidence_refs=[str(budget_payload.get("budget_proposal_id", "unknown"))],
    )


def _staleness_months(cell: RateBenchmarkCell, as_of: date) -> int:
    period_end = _cell_period_end(cell)
    months = (as_of.year - period_end.year) * 12 + (as_of.month - period_end.month)
    if as_of.day < period_end.day:
        months -= 1
    return max(0, months)


def _cell_period_end(cell: RateBenchmarkCell) -> date:
    if cell.observation_period_end:
        return _parse_date(cell.observation_period_end)
    return date(cell.year, 12, 31)


def _parse_date(value: str) -> date:
    normalized = value.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized).date()
    except ValueError:
        return date.fromisoformat(value[:10])


def _valid_sha256(value: str) -> bool:
    if not value.startswith("sha256:") or len(value) != len("sha256:") + 64:
        return False
    suffix = value[len("sha256:") :]
    return all(character in "0123456789abcdef" for character in suffix.lower())


def _budget_id(payload: Any, budget: BudgetProposal | None) -> str | None:
    if budget is not None:
        return budget.budget_proposal_id
    if isinstance(payload, dict):
        value = payload.get("budget_proposal_id")
        return str(value) if value is not None else None
    return None


def _snapshot_id(payload: Any, manifest: BenchmarkSnapshotManifest | None) -> str | None:
    if manifest is not None:
        return manifest.benchmark_snapshot_id
    if isinstance(payload, dict):
        value = payload.get("benchmark_snapshot_id")
        return str(value) if value is not None else None
    return None


def _pricing_status_literal(
    value: str,
) -> str:
    if value in {"priced", "hours_only", "insufficient_information"}:
        return value
    return "unknown"


def _passed_check(
    check_id: str,
    message: str,
    *,
    evidence_refs: list[str] | None = None,
) -> BenchmarkReplayCheck:
    return BenchmarkReplayCheck(
        check_id=check_id,
        status="passed",
        message=message,
        evidence_refs=evidence_refs or [],
    )


def _failed_check(
    check_id: str,
    message: str,
    *,
    evidence_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> BenchmarkReplayCheck:
    return BenchmarkReplayCheck(
        check_id=check_id,
        status="failed",
        message=message,
        evidence_refs=evidence_refs or [],
        blocking_refs=blocking_refs or [],
    )
