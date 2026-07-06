from lawfirm_os_intake.budget import _budget_totals
from lawfirm_os_intake.budget_invariants import (
    audit_budget_invariants,
    build_budget_invariant_report,
)
from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import BudgetLine, HumanConfirmation
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _confirmed_packet(tmp_path, repo_root):
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
    confirmation = bind_confirmation_to_packet_evidence(
        packet,
        HumanConfirmation.model_validate(raw),
    )
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    return run_dir, confirmation_path


def test_budget_totals_honor_explicit_zero_line_minimum():
    line = BudgetLine(
        phase_id="L300",
        phase_name="Discovery",
        task_id="L340",
        task_name="Dispositive motions",
        staffing_role="associate",
        estimated_hours=18.0,
        estimated_hours_min=0.0,
        estimated_hours_max=24.0,
        hourly_rate=250.0,
        rate_source="synthetic_profile",
        estimated_fees=4500.0,
        estimated_expenses=0.0,
        estimated_expenses_min=0.0,
        estimated_expenses_max=0.0,
        external_code_candidate="L340",
        estimate_basis_refs=[
            "practice-profile://synthetic-test/budget_templates/test/phases/L300/tasks/L340"
        ],
    )

    totals = _budget_totals([line], contingency_percent=0.0)

    assert totals.subtotal_fees_min == 0.0
    assert totals.total_min == 0.0
    assert totals.subtotal_fees == 4500.0


def test_budget_invariant_report_accepts_current_budget_and_is_written(tmp_path, repo_root):
    run_dir, confirmation_path = _confirmed_packet(tmp_path, repo_root)
    budget, budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )

    report = build_budget_invariant_report(budget)
    written_report = load_json(budget_dir / "budget_invariant_report.json")
    manifest = load_json(budget_dir / "review_package_manifest.json")

    assert report["status"] == "passed"
    assert written_report["status"] == "passed"
    assert written_report["checked_invariants"] == [
        "I1",
        "I2",
        "I4",
        "I5",
        "I6",
        "I8",
        "I10",
        "I13",
        "I15",
    ]
    assert manifest["artifact_refs"]["budget_invariant_report"].endswith(
        "budget_invariant_report.json"
    )


def test_budget_invariants_catch_zero_band_regression(tmp_path, repo_root):
    run_dir, confirmation_path = _confirmed_packet(tmp_path, repo_root)
    budget, _budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )
    payload = budget.model_dump(mode="json")
    selected = next(
        scenario
        for scenario in payload["scenario_set"]["scenarios"]
        if scenario["scenario_id"] == payload["scenario_name"]
    )
    selected["subtotal_fees_min"] = round(
        sum(
            line["estimated_hours"] * line["hourly_rate"]
            for line in payload["lines"]
            if line["hourly_rate"] is not None
        ),
        2,
    )

    violations = audit_budget_invariants(payload)

    assert any(violation["code"] == "scenario_fee_min_mismatch" for violation in violations)


def test_budget_invariants_catch_hours_only_total_leak(tmp_path, repo_root):
    run_dir, confirmation_path = _confirmed_packet(tmp_path, repo_root)
    budget, _budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense-hours-only.yaml",
        tmp_path / "budget",
    )
    payload = budget.model_dump(mode="json")
    payload["total_proposed_budget"] = 1.0

    violations = audit_budget_invariants(payload)

    assert any(violation["invariant_id"] == "I15" for violation in violations)
