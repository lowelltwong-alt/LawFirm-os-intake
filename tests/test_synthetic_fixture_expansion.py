from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetActualsSource,
    IntakeLocalCloseoutCheck,
    IntakeLocalCloseoutReport,
    IntakeVerticalReadinessArtifactCheck,
    IntakeVerticalReadinessAuditReport,
    IntakeVerticalReadinessSliceStatus,
    SyntheticFixtureExpansionManifest,
    SyntheticFixtureExpansionReport,
)
from lawfirm_os_intake.remaining_roadmap import build_remaining_roadmap_report
from lawfirm_os_intake.synthetic_fixture_expansion import (
    run_synthetic_fixture_expansion_audit,
)
from lawfirm_os_intake.util import load_json, write_json


def _remaining_roadmap_path(tmp_path):
    readiness = IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-fixture-expansion-fixture",
        status="ready_for_pr_review_external_adoption_required",
        review_readiness="ready_for_human_pr_review_not_auto_marked",
        source_owner_handoff_report_ref="learning_owner_handoff_report.json",
        source_budget_event_lake_bundle_report_ref=(
            "budget_event_lake_admission_bundle_report.json"
        ),
        source_budget_calibration_readiness_report_ref=("budget_calibration_readiness_report.json"),
        source_budget_fixture_update_review_report_ref=("budget_fixture_update_review_report.json"),
        source_budget_fixture_update_pr_package_report_ref=(
            "budget_fixture_update_pr_package_report.json"
        ),
        total_slice_count=1,
        implemented_slice_count=1,
        slices=[
            IntakeVerticalReadinessSliceStatus(
                slice_id=1,
                title="Synthetic fixture expansion fixture",
                status="implemented_local_candidate",
                requirement_summary="Fixture proves synthetic fixture expansion behavior.",
                proof_artifact_refs=[
                    "examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json"
                ],
                target_owner_repos=["LawFirm-os-intake"],
                remaining_external_actions=["Owner adoption remains external."],
            )
        ],
        artifact_checks=[
            IntakeVerticalReadinessArtifactCheck(
                check_id="synthetic_fixture_expansion_readiness_check",
                status="passed",
                artifact_ref="examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json",
                message="Synthetic fixture expansion readiness proof.",
            )
        ],
        required_external_adoption_actions=[
            "Semantic Substrate owner review for promoted contracts.",
            "Orchestrator owner review for runtime workflow.",
            "Exception Lake owner review for append-only storage.",
        ],
        external_adoption_target_repos=[
            "LawFirm-os-semantic-substrate",
            "LawFirm-os-orchestrator",
            "LawFirm-os-exceptions-lake-runtime",
        ],
        generated_at="2026-06-29T00:00:00Z",
    )
    closeout = IntakeLocalCloseoutReport(
        closeout_report_id="intake-local-closeout-fixture-expansion-fixture",
        status="intake_local_closeout_ready_manual_actions_required",
        observed_pr_number=7,
        observed_pr_url="https://github.com/lowelltwong-alt/LawFirm-os-intake/pull/7",
        observed_pr_state="draft",
        source_readiness_audit_report_id=readiness.audit_report_id,
        source_readiness_audit_report_ref="intake_vertical_readiness_audit_report.json",
        source_readiness_status=readiness.status,
        source_review_readiness=readiness.review_readiness,
        source_pr_review_checklist_id="pr-review-checklist-fixture",
        source_pr_review_checklist_ref="pr_review_checklist.json",
        source_pr_review_checklist_status="ready_for_human_pr_review",
        source_pr_review_checklist_recommendation=("eligible_for_human_to_mark_ready_after_review"),
        source_owner_adoption_report_id="owner-adoption-fixture",
        source_owner_adoption_report_ref="cross_repo_owner_adoption_report.json",
        source_owner_adoption_status="owner_adoption_packets_ready",
        source_owner_issue_draft_report_id="owner-issue-draft-fixture",
        source_owner_issue_draft_report_ref="cross_repo_owner_issue_draft_report.json",
        source_owner_issue_draft_status="issue_drafts_ready_for_manual_creation",
        check_count=1,
        passed_check_count=1,
        blocking_check_count=0,
        checks=[
            IntakeLocalCloseoutCheck(
                check_id="synthetic_fixture_expansion_closeout_check",
                status="passed",
                message="Synthetic closeout proof.",
                artifact_refs=["intake_local_closeout_report.json"],
            )
        ],
        manual_actions_remaining=[
            "PR remains draft and owner adoption remains manual.",
        ],
        generated_artifact_refs=["intake_local_closeout_report.json"],
        generated_at="2026-06-29T00:00:00Z",
    )
    roadmap = build_remaining_roadmap_report(
        readiness=readiness,
        readiness_ref="intake_vertical_readiness_audit_report.json",
        closeout=closeout,
        closeout_ref="intake_local_closeout_report.json",
    )
    return write_json(
        tmp_path / "remaining-roadmap" / "remaining_roadmap_report.json",
        roadmap.model_dump(mode="json"),
    )


def _manifest_path(repo_root):
    return repo_root / "examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json"


def test_synthetic_fixture_expansion_manifest_is_ready_for_review(tmp_path, repo_root):
    roadmap_path = _remaining_roadmap_path(tmp_path)

    report, run_dir = run_synthetic_fixture_expansion_audit(
        remaining_roadmap_report_path=roadmap_path,
        manifest_path=_manifest_path(repo_root),
        repo_root=repo_root,
        out_dir=tmp_path / "fixture-expansion",
    )
    persisted = SyntheticFixtureExpansionReport.model_validate(
        load_json(run_dir / "synthetic_fixture_expansion_report.json")
    )

    assert persisted.fixture_expansion_report_id == report.fixture_expansion_report_id
    assert persisted.status == "synthetic_fixture_expansion_ready_for_review"
    assert persisted.required_family_count == 4
    assert persisted.holdout_count == 7
    assert persisted.family_counts == {
        "ambiguous_roles": 2,
        "budget_driver_edges": 2,
        "carrier_rejection_variants": 2,
        "missing_actuals": 1,
    }
    assert persisted.missing_required_families == []
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.calibration_approved is False
    assert persisted.fixture_files_mutated_by_audit is False
    assert persisted.github_write_performed is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes = (run_dir / "synthetic_fixture_expansion_report.md").read_text(encoding="utf-8")
    assert "ambiguous_roles: 2" in notes
    assert "budget_driver_edges: 2" in notes
    assert "carrier_rejection_variants: 2" in notes
    assert "missing_actuals: 1" in notes
    assert "does not approve calibration" in notes


def test_synthetic_fixture_expansion_blocks_missing_required_family(
    tmp_path,
    repo_root,
):
    roadmap_path = _remaining_roadmap_path(tmp_path)
    manifest = SyntheticFixtureExpansionManifest.model_validate(
        load_json(_manifest_path(repo_root))
    )
    reduced_manifest = manifest.model_copy(
        update={
            "manifest_id": "synthetic-fixture-expansion.missing-family.fixture",
            "required_families": [
                "ambiguous_roles",
                "missing_actuals",
                "carrier_rejection_variants",
            ],
            "holdouts": [
                holdout for holdout in manifest.holdouts if holdout.family != "budget_driver_edges"
            ],
        }
    )
    reduced_manifest_path = write_json(
        tmp_path / "fixture-expansion-missing-family.json",
        reduced_manifest.model_dump(mode="json"),
    )

    report, _ = run_synthetic_fixture_expansion_audit(
        remaining_roadmap_report_path=roadmap_path,
        manifest_path=reduced_manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "fixture-expansion-blocked",
    )

    assert report.status == "blocked_by_fixture_expansion_evidence"
    assert any(
        check.check_id == "required_holdout_families_declared" and check.status == "failed"
        for check in report.checks
    )
    assert report.calibration_approved is False
    assert report.external_writes_performed is False


def test_synthetic_fixture_expansion_cli(tmp_path, repo_root, capsys):
    roadmap_path = _remaining_roadmap_path(tmp_path)

    exit_code = main(
        [
            "audit-synthetic-fixture-expansion",
            "--remaining-roadmap-report",
            str(roadmap_path),
            "--manifest",
            str(_manifest_path(repo_root)),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "fixture-expansion-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "synthetic_fixture_expansion_ready_for_review"' in captured.out
    assert '"required_family_count": 4' in captured.out
    assert '"holdout_count": 7' in captured.out
    assert '"calibration_approved": false' in captured.out
    assert '"external_writes_performed": false' in captured.out
    assert (
        tmp_path / "fixture-expansion-cli" / "synthetic_fixture_expansion_report.json"
    ).is_file()


def test_missing_actuals_holdout_fixture_is_valid_synthetic_source(repo_root):
    actuals = BudgetActualsSource.model_validate(
        load_json(repo_root / "examples/synthetic/actuals/medmal-missing-actuals.json")
    )

    assert actuals.actuals_source_id == "synthetic-medmal-missing-actuals.v0_1"
    assert actuals.data_origin == "synthetic"
    assert actuals.actuals_by_phase == {}
    assert actuals.actuals_by_code == {}
    assert actuals.billing_connector_read_performed is False
    assert actuals.billing_connector_write_performed is False
    assert actuals.external_writes_performed is False


def test_budget_driver_edge_holdout_fixture_is_valid_synthetic_source(repo_root):
    fixture = load_json(
        repo_root / "examples/synthetic/budget-drivers/medmal-driver-edge-cases.json"
    )

    assert fixture["fixture_id"] == "synthetic-medmal-budget-driver-edge-cases.v0_1"
    assert fixture["data_origin"] == "synthetic"
    assert fixture["contains_real_client_data"] is False
    assert fixture["contains_real_matter_data"] is False
    assert fixture["contains_privileged_data"] is False
    assert {case["case_id"]: case["expected_signal"] for case in fixture["driver_cases"]} == {
        "soft-clear-favorable": "lower_intensity_projection",
        "catastrophic-contested-plaintiff-friendly": "higher_intensity_projection",
        "unknown-coverage-posture": "unknown_driver_visible_not_observed_fact",
    }
    assert any("not observed facts" in signal for signal in fixture["expected_signals"])
    assert fixture["calibration_approved"] is False
    assert fixture["external_writes_performed"] is False
    assert fixture["silent_learning_performed"] is False
