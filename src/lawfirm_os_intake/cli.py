from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from .budget_form import build_budget_form_template_audit_report, render_budget_form
from .carrier_rejection_lake_admission import (
    run_carrier_rejection_lake_admission_proposal,
)
from .carrier_rejection_learning import run_carrier_rejection_learning
from .carrier_rejection_orchestrator_interface import (
    run_carrier_rejection_orchestrator_interface,
)
from .carrier_rejection_review import run_carrier_rejection_review
from .carrier_rejections import run_carrier_rejection_capture
from .confirmation import bind_confirmation_to_packet_evidence
from .models import BudgetProposal, HumanConfirmation
from .util import load_json, write_json
from .workflow import run_budget, run_preflight


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="lawfirm-os-intake",
        description="Synthetic-only intake-to-budget reference workflow for LawFirm OS.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    preflight = sub.add_parser("preflight", help="Build a human-review intake preflight packet.")
    preflight.add_argument("--input", required=True)
    preflight.add_argument("--practice-profile", required=True)
    preflight.add_argument("--out-dir", default=".lawfirm-os-intake/runs")
    preflight.add_argument("--review-form-out")
    preflight.add_argument("--fixture-gold")
    preflight.add_argument(
        "--adapter", choices=["deterministic", "structured-model"], default="deterministic"
    )
    preflight.add_argument("--strict-evidence", action=argparse.BooleanOptionalAction, default=True)

    budget = sub.add_parser(
        "build-budget", help="Build conflict seed and budget proposal after human confirmation."
    )
    budget.add_argument("--preflight-packet", required=True)
    budget.add_argument("--confirmation", required=True)
    budget.add_argument("--practice-profile", required=True)
    budget.add_argument("--out-dir", required=True)
    budget.add_argument("--fixture-gold")

    demo = sub.add_parser("demo", help="Run the complete synthetic intake-to-budget demonstration.")
    demo.add_argument("--input", required=True)
    demo.add_argument("--practice-profile", required=True)
    demo.add_argument("--confirmation-template", required=True)
    demo.add_argument("--out-dir", default=".lawfirm-os-intake/demo")
    demo.add_argument("--fixture-gold")
    demo.add_argument(
        "--adapter", choices=["deterministic", "structured-model"], default="deterministic"
    )
    demo.add_argument("--strict-evidence", action=argparse.BooleanOptionalAction, default=True)

    budget_form = sub.add_parser(
        "budget-form",
        help="Render a legal budget proposal into a UTBMS budget form workbook (.xlsx).",
    )
    budget_form.add_argument("--budget", required=True, help="Path to legal_budget_proposal.json")
    budget_form.add_argument("--out", required=True, help="Output .xlsx path")
    budget_form.add_argument(
        "--template", help="Optional existing UTBMS budget form to fill instead of generating one"
    )
    budget_form.add_argument(
        "--mapping-report-out",
        help="Optional budget_form_mapping_report.json path; requires --template.",
    )

    budget_form_audit = sub.add_parser(
        "budget-form-audit",
        help="Audit a UTBMS budget form template before template-backed rendering.",
    )
    budget_form_audit.add_argument("--template", required=True, help="Existing UTBMS budget form")
    budget_form_audit.add_argument("--out", required=True, help="Output audit report JSON path")

    carrier_rejections = sub.add_parser(
        "capture-carrier-rejections",
        help="Build a synthetic carrier rejection reconciliation and learning packet.",
    )
    carrier_rejections.add_argument("--budget", required=True)
    carrier_rejections.add_argument("--source-bundle", required=True)
    carrier_rejections.add_argument("--out-dir", required=True)

    carrier_rejection_review = sub.add_parser(
        "review-carrier-rejections",
        help="Build a human-review packet for carrier rejection remediation cases.",
    )
    carrier_rejection_review.add_argument("--reconciliation-report", required=True)
    carrier_rejection_review.add_argument("--out-dir", required=True)

    carrier_rejection_learning = sub.add_parser(
        "propose-carrier-rejection-learning",
        help="Build candidate-only learning proposals from a carrier rejection review packet.",
    )
    carrier_rejection_learning.add_argument("--review-packet", required=True)
    carrier_rejection_learning.add_argument("--out-dir", required=True)

    carrier_rejection_orchestrator = sub.add_parser(
        "draft-carrier-rejection-orchestrator-interface",
        help="Write the candidate Orchestrator interface for future carrier rejection capture and appeal workflows.",
    )
    carrier_rejection_orchestrator.add_argument("--out-dir", required=True)

    carrier_rejection_lake = sub.add_parser(
        "draft-carrier-rejection-lake-admission",
        help="Write the candidate Exception Lake admission proposal for carrier rejection records.",
    )
    carrier_rejection_lake.add_argument("--out-dir", required=True)
    return parser


def _print(value: dict) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.command == "preflight":
            packet, run_dir = run_preflight(
                args.input,
                args.practice_profile,
                args.out_dir,
                adapter=args.adapter,
                strict_evidence=args.strict_evidence,
                fixture_gold=args.fixture_gold,
            )
            if args.review_form_out and packet.intake_review_form_ref:
                shutil.copyfile(packet.intake_review_form_ref, args.review_form_out)
            _print(
                {
                    "status": packet.status,
                    "run_id": packet.run_id,
                    "packet_id": packet.packet_id,
                    "top_matter_candidate": packet.matter_family_candidates[0].label,
                    "human_confirmation_required": packet.human_confirmation_required,
                    "escalation": packet.escalation.model_dump(mode="json"),
                    "contract_state_report": packet.contract_state_report_ref,
                    "data_scope_gate_report": packet.data_scope_gate_report_ref,
                    "fixture_gold_report": packet.fixture_gold_report_ref,
                    "deadline_docketing_guard_report": (packet.deadline_docketing_guard_report_ref),
                    "evidence_completeness_report": packet.evidence_completeness_report_ref,
                    "context_boundary_report": packet.context_boundary_report_ref,
                    "exception_lake_handoff_manifest": packet.exception_lake_handoff_manifest_ref,
                    "run_ledger_integrity_report": packet.run_ledger_integrity_report_ref,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "build-budget":
            proposal, run_dir = run_budget(
                args.preflight_packet,
                args.confirmation,
                args.practice_profile,
                args.out_dir,
                fixture_gold=args.fixture_gold,
            )
            _print(
                {
                    "status": proposal.approval_state,
                    "budget_proposal_id": proposal.budget_proposal_id,
                    "pricing_status": proposal.pricing_status,
                    "total_proposed_budget": proposal.total_proposed_budget,
                    "not_authorized_for_client_submission": proposal.not_authorized_for_client_submission,
                    "matter_opening_review_package": str(
                        run_dir / "matter_opening_review_package.md"
                    ),
                    "review_package_manifest": str(run_dir / "review_package_manifest.json"),
                    "human_confirmation_history": str(run_dir / "human_confirmation_history.jsonl"),
                    "human_gate_status_report": str(run_dir / "human_gate_status_report.json"),
                    "budget_submission_guard_report": str(
                        run_dir / "budget_submission_guard_report.json"
                    ),
                    "budget_precondition_report": str(run_dir / "budget_precondition_report.json"),
                    "safety_gate_report": str(run_dir / "safety_gate_report.json"),
                    "exception_lake_handoff_manifest": str(
                        run_dir / "exception_lake_handoff_manifest.json"
                    ),
                    "run_ledger_integrity_report": str(
                        run_dir / "run_ledger_integrity_report.json"
                    ),
                    "fixture_gold_report": (
                        str(run_dir / "fixture_gold_report.json") if args.fixture_gold else None
                    ),
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "demo":
            root = Path(args.out_dir)
            if root.exists():
                shutil.rmtree(root)
            root.mkdir(parents=True)
            packet, run_dir = run_preflight(
                args.input,
                args.practice_profile,
                root / "preflight",
                adapter=args.adapter,
                strict_evidence=args.strict_evidence,
                fixture_gold=args.fixture_gold,
            )
            confirmation_data = load_json(args.confirmation_template)
            confirmation_data["preflight_packet_id"] = packet.packet_id
            confirmation = HumanConfirmation.model_validate(confirmation_data)
            confirmation = bind_confirmation_to_packet_evidence(packet, confirmation)
            confirmation_path = root / "human_confirmation.json"
            write_json(confirmation_path, confirmation.model_dump(mode="json"))
            proposal, budget_dir = run_budget(
                run_dir / "intake_preflight_packet.json",
                confirmation_path,
                args.practice_profile,
                root / "budget",
                fixture_gold=args.fixture_gold,
            )
            _print(
                {
                    "status": "demo_completed",
                    "preflight_packet": str(run_dir / "intake_preflight_packet.json"),
                    "contract_state_report": packet.contract_state_report_ref,
                    "data_scope_gate_report": packet.data_scope_gate_report_ref,
                    "deadline_docketing_guard_report": (packet.deadline_docketing_guard_report_ref),
                    "human_confirmation": str(confirmation_path),
                    "conflict_seed": str(budget_dir / "conflict_search_seed_packet.json"),
                    "legal_budget_proposal": str(budget_dir / "legal_budget_proposal.json"),
                    "matter_opening_readiness": str(budget_dir / "matter_opening_readiness.json"),
                    "matter_opening_review_package": str(
                        budget_dir / "matter_opening_review_package.md"
                    ),
                    "review_package_manifest": str(budget_dir / "review_package_manifest.json"),
                    "human_confirmation_history": str(
                        budget_dir / "human_confirmation_history.jsonl"
                    ),
                    "human_gate_status_report": str(budget_dir / "human_gate_status_report.json"),
                    "budget_submission_guard_report": str(
                        budget_dir / "budget_submission_guard_report.json"
                    ),
                    "budget_precondition_report": str(
                        budget_dir / "budget_precondition_report.json"
                    ),
                    "safety_gate_report": str(budget_dir / "safety_gate_report.json"),
                    "exception_lake_handoff_manifest": str(
                        budget_dir / "exception_lake_handoff_manifest.json"
                    ),
                    "run_ledger_integrity_report": str(
                        budget_dir / "run_ledger_integrity_report.json"
                    ),
                    "fixture_gold_report": (
                        str(budget_dir / "fixture_gold_report.json") if args.fixture_gold else None
                    ),
                    "total_proposed_budget": proposal.total_proposed_budget,
                    "final_boundary": "blocked_pending_conflicts_and_engagement",
                }
            )
            return 0

        if args.command == "budget-form":
            proposal = BudgetProposal.model_validate(load_json(args.budget))
            out_path = render_budget_form(
                proposal,
                args.out,
                template_path=args.template,
                mapping_report_out=args.mapping_report_out,
            )
            _print(
                {
                    "status": "budget_form_rendered",
                    "budget_proposal_id": proposal.budget_proposal_id,
                    "pricing_status": proposal.pricing_status,
                    "mode": "fill_existing" if args.template else "synthetic_form",
                    "out": str(out_path),
                    "budget_form_mapping_report": args.mapping_report_out,
                    "not_authorized_for_client_submission": (
                        proposal.not_authorized_for_client_submission
                    ),
                }
            )
            return 0

        if args.command == "budget-form-audit":
            report = build_budget_form_template_audit_report(args.template)
            write_json(args.out, report.model_dump(mode="json"))
            failed_checks = [
                check.check_id for check in report.formula_checks if check.status == "failed"
            ]
            _print(
                {
                    "status": "budget_form_template_audit_" + report.status,
                    "out": args.out,
                    "template_sha256": report.template_sha256,
                    "sheet_name": report.sheet_name,
                    "failed_checks": failed_checks,
                    "missing_template_codes": report.missing_template_codes,
                    "duplicate_template_codes": report.duplicate_template_codes,
                    "external_writes_performed": report.external_writes_performed,
                    "non_authoritative": report.non_authoritative,
                }
            )
            return 0 if report.status == "passed" else 2

        if args.command == "capture-carrier-rejections":
            report, run_dir = run_carrier_rejection_capture(
                args.budget,
                args.source_bundle,
                args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "reconciliation_report_id": report.reconciliation_report_id,
                    "budget_proposal_id": report.budget_proposal_id,
                    "expected_response_count": report.expected_response_count,
                    "reconciled_response_count": report.reconciled_response_count,
                    "missing_response_count": report.missing_response_count,
                    "unlinked_notice_count": report.unlinked_notice_count,
                    "duplicate_notice_count": report.duplicate_notice_count,
                    "appeal_result_count": report.appeal_result_count,
                    "exception_lake_candidate_count": len(report.exception_lake_candidates),
                    "not_authorized_for_lake_write": report.not_authorized_for_lake_write,
                    "not_authorized_for_external_submission": (
                        report.not_authorized_for_external_submission
                    ),
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "review-carrier-rejections":
            packet, run_dir = run_carrier_rejection_review(
                args.reconciliation_report,
                args.out_dir,
            )
            _print(
                {
                    "status": packet.status,
                    "review_packet_id": packet.review_packet_id,
                    "reconciliation_report_id": packet.reconciliation_report_id,
                    "recommendation_count": len(packet.recommendations),
                    "red_team_note_count": len(packet.red_team_notes),
                    "decision_template_count": len(packet.decision_templates),
                    "not_authorized_for_lake_write": packet.not_authorized_for_lake_write,
                    "not_authorized_for_external_submission": (
                        packet.not_authorized_for_external_submission
                    ),
                    "external_writes_performed": packet.external_writes_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "propose-carrier-rejection-learning":
            report, run_dir = run_carrier_rejection_learning(
                args.review_packet,
                args.out_dir,
            )
            _print(
                {
                    "status": report.status,
                    "learning_report_id": report.learning_report_id,
                    "review_packet_id": report.review_packet_id,
                    "proposal_count": report.proposal_count,
                    "target_owners": report.target_owners,
                    "reviewed_outcome_required": report.reviewed_outcome_required,
                    "silent_learning_performed": report.silent_learning_performed,
                    "profile_mutation_performed": report.profile_mutation_performed,
                    "template_mutation_performed": report.template_mutation_performed,
                    "connector_mutation_performed": report.connector_mutation_performed,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "draft-carrier-rejection-orchestrator-interface":
            draft, run_dir = run_carrier_rejection_orchestrator_interface(args.out_dir)
            external_write_steps = [
                step.step_id for step in draft.workflow_steps if step.external_write_allowed
            ]
            _print(
                {
                    "status": draft.status,
                    "interface_id": draft.interface_id,
                    "target_repo": draft.target_repo,
                    "connector_channel_count": len(draft.connector_channels),
                    "workflow_step_count": len(draft.workflow_steps),
                    "external_write_steps": external_write_steps,
                    "no_connector_implemented": draft.no_connector_implemented,
                    "no_external_writes_performed": draft.no_external_writes_performed,
                    "no_lake_write_performed": draft.no_lake_write_performed,
                    "no_canonical_mutation": draft.no_canonical_mutation,
                    "run_dir": str(run_dir),
                }
            )
            return 0

        if args.command == "draft-carrier-rejection-lake-admission":
            proposal, run_dir = run_carrier_rejection_lake_admission_proposal(args.out_dir)
            failed_checks = [
                check.check_id for check in proposal.checks if check.status == "failed"
            ]
            _print(
                {
                    "status": proposal.status,
                    "proposal_id": proposal.proposal_id,
                    "target_repo": proposal.target_repo,
                    "record_family_count": len(proposal.record_specs),
                    "failed_checks": failed_checks,
                    "admission_state": proposal.admission_state,
                    "sqlite_owner": proposal.sqlite_owner,
                    "sqlite_write_performed": proposal.sqlite_write_performed,
                    "lake_write_performed": proposal.lake_write_performed,
                    "raw_payload_storage_allowed": proposal.raw_payload_storage_allowed,
                    "run_dir": str(run_dir),
                }
            )
            return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    return 2
