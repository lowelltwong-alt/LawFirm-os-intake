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
    review_text = (run_dir / "intake_review_form.md").read_text(encoding="utf-8")
    assert inventory["syn-email-dup-002"].availability_state == "duplicate"
    assert inventory["syn-email-dup-002"].duplicate_of_source_id == "syn-email-dup-001"
    assert inventory["syn-attachment-missing-001"].read_state == "missing"
    assert packet.source_coverage_summary["coverage_complete"] is False
    assert packet.source_coverage_summary["attachment_reference_count"] >= 2
    assert (run_dir / "intake_review_form.md").exists()
    assert packet.intake_review_form_ref.endswith("intake_review_form.md")
    assert "duplicate_of=syn-email-dup-001" in review_text
    assert "attachments=claim-notes.pdf, complaint.pdf" in review_text
    assert "filename=assignment_duplicate.txt" in review_text
    assert "## Review Outcome Handling" in review_text
    assert (
        "confirmed -> budget_precondition_gate; budget stage may proceed only after exact "
        "packet binding and evidence checks."
    ) in review_text
    assert "needs_more_information -> collect_missing_information" in review_text
    assert "append_or_supersede_only" in review_text


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


def test_correspondence_dump_segmentation_preserves_message_boundaries(repo_root):
    bundle = SourceBundle.model_validate(
        load_json(
            repo_root
            / "examples/synthetic/inbound/holdout-correspondence-dump-message-boundaries.json"
        )
    )
    segments = segment_bundle(bundle)
    dump_segments = [
        segment
        for segment in segments
        if segment.source_id == "syn-correspondence-dump-boundaries-001"
    ]
    kinds = {segment.segment_type for segment in dump_segments}

    assert {0, 1}.issubset(
        {segment.message_index for segment in dump_segments if segment.message_index is not None}
    )
    assert "correspondence_dump_preamble" in kinds
    assert "email_header" in kinds
    assert "email_body" in kinds
    assert "attachment_reference" in kinds
    assert "quoted_email" in kinds
    assert "signature" in kinds
    assert any(
        segment.segment_type == "quoted_email" and segment.source_instruction_risk
        for segment in dump_segments
    )
    assert all(segment.sha256 for segment in dump_segments)
    assert all(segment.start_offset < segment.end_offset for segment in dump_segments)
    assert all(segment.structural_path for segment in dump_segments)


def test_correspondence_dump_prohibited_instructions_remain_dry_run_exceptions(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root
        / "examples/synthetic/inbound/holdout-correspondence-dump-message-boundaries.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    candidates = load_jsonl(run_dir / "exception_lake_candidates.jsonl")
    labels = {candidate["local_event_label"] for candidate in candidates}
    quoted_segments = [
        segment
        for segment in packet.segments
        if segment.segment_type == "quoted_email" and segment.source_instruction_risk
    ]

    assert quoted_segments
    assert "prompt_injection_source_content" in labels
    assert "prohibited_transition_attempted_matter_opened" in labels
    assert "prohibited_transition_attempted_conflicts_cleared" in labels
    assert all(candidate["raw_payload_included"] is False for candidate in candidates)


def test_review_packet_preserves_unknown_and_context_separation(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-misleading-sender-role-ambiguity.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    unknown = next(
        candidate for candidate in packet.matter_family_candidates if candidate.label == "unknown"
    )
    context_only = next(
        candidate
        for candidate in packet.matter_family_candidates
        if candidate.calibration_label == "context_influenced"
        and candidate.source_evidence_status == "source_anchor_only"
    )
    assert unknown.source_evidence_status == "unknown_option"
    assert context_only.observed_evidence_refs
    assert context_only.context_signal_refs
    assert all(candidate.observed_evidence_refs for candidate in packet.matter_family_candidates)
    assert packet.missing_information_candidates
    assert all(item.evidence_refs for item in packet.missing_information_candidates)
    review_text = (run_dir / "intake_review_form.md").read_text(encoding="utf-8")
    context_line = next(
        line for line in review_text.splitlines() if line.startswith(f"- {context_only.label} ")
    )
    unknown_line = next(line for line in review_text.splitlines() if line.startswith("- unknown "))
    assert "context:" in review_text
    assert "source anchor:" in context_line
    assert "no direct observed support" in context_line
    assert "evidence:" not in context_line
    assert "source anchor:" in unknown_line
    assert "explicit unknown option" in unknown_line
    assert "Sample Indemnity Company" in review_text
    assert any(
        f"{item.field_name}: {item.reason}; evidence:" in review_text
        for item in packet.missing_information_candidates
    )
    assert "; evidence:" in review_text
    assert any(finding.code == "ROLE_CANDIDATES_AMBIGUOUS" for finding in packet.critic_findings)
    assert "ROLE_CANDIDATES_AMBIGUOUS" in review_text
