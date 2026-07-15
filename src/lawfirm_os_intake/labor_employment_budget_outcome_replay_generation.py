from __future__ import annotations

from pathlib import Path
from shutil import copy2

from .budget_actuals import run_budget_actual_comparison
from .budget_learning_loop import run_budget_learning_loop_report
from .carrier_rejection_learning import run_carrier_rejection_learning
from .carrier_rejection_review import run_carrier_rejection_review
from .carrier_rejections import run_carrier_rejection_capture
from .reviewed_learning_gate import run_reviewed_learning_gate
from .util import write_json


COMPLETE_CASES = {
    "discrimination-harassment-clean": {
        "fixture_id": "le-learning-discrimination-harassment-clean.v0_1",
        "appeal": False,
    },
    "wage-hour-clean": {
        "fixture_id": "le-learning-wage-hour-clean.v0_1",
        "appeal": False,
    },
    "epli-carrier-clean": {
        "fixture_id": "le-learning-epli-carrier-clean.v0_1",
        "appeal": True,
    },
}


def run_labor_employment_complete_replay_generation(
    *, repo_root: str | Path, out_dir: str | Path
) -> Path:
    """Materialize only complete, already-supported synthetic replay chains locally."""
    root = Path(repo_root)
    output = Path(out_dir)
    output.mkdir(parents=True, exist_ok=True)
    cases = []
    for slug, spec in COMPLETE_CASES.items():
        source = root / "examples" / "synthetic" / "labor-employment" / "replay-inputs" / slug
        case_dir = output / "cases" / slug
        anchors = case_dir / "anchors"
        anchors.mkdir(parents=True, exist_ok=True)
        for name in ["legal_budget_proposal.json", "budget_actuals_source.json"]:
            copy2(source / name, anchors / name)
        bundle_name = (
            "carrier_rejection_capture_source_bundle_with_appeal_results.json"
            if spec["appeal"]
            else "carrier_rejection_capture_source_bundle.json"
        )
        copy2(source / bundle_name, anchors / bundle_name)
        budget = anchors / "legal_budget_proposal.json"
        actuals, actuals_dir = run_budget_actual_comparison(
            budget_path=budget,
            actuals_path=anchors / "budget_actuals_source.json",
            out_dir=case_dir / "actuals",
        )
        carrier, carrier_dir = run_carrier_rejection_capture(
            budget, anchors / bundle_name, case_dir / "carrier"
        )
        review, review_dir = run_carrier_rejection_review(
            carrier_dir / "carrier_rejection_reconciliation_report.json", case_dir / "review"
        )
        learning, learning_dir = run_carrier_rejection_learning(
            review_dir / "carrier_rejection_review_packet.json", case_dir / "learning"
        )
        gate, gate_dir = run_reviewed_learning_gate(
            out_dir=case_dir / "gate",
            carrier_rejection_learning_report_path=learning_dir
            / "carrier_rejection_learning_report.json",
            budget_actual_comparison_report_path=actuals_dir
            / "budget_actual_comparison_report.json",
        )
        loop, loop_dir = run_budget_learning_loop_report(
            budget_actual_comparison_report_path=actuals_dir
            / "budget_actual_comparison_report.json",
            budget_actual_variance_ledger_report_path=actuals_dir
            / "budget_actual_variance_ledger_report.json",
            carrier_rejection_reconciliation_report_path=carrier_dir
            / "carrier_rejection_reconciliation_report.json",
            carrier_rejection_decision_ledger_report_path=carrier_dir
            / "carrier_rejection_decision_ledger_report.json",
            carrier_rejection_review_packet_path=review_dir
            / "carrier_rejection_review_packet.json",
            carrier_rejection_learning_report_path=learning_dir
            / "carrier_rejection_learning_report.json",
            reviewed_learning_gate_report_path=gate_dir / "reviewed_learning_gate_report.json",
            out_dir=case_dir / "learning-loop",
            generated_at="2026-07-15T00:00:00Z",
        )
        cases.append(
            {
                "learning_fixture_id": spec["fixture_id"],
                "case_dir": str(case_dir),
                "budget_actual_comparison_report_ref": str(
                    actuals_dir / "budget_actual_comparison_report.json"
                ),
                "carrier_rejection_learning_report_ref": str(
                    learning_dir / "carrier_rejection_learning_report.json"
                ),
                "budget_learning_loop_report_ref": str(
                    loop_dir / "budget_learning_loop_report.json"
                ),
                "candidate_only": True,
                "synthetic_only": True,
                "external_writes_performed": False,
            }
        )
    return write_json(
        output / "labor_employment_complete_replay_generation_manifest.json",
        {
            "schema_version": "0.1",
            "status": "candidate_complete_replay_generation",
            "cases": cases,
            "candidate_only": True,
            "synthetic_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )
