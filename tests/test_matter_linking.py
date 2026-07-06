from __future__ import annotations

import random

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.matter_linking import (
    MATTER_CLUSTER_PROPOSALS_FILENAME,
    MATTER_LINK_DECISIONS_FILENAME,
    build_matter_linking_cluster_report,
)
from lawfirm_os_intake.matter_link_keys import (
    DEFAULT_MATTER_LINK_POLICY_PATH,
    MATTER_LINK_KEY_EXTRACTION_REPORT_FILENAME,
    build_matter_link_key_extraction_report,
    load_matter_link_policy,
    run_matter_link_key_extraction,
)
from lawfirm_os_intake.models import SourceBundle
from lawfirm_os_intake.util import load_json


FIXED_TIME = "2026-07-06T00:00:00Z"


def _key_report(repo_root, fixture_name: str):
    bundle = SourceBundle.model_validate(
        load_json(repo_root / "examples" / "synthetic" / "inbound" / fixture_name)
    )
    return build_matter_link_key_extraction_report(
        bundle=bundle,
        policy=load_matter_link_policy(repo_root / DEFAULT_MATTER_LINK_POLICY_PATH),
        policy_ref=str(DEFAULT_MATTER_LINK_POLICY_PATH),
        generated_at=FIXED_TIME,
    )


def _cluster_signature(report):
    return sorted(
        (
            tuple(cluster.document_ids),
            cluster.ambiguity_class,
            cluster.disposition,
            tuple(cluster.decision_rule_ids),
        )
        for cluster in report.clusters
    )


def _decision_by_rule(report):
    return {decision.rule_id: decision for decision in report.decisions}


def test_two_matters_one_sender_clusters_by_strong_keys_without_sender_linking(repo_root):
    key_report = _key_report(repo_root, "linking-two-matters-one-sender.source-bundle.json")
    report = build_matter_linking_cluster_report(
        key_report=key_report,
        generated_at=FIXED_TIME,
    )

    assert report.status == "matter_linking_clusters_proposed_for_review"
    assert report.cluster_count == 2
    assert report.proposed_link_cluster_count == 2
    assert report.conflicted_cluster_count == 0
    assert report.matter_identity_asserted is False
    assert report.budget_generation_performed is False
    assert {
        tuple(cluster.document_ids): (cluster.ambiguity_class, cluster.disposition)
        for cluster in report.clusters
    } == {
        ("syn-linking-email-a1", "syn-linking-email-a2"): (
            "corroborated_multi_key",
            "proposed_link",
        ),
        ("syn-linking-email-b1", "syn-linking-email-b2"): (
            "corroborated_multi_key",
            "proposed_link",
        ),
    }
    assert any(decision.rule_id == "R1_strong_key_disagreement" for decision in report.decisions)


def test_thread_drift_blocks_shared_thread_with_conflicting_strong_key(repo_root):
    key_report = _key_report(repo_root, "linking-thread-drift.source-bundle.json")
    report = build_matter_linking_cluster_report(
        key_report=key_report,
        generated_at=FIXED_TIME,
    )

    decisions = _decision_by_rule(report)
    assert "R5_thread_drift_strong_key_conflict" in decisions
    drift_decision = decisions["R5_thread_drift_strong_key_conflict"]
    assert drift_decision.outcome == "block"
    assert drift_decision.supporting_key_ids
    assert drift_decision.conflicting_key_ids
    assert report.conflicted_cluster_count == 1
    assert report.clusters[0].disposition == "blocked_conflict"


def test_same_claim_with_different_party_pair_blocks_reuse(repo_root):
    key_report = _key_report(repo_root, "linking-claim-number-reuse.source-bundle.json")
    report = build_matter_linking_cluster_report(
        key_report=key_report,
        generated_at=FIXED_TIME,
    )

    decisions = _decision_by_rule(report)
    assert decisions["R3_strong_key_reuse_conflict"].outcome == "block"
    assert report.cluster_count == 1
    assert report.conflicted_cluster_count == 1
    assert report.clusters[0].ambiguity_class == "conflicted"


def test_shared_policy_with_different_claim_context_splits_and_holds(repo_root):
    key_report = _key_report(repo_root, "linking-policy-shared.source-bundle.json")
    report = build_matter_linking_cluster_report(
        key_report=key_report,
        generated_at=FIXED_TIME,
    )

    decisions = _decision_by_rule(report)
    assert decisions["R4_shared_policy_different_claim_context"].outcome == "split"
    assert report.cluster_count == 2
    assert report.hold_cluster_count == 2
    assert all(cluster.ambiguity_class == "medium_key_only" for cluster in report.clusters)


def test_no_key_sources_hold_without_linking(repo_root):
    key_report = _key_report(repo_root, "linking-no-keys-attachment.source-bundle.json")
    report = build_matter_linking_cluster_report(
        key_report=key_report,
        generated_at=FIXED_TIME,
    )

    decisions = _decision_by_rule(report)
    assert decisions["R14_insufficient_keys"].outcome == "hold"
    assert report.cluster_count == 2
    assert report.hold_cluster_count == 2


def test_bridge_document_blocks_transitive_merge_laundering(repo_root):
    key_report = _key_report(repo_root, "linking-bridge-document.source-bundle.json")
    report = build_matter_linking_cluster_report(
        key_report=key_report,
        generated_at=FIXED_TIME,
    )

    rule_ids = {decision.rule_id for decision in report.decisions}
    assert "B2_bridge_document_multiple_strong_keys" in rule_ids
    assert "R1_strong_key_disagreement" in rule_ids
    assert report.cluster_count == 1
    assert report.conflicted_cluster_count == 1
    assert report.clusters[0].disposition == "blocked_conflict"


def test_cluster_proposals_are_permutation_invariant(repo_root):
    original = SourceBundle.model_validate(
        load_json(
            repo_root
            / "examples/synthetic/inbound/linking-two-matters-one-sender.source-bundle.json"
        )
    )
    policy = load_matter_link_policy(repo_root / DEFAULT_MATTER_LINK_POLICY_PATH)
    baseline_key_report = build_matter_link_key_extraction_report(
        bundle=original,
        policy=policy,
        policy_ref=str(DEFAULT_MATTER_LINK_POLICY_PATH),
        generated_at=FIXED_TIME,
    )
    baseline = _cluster_signature(
        build_matter_linking_cluster_report(
            key_report=baseline_key_report,
            generated_at=FIXED_TIME,
        )
    )

    for seed in range(20):
        shuffled_sources = list(original.sources)
        random.Random(seed).shuffle(shuffled_sources)
        shuffled = original.model_copy(update={"sources": shuffled_sources})
        key_report = build_matter_link_key_extraction_report(
            bundle=shuffled,
            policy=policy,
            policy_ref=str(DEFAULT_MATTER_LINK_POLICY_PATH),
            generated_at=FIXED_TIME,
        )
        observed = _cluster_signature(
            build_matter_linking_cluster_report(
                key_report=key_report,
                generated_at=FIXED_TIME,
            )
        )
        assert observed == baseline


def test_matter_linking_cluster_cli_writes_report_and_decisions(repo_root, tmp_path):
    key_report, key_run_dir = run_matter_link_key_extraction(
        input_path=repo_root
        / "examples/synthetic/inbound/linking-two-matters-one-sender.source-bundle.json",
        out_dir=tmp_path / "keys",
        policy_path=repo_root / DEFAULT_MATTER_LINK_POLICY_PATH,
        generated_at=FIXED_TIME,
    )
    assert key_report.status == "matter_link_keys_extracted_for_review"

    exit_code = main(
        [
            "audit-matter-linking-clusters",
            "--key-extraction-report",
            str(key_run_dir / MATTER_LINK_KEY_EXTRACTION_REPORT_FILENAME),
            "--out-dir",
            str(tmp_path / "clusters"),
            "--generated-at",
            FIXED_TIME,
        ]
    )

    assert exit_code == 0
    report = load_json(tmp_path / "clusters" / MATTER_CLUSTER_PROPOSALS_FILENAME)
    decisions = (tmp_path / "clusters" / MATTER_LINK_DECISIONS_FILENAME).read_text(encoding="utf-8")
    assert report["status"] == "matter_linking_clusters_proposed_for_review"
    assert report["cluster_count"] == 2
    assert report["matter_identity_asserted"] is False
    assert report["budget_generation_performed"] is False
    assert "matter_link_decision_" in decisions
