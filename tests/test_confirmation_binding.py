import pytest
from lawfirm_os_intake.models import BudgetPreconditionReport
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
