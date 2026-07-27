"""Scores must decompose, absences must stay absent, and ranking must not sneak in.

The property under test is honesty of the numbers: every score carries the
numerator and denominator that produced it; a dimension that cannot be computed
carries no score rather than an imputed one; and ``ranking_supported`` cannot be
edited into a report whose evidence does not support ranking.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lawfirm_os_intake.condition_comparison import (
    load_condition_specs,
    run_condition_comparison,
)
from lawfirm_os_intake.condition_grading import run_condition_grading
from lawfirm_os_intake.models import (
    ConditionDimensionAggregate,
    ConditionGradingReport,
    GradedDimensionScore,
)

SPLIT_REF = "examples/synthetic/evaluation/intake-evaluation-split.json"
SPECS_REF = "examples/synthetic/evaluation/intake-condition-specs.json"


def _comparison(repo_root: Path, tmp_path: Path, partition: str = "holdout") -> Path:
    out = tmp_path / f"comparison-{partition}"
    run_condition_comparison(
        split_manifest_path=repo_root / SPLIT_REF,
        conditions=load_condition_specs(repo_root / SPECS_REF),
        out_dir=out,
        repo_root=repo_root,
        scored_partition=partition,
        generated_at="2026-07-27T00:00:00Z",
    )
    return out


def test_holdout_grading_scores_discipline_but_not_correctness(
    repo_root: Path, tmp_path: Path
) -> None:
    """The current honest state: no holdout case has reviewed gold, so
    correctness is explicitly ungraded there rather than imputed."""

    comparison_dir = _comparison(repo_root, tmp_path)
    report, out_dir = run_condition_grading(
        comparison_dir=comparison_dir,
        split_manifest_path=repo_root / SPLIT_REF,
        out_dir=tmp_path / "grading",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )

    assert report.status == "passed", [c for c in report.checks if c.status == "failed"]
    assert report.case_count == 5
    assert report.gold_coverage_complete is False
    assert len(report.cases_missing_gold) == 5
    assert report.ranking_supported is False

    by_dimension = {}
    for aggregate in report.aggregates:
        by_dimension[aggregate.dimension] = aggregate
    for dimension in ("evidence_completeness", "run_integrity", "adapter_boundary"):
        assert by_dimension[dimension].mean_score == 1.0
        assert by_dimension[dimension].computable_case_count == 5
    gold = by_dimension["gold_conformance"]
    assert gold.mean_score is None
    assert gold.computable_case_count == 0
    assert gold.total_case_count == 5

    persisted = json.loads((out_dir / "condition_grading_report.json").read_text(encoding="utf-8"))
    assert persisted["external_writes_performed"] is False
    assert persisted["lake_write_performed"] is False
    assert (out_dir / "condition_grading_report.md").is_file()


def test_development_grading_exercises_the_gold_path(repo_root: Path, tmp_path: Path) -> None:
    """Two development cases carry reviewed gold; grading them must produce a
    real gold_conformance score with decomposable counts."""

    comparison_dir = _comparison(repo_root, tmp_path, partition="development")
    report, _ = run_condition_grading(
        comparison_dir=comparison_dir,
        split_manifest_path=repo_root / SPLIT_REF,
        out_dir=tmp_path / "grading-dev",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )

    gold_scores = [
        item
        for item in report.scores
        if item.dimension == "gold_conformance" and item.basis == "gold_compared"
    ]
    assert len(gold_scores) == 2, "both gold-mapped development cases must be gold-graded"
    for item in gold_scores:
        assert item.score is not None
        assert item.denominator and item.denominator > 0
        assert round(item.score, 6) == round(item.numerator / item.denominator, 6)

    aggregate = next(a for a in report.aggregates if a.dimension == "gold_conformance")
    assert aggregate.computable_case_count == 2
    assert aggregate.mean_score is not None


def test_gold_grading_passes_exception_candidates_through(repo_root: Path, tmp_path: Path) -> None:
    """Regression for this module's own first defect: the gold exception-label
    check compares against the run's dry-run exception candidates, and omitting
    them scored recall against an empty list (a grader_defect, caught by
    decomposing the score). Both gold-mapped cases must now conform fully."""

    comparison_dir = _comparison(repo_root, tmp_path, partition="development")
    report, _ = run_condition_grading(
        comparison_dir=comparison_dir,
        split_manifest_path=repo_root / SPLIT_REF,
        out_dir=tmp_path / "grading-dev",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )

    gold_scores = [
        item
        for item in report.scores
        if item.dimension == "gold_conformance" and item.basis == "gold_compared"
    ]
    assert gold_scores, "gold-mapped cases must be graded"
    for item in gold_scores:
        assert item.score == 1.0, (
            f"{item.case_ref}: {item.numerator}/{item.denominator} — an exception-label "
            "recall failure here usually means candidates were not passed to the gold builder"
        )


def test_ranking_cannot_be_edited_into_the_report(repo_root: Path, tmp_path: Path) -> None:
    comparison_dir = _comparison(repo_root, tmp_path)
    _, out_dir = run_condition_grading(
        comparison_dir=comparison_dir,
        split_manifest_path=repo_root / SPLIT_REF,
        out_dir=tmp_path / "grading",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )
    payload = json.loads((out_dir / "condition_grading_report.json").read_text(encoding="utf-8"))
    payload["ranking_supported"] = True

    with pytest.raises(ValueError, match="ranking_supported"):
        ConditionGradingReport.model_validate(payload)


def test_score_must_decompose_into_its_counts() -> None:
    with pytest.raises(ValueError, match="score must equal numerator/denominator"):
        GradedDimensionScore(
            case_ref="x",
            condition_id="c0",
            dimension="run_integrity",
            basis="measured_from_artifacts",
            score=0.9,
            numerator=1,
            denominator=2,
        )


def test_non_computable_dimension_may_not_carry_a_score() -> None:
    with pytest.raises(ValueError, match="may not carry a score"):
        GradedDimensionScore(
            case_ref="x",
            condition_id="c0",
            dimension="gold_conformance",
            basis="not_computable_missing_gold",
            score=1.0,
            numerator=1,
            denominator=1,
            note="missing gold",
        )


def test_non_computable_dimension_must_say_why() -> None:
    with pytest.raises(ValueError, match="must say why"):
        GradedDimensionScore(
            case_ref="x",
            condition_id="c0",
            dimension="gold_conformance",
            basis="not_computable_missing_gold",
        )


def test_aggregate_over_zero_computable_cases_may_not_carry_a_mean() -> None:
    with pytest.raises(ValueError, match="may not carry a mean"):
        ConditionDimensionAggregate(
            condition_id="c0",
            dimension="gold_conformance",
            mean_score=1.0,
            computable_case_count=0,
            total_case_count=5,
        )


def test_missing_run_directory_is_a_failed_check(repo_root: Path, tmp_path: Path) -> None:
    comparison_dir = _comparison(repo_root, tmp_path)
    payload_path = comparison_dir / "condition_comparison_report.json"
    payload = json.loads(payload_path.read_text(encoding="utf-8"))
    payload["records"][0]["run_dir_ref"] = str(tmp_path / "vanished-run-dir")
    payload_path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )

    report, _ = run_condition_grading(
        comparison_dir=comparison_dir,
        split_manifest_path=repo_root / SPLIT_REF,
        out_dir=tmp_path / "grading",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )

    assert report.status == "failed"
    check = next(c for c in report.checks if c.check_id == "all_run_directories_found")
    assert check.status == "failed"
