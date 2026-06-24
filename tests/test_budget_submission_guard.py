import pytest

from lawfirm_os_intake.budget_submission_guard import (
    build_budget_submission_guard_report,
    enforce_budget_submission_guard_report,
)
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import (
    BudgetProposal,
    BudgetSubmissionGuardReport,
    HumanConfirmation,
    HumanGateStatusReport,
    MatterOpeningReadiness,
    ReviewPackageManifest,
)
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _confirmation(packet, repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    return bind_confirmation_to_packet_evidence(packet, HumanConfirmation.model_validate(raw))


def _budget_run(tmp_path, repo_root):
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
    return budget_dir


def _guard_inputs(budget_dir):
    manifest = ReviewPackageManifest.model_validate(
        load_json(budget_dir / "review_package_manifest.json")
    )
    return (
        BudgetProposal.model_validate(load_json(budget_dir / "legal_budget_proposal.json")),
        MatterOpeningReadiness.model_validate(
            load_json(budget_dir / "matter_opening_readiness.json")
        ),
        HumanGateStatusReport.model_validate(
            load_json(budget_dir / "human_gate_status_report.json")
        ),
        manifest,
    )


def test_budget_run_writes_passing_budget_submission_guard(tmp_path, repo_root):
    budget_dir = _budget_run(tmp_path, repo_root)
    report = BudgetSubmissionGuardReport.model_validate(
        load_json(budget_dir / "budget_submission_guard_report.json")
    )
    manifest = ReviewPackageManifest.model_validate(
        load_json(budget_dir / "review_package_manifest.json")
    )
    review_text = (budget_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")

    assert report.status == "passed"
    assert report.approval_state == "proposed_for_human_review"
    assert report.not_authorized_for_client_submission is True
    assert report.client_submission_performed is False
    assert report.carrier_submission_performed is False
    assert report.billing_handoff_performed is False
    assert report.external_writes_performed is False
    assert report.required_human_gate == "human_budget_review"
    assert {
        "client_budget_submission",
        "carrier_budget_submission",
        "billing_handoff",
    }.issubset(set(report.guarded_actions))
    assert {check.status for check in report.checks} == {"passed"}
    assert {
        "budget_proposal_review_only",
        "human_budget_review_gate_pending",
        "readiness_blocks_budget_submission",
        "no_submission_or_billing_handoff_performed",
        "controlled_artifacts_are_local",
    } == {check.check_id for check in report.checks}
    assert manifest.budget_submission_guard_report_ref == str(
        budget_dir / "budget_submission_guard_report.json"
    )
    assert manifest.artifact_refs["budget_submission_guard_report"].endswith(
        "budget_submission_guard_report.json"
    )
    assert "Budget submission guard report:" in review_text
    assert "Client submission performed: False" in review_text
    assert "Carrier submission performed: False" in review_text
    assert "Billing handoff performed: False" in review_text


def test_budget_submission_guard_fails_on_submittable_budget(tmp_path, repo_root):
    budget_dir = _budget_run(tmp_path, repo_root)
    budget, readiness, human_gates, manifest = _guard_inputs(budget_dir)
    unsafe = budget.model_copy(deep=True)
    unsafe.not_authorized_for_client_submission = False

    report = build_budget_submission_guard_report(
        run_id=manifest.run_id,
        preflight_packet_id=manifest.preflight_packet_id,
        confirmation_id=manifest.confirmation_id,
        budget=unsafe,
        readiness=readiness,
        human_gate_status_report=human_gates,
        artifact_refs=manifest.artifact_refs,
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "budget_proposal_review_only" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="budget_proposal_review_only"):
        enforce_budget_submission_guard_report(report)


def test_budget_submission_guard_fails_when_budget_gate_marked_complete(tmp_path, repo_root):
    budget_dir = _budget_run(tmp_path, repo_root)
    budget, readiness, human_gates, manifest = _guard_inputs(budget_dir)
    unsafe_gates = human_gates.model_copy(deep=True)
    for gate in unsafe_gates.gates:
        if gate.gate_id == "human_budget_review":
            gate.status = "completed"
            gate.completed_by_human = True

    report = build_budget_submission_guard_report(
        run_id=manifest.run_id,
        preflight_packet_id=manifest.preflight_packet_id,
        confirmation_id=manifest.confirmation_id,
        budget=budget,
        readiness=readiness,
        human_gate_status_report=unsafe_gates,
        artifact_refs=manifest.artifact_refs,
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "human_budget_review_gate_pending" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="human_budget_review_gate_pending"):
        enforce_budget_submission_guard_report(report)


def test_budget_submission_guard_enforcer_fails_on_runtime_billing_drift(tmp_path, repo_root):
    budget_dir = _budget_run(tmp_path, repo_root)
    report = BudgetSubmissionGuardReport.model_validate(
        load_json(budget_dir / "budget_submission_guard_report.json")
    )
    report.billing_handoff_performed = True

    with pytest.raises(ValueError, match="billing_handoff_performed"):
        enforce_budget_submission_guard_report(report)
