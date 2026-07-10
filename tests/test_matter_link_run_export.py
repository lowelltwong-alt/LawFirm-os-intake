from __future__ import annotations

from copy import deepcopy

import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.matter_link_keys import (
    DEFAULT_MATTER_LINK_POLICY_PATH,
    build_matter_link_key_extraction_report,
    load_matter_link_policy,
)
from lawfirm_os_intake.matter_link_run_export import (
    MATTER_LINK_RUN_EXPORT_FILENAME,
    build_matter_link_run_export,
    run_matter_link_run_export,
)
from lawfirm_os_intake.matter_linking import build_matter_linking_cluster_report
from lawfirm_os_intake.models import MatterLinkHumanDecision, SourceBundle
from lawfirm_os_intake.util import load_json, write_json


FIXED_TIME = "2026-07-10T00:00:00Z"


def _key_and_cluster_reports(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(
            repo_root
            / "examples"
            / "synthetic"
            / "inbound"
            / "linking-two-matters-one-sender.source-bundle.json"
        )
    )
    policy = load_matter_link_policy(repo_root / DEFAULT_MATTER_LINK_POLICY_PATH)
    key_report = build_matter_link_key_extraction_report(
        bundle=bundle,
        policy=policy,
        policy_ref=str(DEFAULT_MATTER_LINK_POLICY_PATH),
        generated_at=FIXED_TIME,
    )
    cluster_report = build_matter_linking_cluster_report(
        key_report=key_report,
        generated_at=FIXED_TIME,
    )
    return key_report, cluster_report


def test_matter_link_run_export_is_deterministic_and_has_no_persistent_authority(repo_root):
    key_report, cluster_report = _key_and_cluster_reports(repo_root)
    first = build_matter_link_run_export(
        key_report=key_report,
        cluster_report=cluster_report,
        generated_at=FIXED_TIME,
    )
    second = build_matter_link_run_export(
        key_report=key_report,
        cluster_report=cluster_report,
        generated_at=FIXED_TIME,
    )
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.prior_context_consumed is None
    assert first.orchestrator_persistence_required is True
    assert first.matter_identity_asserted is False
    assert first.external_writes_performed is False
    assert first.lake_write_performed is False
    assert first.sqlite_write_performed is False
    assert first.silent_learning_performed is False


def test_matter_link_run_export_fails_closed_on_mismatched_source_chain(repo_root):
    key_report, cluster_report = _key_and_cluster_reports(repo_root)
    mismatched = cluster_report.model_copy(
        update={"source_matter_link_key_extraction_report_id": "other_key_report"}
    )
    with pytest.raises(ValueError, match="source reports do not match"):
        build_matter_link_run_export(
            key_report=key_report,
            cluster_report=mismatched,
            generated_at=FIXED_TIME,
        )


def test_matter_link_run_export_writes_only_local_artifact(repo_root, tmp_path):
    key_report, cluster_report = _key_and_cluster_reports(repo_root)
    key_path = write_json(tmp_path / "keys.json", key_report.model_dump(mode="json"))
    cluster_path = write_json(tmp_path / "clusters.json", cluster_report.model_dump(mode="json"))
    export, run_dir = run_matter_link_run_export(
        matter_link_key_extraction_report_path=key_path,
        matter_linking_cluster_report_path=cluster_path,
        out_dir=tmp_path / "export",
        generated_at=FIXED_TIME,
    )
    persisted = load_json(run_dir / MATTER_LINK_RUN_EXPORT_FILENAME)
    assert persisted["matter_link_run_export_id"] == export.matter_link_run_export_id
    assert persisted["local_json_only"] is True
    assert persisted["orchestrator_persistence_required"] is True
    assert deepcopy(persisted)["external_writes_performed"] is False


def test_matter_link_run_export_only_accepts_human_decisions_in_normalized_key_space(
    repo_root,
):
    key_report, cluster_report = _key_and_cluster_reports(repo_root)
    human_decision = MatterLinkHumanDecision(
        decision_id="human_link_decision_001",
        decided_at=FIXED_TIME,
        reviewer_id="synthetic_reviewer_001",
        decision_type="split",
        subject_key_signatures=["sha256:aaa", "sha256:bbb"],
        evidence_key_ids=["matter_link_key_001", "matter_link_key_002"],
        observable_rationale="The reviewed normalized keys identify two distinct synthetic matters.",
    )
    export = build_matter_link_run_export(
        key_report=key_report,
        cluster_report=cluster_report,
        generated_at=FIXED_TIME,
        human_link_decisions=[human_decision],
    )
    assert export.human_link_decisions == [human_decision]

    with pytest.raises(ValueError, match="sha256 hashes"):
        MatterLinkHumanDecision(
            decision_id="human_link_decision_bad",
            decided_at=FIXED_TIME,
            reviewer_id="synthetic_reviewer_001",
            decision_type="confirm_cluster",
            subject_key_signatures=["document_001"],
            evidence_key_ids=["matter_link_key_001"],
            observable_rationale="A document ID is not durable normalized key space.",
        )


def test_export_matter_link_run_cli_emits_candidate_only_local_artifact(
    repo_root, tmp_path, capsys
):
    key_report, cluster_report = _key_and_cluster_reports(repo_root)
    key_path = write_json(tmp_path / "keys.json", key_report.model_dump(mode="json"))
    cluster_path = write_json(tmp_path / "clusters.json", cluster_report.model_dump(mode="json"))
    out_dir = tmp_path / "export"

    exit_code = main(
        [
            "export-matter-link-run",
            "--key-extraction-report",
            str(key_path),
            "--matter-linking-cluster-report",
            str(cluster_path),
            "--out-dir",
            str(out_dir),
            "--generated-at",
            FIXED_TIME,
        ]
    )

    payload = capsys.readouterr().out
    assert exit_code == 0
    assert "ready_for_orchestrator_candidate_review" in payload
    assert '"external_writes_performed": false' in payload
    assert (out_dir / MATTER_LINK_RUN_EXPORT_FILENAME).is_file()
