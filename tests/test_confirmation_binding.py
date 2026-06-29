import pytest
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import BudgetPreconditionReport, HumanConfirmation
from lawfirm_os_intake.util import load_json, load_jsonl, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def test_confirmation_must_bind_to_packet(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = "wrong-packet"
    confirmation = write_json(tmp_path / "confirmation.json", raw)
    budget_dir = tmp_path / "budget"
    with pytest.raises(ValueError, match="budget precondition gate failed"):
        run_budget(
            run_dir / "intake_preflight_packet.json",
            confirmation,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            budget_dir,
        )
    report = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    exception_candidates = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")
    ledger_events = load_jsonl(budget_dir / "run_ledger.jsonl")

    assert report.status == "failed"
    assert report.blocked_state == "budget_precondition_failed"
    assert any(
        check.check_id == "confirmation_matches_preflight_packet" and check.status == "failed"
        for check in report.checks
    )
    assert exception_candidates[0]["local_event_label"] == "budget_precondition_failed"
    assert exception_candidates[0]["raw_payload_included"] is False
    assert not (budget_dir / "legal_budget_proposal.json").exists()
    assert not (budget_dir / "conflict_search_seed_packet.json").exists()
    assert not (budget_dir / "matter_opening_review_package.md").exists()
    assert any(
        event["step_name"] == "budget_generation_blocked" and event["status"] == "blocked"
        for event in ledger_events
    )


def test_unconfirmed_budget_attempt_records_blocked_precondition(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    raw["status"] = "needs_more_information"
    confirmation = write_json(tmp_path / "confirmation.json", raw)
    budget_dir = tmp_path / "budget"

    with pytest.raises(ValueError, match="budget precondition gate failed"):
        run_budget(
            run_dir / "intake_preflight_packet.json",
            confirmation,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            budget_dir,
        )

    report = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    exception_candidates = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")

    assert report.status == "failed"
    assert report.blocked_state == "budget_blocked_before_human_confirmation"
    assert any(
        check.check_id == "confirmation_status_confirmed" and check.status == "failed"
        for check in report.checks
    )
    assert (
        exception_candidates[0]["local_event_label"] == "budget_blocked_before_human_confirmation"
    )
    assert exception_candidates[0]["canonical_lake_class"] == "workflow_escalation"
    assert not (budget_dir / "legal_budget_proposal.json").exists()
    assert not (budget_dir / "safety_gate_report.json").exists()


@pytest.mark.parametrize(
    ("status", "next_gate"),
    [
        ("needs_more_information", "collect_missing_information"),
        ("unknown", "human_classification_correction"),
        ("human_only", "human_only_handling"),
        ("declined", "declined_or_referred_handoff"),
        ("declined_or_referred", "declined_or_referred_handoff"),
    ],
)
def test_non_confirmed_review_outcomes_record_artifact_and_block_budget(
    tmp_path, repo_root, status, next_gate
):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    raw["status"] = status
    confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(raw)
    )
    confirmation_path = write_json(
        tmp_path / "confirmation.json",
        confirmation.model_dump(mode="json"),
    )
    budget_dir = tmp_path / "budget"

    with pytest.raises(ValueError, match="budget precondition gate failed"):
        run_budget(
            run_dir / "intake_preflight_packet.json",
            confirmation_path,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            budget_dir,
        )

    outcome_path = budget_dir / f"human_review_outcome.{confirmation.confirmation_id}.json"
    outcome = load_json(outcome_path)
    history = load_jsonl(budget_dir / "human_confirmation_history.jsonl")
    report = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )

    assert len(history) == 1
    assert history[0] == outcome
    assert outcome["status"] == status
    assert outcome["budget_stage_allowed"] is False
    assert outcome["required_next_gate"] == next_gate
    assert outcome["mutation_policy"] == "append_or_supersede_only"
    assert outcome["decision_evidence_refs"]
    assert outcome["confirmed_party_evidence_refs"]
    assert report.human_review_outcome_ref == str(outcome_path)
    assert not (budget_dir / "legal_budget_proposal.json").exists()
    assert not (budget_dir / "conflict_search_seed_packet.json").exists()


def test_superseding_confirmation_appends_history_before_budget(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    raw["confirmation_id"] = "human-confirmation-needs-more-info"
    raw["status"] = "needs_more_information"
    first_confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(raw)
    )
    first_path = write_json(
        tmp_path / "first-confirmation.json",
        first_confirmation.model_dump(mode="json"),
    )
    budget_dir = tmp_path / "budget"

    with pytest.raises(ValueError, match="budget precondition gate failed"):
        run_budget(
            run_dir / "intake_preflight_packet.json",
            first_path,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            budget_dir,
        )

    corrected = dict(raw)
    corrected["confirmation_id"] = "human-confirmation-corrected"
    corrected["status"] = "confirmed"
    corrected["supersedes_confirmation_id"] = first_confirmation.confirmation_id
    corrected_confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(corrected)
    )
    corrected_path = write_json(
        tmp_path / "corrected-confirmation.json",
        corrected_confirmation.model_dump(mode="json"),
    )

    run_budget(
        run_dir / "intake_preflight_packet.json",
        corrected_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        budget_dir,
    )

    history = load_jsonl(budget_dir / "human_confirmation_history.jsonl")
    manifest = load_json(budget_dir / "review_package_manifest.json")
    ledger_integrity = load_json(budget_dir / "run_ledger_integrity_report.json")

    assert [item["confirmation_id"] for item in history] == [
        first_confirmation.confirmation_id,
        corrected_confirmation.confirmation_id,
    ]
    assert history[0]["budget_stage_allowed"] is False
    assert history[1]["budget_stage_allowed"] is True
    assert history[1]["supersedes_confirmation_id"] == first_confirmation.confirmation_id
    assert manifest["artifact_refs"]["human_confirmation_history"].endswith(
        "human_confirmation_history.jsonl"
    )
    assert ledger_integrity["status"] == "passed"
    assert ledger_integrity["stage"] == "budget_success"
    assert ledger_integrity["observed_steps"].count("budget_run_started") == 1
    assert (budget_dir / "legal_budget_proposal.json").exists()


def test_evidence_free_confirmation_blocks_budget_generation(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = write_json(tmp_path / "confirmation.json", raw)
    budget_dir = tmp_path / "budget"

    with pytest.raises(ValueError, match="budget precondition gate failed"):
        run_budget(
            run_dir / "intake_preflight_packet.json",
            confirmation,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            budget_dir,
        )

    report = BudgetPreconditionReport.model_validate(
        load_json(budget_dir / "budget_precondition_report.json")
    )
    exception_candidates = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")

    assert report.status == "failed"
    assert report.blocked_state == "budget_confirmation_evidence_missing"
    assert any(
        check.check_id == "decision_evidence_refs_present" and check.status == "failed"
        for check in report.checks
    )
    assert any(
        check.check_id == "confirmed_party_evidence_refs_present" and check.status == "failed"
        for check in report.checks
    )
    assert exception_candidates[0]["local_event_label"] == "budget_confirmation_evidence_missing"
    assert not (budget_dir / "legal_budget_proposal.json").exists()
