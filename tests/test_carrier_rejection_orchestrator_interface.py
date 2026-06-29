from lawfirm_os_intake.carrier_rejection_orchestrator_interface import (
    build_carrier_rejection_orchestrator_interface_draft,
    run_carrier_rejection_orchestrator_interface,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import CarrierRejectionOrchestratorInterfaceDraft
from lawfirm_os_intake.util import load_json


def test_carrier_rejection_orchestrator_interface_keeps_connectors_out_of_intake():
    draft = build_carrier_rejection_orchestrator_interface_draft()

    assert draft.status == "candidate_only"
    assert draft.target_repo == "LawFirm-os-orchestrator"
    assert draft.response_state_ledger_required is True
    assert draft.deterministic_reconciliation_required is True
    assert draft.no_route_ids_assigned is True
    assert draft.no_connector_implemented is True
    assert draft.no_external_writes_performed is True
    assert draft.no_lake_write_performed is True
    assert draft.no_canonical_mutation is True

    channel_ids = {channel.channel_id for channel in draft.connector_channels}
    assert {
        "carrier_portal_notice",
        "email_rejection_notice",
        "ledes_response_file",
        "returned_budget_workbook",
        "appeal_correspondence",
        "manual_human_entry",
    } == channel_ids
    assert all(
        channel.connector_owner == "LawFirm-os-orchestrator" for channel in draft.connector_channels
    )
    assert all(not channel.raw_payload_storage_allowed for channel in draft.connector_channels)
    assert all(
        not channel.intake_connector_implementation_allowed for channel in draft.connector_channels
    )


def test_carrier_rejection_orchestrator_interface_external_write_is_human_authorized_only():
    draft = build_carrier_rejection_orchestrator_interface_draft()
    external_write_steps = [step for step in draft.workflow_steps if step.external_write_allowed]

    assert [step.step_id for step in external_write_steps] == ["human_authorized_appeal_submission"]
    appeal_step = external_write_steps[0]
    assert appeal_step.owner_repo == "LawFirm-os-orchestrator"
    assert appeal_step.required_human_gate == "human_appeal_submission_authorization"
    assert "connector_authority_check" in appeal_step.input_artifacts
    assert "appeal_submission" in draft.prohibited_intake_actions
    assert "carrier_portal_write" in draft.prohibited_intake_actions


def test_carrier_rejection_orchestrator_interface_writes_json_and_markdown(tmp_path):
    draft, run_dir = run_carrier_rejection_orchestrator_interface(tmp_path / "orchestrator")
    payload = load_json(run_dir / "carrier_rejection_orchestrator_interface.json")
    loaded = CarrierRejectionOrchestratorInterfaceDraft.model_validate(payload)
    notes_text = (run_dir / "carrier_rejection_orchestrator_interface.md").read_text(
        encoding="utf-8"
    )

    assert loaded.interface_id == draft.interface_id
    assert "Connector Channels" in notes_text
    assert "Human Pauses" in notes_text
    assert "No connector implemented: True" in notes_text
    assert "does not implement connectors" in notes_text


def test_carrier_rejection_orchestrator_interface_cli(tmp_path, capsys):
    exit_code = main(
        [
            "draft-carrier-rejection-orchestrator-interface",
            "--out-dir",
            str(tmp_path / "orchestrator"),
        ]
    )
    captured = capsys.readouterr()
    payload = load_json(tmp_path / "orchestrator/carrier_rejection_orchestrator_interface.json")
    draft = CarrierRejectionOrchestratorInterfaceDraft.model_validate(payload)

    assert exit_code == 0
    assert draft.workflow_steps
    assert '"status": "candidate_only"' in captured.out
    assert '"human_authorized_appeal_submission"' in captured.out
