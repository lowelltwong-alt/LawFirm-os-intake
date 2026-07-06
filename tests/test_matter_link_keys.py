from __future__ import annotations

from copy import deepcopy

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.matter_link_keys import (
    DEFAULT_MATTER_LINK_POLICY_PATH,
    MATTER_LINK_KEY_EXTRACTION_REPORT_FILENAME,
    build_matter_link_key_extraction_report,
    compare_entity_names,
    load_matter_link_policy,
    normalize_entity_name,
    run_matter_link_key_extraction,
)
from lawfirm_os_intake.models import SourceBundle
from lawfirm_os_intake.util import digest_text, load_json


FIXED_TIME = "2026-07-06T00:00:00Z"


def _policy(repo_root):
    return load_matter_link_policy(repo_root / DEFAULT_MATTER_LINK_POLICY_PATH)


def _bundle(repo_root, name: str) -> SourceBundle:
    return SourceBundle.model_validate(
        load_json(repo_root / "examples" / "synthetic" / "inbound" / name)
    )


def test_matter_link_key_extraction_preserves_offsets_and_never_uses_sender_as_key(repo_root):
    bundle = _bundle(repo_root, "linking-two-matters-one-sender.source-bundle.json")
    report = build_matter_link_key_extraction_report(
        bundle=bundle,
        policy=_policy(repo_root),
        policy_ref=str(DEFAULT_MATTER_LINK_POLICY_PATH),
        generated_at=FIXED_TIME,
    )

    assert report.status == "matter_link_keys_extracted_for_review"
    assert report.document_count == 4
    assert report.sender_identity_used_as_link_key is False
    assert report.fuzzy_matching_performed is False
    assert report.acronym_inference_performed is False
    keys = [key for key_set in report.key_sets for key in key_set.keys]
    assert {key.key_type for key in keys} >= {
        "claim_number",
        "policy_number",
        "adjuster_ref",
        "email_thread",
        "incident_date_party",
        "counsel_ref",
    }
    assert {key.normalized_value for key in keys if key.key_type == "claim_number"} == {
        "HPLE1001",
        "HPLE2002",
    }
    assert all(key.key_type != "sender_identity" for key in keys)

    sources_by_id = {source.source_id: source for source in bundle.sources}
    for key in keys:
        assert key.evidence_refs
        for ref in key.evidence_refs:
            source = sources_by_id[ref.source_id]
            assert source.text[ref.start_offset : ref.end_offset] == key.raw_value
            assert ref.sha256 == digest_text(key.raw_value)
            assert ref.segment_id == f"{ref.source_id}:source_text"


def test_matter_link_key_extraction_surfaces_no_key_and_unreadable_gaps(repo_root, tmp_path):
    report, run_dir = run_matter_link_key_extraction(
        input_path=repo_root
        / "examples/synthetic/inbound/linking-no-keys-attachment.source-bundle.json",
        out_dir=tmp_path,
        policy_path=repo_root / DEFAULT_MATTER_LINK_POLICY_PATH,
        generated_at=FIXED_TIME,
    )

    assert report.status == "matter_link_keys_extracted_for_review"
    by_document = {key_set.document_id: key_set for key_set in report.key_sets}
    assert by_document["syn-no-key-attachment-001"].keys == []
    assert by_document["syn-no-key-attachment-001"].extraction_gaps == [
        "source_text_empty_or_unreadable"
    ]
    assert by_document["syn-no-key-email-001"].extraction_gaps == ["no_extractable_link_keys"]
    persisted = load_json(run_dir / MATTER_LINK_KEY_EXTRACTION_REPORT_FILENAME)
    assert persisted["budget_amount_output_authorized"] is False
    assert persisted["matter_opening_authorized"] is False
    assert persisted["lake_write_performed"] is False


def test_matter_link_key_extraction_blocks_non_synthetic_bundle(repo_root):
    payload = deepcopy(
        load_json(
            repo_root
            / "examples/synthetic/inbound/linking-two-matters-one-sender.source-bundle.json"
        )
    )
    payload["data_origin"] = "production"
    payload["contains_real_matter_data"] = True
    bundle = SourceBundle.model_validate(payload)

    report = build_matter_link_key_extraction_report(
        bundle=bundle,
        policy=_policy(repo_root),
        policy_ref=str(DEFAULT_MATTER_LINK_POLICY_PATH),
        generated_at=FIXED_TIME,
    )

    assert report.status == "blocked_matter_link_key_extraction"
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert failed == {"source_bundle_is_synthetic"}


def test_entity_normalization_is_deterministic_and_idempotent(repo_root):
    policy = _policy(repo_root)
    first = normalize_entity_name("Valley Med. Ctr.", policy)
    second = normalize_entity_name(first.normalized_value, policy)

    assert first.normalized_value == "valley medical center"
    assert second.normalized_value == "valley medical center"
    assert first.base_value == second.base_value
    assert first.rewrites_applied == ["med->medical", "ctr->center"]


def test_entity_comparison_holds_suffix_conflicts_and_affiliates(repo_root):
    policy = _policy(repo_root)

    suffix_conflict = compare_entity_names("Sierra Staffing LLC", "Sierra Staffing Inc", policy)
    assert suffix_conflict.outcome == "hold"
    assert suffix_conflict.disposition == "suffix_conflict"
    assert suffix_conflict.review_required is True

    normalized_match = compare_entity_names("Valley Med. Ctr.", "Valley Medical Center", policy)
    assert normalized_match.outcome == "match"
    assert normalized_match.disposition == "normalized_exact"

    acronym_negative = compare_entity_names("VMC", "Valley Medical Center", policy)
    assert acronym_negative.outcome == "no_match"
    assert acronym_negative.comparison_rung == "E6_no_match"

    possible_affiliate = compare_entity_names(
        "Valley Medical Center",
        "Valley Medical Center of Henderson LLC",
        policy,
    )
    assert possible_affiliate.outcome == "hold"
    assert possible_affiliate.disposition == "possible_affiliate"
    assert possible_affiliate.alias_proposal_required is True


def test_matter_link_key_cli_writes_report(repo_root, tmp_path):
    exit_code = main(
        [
            "audit-matter-link-keys",
            "--input",
            str(repo_root / "examples/synthetic/inbound/linking-thread-drift.source-bundle.json"),
            "--out-dir",
            str(tmp_path),
            "--policy",
            str(repo_root / DEFAULT_MATTER_LINK_POLICY_PATH),
            "--generated-at",
            FIXED_TIME,
        ]
    )

    assert exit_code == 0
    report = load_json(tmp_path / MATTER_LINK_KEY_EXTRACTION_REPORT_FILENAME)
    assert report["status"] == "matter_link_keys_extracted_for_review"
    assert report["no_clustering_performed"] is True
    claim_values = {
        key["normalized_value"]
        for key_set in report["key_sets"]
        for key in key_set["keys"]
        if key["key_type"] == "claim_number"
    }
    assert claim_values == {"HPLE3100", "HPLE9999"}
