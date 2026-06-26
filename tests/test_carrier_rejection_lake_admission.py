from lawfirm_os_intake.carrier_rejection_lake_admission import (
    build_carrier_rejection_lake_admission_proposal,
    run_carrier_rejection_lake_admission_proposal,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import CarrierRejectionLakeAdmissionProposal
from lawfirm_os_intake.util import load_json


def test_carrier_rejection_lake_admission_proposal_is_candidate_only():
    proposal = build_carrier_rejection_lake_admission_proposal()

    assert proposal.status == "candidate_only"
    assert proposal.target_repo == "LawFirm-os-exceptions-lake-runtime"
    assert proposal.admission_state == "proposal_not_admitted"
    assert proposal.sqlite_owner == "LawFirm-os-exceptions-lake-runtime"
    assert proposal.sqlite_write_performed is False
    assert proposal.lake_write_performed is False
    assert proposal.external_writes_performed is False
    assert proposal.raw_payload_storage_allowed is False
    assert proposal.no_canonical_mutation is True
    assert all(check.status == "passed" for check in proposal.checks)


def test_carrier_rejection_lake_admission_proposal_covers_required_record_families():
    proposal = build_carrier_rejection_lake_admission_proposal()
    record_types = {spec.record_type for spec in proposal.record_specs}

    assert {
        "carrier_rejection_notice_record",
        "carrier_rejection_reconciliation_record",
        "carrier_rejection_review_outcome_record",
        "carrier_appeal_submission_record",
        "carrier_appeal_result_record",
        "carrier_financial_outcome_record",
        "carrier_rejection_learning_candidate_record",
    } == record_types
    assert all(
        spec.correction_policy == "append_only_supersession" for spec in proposal.record_specs
    )
    assert all(not spec.raw_payload_storage_allowed for spec in proposal.record_specs)
    assert all(not spec.admitted_by_intake for spec in proposal.record_specs)
    assert all(spec.requires_orchestrator_evidence_packet for spec in proposal.record_specs)
    assert all(spec.requires_lake_record_hash for spec in proposal.record_specs)
    assert all(spec.idempotency_fields for spec in proposal.record_specs)
    assert all(spec.required_hash_fields for spec in proposal.record_specs)


def test_carrier_rejection_lake_admission_proposal_has_human_and_financial_records():
    proposal = build_carrier_rejection_lake_admission_proposal()
    specs = {spec.record_type: spec for spec in proposal.record_specs}

    assert (
        "supersedes_record_id_if_correction"
        in specs["carrier_rejection_review_outcome_record"].required_human_review_fields
    )
    assert (
        "human_appeal_submission_authorization"
        in specs["carrier_appeal_submission_record"].required_human_review_fields
    )
    assert (
        "remaining_write_down"
        in specs["carrier_financial_outcome_record"].required_human_review_fields
    )
    assert (
        "human_learning_candidate_review"
        in specs["carrier_rejection_learning_candidate_record"].required_human_review_fields
    )
    assert "sqlite_write" in proposal.prohibited_intake_actions
    assert "correction_in_place" in proposal.prohibited_intake_actions


def test_carrier_rejection_lake_admission_proposal_writes_json_and_markdown(tmp_path):
    proposal, run_dir = run_carrier_rejection_lake_admission_proposal(tmp_path / "lake")
    payload = load_json(run_dir / "carrier_rejection_lake_admission_proposal.json")
    loaded = CarrierRejectionLakeAdmissionProposal.model_validate(payload)
    notes_text = (run_dir / "carrier_rejection_lake_admission_proposal.md").read_text(
        encoding="utf-8"
    )

    assert loaded.proposal_id == proposal.proposal_id
    assert "Record Families" in notes_text
    assert "Append-only required: True" in notes_text
    assert "SQLite write performed: False" in notes_text
    assert "does not create Lake tables" in notes_text


def test_carrier_rejection_lake_admission_cli(tmp_path, capsys):
    exit_code = main(
        [
            "draft-carrier-rejection-lake-admission",
            "--out-dir",
            str(tmp_path / "lake"),
        ]
    )
    captured = capsys.readouterr()
    payload = load_json(tmp_path / "lake" / "carrier_rejection_lake_admission_proposal.json")
    proposal = CarrierRejectionLakeAdmissionProposal.model_validate(payload)

    assert exit_code == 0
    assert proposal.record_specs
    assert '"status": "candidate_only"' in captured.out
    assert '"lake_write_performed": false' in captured.out
