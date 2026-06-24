import json

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.util import load_json, load_jsonl


def test_north_star_demo_outputs_complete_messy_review_package(tmp_path, repo_root):
    code = main(
        [
            "demo",
            "--input",
            str(repo_root / "examples/synthetic/inbound/north-star-messy-intake.json"),
            "--practice-profile",
            str(repo_root / "context/synthetic-profiles/insurance-defense.yaml"),
            "--confirmation-template",
            str(
                repo_root
                / "examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json"
            ),
            "--out-dir",
            str(tmp_path / "north-star"),
        ]
    )

    assert code == 0
    preflight_dir = next((tmp_path / "north-star/preflight").iterdir())
    packet = load_json(preflight_dir / "intake_preflight_packet.json")
    ingestion_result = load_json(preflight_dir / "ingestion_result.json")
    ingestion_volume = load_json(preflight_dir / "ingestion_volume_profile.json")
    contract_state = load_json(preflight_dir / "contract_state_report.json")
    preflight_exceptions = load_jsonl(preflight_dir / "exception_lake_candidates.jsonl")
    preflight_exception_readiness = load_json(
        preflight_dir / "exception_lake_readiness_report.json"
    )
    budget_dir = tmp_path / "north-star/budget"
    confirmation = load_json(tmp_path / "north-star/human_confirmation.json")
    conflict_seed = load_json(budget_dir / "conflict_search_seed_packet.json")
    budget_exceptions = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")
    budget_exception_readiness = load_json(budget_dir / "exception_lake_readiness_report.json")
    safety = load_json(budget_dir / "safety_gate_report.json")
    manifest = load_json(budget_dir / "review_package_manifest.json")
    completeness = load_json(budget_dir / "review_package_completeness_report.json")
    budget_preconditions = load_json(budget_dir / "budget_precondition_report.json")
    confirmation_history = load_jsonl(budget_dir / "human_confirmation_history.jsonl")
    graph = load_json(budget_dir / "evidence_graph.json")
    review_text = (budget_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")

    labels = {item["local_event_label"] for item in preflight_exceptions}
    budget_labels = {item["local_event_label"] for item in budget_exceptions}
    assert packet["source_coverage_summary"]["missing_sources"] == 1
    assert packet["ingestion_result_ref"].endswith("ingestion_result.json")
    assert packet["ingestion_volume_profile_ref"].endswith("ingestion_volume_profile.json")
    assert ingestion_result["parity_contract"] == "rust_ready_ingestion_v0_1"
    assert ingestion_result["rust_replacement_allowed"] is False
    assert ingestion_volume["ingestion_result_id"] == ingestion_result["ingestion_result_id"]
    assert ingestion_volume["rust_replacement_allowed"] is False
    assert ingestion_volume["decision"] == "keep_python_reference"
    assert len(ingestion_result["segment_evidence_refs"]) == len(ingestion_result["segments"])
    assert packet["contract_state_report_ref"].endswith("contract_state_report.json")
    assert contract_state["status"] == "passed"
    assert confirmation["decision_evidence_refs"]
    assert all(party["evidence_refs"] for party in confirmation["confirmed_parties"])
    assert confirmation_history[0]["confirmation_id"] == confirmation["confirmation_id"]
    assert confirmation_history[0]["budget_stage_allowed"] is True
    assert all(term["evidence_refs"] for term in conflict_seed["normalized_search_terms"])
    assert "conflict_search_term" in {node["node_type"] for node in graph["nodes"]}
    assert "party_role_candidate" in {node["node_type"] for node in graph["nodes"]}
    assert "budget_support_item" in {node["node_type"] for node in graph["nodes"]}
    assert "supports_party_role_candidate" in {edge["relationship"] for edge in graph["edges"]}
    assert "supports_conflict_search_term" in {edge["relationship"] for edge in graph["edges"]}
    assert packet["source_coverage_summary"]["duplicate_sources"] == 1
    assert packet["source_coverage_summary"]["coverage_complete"] is False
    assert "incident_date" in packet["missing_information"]
    assert "jurisdiction" in packet["missing_information"]
    assert "duplicate_source_detected" in labels
    assert "source_missing" in labels
    assert "prompt_injection_source_content" in labels
    assert "prohibited_transition_attempted_conflicts_cleared" in labels
    assert "prohibited_transition_attempted_deadline_docketed" in labels
    assert "prohibited_transition_attempted_matter_opened" in labels
    assert preflight_exception_readiness["status"] == "passed"
    assert {
        ref["source_id"]
        for item in preflight_exceptions
        if item["local_event_label"] == "prompt_injection_source_content"
        for ref in item["evidence_refs"]
    } == {"syn-northstar-injection-001"}
    assert "matter_opening_blocked_pending_conflicts_and_engagement" in budget_labels
    assert "budget_unknowns_require_review" in budget_labels
    assert budget_exception_readiness["status"] == "passed"
    assert budget_exception_readiness["admission_state"] == "dry_run_not_admitted"
    assert safety["status"] == "passed"
    assert budget_preconditions["status"] == "passed"
    assert safety["final_boundary"] == "blocked_pending_conflicts_and_engagement"
    assert manifest["status"] == "blocked_pending_conflicts_and_engagement"
    assert manifest["artifact_refs"]["budget_precondition_report"].endswith(
        "budget_precondition_report.json"
    )
    assert manifest["artifact_refs"]["human_confirmation_history"].endswith(
        "human_confirmation_history.jsonl"
    )
    assert manifest["artifact_refs"]["human_review_outcome"].endswith(".json")
    assert manifest["artifact_refs"]["safety_gate_report"].endswith("safety_gate_report.json")
    assert manifest["artifact_refs"]["review_package_completeness_report"].endswith(
        "review_package_completeness_report.json"
    )
    assert manifest["artifact_refs"]["preflight_ingestion_volume_profile"].endswith(
        "ingestion_volume_profile.json"
    )
    assert manifest["review_package_completeness_report_ref"].endswith(
        "review_package_completeness_report.json"
    )
    assert completeness["status"] == "passed"
    assert completeness["review_package_id"] == manifest["review_package_id"]
    assert {check["status"] for check in completeness["checks"]} == {"passed"}
    assert manifest["artifact_refs"]["budget_exception_lake_readiness_report"].endswith(
        "exception_lake_readiness_report.json"
    )
    assert manifest["artifact_refs"]["contract_state_report"].endswith("contract_state_report.json")
    assert manifest["exception_lake_readiness_report_ref"].endswith(
        "exception_lake_readiness_report.json"
    )
    assert manifest["contract_state_report_ref"].endswith("contract_state_report.json")

    for phrase in [
        "## Authority And Preconditions",
        "### Contract State",
        "Contract state status: passed",
        "Lock status: reviewed_seed_lock",
        "LawFirm-os-semantic-substrate",
        "### Human Review Outcome",
        "Human review outcome status: confirmed",
        "Budget stage allowed: True",
        "Required next gate: budget_precondition_gate",
        "### Budget Preconditions",
        "Budget precondition status: passed",
        "Budget blocked state: none",
        "Prohibited outputs before gate failure:",
        "## Source Inventory",
        "Source coverage complete: False",
        "Ingestion volume profile:",
        "syn-northstar-attachment-missing-001",
        "read_state=missing",
        "availability=duplicate",
        "Human confirmation decision evidence:",
        "] sha=sha256:",
        "## Candidate Alternatives",
        "### Matter Family Candidates",
        "### Party And Role Candidates",
        "role candidates:",
        "## Required Human Gates",
        "human_conflicts_clearance: required",
        "human_budget_review: required",
        "Missing sources: 1",
        "Duplicate sources: 1",
        "missing information: incident_date;",
        "missing information: jurisdiction;",
        "not docketed; evidence:",
        "prompt_injection_source_content",
        "prohibited_transition_attempted_deadline_docketed",
        "Exception Lake readiness report:",
        "### Exception Lake Readiness",
        "Readiness status: passed",
        "Admission state: dry_run_not_admitted",
        "Target runtime repo: LawFirm-os-exceptions-lake-runtime",
        "### Exception Candidate Details",
        "raw_payload_included=False",
        "canonical_promotion_required=True",
        "source_refs=",
        "structured_refs=",
        "review_package_completeness_report.json",
        "no_conflict_conclusion",
        "normalized:",
        "evidence:",
        "Scenario: baseline",
        "### Calculation Summary",
        "### Budget Lines",
        "synthetic rate:",
        "### Budget Supports",
        "Status: passed",
        "contract_state_report.json",
        "blocker: conflicts_not_cleared",
        "blocker: engagement_not_authorized",
        "blocker: matter_opening_not_approved",
        "## Evidence Graph Summary",
        "Node types:",
        "conflict_search_term=",
        "budget_support_item=",
        "Relationships:",
        "supports_party_role_candidate=",
        "edge supports_conflict_search_term:",
        "## Run Ledger Summary",
        "preflight step 2: contract_state_gate",
        "budget step 4: conflict_seed_and_budget_proposal_built",
        "This package does not clear conflicts",
    ]:
        assert phrase in review_text

    json.dumps(manifest)
