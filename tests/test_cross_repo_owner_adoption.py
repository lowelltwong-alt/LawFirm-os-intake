from lawfirm_os_intake.cli import main
from lawfirm_os_intake.cross_repo_owner_adoption import run_cross_repo_owner_adoption
from lawfirm_os_intake.models import (
    CrossRepoOwnerAdoptionReport,
    IntakeVerticalReadinessArtifactCheck,
    IntakeVerticalReadinessAuditReport,
    IntakeVerticalReadinessSliceStatus,
)
from lawfirm_os_intake.pr_review_checklist import run_pr_review_checklist
from lawfirm_os_intake.util import load_json, write_json


REQUIRED_TARGET_REPOS = {
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
    "LawFirm-os-skills-registry",
    "LawFirm-os-legal-knowledge-runtime",
}


def _readiness_report_path(tmp_path, *, ready=True):
    slice_status = IntakeVerticalReadinessSliceStatus(
        slice_id=1,
        title="Synthetic owner adoption fixture",
        status="implemented_local_candidate",
        requirement_summary="Fixture proves owner adoption packet behavior.",
        proof_artifact_refs=["promotion/cross_repo_promotion_package.json"],
        target_owner_repos=["LawFirm-os-intake"],
        remaining_external_actions=["Owner adoption remains required."],
    )
    artifact_check = IntakeVerticalReadinessArtifactCheck(
        check_id="synthetic_owner_adoption_check",
        status=("passed" if ready else "failed"),
        artifact_ref="promotion/cross_repo_promotion_package.json",
        message=(
            "Synthetic owner adoption proof." if ready else "Synthetic owner adoption blocker."
        ),
    )
    report = IntakeVerticalReadinessAuditReport(
        audit_report_id="intake-vertical-readiness-owner-adoption-fixture",
        status=(
            "ready_for_pr_review_external_adoption_required"
            if ready
            else "blocked_missing_or_failed_learning_artifacts"
        ),
        review_readiness=(
            "ready_for_human_pr_review_not_auto_marked"
            if ready
            else "not_ready_learning_artifact_chain_blocked"
        ),
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
        slices=[slice_status],
        artifact_checks=[artifact_check],
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
        generated_at="2026-06-26T00:00:00Z",
    )
    return write_json(
        tmp_path / "readiness" / "intake_vertical_readiness_audit_report.json",
        report.model_dump(mode="json"),
    )


def _checklist_path(tmp_path, *, ready=True):
    readiness_path = _readiness_report_path(tmp_path, ready=ready)
    _, checklist_dir = run_pr_review_checklist(
        readiness_audit_report_path=readiness_path,
        out_dir=tmp_path
        / ("pr-review-checklist-ready" if ready else "pr-review-checklist-blocked"),
    )
    return checklist_dir / "pr_review_checklist.json", readiness_path


def test_cross_repo_owner_adoption_groups_all_target_repos_without_writes(
    tmp_path,
    repo_root,
):
    checklist_path, readiness_path = _checklist_path(tmp_path, ready=True)

    report, run_dir = run_cross_repo_owner_adoption(
        promotion_package_path=repo_root / "promotion/cross_repo_promotion_package.json",
        readiness_audit_report_path=readiness_path,
        pr_review_checklist_path=checklist_path,
        out_dir=tmp_path / "owner-adoption",
    )
    persisted = CrossRepoOwnerAdoptionReport.model_validate(
        load_json(run_dir / "cross_repo_owner_adoption_report.json")
    )

    assert persisted.owner_adoption_report_id == report.owner_adoption_report_id
    assert persisted.status == "owner_adoption_packets_ready"
    assert persisted.packet_count == persisted.ready_packet_count == 5
    assert persisted.blocked_packet_count == 0
    assert persisted.proposal_count == 9
    assert set(persisted.target_repos) == REQUIRED_TARGET_REPOS
    assert set(packet.target_repo for packet in persisted.packets) == REQUIRED_TARGET_REPOS
    assert all(packet.status == "ready_for_owner_review" for packet in persisted.packets)
    assert all(packet.required_owner_actions for packet in persisted.packets)
    assert all(packet.acceptance_checks for packet in persisted.packets)
    assert all(packet.red_team_notes for packet in persisted.packets)
    assert all((repo_root / ref).exists() for ref in persisted.packet_output_refs)
    assert (run_dir / "cross_repo_owner_adoption_packets.jsonl").is_file()
    assert persisted.github_issue_created is False
    assert persisted.github_pr_created is False
    assert persisted.github_write_performed is False
    assert persisted.sibling_repo_write_performed is False
    assert persisted.promotion_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes_text = (run_dir / "cross_repo_owner_adoption_report.md").read_text(encoding="utf-8")
    assert "LawFirm-os-semantic-substrate" in notes_text
    assert "LawFirm-os-orchestrator" in notes_text
    assert "does not create issues" in notes_text


def test_cross_repo_owner_adoption_blocks_when_pr_review_is_not_ready(
    tmp_path,
    repo_root,
):
    checklist_path, readiness_path = _checklist_path(tmp_path, ready=False)

    report, _ = run_cross_repo_owner_adoption(
        promotion_package_path=repo_root / "promotion/cross_repo_promotion_package.json",
        readiness_audit_report_path=readiness_path,
        pr_review_checklist_path=checklist_path,
        out_dir=tmp_path / "owner-adoption-blocked",
    )

    assert report.status == "blocked_by_pr_readiness"
    assert report.ready_packet_count == 0
    assert report.blocked_packet_count == 5
    assert all(packet.status == "blocked_by_pr_readiness" for packet in report.packets)
    assert report.github_issue_created is False
    assert report.github_write_performed is False
    assert report.sibling_repo_write_performed is False


def test_cross_repo_owner_adoption_cli(tmp_path, repo_root, capsys):
    checklist_path, readiness_path = _checklist_path(tmp_path, ready=True)

    exit_code = main(
        [
            "build-cross-repo-owner-adoption",
            "--promotion-package",
            str(repo_root / "promotion/cross_repo_promotion_package.json"),
            "--readiness-audit-report",
            str(readiness_path),
            "--pr-review-checklist",
            str(checklist_path),
            "--out-dir",
            str(tmp_path / "owner-adoption-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "owner_adoption_packets_ready"' in captured.out
    assert '"packet_count": 5' in captured.out
    assert '"proposal_count": 9' in captured.out
    assert '"github_write_performed": false' in captured.out
    assert (tmp_path / "owner-adoption-cli" / "cross_repo_owner_adoption_report.json").is_file()
