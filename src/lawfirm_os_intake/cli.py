from __future__ import annotations

import argparse
import json
from pathlib import Path
import shutil
import sys

from .models import HumanConfirmation
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

    demo = sub.add_parser("demo", help="Run the complete synthetic intake-to-budget demonstration.")
    demo.add_argument("--input", required=True)
    demo.add_argument("--practice-profile", required=True)
    demo.add_argument("--confirmation-template", required=True)
    demo.add_argument("--out-dir", default=".lawfirm-os-intake/demo")
    demo.add_argument(
        "--adapter", choices=["deterministic", "structured-model"], default="deterministic"
    )
    demo.add_argument("--strict-evidence", action=argparse.BooleanOptionalAction, default=True)
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
            )
            confirmation_data = load_json(args.confirmation_template)
            confirmation_data["preflight_packet_id"] = packet.packet_id
            confirmation = HumanConfirmation.model_validate(confirmation_data)
            confirmation_path = root / "human_confirmation.json"
            write_json(confirmation_path, confirmation.model_dump(mode="json"))
            proposal, budget_dir = run_budget(
                run_dir / "intake_preflight_packet.json",
                confirmation_path,
                args.practice_profile,
                root / "budget",
            )
            _print(
                {
                    "status": "demo_completed",
                    "preflight_packet": str(run_dir / "intake_preflight_packet.json"),
                    "human_confirmation": str(confirmation_path),
                    "conflict_seed": str(budget_dir / "conflict_search_seed_packet.json"),
                    "legal_budget_proposal": str(budget_dir / "legal_budget_proposal.json"),
                    "matter_opening_readiness": str(budget_dir / "matter_opening_readiness.json"),
                    "matter_opening_review_package": str(
                        budget_dir / "matter_opening_review_package.md"
                    ),
                    "review_package_manifest": str(budget_dir / "review_package_manifest.json"),
                    "total_proposed_budget": proposal.total_proposed_budget,
                    "final_boundary": "blocked_pending_conflicts_and_engagement",
                }
            )
            return 0
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    return 2
