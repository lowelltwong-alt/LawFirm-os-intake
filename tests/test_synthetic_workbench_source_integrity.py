"""Independent source-mutation checks for the fixed synthetic workbenches."""

import json
import shutil

import lawfirm_os_intake.synthetic_actuals_workbench as actuals_workbench
import lawfirm_os_intake.synthetic_budget_configuration_workbench as configuration_workbench
import lawfirm_os_intake.synthetic_budget_input_workbench as input_workbench
from lawfirm_os_intake.synthetic_actuals_workbench import (
    ACTUALS_SOURCE_REF,
    BUDGET_PROPOSAL_REF as ACTUALS_BUDGET_REF,
    build_synthetic_actuals_workbench_report,
)
from lawfirm_os_intake.synthetic_budget_configuration_workbench import (
    SOURCE_SPECS,
    build_synthetic_budget_configuration_workbench_report,
)
from lawfirm_os_intake.synthetic_budget_input_workbench import (
    BUDGET_PROPOSAL_REF as INPUT_BUDGET_REF,
    CONTEXT_SOURCES,
    build_synthetic_budget_input_workbench_report,
)
from lawfirm_os_intake.synthetic_guideline_projection_workbench import (
    SOURCE_REFS,
    build_synthetic_guideline_projection_workbench_report,
)
from lawfirm_os_intake.util import digest_text
from lawfirm_os_intake.synthetic_rate_card_workbench import (
    build_synthetic_rate_card_workbench_report,
)
from lawfirm_os_intake.synthetic_rejection_appeal_workbench import (
    BUDGET_REF as REJECTION_BUDGET_REF,
    BUNDLE_REF,
    build_synthetic_rejection_appeal_workbench_report,
)


FIXED_TIME = "2026-07-15T00:00:00Z"


def _snapshot(repo_root, refs):
    return {source_ref: (repo_root / source_ref).read_bytes() for source_ref in sorted(set(refs))}


def _copy_sources(repo_root, target_root, refs):
    for source_ref in refs:
        source = repo_root / source_ref
        target = target_root / source_ref
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)


def test_fixed_synthetic_workbenches_do_not_mutate_declared_source_bytes(repo_root):
    refs = {
        ACTUALS_BUDGET_REF,
        ACTUALS_SOURCE_REF,
        INPUT_BUDGET_REF,
        REJECTION_BUDGET_REF,
        BUNDLE_REF,
        *[source_ref for _, _, source_ref, _ in CONTEXT_SOURCES],
        *[source_ref for _, _, source_ref in SOURCE_REFS],
        *[source_ref for _, source_ref, _ in SOURCE_SPECS],
    }
    before = _snapshot(repo_root, refs)

    reports = [
        build_synthetic_actuals_workbench_report(repo_root=repo_root, generated_at=FIXED_TIME),
        build_synthetic_budget_input_workbench_report(repo_root=repo_root, generated_at=FIXED_TIME),
        build_synthetic_guideline_projection_workbench_report(
            repo_root=repo_root, generated_at=FIXED_TIME
        ),
        build_synthetic_rejection_appeal_workbench_report(
            repo_root=repo_root, generated_at=FIXED_TIME
        ),
        build_synthetic_budget_configuration_workbench_report(
            repo_root=repo_root, generated_at=FIXED_TIME
        ),
        build_synthetic_rate_card_workbench_report(
            repo_root / "config/synthetic-carrier-rate-card.yaml",
            repo_root=repo_root,
            generated_at=FIXED_TIME,
        ),
    ]

    assert all("ready_for_review" in report.status for report in reports)
    assert _snapshot(repo_root, refs) == before
    assert all(report.external_writes_performed is False for report in reports)
    assert all(report.lake_write_performed is False for report in reports)
    assert all(report.sqlite_write_performed is False for report in reports)


def test_actuals_workbench_binds_hash_and_math_to_one_immutable_snapshot(
    tmp_path, repo_root, monkeypatch
):
    candidate_root = tmp_path / "actuals-candidate"
    _copy_sources(repo_root, candidate_root, [ACTUALS_BUDGET_REF, ACTUALS_SOURCE_REF])
    actuals_path = candidate_root / ACTUALS_SOURCE_REF
    captured_text = actuals_path.read_text(encoding="utf-8")
    original_comparison = actuals_workbench.build_budget_actual_comparison_report

    def compare_then_mutate(*args, **kwargs):
        comparison = original_comparison(*args, **kwargs)
        payload = json.loads(captured_text)
        payload["actuals_by_code"]["L110"]["fees"] += 100
        actuals_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        return comparison

    monkeypatch.setattr(
        actuals_workbench, "build_budget_actual_comparison_report", compare_then_mutate
    )
    report = actuals_workbench.build_synthetic_actuals_workbench_report(
        repo_root=candidate_root, generated_at=FIXED_TIME
    )

    assert report.status == "blocked_by_synthetic_actuals_workbench"
    assert report.comparison.total_actual == 60350.0
    assert report.actuals_source_sha256 == digest_text(captured_text)
    assert report.actuals_source_sha256 != digest_text(actuals_path.read_text(encoding="utf-8"))
    assert "source_inputs_unchanged_during_build" in {
        check.check_id for check in report.checks if check.status == "failed"
    }


def test_budget_input_workbench_blocks_source_mutation_during_build(
    tmp_path, repo_root, monkeypatch
):
    candidate_root = tmp_path / "input-candidate"
    source_refs = [INPUT_BUDGET_REF, *[source_ref for _, _, source_ref, _ in CONTEXT_SOURCES]]
    _copy_sources(repo_root, candidate_root, source_refs)
    original_load_json = input_workbench.load_json

    def load_json_then_mutate(path):
        payload = original_load_json(path)
        rate_card_path = candidate_root / "config/synthetic-carrier-rate-card.yaml"
        rate_card_path.write_text(
            rate_card_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )
        return payload

    monkeypatch.setattr(input_workbench, "load_json", load_json_then_mutate)
    report = input_workbench.build_synthetic_budget_input_workbench_report(
        repo_root=candidate_root, generated_at=FIXED_TIME
    )

    assert report.status == "blocked_by_synthetic_budget_input_workbench"
    assert "source_inputs_unchanged_during_build" in {
        check.check_id for check in report.checks if check.status == "failed"
    }


def test_budget_configuration_workbench_blocks_source_mutation_during_build(
    tmp_path, repo_root, monkeypatch
):
    candidate_root = tmp_path / "configuration-candidate"
    _copy_sources(repo_root, candidate_root, [source_ref for _, source_ref, _ in SOURCE_SPECS])
    original_entries = configuration_workbench._entries

    def entries_then_mutate(loaded):
        guideline_path = candidate_root / "config/synthetic-carrier-guideline.yaml"
        guideline_path.write_text(
            guideline_path.read_text(encoding="utf-8") + "\n", encoding="utf-8"
        )
        return original_entries(loaded)

    monkeypatch.setattr(configuration_workbench, "_entries", entries_then_mutate)
    report = configuration_workbench.build_synthetic_budget_configuration_workbench_report(
        repo_root=candidate_root, generated_at=FIXED_TIME
    )

    assert report.status == "blocked_by_synthetic_budget_configuration_workbench"
    assert "source_inputs_unchanged_during_build" in {
        check.check_id for check in report.checks if check.status == "failed"
    }
