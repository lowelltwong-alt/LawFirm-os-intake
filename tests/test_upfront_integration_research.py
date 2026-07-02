from lawfirm_os_intake.util import load_json


def test_upfront_research_doc_records_public_unknowns(repo_root):
    doc = repo_root / "docs/integrations/upfront-intake-integration-research.md"
    text = doc.read_text(encoding="utf-8")

    assert "Fulcrum GT" in text
    assert "Upfront" in text
    assert "No public Upfront API reference" in text
    assert "matter-linking-preflight" in text
    assert "source_matter_link_ambiguous" in text
    assert "same sender plus same carrier but different claimant/insured must not merge" in text
    assert "vendor/firm-provided" in text
    assert "no Lake/SQLite" in text and "write" in text


def test_upfront_like_output_fixture_blocks_ambiguous_same_sender_matters(repo_root):
    fixture = load_json(
        repo_root / "examples/synthetic/upfront/upfront-like-intake-output.example.json"
    )

    assert fixture["artifact_type"] == "upfront_like_intake_output_candidate"
    assert fixture["status"] == "requires_human_linking_review"
    assert fixture["data_origin"] == "synthetic"
    assert fixture["source_system"]["real_upfront_export"] is False
    assert fixture["source_system"]["api_contract_verified"] is False

    linking = fixture["matter_linking"]
    assert linking["official_matter_number_status"] == "not_available"
    assert linking["overall_link_state"] == "ambiguous_multiple_candidates"
    assert linking["requires_human_confirmation"] is True
    assert linking["requires_sender_followup"] is True
    assert len(linking["candidate_clusters"]) == 2
    assert {cluster["cluster_id"] for cluster in linking["candidate_clusters"]} == {
        "cluster.case-a",
        "cluster.case-b",
    }
    assert all(
        cluster["match_strength"] == "high_evidence_candidate_not_authorized"
        for cluster in linking["candidate_clusters"]
    )
    assert {
        signal["signal_type"] for signal in linking["weak_signals_not_sufficient_for_merge"]
    } == {"same_sender", "same_carrier"}

    labels = set(fixture["candidate_exception_lake_labels"])
    assert "source_matter_link_ambiguous" in labels
    assert "multiple_possible_matters_same_sender" in labels
    assert "missing_official_matter_number" in labels
    assert "document_cluster_split_required" in labels

    boundaries = fixture["output_boundaries"]
    assert boundaries["upfront_connector_implemented"] is False
    assert boundaries["vendor_api_called"] is False
    assert boundaries["external_write_performed"] is False
    assert boundaries["lake_write_performed"] is False
    assert boundaries["sqlite_write_performed"] is False
    assert boundaries["matter_opening_authorized"] is False
    assert boundaries["budget_amount_output_authorized"] is False
    assert boundaries["conflict_conclusion_emitted"] is False
    assert boundaries["screen_created"] is False
    assert boundaries["silent_learning_performed"] is False


def test_upfront_like_resolved_followup_fixture_stays_candidate_only(repo_root):
    fixture = load_json(
        repo_root
        / "examples/synthetic/upfront/upfront-like-intake-output.resolved-followup.example.json"
    )

    assert fixture["artifact_type"] == "upfront_like_intake_output_candidate"
    assert fixture["status"] == "resolved_candidate_requires_human_confirmation"
    assert fixture["data_origin"] == "synthetic"
    assert fixture["source_system"]["real_upfront_export"] is False
    assert fixture["source_system"]["api_contract_verified"] is False

    linking = fixture["matter_linking"]
    assert linking["overall_link_state"] == "resolved_split_candidates_pending_human_confirmation"
    assert linking["official_matter_number_status"] == "not_available"
    assert linking["requires_human_confirmation"] is True
    assert linking["requires_sender_followup"] is False
    assert len(linking["candidate_clusters"]) == 2
    for cluster in linking["candidate_clusters"]:
        signal_types = {signal["signal_type"] for signal in cluster["supporting_signals"]}
        assert "sender_followup_claim_cluster_confirmation" in signal_types
        assert "upfront_like_request_id" in signal_types
        assert cluster["link_state"] == "resolved_candidate_pending_human_confirmation"

    labels = set(fixture["candidate_exception_lake_labels"])
    assert "source_matter_link_resolved_candidate" in labels
    assert "document_cluster_split_resolved_candidate" in labels
    assert "human_matter_linking_confirmation_required" in labels

    assert "sender_reference_followup" not in fixture["required_next_gates"]
    assert "human_matter_linking_review" in fixture["required_next_gates"]
    assert "no_budget_amount_until_cluster_and_roles_confirmed" in fixture["required_next_gates"]
    assert "no_matter_opening_without_official_authority" in fixture["required_next_gates"]

    boundaries = fixture["output_boundaries"]
    assert boundaries["vendor_api_called"] is False
    assert boundaries["external_write_performed"] is False
    assert boundaries["lake_write_performed"] is False
    assert boundaries["sqlite_write_performed"] is False
    assert boundaries["matter_opening_authorized"] is False
    assert boundaries["budget_amount_output_authorized"] is False
    assert boundaries["conflict_conclusion_emitted"] is False
    assert boundaries["screen_created"] is False
    assert boundaries["silent_learning_performed"] is False
