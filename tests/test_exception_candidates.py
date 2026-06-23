import json

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _jsonl(path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]


def _confirmation(packet, repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return bind_confirmation_to_packet_evidence(packet, HumanConfirmation.model_validate(raw))


def test_preflight_emits_lake_shaped_candidates_for_missing_and_duplicate_sources(
    tmp_path,
    repo_root,
):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-duplicate-missing-attachment.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )

    candidate_path = run_dir / "exception_lake_candidates.jsonl"
    candidates = _jsonl(candidate_path)
    labels = {candidate["local_event_label"] for candidate in candidates}

    assert packet.exception_candidates_ref == str(candidate_path)
    assert "source_missing" in labels
    assert "duplicate_source_detected" in labels
    assert {
        candidate["canonical_lake_class"]
        for candidate in candidates
        if candidate["local_event_label"] == "source_missing"
    } == {"retrieval_miss"}
    assert all(candidate["status"] == "dry_run_candidate" for candidate in candidates)
    assert all(candidate["raw_payload_included"] is False for candidate in candidates)
    assert all(candidate["canonical_promotion_required"] is True for candidate in candidates)
    assert all("text" not in candidate for candidate in candidates)


def test_prompt_injection_becomes_workflow_escalation_candidate(tmp_path, repo_root):
    _, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/prompt-injection-email.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )

    candidates = _jsonl(run_dir / "exception_lake_candidates.jsonl")
    injection = [
        candidate
        for candidate in candidates
        if candidate["local_event_label"] == "prompt_injection_source_content"
    ]

    assert injection
    assert injection[0]["canonical_lake_class"] == "workflow_escalation"
    assert injection[0]["evidence_refs"]
    assert injection[0]["blocked_state"] == "human_intake_review_required"


def test_budget_blocker_emits_local_exception_candidate(tmp_path, repo_root):
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

    candidates = _jsonl(budget_dir / "exception_lake_candidates.jsonl")
    blockers = [
        candidate
        for candidate in candidates
        if candidate["local_event_label"]
        == "matter_opening_blocked_pending_conflicts_and_engagement"
    ]

    assert blockers
    assert blockers[0]["canonical_lake_class"] == "workflow_escalation"
    assert blockers[0]["blocked_state"] == "blocked_pending_conflicts_and_engagement"
