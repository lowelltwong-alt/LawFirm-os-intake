import json
from copy import deepcopy

import yaml

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.models import ExceptionLakeCandidate, HumanConfirmation
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
    assert injection[0]["identity_key"].startswith("sha256:")
    assert injection[0]["severity"] == "S0"
    assert injection[0]["occurrence_hint"] == "count_recurrence_by_identity_key"
    assert injection[0]["holdout_origin"] is False
    assert injection[0]["evidence_refs"]
    assert injection[0]["blocked_state"] == "human_intake_review_required"


def test_prohibited_transition_attempts_become_specific_exception_candidates(
    tmp_path,
    repo_root,
):
    _, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/prompt-injection-email.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )

    candidates = _jsonl(run_dir / "exception_lake_candidates.jsonl")
    labels = {candidate["local_event_label"] for candidate in candidates}
    expected_labels = {
        "prohibited_transition_attempted_budget_submitted",
        "prohibited_transition_attempted_conflicts_cleared",
        "prohibited_transition_attempted_deadline_docketed",
        "prohibited_transition_attempted_external_message_sent",
        "prohibited_transition_attempted_imanage_workspace_created",
        "prohibited_transition_attempted_matter_opened",
    }
    transition_candidates = [
        candidate for candidate in candidates if candidate["local_event_label"] in expected_labels
    ]

    assert expected_labels.issubset(labels)
    assert all(
        candidate["canonical_lake_class"] == "workflow_escalation"
        for candidate in transition_candidates
    )
    assert all(candidate["evidence_refs"] for candidate in transition_candidates)
    assert all(candidate["structured_refs"] for candidate in transition_candidates)
    assert all(
        candidate["blocked_state"] == "human_intake_review_required"
        for candidate in transition_candidates
    )
    assert all(candidate["raw_payload_included"] is False for candidate in transition_candidates)
    assert all(candidate["severity"] == "S0" for candidate in transition_candidates)
    assert all(
        candidate["identity_key"].startswith("sha256:") for candidate in transition_candidates
    )
    assert all("text" not in candidate for candidate in transition_candidates)


def test_role_ambiguity_becomes_workflow_escalation_candidate(tmp_path, repo_root):
    _, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-misleading-sender-role-ambiguity.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )

    candidates = _jsonl(run_dir / "exception_lake_candidates.jsonl")
    role_ambiguity = [
        candidate
        for candidate in candidates
        if candidate["local_event_label"] == "critic_role_candidates_ambiguous"
    ]

    assert role_ambiguity
    assert role_ambiguity[0]["canonical_lake_class"] == "workflow_escalation"
    assert role_ambiguity[0]["evidence_refs"]
    assert role_ambiguity[0]["raw_payload_included"] is False
    assert "text" not in role_ambiguity[0]


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

    unknowns = [
        candidate
        for candidate in candidates
        if candidate["local_event_label"] == "budget_unknowns_require_review"
    ]
    assert unknowns
    assert unknowns[0]["canonical_lake_class"] == "workflow_escalation"
    assert unknowns[0]["severity"] == "S2"
    assert unknowns[0]["structured_refs"]
    assert unknowns[0]["raw_payload_included"] is False


def test_hours_only_budget_emits_missing_rate_exception_candidate(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    no_rate_profile = deepcopy(profile)
    no_rate_profile["synthetic_hourly_rates"] = {}
    profile_path = tmp_path / "no-rates-profile.yaml"
    profile_path.write_text(yaml.safe_dump(no_rate_profile), encoding="utf-8")

    budget, budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        profile_path,
        tmp_path / "budget",
    )

    candidates = _jsonl(budget_dir / "exception_lake_candidates.jsonl")
    rate_gaps = [
        candidate
        for candidate in candidates
        if candidate["local_event_label"] == "budget_hours_only_missing_rates"
    ]

    assert budget.pricing_status == "hours_only"
    assert rate_gaps
    assert rate_gaps[0]["blocked_state"] == "budget_hours_only"
    assert rate_gaps[0]["evidence_refs"]
    assert rate_gaps[0]["structured_refs"] == [f"budget-proposal://{budget.budget_proposal_id}"]


def test_missing_budget_template_emits_budget_template_exception_candidate(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    profile = load_profile(repo_root / "context/synthetic-profiles/insurance-defense.yaml")
    no_template_profile = deepcopy(profile)
    no_template_profile["budget_templates"] = {}
    profile_path = tmp_path / "no-template-profile.yaml"
    profile_path.write_text(yaml.safe_dump(no_template_profile), encoding="utf-8")

    budget, budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        profile_path,
        tmp_path / "budget",
    )

    candidates = _jsonl(budget_dir / "exception_lake_candidates.jsonl")
    template_gaps = [
        candidate
        for candidate in candidates
        if candidate["local_event_label"] == "budget_template_missing"
    ]

    assert budget.pricing_status == "insufficient_information"
    assert template_gaps
    assert template_gaps[0]["blocked_state"] == "budget_insufficient_information"
    assert template_gaps[0]["structured_refs"]
    assert template_gaps[0]["raw_payload_included"] is False


def test_exception_identity_key_is_stable_across_runs_and_subject_sensitive():
    first = ExceptionLakeCandidate(
        candidate_id="exc-first",
        run_id="run-a",
        preflight_packet_id="packet-a",
        local_event_label="scenario_policy_invalid",
        canonical_lake_class="workflow_escalation",
        reason="first occurrence",
        structured_refs=["budget-policy://scenario/L250"],
        blocked_state="scenario_policy_invalid",
    )
    repeat = ExceptionLakeCandidate(
        candidate_id="exc-repeat",
        run_id="run-b",
        preflight_packet_id="packet-b",
        local_event_label="scenario_policy_invalid",
        canonical_lake_class="workflow_escalation",
        reason="same logical occurrence",
        structured_refs=["budget-policy://scenario/L250"],
        blocked_state="scenario_policy_invalid",
    )
    different_subject = ExceptionLakeCandidate(
        candidate_id="exc-other",
        run_id="run-c",
        preflight_packet_id="packet-c",
        local_event_label="scenario_policy_invalid",
        canonical_lake_class="workflow_escalation",
        reason="different logical occurrence",
        structured_refs=["budget-policy://scenario/L260"],
        blocked_state="scenario_policy_invalid",
    )
    authority_conflict = ExceptionLakeCandidate(
        candidate_id="exc-authority",
        run_id="run-d",
        preflight_packet_id="packet-d",
        local_event_label="rate_resolution_ambiguous",
        canonical_lake_class="authority_conflict_override",
        reason="ambiguous carrier authority",
        structured_refs=["rate-card://carrier/a|carrier/b"],
        blocked_state="rate_resolution_ambiguous",
    )

    assert first.identity_key == repeat.identity_key
    assert first.identity_key != different_subject.identity_key
    assert first.severity == "S1"
    assert authority_conflict.severity == "S0"
    assert first.occurrence_hint == "count_recurrence_by_identity_key"
