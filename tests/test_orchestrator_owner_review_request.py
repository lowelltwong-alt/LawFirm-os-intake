from copy import deepcopy

import pytest

from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    HumanConfirmation,
    OrchestratorOwnerReviewRequest,
)
from lawfirm_os_intake.orchestrator_owner_review_request import (
    build_orchestrator_owner_review_request,
    run_orchestrator_owner_review_request,
)
from lawfirm_os_intake.util import load_json, write_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _run_budget(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    raw_confirmation = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw_confirmation["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw_confirmation),
    )
    confirmation_path = write_json(
        tmp_path / "human_confirmation.json",
        confirmation.model_dump(mode="json"),
    )
    budget, budget_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    return packet, preflight_dir, confirmation, confirmation_path, budget, budget_dir


def _run_actuals_and_rejections(tmp_path, repo_root, budget_dir):
    _, actuals_dir = run_budget_actual_comparison(
        budget_path=budget_dir / "legal_budget_proposal.json",
        actuals_path=repo_root / "examples/synthetic/actuals/medmal-phase-code-actuals.json",
        out_dir=tmp_path / "actuals",
    )
    _, carrier_dir = run_carrier_rejection_capture(
        budget_dir / "legal_budget_proposal.json",
        repo_root / "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json",
        tmp_path / "carrier-rejections",
    )
    return actuals_dir, carrier_dir


def test_orchestrator_owner_review_request_targets_current_orchestrator_shape(
    tmp_path,
    repo_root,
):
    _, preflight_dir, _, confirmation_path, _, budget_dir = _run_budget(tmp_path, repo_root)
    actuals_dir, carrier_dir = _run_actuals_and_rejections(tmp_path, repo_root, budget_dir)

    request, run_dir = run_orchestrator_owner_review_request(
        preflight_packet_path=preflight_dir / "intake_preflight_packet.json",
        confirmation_path=confirmation_path,
        budget_path=budget_dir / "legal_budget_proposal.json",
        budget_precondition_report_path=budget_dir / "budget_precondition_report.json",
        budget_actual_comparison_report_path=actuals_dir / "budget_actual_comparison_report.json",
        carrier_rejection_decision_ledger_report_path=(
            carrier_dir / "carrier_rejection_decision_ledger_report.json"
        ),
        carrier_rejection_source_bundle_path=repo_root
        / "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json",
        out_dir=tmp_path / "orchestrator-request",
        lake_handoff_mode="validate_only",
    )

    persisted = OrchestratorOwnerReviewRequest.model_validate(
        load_json(run_dir / "orchestrator_owner_review_request.json")
    )
    payload = persisted.model_dump(mode="json")
    source_ids = {source.source_ref_id for source in persisted.source_refs}

    assert persisted.request_id == request.request_id
    assert payload["schema_version"] == "intake_owner_review_request.v0_1"
    assert payload["workflow_label"] == "orchestrator.local.intake_to_budget_owner_review"
    assert payload["synthetic"] is True
    assert payload["contains_real_firm_data"] is False
    assert payload["contains_real_client_data"] is False
    assert payload["contains_real_matter_data"] is False
    assert payload["contains_privileged_data"] is False
    assert persisted.lake_handoff_mode == "validate_only"
    assert {
        "confirm_matter_family",
        "confirm_representation_posture",
        "confirm_principal_party_roles",
        "approve_budget_proposal_before_external_submission",
        "approve_exception_lake_handoff_before_admission",
    } == set(persisted.human_confirmations)
    assert persisted.human_confirmations["confirm_matter_family"].status == "confirmed"
    assert (
        persisted.human_confirmations["approve_budget_proposal_before_external_submission"].status
        == "pending"
    )
    assert all(
        len(source.sha256) == 64 and not source.sha256.startswith("sha256:")
        for source in persisted.source_refs
    )
    assert all(notice.source_ref_id in source_ids for notice in persisted.carrier_rejection_notices)
    assert {notice.notice_id for notice in persisted.carrier_rejection_notices} >= {
        "notice-portal-001",
        "notice-email-001",
        "notice-unlinked-001",
        "notice-parse-001",
    }
    assert any(notice.appeal_results for notice in persisted.carrier_rejection_notices)
    assert any(notice.financial_outcome for notice in persisted.carrier_rejection_notices)
    assert any(
        line.write_down_or_disallowed_amount == "7000.00" for line in persisted.budget_actual_lines
    )
    assert (run_dir / "orchestrator_owner_review_request.md").is_file()


def test_orchestrator_owner_review_request_cli_writes_local_artifacts(
    tmp_path,
    repo_root,
    capsys,
):
    _, preflight_dir, _, confirmation_path, _, budget_dir = _run_budget(tmp_path, repo_root)

    exit_code = main(
        [
            "build-orchestrator-owner-review-request",
            "--preflight-packet",
            str(preflight_dir / "intake_preflight_packet.json"),
            "--confirmation",
            str(confirmation_path),
            "--budget",
            str(budget_dir / "legal_budget_proposal.json"),
            "--budget-precondition-report",
            str(budget_dir / "budget_precondition_report.json"),
            "--out-dir",
            str(tmp_path / "orchestrator-request-cli"),
        ]
    )
    captured = capsys.readouterr()
    request = OrchestratorOwnerReviewRequest.model_validate(
        load_json(tmp_path / "orchestrator-request-cli/orchestrator_owner_review_request.json")
    )

    assert exit_code == 0
    assert request.workflow_label == "orchestrator.local.intake_to_budget_owner_review"
    assert request.carrier_rejection_notices == []
    assert request.budget_actual_lines
    assert request.contains_real_client_data is False
    assert '"status": "orchestrator_owner_review_request_ready"' in captured.out
    assert '"pending_human_pause_count": 2' in captured.out
    assert '"contains_privileged_data": false' in captured.out
    assert (tmp_path / "orchestrator-request-cli/orchestrator_owner_review_request.md").is_file()


def test_orchestrator_owner_review_request_fails_closed_on_bad_source_hash(
    tmp_path,
    repo_root,
):
    packet, _, confirmation, _, budget, _ = _run_budget(tmp_path, repo_root)
    packet = packet.model_copy(deep=True)
    packet.source_inventory[0].source_sha256 = "sha256:not-a-real-hash"

    with pytest.raises(ValueError, match="source hash must be"):
        build_orchestrator_owner_review_request(
            packet=packet,
            confirmation=confirmation,
            budget=budget,
        )


def test_orchestrator_owner_review_request_rejects_real_carrier_source_bundle(
    tmp_path,
    repo_root,
):
    _, preflight_dir, _, confirmation_path, budget, budget_dir = _run_budget(tmp_path, repo_root)
    raw = deepcopy(
        load_json(
            repo_root
            / "examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json"
        )
    )
    raw["budget_proposal_id"] = budget.budget_proposal_id
    raw["preflight_packet_id"] = budget.preflight_packet_id
    raw["contains_real_matter_data"] = True
    source_path = write_json(tmp_path / "bad-carrier-source-bundle.json", raw)

    with pytest.raises(ValueError, match="real client, matter, or privileged data"):
        run_orchestrator_owner_review_request(
            preflight_packet_path=preflight_dir / "intake_preflight_packet.json",
            confirmation_path=confirmation_path,
            budget_path=budget_dir / "legal_budget_proposal.json",
            carrier_rejection_source_bundle_path=source_path,
            out_dir=tmp_path / "blocked-orchestrator-request",
        )
