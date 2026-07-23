"""Executable replay evidence for the three newly-covered L&E families.

Retaliation/wrongful-termination and administrative-exhaustion exercise the
deterministic actuals-variance builder; restrictive-covenant/trade-secret
exercises carrier rejection capture. Each case carries at least one
counterfactual/metamorphic assertion and at least one prohibited-transition
assertion, and none authorizes submission, Lake, SQLite, or silent learning.
All inputs are synthetic and candidate-only.
"""

import pytest

from lawfirm_os_intake.budget_actuals import run_budget_actual_comparison
from lawfirm_os_intake.carrier_rejections import run_carrier_rejection_capture
from lawfirm_os_intake.models import (
    BudgetActualComparisonReport,
    CarrierRejectionDecisionLedgerReport,
    SyntheticBudgetInputWorkbenchReport,
)
from lawfirm_os_intake.synthetic_budget_input_workbench import (
    BUDGET_PROPOSAL_REF as BUDGET_INPUT_DEFAULT_REF,
    build_synthetic_budget_input_workbench_report,
)
from lawfirm_os_intake.util import digest_text, load_json, write_json

WAGE_HOUR_BUDGET_REF = (
    "examples/synthetic/labor-employment/replay-inputs/wage-hour-clean/legal_budget_proposal.json"
)

REPLAY_INPUTS = "examples/synthetic/labor-employment/replay-inputs"
ACTUALS_FAMILIES = {
    "retaliation": (
        "retaliation-wrongful-termination-messy-thread",
        "le-budget-retaliation-wrongful-termination-messy-thread.v0_1",
        "le-preflight-retaliation-wrongful-termination-messy-thread.v0_1",
    ),
    "admin_exhaustion": (
        "admin-exhaustion-clean",
        "le-budget-admin-exhaustion-clean.v0_1",
        "le-preflight-admin-exhaustion-clean.v0_1",
    ),
}


def _case(repo_root, slug):
    root = repo_root / REPLAY_INPUTS / slug
    return root / "legal_budget_proposal.json", root / "budget_actuals_source.json"


@pytest.mark.parametrize("family", sorted(ACTUALS_FAMILIES))
def test_new_family_actuals_replay_inputs_run_builder(repo_root, tmp_path, family):
    slug, budget_id, preflight_id = ACTUALS_FAMILIES[family]
    budget_path, actuals_path = _case(repo_root, slug)

    report, run_dir = run_budget_actual_comparison(
        budget_path=budget_path,
        actuals_path=actuals_path,
        out_dir=tmp_path / f"{family}-actuals-replay",
    )
    persisted = BudgetActualComparisonReport.model_validate(
        load_json(run_dir / "budget_actual_comparison_report.json")
    )

    # Executable replay evidence: deterministic phase+code variance review packet.
    assert report.budget_proposal_id == budget_id
    assert report.preflight_packet_id == preflight_id
    assert report.status == "variance_review_required"
    assert report.comparison_scope == "phase_and_code"
    assert persisted.budget_actual_comparison_report_id == report.budget_actual_comparison_report_id

    # Metamorphic/consistency: the headline variance equals actual minus
    # budgeted, and the phase view reconciles to the displayed total actual.
    assert report.total_variance_amount == round(
        (report.total_actual or 0) - (report.total_budgeted or 0), 2
    )
    phase_actual = round(sum(row.actual_total or 0 for row in persisted.phase_comparisons), 2)
    assert phase_actual == report.total_actual

    # Prohibited-transition: replay never reads/writes billing, Lake, or learns.
    assert report.billing_connector_read_performed is False
    assert report.billing_connector_write_performed is False
    assert report.external_writes_performed is False
    assert all(row.requires_human_review for row in persisted.phase_comparisons)


@pytest.mark.parametrize("family", sorted(ACTUALS_FAMILIES))
def test_new_family_actuals_reject_mismatched_budget_id(repo_root, tmp_path, family):
    slug, _budget_id, _preflight_id = ACTUALS_FAMILIES[family]
    budget_path, actuals_path = _case(repo_root, slug)

    # Counterfactual: a concrete (non-placeholder) mismatched budget id must be
    # rejected rather than silently reconciled to a different case.
    bad_actuals = load_json(actuals_path)
    bad_actuals["budget_proposal_id"] = "wrong-budget-proposal-id"
    bad_actuals_path = write_json(tmp_path / f"{family}-bad-actuals.json", bad_actuals)

    with pytest.raises(ValueError, match="actuals source budget_proposal_id does not match"):
        run_budget_actual_comparison(
            budget_path=budget_path,
            actuals_path=bad_actuals_path,
            out_dir=tmp_path / f"{family}-bad-actuals-run",
        )


def test_restrictive_covenant_carrier_rejection_inputs_run_builder(repo_root, tmp_path):
    root = repo_root / REPLAY_INPUTS / "restrictive-covenant-messy-thread"
    budget_path = root / "legal_budget_proposal.json"
    bundle_path = root / "carrier_rejection_capture_source_bundle.json"

    report, run_dir = run_carrier_rejection_capture(
        budget_path, bundle_path, tmp_path / "restrictive-covenant-carrier-replay"
    )
    ledger = CarrierRejectionDecisionLedgerReport.model_validate(
        load_json(run_dir / "carrier_rejection_decision_ledger_report.json")
    )

    # Executable replay evidence: deterministic dry-run carrier capture.
    assert report.status == "dry_run_ready_for_review"
    assert report.budget_proposal_id == "le-budget-restrictive-covenant-messy-thread.v0_1"
    assert report.source_bundle_id == "le-carrier-rejection-restrictive-covenant-messy-thread.v0_1"
    assert report.reconciled_response_count == 1
    assert report.unlinked_notice_count == 0
    assert report.parser_failure_count == 0

    # Counterfactual: a mismatched preflight packet id must fail closed.
    bad_bundle = load_json(bundle_path)
    bad_bundle["preflight_packet_id"] = "wrong-preflight-packet-id"
    bad_bundle["budget_proposal_id"] = "le-budget-restrictive-covenant-messy-thread.v0_1"
    bad_bundle_path = write_json(tmp_path / "rc-bad-bundle.json", bad_bundle)
    with pytest.raises(ValueError, match="preflight_packet_id does not match"):
        run_carrier_rejection_capture(budget_path, bad_bundle_path, tmp_path / "rc-bad-carrier-run")

    # Prohibited-transition: no appeal submission, Lake/SQLite, or external write.
    assert report.not_authorized_for_lake_write is True
    assert report.not_authorized_for_external_submission is True
    assert report.external_writes_performed is False
    assert ledger.appeal_submission_performed is False
    assert ledger.lake_write_performed is False
    assert ledger.sqlite_write_performed is False
    assert ledger.silent_learning_performed is False


@pytest.mark.parametrize(
    ("budget_ref", "expected_family"),
    [
        (BUDGET_INPUT_DEFAULT_REF, "epli_carrier_assignment"),
        (WAGE_HOUR_BUDGET_REF, "wage_hour_flsa_state"),
    ],
)
def test_budget_input_workbench_covers_materially_different_families(
    repo_root, budget_ref, expected_family
):
    # Budget input is exercised against two materially different proposal
    # families through the same governed, read-only workbench surface.
    report = build_synthetic_budget_input_workbench_report(
        repo_root=repo_root, generated_at="2026-07-21T00:00:00Z", budget_ref=budget_ref
    )
    SyntheticBudgetInputWorkbenchReport.model_validate(report.model_dump(mode="json"))

    assert report.status == "synthetic_budget_input_workbench_ready_for_review"
    assert report.matter_family == expected_family
    # Coherent provenance: the report's ref and hash match the selected family.
    assert report.budget_proposal_ref == budget_ref
    assert report.budget_proposal_sha256 == digest_text(
        (repo_root / budget_ref).read_text(encoding="utf-8")
    )
    # Read-only / candidate-only boundary holds for the second family too.
    assert report.read_only_ui is True
    assert report.external_writes_performed is False
    assert report.budget_submission_authorized is False
    # Totals reconcile to lines (the hardened boundary) for this family.
    line_fee_total = round(sum(float(line.estimated_fees or 0) for line in report.lines), 2)
    line_expense_total = round(sum(line.estimated_expenses for line in report.lines), 2)
    assert report.subtotal_fees == line_fee_total
    assert report.subtotal_expenses == line_expense_total
    assert report.total_proposed_budget == round(
        line_fee_total + line_expense_total + float(report.contingency_amount or 0), 2
    )


def test_budget_input_workbench_two_families_are_materially_different(repo_root):
    epli = build_synthetic_budget_input_workbench_report(
        repo_root=repo_root, generated_at="2026-07-21T00:00:00Z"
    )
    wage_hour = build_synthetic_budget_input_workbench_report(
        repo_root=repo_root, generated_at="2026-07-21T00:00:00Z", budget_ref=WAGE_HOUR_BUDGET_REF
    )
    assert epli.matter_family != wage_hour.matter_family
    assert epli.total_proposed_budget != wage_hour.total_proposed_budget
    assert epli.budget_proposal_sha256 != wage_hour.budget_proposal_sha256
