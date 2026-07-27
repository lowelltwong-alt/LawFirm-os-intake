"""Grade condition runs into per-dimension numeric scores.

The first numeric scoring in this repository. Everything else is
pass/fail/blocked check lists — right for gates, but unable to express
"condition A satisfied 14 of 17 gold expectations while B satisfied 11".
Each score keeps its numerator and denominator, so any number can be
decomposed back into the checks that produced it.

Dimensions
----------
``evidence_completeness``, ``run_integrity``, ``adapter_boundary`` are
**measured from the run's own artifacts**. They measure discipline — the run
kept its evidence bound, its ledger coherent, its boundary intact. They cannot
measure correctness, because correctness needs an expectation to compare
against.

``gold_conformance`` is **compared against a reviewed gold spec** and is the
only dimension that speaks to correctness. Where no gold exists the dimension
is recorded as not computable, with no score. As of this writing, no holdout
case has a gold spec: grading the holdout set for correctness is impossible
until a human authors and reviews those specs, and this module reports that
fact as data (``gold_coverage_complete`` / ``cases_missing_gold``) rather than
imputing anything.

Ranking
-------
``ranking_supported`` is a model invariant: it requires more than one condition
AND complete gold coverage on the graded cases. Artifact-discipline scores
alone cannot rank strategies, and one condition cannot be ranked against
itself.
"""

from __future__ import annotations

from pathlib import Path

from .gold import build_fixture_gold_report
from .models import (
    ConditionComparisonReport,
    ConditionDimensionAggregate,
    ConditionGradingCheck,
    ConditionGradingReport,
    EvaluationSplitManifest,
    FixtureGoldSpec,
    GradedDimensionScore,
    IntakePreflightPacket,
)
from .util import digest_json, digest_text, load_json, load_jsonl, now_iso, write_json

CONDITION_GRADING_REPORT_FILENAME = "condition_grading_report.json"
CONDITION_GRADING_NOTES_FILENAME = "condition_grading_report.md"

ARTIFACT_DIMENSIONS = ("evidence_completeness", "run_integrity", "adapter_boundary")
GOLD_DIMENSION = "gold_conformance"

REQUIRED_NEXT_GATES = [
    "author_and_review_gold_specs_for_every_holdout_case",
    "second_real_condition_before_any_ranking",
    "human_review_of_scores_before_any_published_claim",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _check(
    check_id: str, ok: bool, message: str, offending: list[str] | None = None
) -> ConditionGradingCheck:
    return ConditionGradingCheck(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        offending_refs=sorted(offending or []),
    )


def _ratio_from_checks(payload: dict) -> tuple[int, int]:
    checks = payload.get("checks", [])
    passed = sum(1 for check in checks if check.get("status") == "passed")
    total = sum(1 for check in checks if check.get("status") in ("passed", "failed"))
    return passed, total


def _score(
    *,
    case_ref: str,
    condition_id: str,
    dimension: str,
    basis: str,
    numerator: int | None = None,
    denominator: int | None = None,
    note: str = "",
) -> GradedDimensionScore:
    score = None
    if numerator is not None and denominator:
        score = numerator / denominator
    return GradedDimensionScore(
        case_ref=case_ref,
        condition_id=condition_id,
        dimension=dimension,
        basis=basis,  # type: ignore[arg-type]
        score=score,
        numerator=numerator,
        denominator=denominator,
        note=note,
    )


def _grade_artifacts(
    *, case_ref: str, condition_id: str, run_dir: Path
) -> list[GradedDimensionScore]:
    """Score the discipline dimensions from the run's own artifacts."""

    scores: list[GradedDimensionScore] = []

    evidence_path = run_dir / "evidence_completeness_report.json"
    if evidence_path.is_file():
        passed, total = _ratio_from_checks(load_json(evidence_path))
        scores.append(
            _score(
                case_ref=case_ref,
                condition_id=condition_id,
                dimension="evidence_completeness",
                basis="measured_from_artifacts",
                numerator=passed,
                denominator=total or 1,
            )
        )
    else:
        scores.append(
            _score(
                case_ref=case_ref,
                condition_id=condition_id,
                dimension="evidence_completeness",
                basis="not_computable_missing_artifact",
                note="evidence_completeness_report.json absent from the run directory",
            )
        )

    integrity_path = run_dir / "run_ledger_integrity_report.json"
    if integrity_path.is_file():
        passed, total = _ratio_from_checks(load_json(integrity_path))
        scores.append(
            _score(
                case_ref=case_ref,
                condition_id=condition_id,
                dimension="run_integrity",
                basis="measured_from_artifacts",
                numerator=passed,
                denominator=total or 1,
            )
        )
    else:
        scores.append(
            _score(
                case_ref=case_ref,
                condition_id=condition_id,
                dimension="run_integrity",
                basis="not_computable_missing_artifact",
                note="run_ledger_integrity_report.json absent from the run directory",
            )
        )

    adapter_path = run_dir / "model_adapter_report.json"
    if adapter_path.is_file():
        adapter = load_json(adapter_path)
        boundary_flags = [
            adapter.get("provider_call_performed") is False,
            adapter.get("network_access_allowed") is False,
            adapter.get("external_writes_allowed") is False,
            adapter.get("raw_payload_externalized") is False,
        ]
        scores.append(
            _score(
                case_ref=case_ref,
                condition_id=condition_id,
                dimension="adapter_boundary",
                basis="measured_from_artifacts",
                numerator=sum(boundary_flags),
                denominator=len(boundary_flags),
            )
        )
    else:
        scores.append(
            _score(
                case_ref=case_ref,
                condition_id=condition_id,
                dimension="adapter_boundary",
                basis="not_computable_missing_artifact",
                note="model_adapter_report.json absent from the run directory",
            )
        )

    return scores


def _grade_gold(
    *,
    case_ref: str,
    condition_id: str,
    run_dir: Path,
    gold_refs: list[str],
    repo_root: Path,
) -> GradedDimensionScore:
    """Score correctness against the reviewed gold spec, where one exists."""

    if not gold_refs:
        return _score(
            case_ref=case_ref,
            condition_id=condition_id,
            dimension=GOLD_DIMENSION,
            basis="not_computable_missing_gold",
            note=(
                "no reviewed gold spec exists for this case; correctness cannot be graded "
                "until one is authored and human-reviewed"
            ),
        )
    packet_path = run_dir / "intake_preflight_packet.json"
    if not packet_path.is_file():
        return _score(
            case_ref=case_ref,
            condition_id=condition_id,
            dimension=GOLD_DIMENSION,
            basis="not_computable_missing_artifact",
            note="intake_preflight_packet.json absent from the run directory",
        )
    packet = IntakePreflightPacket.model_validate(load_json(packet_path))
    # The gold exception-label check compares against the run's dry-run
    # exception candidates; omitting them scores recall against an empty list.
    # That omission was this module's own first defect, caught by decomposing
    # the very scores it produces (grader_defect, per the failure taxonomy).
    exception_candidates = load_jsonl(run_dir / "exception_lake_candidates.jsonl")
    passed = failed = 0
    for gold_ref in gold_refs:
        gold = FixtureGoldSpec.model_validate(load_json(repo_root / gold_ref))
        gold_report = build_fixture_gold_report(
            gold=gold,
            gold_ref=gold_ref,
            packet=packet,
            stage="preflight",
            evaluated_artifact_refs={"preflight_packet": str(packet_path)},
            preflight_exception_candidates=exception_candidates,
        )
        passed += sum(1 for check in gold_report.checks if check.status == "passed")
        failed += sum(1 for check in gold_report.checks if check.status == "failed")
    return _score(
        case_ref=case_ref,
        condition_id=condition_id,
        dimension=GOLD_DIMENSION,
        basis="gold_compared",
        numerator=passed,
        denominator=(passed + failed) or 1,
    )


def build_condition_grading_report(
    *,
    comparison: ConditionComparisonReport,
    manifest: EvaluationSplitManifest,
    comparison_report_ref: str,
    comparison_dir: Path,
    repo_root: Path,
    generated_at: str | None = None,
) -> ConditionGradingReport:
    gold_by_ref = {item.fixture_ref: item.gold_refs for item in manifest.assignments}

    scores: list[GradedDimensionScore] = []
    missing_dirs: list[str] = []
    completed = [record for record in comparison.records if record.status == "completed"]
    for record in completed:
        run_dir = Path(record.run_dir_ref)
        if not run_dir.is_absolute():
            # Run dirs are recorded relative to where the comparison ran.
            run_dir = comparison_dir / run_dir if (comparison_dir / run_dir).exists() else run_dir
        if not run_dir.exists():
            missing_dirs.append(record.run_dir_ref)
            continue
        scores.extend(
            _grade_artifacts(
                case_ref=record.case_ref, condition_id=record.condition_id, run_dir=run_dir
            )
        )
        scores.append(
            _grade_gold(
                case_ref=record.case_ref,
                condition_id=record.condition_id,
                run_dir=run_dir,
                gold_refs=gold_by_ref.get(record.case_ref, []),
                repo_root=repo_root,
            )
        )

    cases = sorted({record.case_ref for record in completed})
    cases_missing_gold = sorted(case for case in cases if not gold_by_ref.get(case))
    gold_coverage_complete = not cases_missing_gold and bool(cases)

    aggregates: list[ConditionDimensionAggregate] = []
    for condition_id in comparison.condition_ids:
        for dimension in (*ARTIFACT_DIMENSIONS, GOLD_DIMENSION):
            relevant = [
                item
                for item in scores
                if item.condition_id == condition_id and item.dimension == dimension
            ]
            if not relevant:
                continue
            computable = [item for item in relevant if item.score is not None]
            aggregates.append(
                ConditionDimensionAggregate(
                    condition_id=condition_id,
                    dimension=dimension,
                    mean_score=(
                        sum(item.score for item in computable) / len(computable)
                        if computable
                        else None
                    ),
                    computable_case_count=len(computable),
                    total_case_count=len(relevant),
                )
            )

    checks: list[ConditionGradingCheck] = []
    checks.append(
        _check(
            "all_run_directories_found",
            not missing_dirs,
            "Every completed run's directory was found and graded.",
            missing_dirs,
        )
    )
    checks.append(
        _check(
            "artifact_dimensions_computable_for_all_runs",
            not any(item.basis == "not_computable_missing_artifact" for item in scores),
            "Discipline dimensions were computable from every run's artifacts.",
            sorted(
                {
                    f"{item.case_ref}::{item.dimension}"
                    for item in scores
                    if item.basis == "not_computable_missing_artifact"
                }
            ),
        )
    )
    checks.append(
        _check(
            "grading_scored_at_least_one_case",
            bool(cases),
            "At least one completed run was available to grade.",
        )
    )

    multi_condition = len(set(comparison.condition_ids)) > 1
    supported = multi_condition and gold_coverage_complete
    if not multi_condition and not gold_coverage_complete:
        ranking_note = (
            "Ranking is unsupported twice over: only one condition ran, and "
            f"{len(cases_missing_gold)} of {len(cases)} graded cases have no reviewed gold "
            "spec. Discipline scores measure whether a run kept its rules, not whether it "
            "was right."
        )
    elif not multi_condition:
        ranking_note = "One condition cannot be ranked against itself; these scores are a baseline."
    elif not gold_coverage_complete:
        ranking_note = (
            "Gold coverage is incomplete, so correctness cannot be compared across "
            "conditions on every case."
        )
    else:
        ranking_note = (
            "Multiple conditions with complete gold coverage: scores may inform a ranking, "
            "subject to human review."
        )

    failed_checks = [check for check in checks if check.status == "failed"]
    core = {
        "comparison_report_ref": comparison_report_ref,
        "scores": sorted(
            f"{item.case_ref}::{item.condition_id}::{item.dimension}::{item.score}"
            for item in scores
        ),
    }
    return ConditionGradingReport(
        report_id=_stable_id("conditiongrading", digest_json(core)),
        comparison_report_ref=comparison_report_ref,
        split_id=comparison.split_id,
        graded_partition=comparison.scored_partition,
        generated_at=generated_at or now_iso(),
        condition_ids=comparison.condition_ids,
        case_count=len(cases),
        scores=scores,
        aggregates=aggregates,
        gold_coverage_complete=gold_coverage_complete,
        cases_missing_gold=cases_missing_gold,
        checks=checks,
        status="failed" if failed_checks else "passed",
        ranking_supported=supported,
        ranking_note=ranking_note,
        required_next_gates=REQUIRED_NEXT_GATES,
    )


def render_condition_grading_report(report: ConditionGradingReport) -> str:
    lines = [
        "# Condition Grading",
        "",
        f"- Comparison: `{report.comparison_report_ref}`",
        f"- Graded partition: **{report.graded_partition}**",
        f"- Conditions: {', '.join(f'`{c}`' for c in report.condition_ids)}",
        f"- Cases graded: {report.case_count}",
        f"- Gold coverage complete: **{report.gold_coverage_complete}**",
        f"- Status: **{report.status}**",
        "",
        "## Ranking",
        "",
        f"Ranking supported: **{report.ranking_supported}**",
        "",
        report.ranking_note,
        "",
        "## Aggregates",
        "",
        "| Condition | Dimension | Mean | Computable / total cases |",
        "|---|---|---|---|",
    ]
    for aggregate in report.aggregates:
        mean = "—" if aggregate.mean_score is None else f"{aggregate.mean_score:.3f}"
        lines.append(
            f"| `{aggregate.condition_id}` | `{aggregate.dimension}` | {mean} "
            f"| {aggregate.computable_case_count} / {aggregate.total_case_count} |"
        )
    if report.cases_missing_gold:
        lines += [
            "",
            "## Cases without reviewed gold",
            "",
            "Correctness cannot be graded for these until a gold spec is authored and",
            "human-reviewed. This is the current limit of what these scores can claim:",
            "",
        ]
        lines += [f"- `{case}`" for case in report.cases_missing_gold]
    lines += [
        "",
        "## Boundary",
        "",
        "Discipline dimensions (evidence, integrity, boundary) are measured from run",
        "artifacts and say nothing about correctness. Only gold_conformance compares",
        "against a reviewed expectation. Nothing here promotes, ranks, or authorizes",
        "anything; no external or Lake write occurred.",
        "",
        "## Required Next Gates",
        "",
    ]
    lines += [f"- {gate}" for gate in report.required_next_gates]
    return "\n".join(lines) + "\n"


def run_condition_grading(
    *,
    comparison_dir: str | Path,
    split_manifest_path: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    generated_at: str | None = None,
) -> tuple[ConditionGradingReport, Path]:
    comparison_path = Path(comparison_dir) / "condition_comparison_report.json"
    comparison = ConditionComparisonReport.model_validate(load_json(comparison_path))
    manifest = EvaluationSplitManifest.model_validate(load_json(split_manifest_path))
    report = build_condition_grading_report(
        comparison=comparison,
        manifest=manifest,
        comparison_report_ref=str(comparison_path.as_posix()),
        comparison_dir=Path(comparison_dir),
        repo_root=Path(repo_root),
        generated_at=generated_at,
    )
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / CONDITION_GRADING_REPORT_FILENAME, report.model_dump(mode="json"))
    (target / CONDITION_GRADING_NOTES_FILENAME).write_text(
        render_condition_grading_report(report), encoding="utf-8", newline="\n"
    )
    return report, target
