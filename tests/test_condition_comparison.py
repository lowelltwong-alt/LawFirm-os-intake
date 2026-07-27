"""The comparison harness must refuse to overclaim and must refuse to spend.

Two properties carry the weight here:

* A single-condition run is a **baseline**, not a comparison. If the report can
  be read as comparative when only one condition ran, the harness is a liability
  rather than evidence.
* The budget ceiling must stop an over-budget configuration *before* anything
  executes, and the zero-spend claim must be corroborated by each run's own
  artifact rather than by the spec that requested it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lawfirm_os_intake.condition_comparison import (
    BudgetCeilingExceeded,
    assert_within_budget_ceiling,
    load_condition_specs,
    run_condition_comparison,
)
from lawfirm_os_intake.models import ConditionComparisonReport, EvaluationConditionSpec

SPLIT_REF = "examples/synthetic/evaluation/intake-evaluation-split.json"
SPECS_REF = "examples/synthetic/evaluation/intake-condition-specs.json"


def _specs(repo_root: Path) -> list[EvaluationConditionSpec]:
    return load_condition_specs(repo_root / SPECS_REF)


def test_baseline_runs_over_holdout_without_spending(repo_root: Path, tmp_path: Path) -> None:
    report, out_dir = run_condition_comparison(
        split_manifest_path=repo_root / SPLIT_REF,
        conditions=_specs(repo_root),
        out_dir=tmp_path / "comparison",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )

    assert report.status == "passed", [c for c in report.checks if c.status == "failed"]
    assert report.case_count >= 1
    assert report.completed_run_count == report.case_count
    assert report.failed_run_count == 0
    assert report.provider_calls_performed == 0
    assert report.max_model_calls_permitted == 0
    assert all(record.partition == "holdout" for record in report.records)

    persisted = json.loads(
        (out_dir / "condition_comparison_report.json").read_text(encoding="utf-8")
    )
    assert persisted["external_writes_performed"] is False
    assert persisted["lake_write_performed"] is False
    assert (out_dir / "condition_comparison_report.md").is_file()
    lines = (out_dir / "condition_run_records.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == len(report.records)


def test_single_condition_does_not_support_a_comparative_claim(
    repo_root: Path, tmp_path: Path
) -> None:
    """The honesty property: one condition is a baseline, and the report says so."""

    report, _ = run_condition_comparison(
        split_manifest_path=repo_root / SPLIT_REF,
        conditions=_specs(repo_root),
        out_dir=tmp_path / "comparison",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )

    assert len(report.condition_ids) == 1
    assert report.comparative_claim_supported is False
    assert "baseline, not a comparison" in report.comparative_claim_note
    assert report.pair_deltas == []


def test_report_cannot_claim_comparison_it_did_not_make(repo_root: Path, tmp_path: Path) -> None:
    """Hand-editing the flag must be rejected by the model, not merely discouraged."""

    report, out_dir = run_condition_comparison(
        split_manifest_path=repo_root / SPLIT_REF,
        conditions=_specs(repo_root),
        out_dir=tmp_path / "comparison",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )
    payload = json.loads((out_dir / "condition_comparison_report.json").read_text(encoding="utf-8"))
    payload["comparative_claim_supported"] = True

    with pytest.raises(ValueError, match="comparative_claim_supported"):
        ConditionComparisonReport.model_validate(payload)

    assert report.comparative_claim_supported is False


def test_budget_ceiling_refuses_before_anything_runs(repo_root: Path, tmp_path: Path) -> None:
    """An over-budget configuration must cost nothing to discover."""

    profile = "context/synthetic-profiles/insurance-defense.yaml"
    hungry = EvaluationConditionSpec(
        condition_id="c1-retrieval-assisted",
        description="hypothetical condition that would call a provider",
        adapter="structured-model",
        practice_profile_ref=profile,
        model_calls_permitted=3,
        config_digest="sha256:" + "a" * 64,
    )

    with pytest.raises(BudgetCeilingExceeded, match="exceeding the ceiling"):
        assert_within_budget_ceiling([hungry], case_count=5, max_model_calls=0)

    out_dir = tmp_path / "never-runs"
    with pytest.raises(BudgetCeilingExceeded):
        run_condition_comparison(
            split_manifest_path=repo_root / SPLIT_REF,
            conditions=[hungry],
            out_dir=out_dir,
            repo_root=repo_root,
            max_model_calls=0,
        )
    # Nothing executed, so no run tree exists.
    assert not (out_dir / "runs").exists()


def test_budget_ceiling_admits_a_deliberately_raised_ceiling(repo_root: Path) -> None:
    profile = "context/synthetic-profiles/insurance-defense.yaml"
    hungry = EvaluationConditionSpec(
        condition_id="c1-retrieval-assisted",
        description="hypothetical",
        adapter="structured-model",
        practice_profile_ref=profile,
        model_calls_permitted=2,
        config_digest="sha256:" + "b" * 64,
    )
    assert assert_within_budget_ceiling([hungry], case_count=5, max_model_calls=10) == 10


def test_deterministic_condition_may_not_permit_model_calls() -> None:
    """A deterministic condition makes no provider call by construction, so a
    spec claiming otherwise is incoherent rather than merely over-budget."""

    with pytest.raises(ValueError, match="deterministic condition may not permit model calls"):
        EvaluationConditionSpec(
            condition_id="incoherent",
            description="deterministic yet permitted to call a model",
            adapter="deterministic",
            practice_profile_ref="context/synthetic-profiles/insurance-defense.yaml",
            model_calls_permitted=1,
            config_digest="sha256:" + "c" * 64,
        )


def test_records_are_keyed_on_case_and_condition(repo_root: Path, tmp_path: Path) -> None:
    report, _ = run_condition_comparison(
        split_manifest_path=repo_root / SPLIT_REF,
        conditions=_specs(repo_root),
        out_dir=tmp_path / "comparison",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )
    keys = [(record.case_ref, record.condition_id) for record in report.records]
    assert len(keys) == len(set(keys)), "each (case, condition) pair must appear once"
    for record in report.records:
        assert record.case_digest.startswith("sha256:")
        assert record.outcome_projection_digest.startswith("sha256:")
        assert record.provider_call_performed is False


def test_scoring_the_development_partition_is_possible_but_labelled(
    repo_root: Path, tmp_path: Path
) -> None:
    """Debugging against development cases must remain possible, but the report
    records which partition it scored so the distinction survives."""

    report, _ = run_condition_comparison(
        split_manifest_path=repo_root / SPLIT_REF,
        conditions=_specs(repo_root),
        out_dir=tmp_path / "dev-comparison",
        repo_root=repo_root,
        scored_partition="development",
        generated_at="2026-07-27T00:00:00Z",
    )
    assert report.scored_partition == "development"
    assert all(record.partition == "development" for record in report.records)
