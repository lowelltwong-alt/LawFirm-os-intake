import shutil

import pytest
import yaml

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import SkillsRegistrySpecialistReviewReport
from lawfirm_os_intake.skills_registry_specialist_review import (
    run_skills_registry_specialist_review,
)
from lawfirm_os_intake.util import load_json, load_jsonl


EXPECTED_WORKERS = {
    "source-reader",
    "party-role-extractor",
    "matter-router",
    "deadline-gap-extractor",
    "evidence-critic",
    "budget-planner",
    "frontier-adjudicator",
}


def _copy_skill_surface(tmp_path, repo_root):
    target = tmp_path / "skill-surface"
    for directory in ("agents", "harnesses", "prompts", "schemas"):
        shutil.copytree(repo_root / directory, target / directory)
    shutil.copy(repo_root / "skill-agent-manifest.json", target / "skill-agent-manifest.json")
    return target


def _assert_no_authority_flags(report):
    assert report.skill_promoted is False
    assert report.skill_trust_record_created is False
    assert report.dynamic_agent_created is False
    assert report.model_provider_enabled is False
    assert report.real_data_approved is False
    assert report.external_tools_allowed is False
    assert report.github_issue_created is False
    assert report.github_pr_created is False
    assert report.github_write_performed is False
    assert report.sibling_repo_write_performed is False
    assert report.promotion_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_skills_registry_specialist_review_ready(tmp_path, repo_root):
    report, run_dir = run_skills_registry_specialist_review(
        repo_root=repo_root,
        out_dir=tmp_path / "skills-registry-specialist-review",
    )
    persisted = SkillsRegistrySpecialistReviewReport.model_validate(
        load_json(run_dir / "skills_registry_specialist_review_report.json")
    )
    candidates = load_jsonl(run_dir / "skills_registry_specialist_candidates.jsonl")

    assert persisted.specialist_review_report_id == report.specialist_review_report_id
    assert persisted.status == "skills_registry_specialist_review_ready"
    assert persisted.target_repo == "LawFirm-os-skills-registry"
    assert persisted.expected_harness_count == 4
    assert persisted.missing_harness_refs == []
    assert persisted.expected_worker_count == 7
    assert persisted.candidate_count == 7
    assert persisted.ready_candidate_count == 7
    assert persisted.blocked_candidate_count == 0
    assert set(candidate.worker_id for candidate in persisted.candidates) == EXPECTED_WORKERS
    assert len(candidates) == 7
    assert len(persisted.candidate_packet_refs) == 14
    for packet_ref in persisted.candidate_packet_refs:
        assert (run_dir / packet_ref).is_file()
    assert all(candidate["prompt_hash_verified"] for candidate in candidates)
    assert all(candidate["prompt_hash"].startswith("sha256:") for candidate in candidates)
    assert all(candidate["prompt_lifecycle"] == "staged_candidate" for candidate in candidates)
    assert all(candidate["approved_for_real_data"] is False for candidate in candidates)
    assert all(candidate["allowed_tool_refs"] == [] for candidate in candidates)
    assert all(candidate["tool_denylist"] for candidate in candidates)
    assert all(candidate["input_schema_exists"] for candidate in candidates)
    assert all(candidate["output_schema_exists"] for candidate in candidates)
    assert all(candidate["human_gate_required"] is True for candidate in candidates)
    assert all(
        candidate["revocation_owner"] == "LawFirm-os-skills-registry" for candidate in candidates
    )
    assert any(
        candidate["worker_id"] == "frontier-adjudicator"
        and candidate["raw_source_access"] == "bounded_packet_only"
        for candidate in candidates
    )
    assert {check.status for check in persisted.checks} == {"passed"}
    _assert_no_authority_flags(persisted)

    notes = (run_dir / "skills_registry_specialist_review_report.md").read_text(encoding="utf-8")
    source_reader_packet = (
        run_dir
        / "skills_registry_specialist_packets"
        / "source-reader.skills_registry_specialist_candidate.md"
    ).read_text(encoding="utf-8")
    assert "Frontier adjudicator remains bounded-packet-only" in notes
    assert "**Expected harnesses:** 4" in notes
    assert "Skill promoted: False" in notes
    assert "This report is local candidate metadata for Skills Registry review only." in notes
    assert "This packet is candidate-only Skills Registry owner-review evidence." in (
        source_reader_packet
    )


def test_skills_registry_specialist_review_blocks_missing_schema_metadata(tmp_path, repo_root):
    copied = _copy_skill_surface(tmp_path, repo_root)
    matter_router_path = copied / "agents" / "matter-router.yaml"
    matter_router = yaml.safe_load(matter_router_path.read_text(encoding="utf-8"))
    matter_router.pop("input_schema_ref")
    matter_router.pop("output_schema_ref")
    matter_router_path.write_text(yaml.safe_dump(matter_router, sort_keys=False), encoding="utf-8")

    report, _ = run_skills_registry_specialist_review(
        repo_root=copied,
        out_dir=tmp_path / "blocked-skills-registry-specialist-review",
    )
    by_worker = {candidate.worker_id: candidate for candidate in report.candidates}

    assert report.status == "blocked_by_specialist_metadata_gaps"
    assert report.ready_candidate_count == 6
    assert report.blocked_candidate_count == 1
    assert by_worker["matter-router"].status == "blocked_by_specialist_metadata_gap"
    assert "input_schema_ref" in by_worker["matter-router"].missing_metadata_fields
    assert "output_schema_ref" in by_worker["matter-router"].missing_metadata_fields
    assert any(
        check.check_id == "specialist_schema_refs_present_and_existing" and check.status == "failed"
        for check in report.checks
    )
    _assert_no_authority_flags(report)


def test_skills_registry_specialist_review_blocks_prompt_hash_drift(tmp_path, repo_root):
    copied = _copy_skill_surface(tmp_path, repo_root)
    prompt_path = copied / "prompts" / "budget-planner.md"
    prompt_path.write_text(
        prompt_path.read_text(encoding="utf-8") + "\nSynthetic drift for test.\n",
        encoding="utf-8",
    )

    report, _ = run_skills_registry_specialist_review(
        repo_root=copied,
        out_dir=tmp_path / "hash-drift-skills-registry-specialist-review",
    )
    by_worker = {candidate.worker_id: candidate for candidate in report.candidates}

    assert report.status == "blocked_by_specialist_metadata_gaps"
    assert by_worker["budget-planner"].prompt_hash_verified is False
    assert "prompt_hash_verified" in by_worker["budget-planner"].missing_metadata_fields
    assert any(
        check.check_id == "prompt_registry_complete_and_hash_verified" and check.status == "failed"
        for check in report.checks
    )
    _assert_no_authority_flags(report)


def test_skills_registry_specialist_review_blocks_missing_manifest_harness(tmp_path, repo_root):
    copied = _copy_skill_surface(tmp_path, repo_root)
    missing_harness = copied / "harnesses" / "budget-proposal.local.yaml"
    missing_harness.unlink()

    report, _ = run_skills_registry_specialist_review(
        repo_root=copied,
        out_dir=tmp_path / "missing-harness-skills-registry-specialist-review",
    )

    assert report.status == "blocked_by_specialist_metadata_gaps"
    assert report.missing_harness_refs == ["harnesses/budget-proposal.local.yaml"]
    assert report.ready_candidate_count == 7
    assert report.blocked_candidate_count == 0
    assert any(
        check.check_id == "manifest_harness_refs_exist" and check.status == "failed"
        for check in report.checks
    )
    _assert_no_authority_flags(report)


def test_skills_registry_specialist_review_model_rejects_ready_with_blocked_candidate(
    tmp_path,
    repo_root,
):
    report, _ = run_skills_registry_specialist_review(
        repo_root=repo_root,
        out_dir=tmp_path / "skills-registry-specialist-review",
    )
    payload = report.model_dump(mode="json")
    payload["status"] = "skills_registry_specialist_review_ready"
    payload["ready_candidate_count"] = 6
    payload["blocked_candidate_count"] = 1
    payload["candidates"][0]["status"] = "blocked_by_specialist_metadata_gap"
    payload["candidates"][0]["missing_metadata_fields"] = ["synthetic_gap"]

    with pytest.raises(ValueError, match="cannot include blockers"):
        SkillsRegistrySpecialistReviewReport.model_validate(payload)


def test_skills_registry_specialist_review_cli(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "build-skills-registry-specialist-review",
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "skills-registry-specialist-review-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "skills_registry_specialist_review_ready"' in captured.out
    assert '"candidate_count": 7' in captured.out
    assert '"expected_harness_count": 4' in captured.out
    assert '"candidate_packet_count": 14' in captured.out
    assert '"skill_promoted": false' in captured.out
    assert '"github_issue_created": false' in captured.out
    assert (
        tmp_path
        / "skills-registry-specialist-review-cli"
        / "skills_registry_specialist_review_report.json"
    ).is_file()
    assert (
        tmp_path
        / "skills-registry-specialist-review-cli"
        / "skills_registry_specialist_packets"
        / "budget-planner.skills_registry_specialist_candidate.json"
    ).is_file()
