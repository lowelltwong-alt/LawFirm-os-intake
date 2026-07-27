"""Run implementation conditions over the held-out set and record the outcomes.

What this is
------------
The comparative unit is a ``(case, condition)`` pair. Every other report in this
repo is single-condition, and ``ModelAdapterReport``'s comparison fields are
currently tautological — ``structured_candidate_hash`` is set equal to
``deterministic_baseline_hash``, so "compared to baseline" is true by
construction rather than by measurement. This module produces records that can
actually disagree.

What this deliberately is not
-----------------------------
A ranking. This runs conditions and records what each produced; it does not say
which is better. Scoring against gold expectations is a separate concern, and
"the two conditions agreed" is not the same as "the condition was correct" —
both can be wrong identically. ``ConditionPairDelta.outcomes_identical`` means
agreement and nothing more.

With only the deterministic condition available, this produces a **baseline**,
not a comparison. The report says so in ``comparative_claim_supported`` rather
than leaving a reader to infer it.

Spend
-----
The budget ceiling is enforced in code, twice: before anything runs, the
declared permissions of every condition are summed and refused if they exceed
the ceiling; after each run, the run's own adapter artifact is re-read and
checked to confirm no provider call occurred. A ceiling that only exists in a
policy document is not a ceiling.
"""

from __future__ import annotations

from itertools import combinations
from pathlib import Path
from typing import Any

from .adapters import preflight_projection
from .models import (
    ConditionComparisonCheck,
    ConditionComparisonReport,
    ConditionPairDelta,
    ConditionRunRecord,
    EvaluationConditionSpec,
    EvaluationSplitManifest,
)
from .util import digest_json, digest_text, load_json, now_iso, write_json
from .workflow import run_preflight

CONDITION_COMPARISON_REPORT_FILENAME = "condition_comparison_report.json"
CONDITION_COMPARISON_NOTES_FILENAME = "condition_comparison_report.md"
CONDITION_RUN_RECORDS_FILENAME = "condition_run_records.jsonl"

REQUIRED_NEXT_GATES = [
    "human_review_before_any_comparative_claim",
    "grading_against_reviewed_gold_before_ranking_conditions",
    "cost_and_reviewer_effort_measurement_before_value_claims",
]


class BudgetCeilingExceeded(RuntimeError):
    """Raised before any run when declared spend exceeds the ceiling."""


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _digest_file(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return digest_text(raw.decode("utf-8"))


def _check(
    check_id: str, ok: bool, message: str, offending: list[str] | None = None
) -> ConditionComparisonCheck:
    return ConditionComparisonCheck(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        offending_refs=sorted(offending or []),
    )


def assert_within_budget_ceiling(
    conditions: list[EvaluationConditionSpec], case_count: int, max_model_calls: int
) -> int:
    """Refuse the whole run if declared spend could exceed the ceiling.

    Checked before any case executes, so an over-budget configuration costs
    nothing rather than being discovered part-way through.
    """

    declared = sum(spec.model_calls_permitted for spec in conditions) * case_count
    if declared > max_model_calls:
        raise BudgetCeilingExceeded(
            f"conditions declare up to {declared} model calls across {case_count} cases, "
            f"exceeding the ceiling of {max_model_calls}; raise --max-model-calls "
            f"deliberately or use conditions that make no provider call"
        )
    return declared


def _adapter_artifact_shows_no_provider_call(run_dir: Path) -> bool:
    """Re-read the run's own adapter artifact rather than trusting the spec."""

    artifact = run_dir / "model_adapter_report.json"
    if not artifact.is_file():
        return False
    payload = load_json(artifact)
    return payload.get("provider_call_performed") is False


def build_condition_comparison_report(
    *,
    manifest: EvaluationSplitManifest,
    conditions: list[EvaluationConditionSpec],
    records: list[ConditionRunRecord],
    split_manifest_ref: str,
    scored_partition: str,
    max_model_calls: int,
    provider_calls_performed: int,
    generated_at: str | None = None,
) -> ConditionComparisonReport:
    condition_ids = [spec.condition_id for spec in conditions]
    completed = [record for record in records if record.status == "completed"]
    failed = [record for record in records if record.status == "failed"]

    checks: list[ConditionComparisonCheck] = []
    checks.append(
        _check(
            "no_provider_call_performed",
            provider_calls_performed == 0,
            "No condition performed a provider call; this run cost nothing.",
        )
    )
    checks.append(
        _check(
            "every_case_ran_under_every_condition",
            len(records) == len(condition_ids) * len({record.case_ref for record in records})
            if records
            else True,
            "Each scored case was attempted under each declared condition.",
        )
    )
    checks.append(
        _check(
            "all_runs_completed",
            not failed,
            "Every condition run completed.",
            [f"{record.case_ref}::{record.condition_id}" for record in failed],
        )
    )
    checks.append(
        _check(
            "scored_cases_are_holdout",
            all(record.partition == scored_partition for record in records),
            f"Every scored case comes from the {scored_partition} partition.",
            [record.case_ref for record in records if record.partition != scored_partition],
        )
    )
    pair_deltas: list[ConditionPairDelta] = []
    by_case: dict[str, dict[str, ConditionRunRecord]] = {}
    for record in completed:
        by_case.setdefault(record.case_ref, {})[record.condition_id] = record
    for case_ref, per_condition_record in sorted(by_case.items()):
        for left, right in combinations(sorted(per_condition_record), 2):
            left_record = per_condition_record[left]
            right_record = per_condition_record[right]
            pair_deltas.append(
                ConditionPairDelta(
                    case_ref=case_ref,
                    left_condition_id=left,
                    right_condition_id=right,
                    outcomes_identical=(
                        left_record.outcome_projection_digest
                        == right_record.outcome_projection_digest
                    ),
                    left_projection_digest=left_record.outcome_projection_digest,
                    right_projection_digest=right_record.outcome_projection_digest,
                )
            )

    multi_condition = len(set(condition_ids)) > 1
    supported = multi_condition and bool(completed)
    if not multi_condition:
        note = (
            "Single condition: this report is a baseline, not a comparison. No claim about "
            "the relative merit of implementation strategies is supported by it."
        )
    elif not completed:
        note = "No condition run completed, so no comparative claim is supported."
    elif pair_deltas and all(delta.outcomes_identical for delta in pair_deltas):
        note = (
            "All conditions produced identical outcomes on every scored case. The harness "
            "cannot distinguish them on this evidence; agreement is not correctness, and "
            "both could be wrong identically."
        )
    else:
        note = (
            "Conditions produced differing outcomes on at least one case. Differences are "
            "recorded, not ranked: ranking requires grading against reviewed gold."
        )

    failed_checks = [check for check in checks if check.status == "failed"]
    core = {
        "split_id": manifest.split_id,
        "conditions": sorted(condition_ids),
        "records": sorted(
            f"{record.case_ref}::{record.condition_id}::{record.outcome_projection_digest}"
            for record in records
        ),
    }
    return ConditionComparisonReport(
        report_id=_stable_id("conditioncomparison", digest_json(core)),
        split_id=manifest.split_id,
        split_manifest_ref=split_manifest_ref,
        generated_at=generated_at or now_iso(),
        scored_partition=scored_partition,  # type: ignore[arg-type]
        condition_ids=condition_ids,
        case_count=len({record.case_ref for record in records}),
        completed_run_count=len(completed),
        failed_run_count=len(failed),
        max_model_calls_permitted=max_model_calls,
        provider_calls_performed=provider_calls_performed,
        records=records,
        pair_deltas=pair_deltas,
        checks=checks,
        status="failed" if failed_checks else "passed",
        comparative_claim_supported=supported,
        comparative_claim_note=note,
        required_next_gates=REQUIRED_NEXT_GATES,
    )


def render_condition_comparison_report(report: ConditionComparisonReport) -> str:
    lines = [
        "# Condition Comparison",
        "",
        f"- Split: `{report.split_id}`",
        f"- Scored partition: **{report.scored_partition}**",
        f"- Conditions: {', '.join(f'`{c}`' for c in report.condition_ids)}",
        f"- Cases: {report.case_count}",
        f"- Runs completed / failed: {report.completed_run_count} / {report.failed_run_count}",
        f"- Model call ceiling: {report.max_model_calls_permitted}; "
        f"provider calls performed: {report.provider_calls_performed}",
        f"- Status: **{report.status}**",
        "",
        "## What this supports",
        "",
        f"Comparative claim supported: **{report.comparative_claim_supported}**",
        "",
        report.comparative_claim_note,
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in report.checks:
        detail = check.message
        if check.offending_refs:
            detail += " Offending: " + ", ".join(f"`{ref}`" for ref in check.offending_refs)
        lines.append(f"| `{check.check_id}` | {check.status} | {detail} |")
    if report.pair_deltas:
        lines += [
            "",
            "## Pairwise outcomes",
            "",
            "Agreement means the two conditions produced the same projection. It does not",
            "mean either was correct.",
            "",
            "| Case | Left | Right | Identical |",
            "|---|---|---|---|",
        ]
        for delta in report.pair_deltas:
            lines.append(
                f"| `{Path(delta.case_ref).name}` | `{delta.left_condition_id}` "
                f"| `{delta.right_condition_id}` | {delta.outcomes_identical} |"
            )
    lines += [
        "",
        "## Boundary",
        "",
        "This report records what each condition produced. It ranks nothing, scores nothing",
        "against gold, promotes nothing, and performs no external or Lake write. Cost and",
        "reviewer-effort figures are absent rather than estimated.",
        "",
        "## Required Next Gates",
        "",
    ]
    lines += [f"- {gate}" for gate in report.required_next_gates]
    return "\n".join(lines) + "\n"


def run_condition_comparison(
    *,
    split_manifest_path: str | Path,
    conditions: list[EvaluationConditionSpec],
    out_dir: str | Path,
    repo_root: str | Path = ".",
    scored_partition: str = "holdout",
    max_model_calls: int = 0,
    generated_at: str | None = None,
) -> tuple[ConditionComparisonReport, Path]:
    """Run every condition over every scored case, recording each outcome."""

    manifest = EvaluationSplitManifest.model_validate(load_json(split_manifest_path))
    root = Path(repo_root)
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)

    scored = [item for item in manifest.assignments if item.partition == scored_partition]
    assert_within_budget_ceiling(conditions, len(scored), max_model_calls)

    records: list[ConditionRunRecord] = []
    provider_calls = 0

    for assignment in sorted(scored, key=lambda item: item.fixture_ref):
        case_path = root / assignment.fixture_ref
        for spec in conditions:
            run_root = target / "runs" / Path(assignment.fixture_ref).stem / spec.condition_id
            record_id = _stable_id("conditionrun", f"{assignment.fixture_ref}::{spec.condition_id}")
            try:
                packet, run_dir = run_preflight(
                    case_path,
                    root / spec.practice_profile_ref,
                    run_root,
                    adapter=spec.adapter,
                )
                projection: dict[str, Any] = preflight_projection(packet)
                if not _adapter_artifact_shows_no_provider_call(run_dir):
                    # Fail closed: the run's own artifact must corroborate the
                    # zero-spend claim, not the spec that requested it.
                    provider_calls += 1
                records.append(
                    ConditionRunRecord(
                        record_id=record_id,
                        case_ref=assignment.fixture_ref,
                        case_digest=_digest_file(case_path),
                        partition=assignment.partition,
                        condition_id=spec.condition_id,
                        config_digest=spec.config_digest,
                        status="completed",
                        outcome_projection_digest=digest_json(projection),
                        model_calls_permitted=spec.model_calls_permitted,
                        run_dir_ref=str(Path(run_dir).as_posix()),
                    )
                )
            except Exception as exc:  # a failing condition is data, not a crash
                records.append(
                    ConditionRunRecord(
                        record_id=record_id,
                        case_ref=assignment.fixture_ref,
                        case_digest=_digest_file(case_path),
                        partition=assignment.partition,
                        condition_id=spec.condition_id,
                        config_digest=spec.config_digest,
                        status="failed",
                        outcome_projection_digest="",
                        model_calls_permitted=spec.model_calls_permitted,
                        run_dir_ref=str(run_root.as_posix()),
                        failure_reason=f"{type(exc).__name__}: {exc}"[:400],
                    )
                )

    report = build_condition_comparison_report(
        manifest=manifest,
        conditions=conditions,
        records=records,
        split_manifest_ref=str(Path(split_manifest_path).as_posix()),
        scored_partition=scored_partition,
        max_model_calls=max_model_calls,
        provider_calls_performed=provider_calls,
        generated_at=generated_at,
    )
    write_json(target / CONDITION_COMPARISON_REPORT_FILENAME, report.model_dump(mode="json"))
    (target / CONDITION_COMPARISON_NOTES_FILENAME).write_text(
        render_condition_comparison_report(report), encoding="utf-8", newline="\n"
    )
    records_path = target / CONDITION_RUN_RECORDS_FILENAME
    if records_path.exists():
        records_path.unlink()
    for record in records:
        from .util import append_jsonl

        append_jsonl(records_path, record.model_dump(mode="json"))
    return report, target


def load_condition_specs(path: str | Path) -> list[EvaluationConditionSpec]:
    payload = load_json(path)
    return [EvaluationConditionSpec.model_validate(item) for item in payload["conditions"]]
