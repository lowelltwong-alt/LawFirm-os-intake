from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import RustToolLadderAuditReport
from lawfirm_os_intake.rust_tool_ladder import (
    RUST_TOOL_LADDER_AUDIT_REPORT_FILENAME,
    run_rust_tool_ladder_audit,
)
from lawfirm_os_intake.util import load_json, write_json


LADDER_PATH = "config/rust-tool-ladder.json"


def test_rust_tool_ladder_audit_ready(repo_root, tmp_path):
    report, run_dir = run_rust_tool_ladder_audit(
        ladder_path=repo_root / LADDER_PATH,
        out_dir=tmp_path / "rust-tool-ladder",
        repo_root=repo_root,
    )
    persisted = RustToolLadderAuditReport.model_validate(
        load_json(run_dir / RUST_TOOL_LADDER_AUDIT_REPORT_FILENAME)
    )

    assert persisted.status == report.status == "rust_tool_ladder_ready_for_review"
    assert persisted.tool_count == 8
    assert persisted.s0_candidate_count == 2
    assert persisted.s1_shadow_count == 6
    assert persisted.s2_audit_count == 0
    assert persisted.failed_check_count == 0
    assert persisted.rust_replacement_allowed is False
    assert persisted.rust_authoritative_runtime_enabled is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.budget_submission_authorized is False
    assert persisted.matter_opening_authorized is False
    assert persisted.canonical_promotion_authorized is False


def test_rust_tool_ladder_cli_writes_report(repo_root, tmp_path, capsys):
    exit_code = main(
        [
            "audit-rust-tool-ladder",
            "--repo-root",
            str(repo_root),
            "--ladder",
            str(repo_root / LADDER_PATH),
            "--out-dir",
            str(tmp_path / "rust-tool-ladder-cli"),
        ]
    )
    captured = capsys.readouterr()
    persisted = load_json(
        tmp_path / "rust-tool-ladder-cli" / RUST_TOOL_LADDER_AUDIT_REPORT_FILENAME
    )

    assert exit_code == 0
    assert '"status": "rust_tool_ladder_ready_for_review"' in captured.out
    assert persisted["tool_count"] == 8
    assert persisted["rust_replacement_allowed"] is False
    assert persisted["lake_write_performed"] is False


def test_rust_tool_ladder_blocks_forbidden_scope(repo_root, tmp_path):
    ladder = load_json(repo_root / LADDER_PATH)
    ladder["tools"][0]["scope_items"].append("budget_decisioning")
    ladder_path = tmp_path / "rust-tool-ladder-forbidden.json"
    write_json(ladder_path, ladder)

    report, _ = run_rust_tool_ladder_audit(
        ladder_path=ladder_path,
        out_dir=tmp_path / "rust-tool-ladder",
        repo_root=repo_root,
    )

    assert report.status == "blocked_by_rust_tool_ladder"
    assert _check(report, "rust_tool_forbidden_scope_absent").status == "failed"
    assert "rust_tool_ladder_blocked" in report.candidate_exception_lake_labels


def test_rust_tool_ladder_blocks_stage_above_ceiling(repo_root, tmp_path):
    ladder = load_json(repo_root / LADDER_PATH)
    ladder["tools"][0]["stage"] = "s3_cosign"
    ladder["tools"][0]["history"].append(
        {
            "event_id": "test:event:bad-stage",
            "stage": "s3_cosign",
            "recorded_at": "2026-07-06T00:00:00Z",
            "actor": "test",
            "rationale": "Synthetic bad promotion for fail-closed coverage.",
            "evidence_refs": [],
            "human_signoff_ref": None,
        }
    )
    ladder_path = tmp_path / "rust-tool-ladder-stage-above-ceiling.json"
    write_json(ladder_path, ladder)

    report, _ = run_rust_tool_ladder_audit(
        ladder_path=ladder_path,
        out_dir=tmp_path / "rust-tool-ladder",
        repo_root=repo_root,
    )

    assert report.status == "blocked_by_rust_tool_ladder"
    assert _check(report, "rust_tool_stage_within_ceiling").status == "failed"


def test_rust_tool_ladder_blocks_missing_current_stage_gate_evidence(repo_root, tmp_path):
    ladder = load_json(repo_root / LADDER_PATH)
    ladder["tools"][0]["gate_evidence"] = {}
    ladder_path = tmp_path / "rust-tool-ladder-missing-gate-evidence.json"
    write_json(ladder_path, ladder)

    report, _ = run_rust_tool_ladder_audit(
        ladder_path=ladder_path,
        out_dir=tmp_path / "rust-tool-ladder",
        repo_root=repo_root,
    )

    assert report.status == "blocked_by_rust_tool_ladder"
    assert _check(report, "rust_tool_current_stage_gate_evidence_present").status == "failed"


def test_rust_tool_ladder_blocks_s2_without_parity_evidence(repo_root, tmp_path):
    ladder = load_json(repo_root / LADDER_PATH)
    ladder["tools"][0]["stage"] = "s2_audit"
    ladder["tools"][0]["stage_ceiling"] = "s2_audit"
    ladder["tools"][0]["history"].append(
        {
            "event_id": "test:event:s2-without-parity",
            "stage": "s2_audit",
            "recorded_at": "2026-07-06T00:00:00Z",
            "actor": "test",
            "rationale": "Synthetic S2 promotion missing parity artifacts.",
            "evidence_refs": [],
            "human_signoff_ref": None,
        }
    )
    ladder_path = tmp_path / "rust-tool-ladder-s2-missing-parity.json"
    write_json(ladder_path, ladder)

    report, _ = run_rust_tool_ladder_audit(
        ladder_path=ladder_path,
        out_dir=tmp_path / "rust-tool-ladder",
        repo_root=repo_root,
    )

    assert report.status == "blocked_by_rust_tool_ladder"
    checks = {
        check.check_id
        for check in report.checks
        if check.tool_id == "rust-fixture-boundary-checker" and check.status == "failed"
    }
    assert "rust_tool_s2_parity_corpus_exists" in checks
    assert "rust_tool_s2_frozen_goldens_reviewed" in checks


def _check(report, check_id):
    return next(check for check in report.checks if check.check_id == check_id)
