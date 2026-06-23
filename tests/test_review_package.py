from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation, ReviewPackageManifest
from lawfirm_os_intake.util import load_json, load_jsonl
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _confirmation(packet, repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return bind_confirmation_to_packet_evidence(packet, HumanConfirmation.model_validate(raw))


def test_run_budget_writes_complete_matter_opening_review_package(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")

    _, budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )

    review_path = budget_dir / "matter_opening_review_package.md"
    manifest_path = budget_dir / "review_package_manifest.json"
    review_text = review_path.read_text(encoding="utf-8")
    manifest = ReviewPackageManifest.model_validate(load_json(manifest_path))
    graph = load_json(budget_dir / "evidence_graph.json")

    assert "# Matter Opening Review Package" in review_text
    assert "## What Is Known" in review_text
    assert "## What Still Needs Human Review" in review_text
    assert "## Conflict Search Seed" in review_text
    assert "no_conflict_conclusion" in review_text
    assert "evidence:" in review_text
    assert "## Budget Proposal" in review_text
    assert "Scenario: baseline" in review_text
    assert "practice-profile://" in review_text
    assert "workflow-policy://" in review_text
    assert "## Exception And Escalation Records" in review_text
    assert "## Safety Gate" in review_text
    assert "## Matter-Opening Blockers" in review_text
    assert "blocked_pending_conflicts_and_engagement" in review_text
    assert "does not clear conflicts" in review_text
    assert "submit a budget" in review_text

    assert manifest.status == "blocked_pending_conflicts_and_engagement"
    assert manifest.human_readable_review_ref == str(review_path)
    assert manifest.no_conflict_conclusion is True
    assert manifest.budget_not_authorized_for_client_submission is True
    assert manifest.contains_raw_payload is False
    assert manifest.external_writes_performed is False
    assert manifest.safety_gate_report_ref == str(budget_dir / "safety_gate_report.json")
    assert manifest.contract_state_report_ref == packet.contract_state_report_ref
    assert manifest.budget_precondition_report_ref == str(
        budget_dir / "budget_precondition_report.json"
    )
    assert manifest.artifact_refs["contract_state_report"] == packet.contract_state_report_ref
    assert manifest.artifact_refs["budget_precondition_report"] == str(
        budget_dir / "budget_precondition_report.json"
    )
    assert manifest.artifact_refs["human_confirmation_history"] == str(
        budget_dir / "human_confirmation_history.jsonl"
    )
    assert manifest.artifact_refs["human_review_outcome"].endswith(
        f"human_review_outcome.{confirmation.confirmation_id}.json"
    )
    assert "conflict_search_seed" in manifest.artifact_refs
    assert "legal_budget_proposal" in manifest.artifact_refs
    assert "preflight_exception_candidates" in manifest.artifact_refs
    assert manifest.exception_candidate_refs

    ledger_events = load_jsonl(budget_dir / "run_ledger.jsonl")
    assert any(
        event["step_name"] == "matter_opening_review_package_built" for event in ledger_events
    )

    node_types = {node["node_type"] for node in graph["nodes"]}
    relationships = {edge["relationship"] for edge in graph["edges"]}
    assert {
        "human_review_outcome",
        "conflict_seed_packet",
        "conflict_search_term",
        "budget_line",
        "budget_support_item",
        "structured_ref",
    }.issubset(node_types)
    assert {
        "supports_human_confirmation",
        "supports_conflict_search_term",
        "supports_budget_line",
        "supports_budget_support_item",
        "supports_budget_proposal",
    }.issubset(relationships)
    assert all(
        edge["evidence_refs"]
        for edge in graph["edges"]
        if edge["relationship"] == "supports_conflict_search_term"
    )
