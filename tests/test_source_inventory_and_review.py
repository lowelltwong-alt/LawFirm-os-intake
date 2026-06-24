from lawfirm_os_intake.models import SourceBundle
from lawfirm_os_intake.segmenter import segment_bundle
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.util import load_jsonl
from lawfirm_os_intake.workflow import run_preflight


def test_source_inventory_tracks_duplicates_attachments_and_missing_sources(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-duplicate-missing-attachment.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    inventory = {item.source_id: item for item in packet.source_inventory}
    assert inventory["syn-email-dup-002"].availability_state == "duplicate"
    assert inventory["syn-email-dup-002"].duplicate_of_source_id == "syn-email-dup-001"
    assert inventory["syn-attachment-missing-001"].read_state == "missing"
    assert packet.source_coverage_summary["coverage_complete"] is False
    assert packet.source_coverage_summary["attachment_reference_count"] >= 2
    assert (run_dir / "intake_review_form.md").exists()
    assert packet.intake_review_form_ref.endswith("intake_review_form.md")


def test_unread_source_is_coverage_gap_and_exception_candidate(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-unread-source.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    inventory = {item.source_id: item for item in packet.source_inventory}
    candidates = load_jsonl(run_dir / "exception_lake_candidates.jsonl")
    unread = [
        candidate for candidate in candidates if candidate["local_event_label"] == "source_unread"
    ]
    review_text = (run_dir / "intake_review_form.md").read_text(encoding="utf-8")

    assert inventory["syn-unread-guidelines-001"].read_state == "unread"
    assert packet.source_coverage_summary["unread_sources"] == 1
    assert packet.source_coverage_summary["coverage_complete"] is False
    assert unread
    assert unread[0]["canonical_lake_class"] == "retrieval_miss"
    assert unread[0]["source_inventory_refs"] == ["syn-unread-guidelines-001"]
    assert unread[0]["raw_payload_included"] is False
    assert "Unread sources: `1`" in review_text


def test_email_segmentation_separates_quoted_history_and_attachment_refs(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(
            repo_root / "examples/synthetic/inbound/holdout-duplicate-missing-attachment.json"
        )
    )
    segments = segment_bundle(bundle)
    kinds = {segment.segment_type for segment in segments}
    assert "quoted_email" in kinds
    assert "attachment_reference" in kinds
    assert all(segment.structural_path for segment in segments)


def test_review_packet_preserves_unknown_and_context_separation(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-misleading-sender-role-ambiguity.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    assert any(candidate.label == "unknown" for candidate in packet.matter_family_candidates)
    assert all(candidate.observed_evidence_refs for candidate in packet.matter_family_candidates)
    assert packet.missing_information_candidates
    assert all(item.evidence_refs for item in packet.missing_information_candidates)
    review_text = (run_dir / "intake_review_form.md").read_text(encoding="utf-8")
    assert "context:" in review_text
    assert "Sample Indemnity Company" in review_text
    assert any(
        f"{item.field_name}: {item.reason}; evidence:" in review_text
        for item in packet.missing_information_candidates
    )
    assert "; evidence:" in review_text
