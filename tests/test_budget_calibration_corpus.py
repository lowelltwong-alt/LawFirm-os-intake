from lawfirm_os_intake.budget_calibration_corpus import (
    build_budget_calibration_corpus_report,
    run_budget_calibration_corpus_audit,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import BudgetCalibrationCorpusReport
from lawfirm_os_intake.util import load_json, write_json


def test_budget_calibration_corpus_audit_classifies_synthetic_fixtures(repo_root):
    report = build_budget_calibration_corpus_report(
        repo_root / "examples/synthetic",
        repo_root=repo_root,
    )

    assert report.status == "synthetic_corpus_ready_for_review"
    assert report.artifact_count > 0
    assert report.eligible_artifact_count > 0
    assert report.blocked_artifact_count == 0
    assert report.artifact_kind_counts["budget_review_fixture"] >= 1
    assert report.artifact_kind_counts["actuals_fixture"] >= 1
    assert report.artifact_kind_counts["carrier_rejection_fixture"] >= 1
    assert report.artifact_kind_counts["learning_shadow_eval_fixture"] >= 1
    assert {
        "outcome_evidence_fixture",
        "shadow_eval_fixture",
        "reviewed_baseline_fixture",
    } <= set(report.calibration_role_counts)
    assert all(
        artifact.eligibility != "blocked_real_or_privileged_data" for artifact in report.artifacts
    )
    assert report.calibration_applied is False
    assert report.profile_mutation_performed is False
    assert report.template_mutation_performed is False
    assert report.budget_mutation_performed is False
    assert report.carrier_guideline_mutation_performed is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_budget_calibration_corpus_audit_blocks_real_or_mutating_fixture(tmp_path):
    corpus = tmp_path / "corpus"
    real_fixture = write_json(
        corpus / "actuals" / "real-actuals.json",
        {
            "schema_version": "0.1",
            "actuals_source_id": "real-actuals",
            "data_origin": "production",
            "contains_real_client_data": True,
            "external_writes_performed": True,
        },
    )

    report = build_budget_calibration_corpus_report(corpus, repo_root=tmp_path)

    assert report.status == "blocked_real_or_privileged_data"
    assert report.blocked_artifact_count == 1
    artifact = report.artifacts[0]
    assert artifact.artifact_ref == real_fixture.relative_to(tmp_path).as_posix()
    assert artifact.eligibility == "blocked_real_or_privileged_data"
    assert "data_origin=production" in artifact.scope_failures
    assert "contains_real_client_data=true" in artifact.scope_failures
    assert "external_writes_performed" in artifact.boundary_failures


def test_budget_calibration_corpus_cli_writes_report(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "audit-budget-calibration-corpus",
            "--corpus-root",
            str(repo_root / "examples/synthetic"),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "budget-corpus"),
        ]
    )
    captured = capsys.readouterr()
    report_path = tmp_path / "budget-corpus" / "budget_calibration_corpus_report.json"
    notes_path = tmp_path / "budget-corpus" / "budget_calibration_corpus_report.md"
    report = BudgetCalibrationCorpusReport.model_validate(load_json(report_path))

    assert exit_code == 0
    assert report.status == "synthetic_corpus_ready_for_review"
    assert '"calibration_applied": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert "does not calibrate, mutate, promote" in notes_path.read_text(encoding="utf-8")


def test_budget_calibration_corpus_runner_persists_candidate_report(tmp_path, repo_root):
    report, run_dir = run_budget_calibration_corpus_audit(
        corpus_root=repo_root / "examples/synthetic",
        repo_root=repo_root,
        out_dir=tmp_path / "budget-corpus-runner",
    )
    persisted = BudgetCalibrationCorpusReport.model_validate(
        load_json(run_dir / "budget_calibration_corpus_report.json")
    )

    assert persisted.corpus_report_id == report.corpus_report_id
    assert persisted.candidate_only is True
    assert persisted.non_authoritative is True
    assert persisted.synthetic_only is True
