import json

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import PRMergeOrderReadinessPacket, PRMergeOrderSnapshot
from lawfirm_os_intake.pr_merge_order_readiness import (
    build_pr_merge_order_readiness_packet,
    run_pr_merge_order_readiness_packet,
)
from lawfirm_os_intake.util import load_json, write_json


def _snapshot_path(repo_root):
    return repo_root / "examples" / "synthetic" / "pr-merge-order" / "open-draft-prs-20260630.json"


def test_pr_merge_order_recommends_gap_first_then_depth_audit(tmp_path, repo_root):
    report, run_dir = run_pr_merge_order_readiness_packet(
        pr_snapshot_path=_snapshot_path(repo_root),
        out_dir=tmp_path / "pr-merge-order",
    )
    persisted = PRMergeOrderReadinessPacket.model_validate(
        load_json(run_dir / "pr_merge_order_readiness_packet.json")
    )

    assert persisted.packet_id == report.packet_id
    assert persisted.status == "pr_merge_order_ready_manual_queue_required"
    assert persisted.strategy == "gap_first_then_depth_audit"
    assert persisted.pr_count == 4
    assert persisted.ready_queue_count == 4
    assert persisted.blocked_pr_count == 0
    assert persisted.recommended_merge_order_pr_numbers == [16, 18, 17, 19]
    assert persisted.shared_surface_count == 4
    assert persisted.high_risk_shared_surface_count == 4
    assert all(check.status in {"passed", "warning"} for check in persisted.checks)
    assert any(
        check.check_id == "shared_surfaces_require_rebase_attention" and check.status == "warning"
        for check in persisted.checks
    )
    assert persisted.ready_for_review_marked is False
    assert persisted.merge_performed is False
    assert persisted.github_write_performed is False
    assert persisted.github_issue_created is False
    assert persisted.github_pr_created is False
    assert persisted.sibling_repo_write_performed is False
    assert persisted.promotion_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    by_pr = {item.pr_number: item for item in persisted.recommendations}
    assert by_pr[16].recommended_sequence_role == "fixture_gap_closer"
    assert by_pr[18].recommended_sequence_role == "fixture_gap_closer"
    assert by_pr[17].recommended_sequence_role == "fixture_role_expander"
    assert by_pr[19].recommended_sequence_role == "audit_verifier"
    assert by_pr[19].recommended_after_pr_numbers == [16, 18, 17]
    assert "examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json" in (
        by_pr[19].shared_surface_refs
    )

    notes = (run_dir / "pr_merge_order_readiness_packet.md").read_text(encoding="utf-8")
    assert "Recommended order: #16, #18, #17, #19" in notes
    assert "does not mark any PR ready" in notes


def test_pr_merge_order_fails_closed_when_pr_checks_not_green(tmp_path, repo_root):
    data = load_json(_snapshot_path(repo_root))
    for pr in data["prs"]:
        if pr["pr_number"] == 18:
            pr["checks_conclusion"] = "failure"
            pr["successful_status_check_count"] = 3
    snapshot_path = write_json(tmp_path / "blocked-pr-snapshot.json", data)

    report = build_pr_merge_order_readiness_packet(
        snapshot=PRMergeOrderSnapshot.model_validate(load_json(snapshot_path)),
        snapshot_ref=str(snapshot_path),
    )

    assert report.status == "blocked_by_pr_merge_order_evidence"
    assert report.ready_queue_count == 3
    assert report.blocked_pr_count == 1
    assert report.blocked_pr_numbers == [18]
    assert any(
        check.check_id == "pr_snapshot_mergeable_and_checks_green"
        and check.status == "failed"
        and "PR #18" in check.blocking_refs
        for check in report.checks
    )
    assert report.ready_for_review_marked is False
    assert report.merge_performed is False
    assert report.github_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_pr_merge_order_cli_writes_packet(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "plan-pr-merge-order",
            "--pr-snapshot",
            str(_snapshot_path(repo_root)),
            "--out-dir",
            str(tmp_path / "pr-merge-order-cli"),
        ]
    )
    captured = capsys.readouterr()
    stdout = json.loads(captured.out)

    assert exit_code == 0
    assert stdout["status"] == "pr_merge_order_ready_manual_queue_required"
    assert stdout["recommended_merge_order_pr_numbers"] == [16, 18, 17, 19]
    assert stdout["shared_surface_count"] == 4
    assert stdout["ready_for_review_marked"] is False
    assert stdout["merge_performed"] is False
    assert stdout["github_write_performed"] is False
    assert stdout["silent_learning_performed"] is False
    assert (tmp_path / "pr-merge-order-cli" / "pr_merge_order_readiness_packet.json").is_file()
