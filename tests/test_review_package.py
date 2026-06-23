from lawfirm_os_intake.models import HumanConfirmation, ReviewPackageManifest
from lawfirm_os_intake.util import load_json, load_jsonl
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _confirmation(packet, repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return HumanConfirmation.model_validate(raw)


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

    assert "# Matter Opening Review Package" in review_text
    assert "## What Is Known" in review_text
    assert "## What Still Needs Human Review" in review_text
    assert "## Conflict Search Seed" in review_text
    assert "no_conflict_conclusion" in review_text
    assert "## Budget Proposal" in review_text
    assert "Scenario: baseline" in review_text
    assert "## Exception And Escalation Records" in review_text
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
    assert "conflict_search_seed" in manifest.artifact_refs
    assert "legal_budget_proposal" in manifest.artifact_refs
    assert "preflight_exception_candidates" in manifest.artifact_refs
    assert manifest.exception_candidate_refs

    ledger_events = load_jsonl(budget_dir / "run_ledger.jsonl")
    assert any(
        event["step_name"] == "matter_opening_review_package_built" for event in ledger_events
    )
