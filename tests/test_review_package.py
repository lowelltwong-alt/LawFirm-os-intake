from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    HumanConfirmation,
    ReviewPackageCompletenessReport,
    ReviewPackageManifest,
)
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
    completeness_path = budget_dir / "review_package_completeness_report.json"
    review_text = review_path.read_text(encoding="utf-8")
    manifest = ReviewPackageManifest.model_validate(load_json(manifest_path))
    completeness = ReviewPackageCompletenessReport.model_validate(load_json(completeness_path))
    graph = load_json(budget_dir / "evidence_graph.json")

    assert "# Matter Opening Review Package" in review_text
    assert "## Authority And Preconditions" in review_text
    assert "### Contract State" in review_text
    assert "Contract state status: passed" in review_text
    assert "Lock status: reviewed_seed_lock" in review_text
    assert "LawFirm-os-semantic-substrate" in review_text
    assert "### Model Adapter Boundary" in review_text
    assert "Model adapter status: passed" in review_text
    assert "Provider call performed: False" in review_text
    assert "Model calls allowed: False" in review_text
    assert "Baseline comparison state:" in review_text
    assert "### Human Review Outcome" in review_text
    assert "Human review outcome status: confirmed" in review_text
    assert "Budget stage allowed: True" in review_text
    assert "Required next gate: budget_precondition_gate" in review_text
    assert "### Budget Preconditions" in review_text
    assert "Budget precondition status: passed" in review_text
    assert "Budget blocked state: none" in review_text
    assert "External writes performed: False" in review_text
    assert "Prohibited outputs before gate failure:" in review_text
    assert "matter_opening_review_package" in review_text
    assert "## Source Inventory" in review_text
    assert "read_state=read" in review_text
    assert "availability=available" in review_text
    assert "Ingestion volume profile:" in review_text
    assert "Ingestion profile decision: keep_python_reference" in review_text
    assert "Rust adapter proposal state: not_warranted" in review_text
    assert "Required Rust transition gates:" in review_text
    assert "sha=sha256:" in review_text
    assert "## What Is Known" in review_text
    assert "Human confirmation decision evidence:" in review_text
    assert "; evidence:" in review_text
    assert "] sha=sha256:" in review_text
    assert "## Candidate Alternatives" in review_text
    assert "### Matter Family Candidates" in review_text
    assert "### Party And Role Candidates" in review_text
    assert "role candidates:" in review_text
    assert "party evidence:" in review_text
    assert "## What Still Needs Human Review" in review_text
    assert "not docketed; evidence:" in review_text
    assert "missing information:" in review_text
    assert "## Required Human Gates" in review_text
    assert "human_conflicts_clearance: required" in review_text
    assert "human_budget_review: required" in review_text
    assert "human_matter_opening_authorization: required" in review_text
    assert "## Conflict Search Seed" in review_text
    assert "no_conflict_conclusion" in review_text
    assert "evidence:" in review_text
    assert "## Budget Proposal" in review_text
    assert "Scenario: baseline" in review_text
    assert "### Calculation Summary" in review_text
    assert "Deterministic calculation: True" in review_text
    assert "### Budget Lines" in review_text
    assert "rate source:" in review_text
    assert "synthetic rate:" in review_text
    assert "### Budget Supports" in review_text
    assert "practice-profile://" in review_text
    assert "workflow-policy://" in review_text
    assert "## Exception And Escalation Records" in review_text
    assert "Exception Lake readiness report:" in review_text
    assert "### Exception Lake Readiness" in review_text
    assert "Readiness status: passed" in review_text
    assert "Admission state: dry_run_not_admitted" in review_text
    assert "Target runtime repo: LawFirm-os-exceptions-lake-runtime" in review_text
    assert "### Exception Candidate Details" in review_text
    assert "raw_payload_included=False" in review_text
    assert "canonical_promotion_required=True" in review_text
    assert "target=LawFirm-os-exceptions-lake-runtime" in review_text
    assert "structured_refs=" in review_text
    exception_details = review_text.split("### Exception Candidate Details", maxsplit=1)[1].split(
        "## Safety Gate", maxsplit=1
    )[0]
    assert "evidence=syn-email-001/" in exception_details
    assert "] sha=sha256:" in exception_details
    assert "## Safety Gate" in review_text
    assert "## Matter-Opening Blockers" in review_text
    assert "blocked_pending_conflicts_and_engagement" in review_text
    assert "## Evidence Graph Summary" in review_text
    assert "Graph ID:" in review_text
    assert "Node types:" in review_text
    assert "conflict_search_term=" in review_text
    assert "budget_line=" in review_text
    assert "Relationships:" in review_text
    assert "supports_conflict_search_term=" in review_text
    assert "edge supports_budget_line:" in review_text
    assert "## Run Ledger Summary" in review_text
    assert "preflight ledger:" in review_text
    assert "preflight step 2: contract_state_gate" in review_text
    assert "budget ledger:" in review_text
    assert "budget step 4: conflict_seed_and_budget_proposal_built" in review_text
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
    assert manifest.artifact_refs["preflight_source_inventory"].endswith("source_inventory.json")
    assert manifest.artifact_refs["preflight_segments"].endswith("segments.json")
    assert manifest.artifact_refs["preflight_ingestion_result"].endswith("ingestion_result.json")
    assert manifest.artifact_refs["preflight_ingestion_volume_profile"].endswith(
        "ingestion_volume_profile.json"
    )
    assert manifest.artifact_refs["preflight_rust_ingestion_readiness_report"].endswith(
        "rust_ingestion_readiness_report.json"
    )
    assert (
        manifest.artifact_refs["preflight_model_adapter_report"] == packet.model_adapter_report_ref
    )
    assert manifest.artifact_refs["preflight_intake_review_form"].endswith("intake_review_form.md")
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
    assert "preflight_exception_lake_readiness_report" in manifest.artifact_refs
    assert "budget_exception_lake_readiness_report" in manifest.artifact_refs
    assert manifest.exception_candidate_refs
    assert manifest.exception_lake_readiness_report_ref == str(
        budget_dir / "exception_lake_readiness_report.json"
    )
    assert manifest.artifact_refs["matter_opening_review_package"] == str(review_path)
    assert manifest.artifact_refs["review_package_manifest"] == str(manifest_path)
    assert manifest.artifact_refs["review_package_completeness_report"] == str(completeness_path)
    assert manifest.review_package_completeness_report_ref == str(completeness_path)
    assert completeness.status == "passed"
    assert completeness.review_package_id == manifest.review_package_id
    assert completeness.human_readable_review_ref == str(review_path)
    assert completeness.review_package_manifest_ref == str(manifest_path)
    assert "## Authority And Preconditions" in completeness.required_sections
    assert "### Contract State" in completeness.required_sections
    assert "### Model Adapter Boundary" in completeness.required_sections
    assert "### Human Review Outcome" in completeness.required_sections
    assert "### Budget Preconditions" in completeness.required_sections
    assert "## Source Inventory" in completeness.required_sections
    assert "## Candidate Alternatives" in completeness.required_sections
    assert "## Required Human Gates" in completeness.required_sections
    assert "### Budget Lines" in completeness.required_sections
    assert "### Exception Lake Readiness" in completeness.required_sections
    assert "### Exception Candidate Details" in completeness.required_sections
    assert "## Evidence Graph Summary" in completeness.required_sections
    assert "## Run Ledger Summary" in completeness.required_sections
    assert "review_package_completeness_report" in completeness.required_artifact_keys
    assert {check.status for check in completeness.checks} == {"passed"}

    ledger_events = load_jsonl(budget_dir / "run_ledger.jsonl")
    package_event = next(
        event
        for event in ledger_events
        if event["step_name"] == "matter_opening_review_package_built"
    )
    assert str(completeness_path) in package_event["output_refs"]

    node_types = {node["node_type"] for node in graph["nodes"]}
    relationships = {edge["relationship"] for edge in graph["edges"]}
    assert {
        "human_review_outcome",
        "party_role_candidate",
        "conflict_seed_packet",
        "conflict_search_term",
        "budget_line",
        "budget_support_item",
        "structured_ref",
    }.issubset(node_types)
    assert {
        "supports_human_confirmation",
        "supports_party_role_candidate",
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
