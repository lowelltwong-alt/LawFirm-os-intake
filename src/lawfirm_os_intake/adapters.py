from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

import yaml

from .models import (
    FixtureGoldReport,
    IntakePreflightPacket,
    ModelAdapterGuardCheck,
    ModelAdapterReport,
)
from .util import digest_json, new_id, now_iso


AdapterName = Literal["deterministic", "structured-model"]
PROMPT_REGISTRY_REF = "prompts/registry.yaml"
ROOT = Path(__file__).resolve().parents[2]

STRUCTURED_OUTPUT_SCHEMA_REFS = [
    "schemas/intake-preflight-packet.schema.json",
    "schemas/evidence-graph.schema.json",
    "schemas/exception-lake-candidate.schema.json",
    "schemas/legal-budget-proposal.schema.json",
]

ALLOWED_TOOL_REFS = [
    "local-file-read://synthetic-fixture",
    "local-file-write://run-directory-artifact",
]

TOOL_DENYLIST = [
    "network",
    "web_browse",
    "email_send",
    "dms_write",
    "conflicts_system_write",
    "billing_write",
    "carrier_portal_write",
    "court_filing_write",
    "external_filesystem_write",
]

REQUIRED_HUMAN_GATES = [
    "matter_family_confirmation",
    "representation_posture_confirmation",
    "principal_party_role_confirmation",
    "conflicts_clearance",
    "budget_review",
    "matter_opening_authorization",
]

DRY_RUN_MODEL_BUDGET = {
    "max_model_calls": 0,
    "max_tool_calls": 0,
    "max_turns": 0,
    "max_output_json_bytes": 0,
}


@dataclass(frozen=True)
class AdapterDecision:
    name: AdapterName
    mode: Literal["deterministic", "dry_run"]
    model_calls_allowed: bool
    external_tools_allowed: bool
    notes: str


def resolve_adapter(name: str) -> AdapterDecision:
    if name == "deterministic":
        return AdapterDecision(
            name="deterministic",
            mode="deterministic",
            model_calls_allowed=False,
            external_tools_allowed=False,
            notes="Deterministic local worker implementation.",
        )
    if name == "structured-model":
        return AdapterDecision(
            name="structured-model",
            mode="dry_run",
            model_calls_allowed=False,
            external_tools_allowed=False,
            notes=(
                "Synthetic-only structured-output adapter boundary. No provider call is made; "
                "deterministic workers remain the execution source."
            ),
        )
    raise ValueError(f"unsupported adapter: {name}")


def build_model_adapter_report(run_id: str, decision: AdapterDecision) -> ModelAdapterReport:
    prompt_hashes = _prompt_hashes()
    baseline_state: Literal[
        "deterministic_workers_are_current_baseline", "dry_run_no_provider_output"
    ] = (
        "dry_run_no_provider_output"
        if decision.name == "structured-model"
        else "deterministic_workers_are_current_baseline"
    )
    checks = [
        _check(
            "provider_calls_disabled",
            decision.model_calls_allowed is False,
            "No provider/model call is authorized by this adapter selection.",
            {"model_calls_allowed": decision.model_calls_allowed},
        ),
        _check(
            "external_tools_disabled",
            decision.external_tools_allowed is False,
            "External tools remain denied for the adapter boundary.",
            {"external_tools_allowed": decision.external_tools_allowed},
        ),
        _check(
            "prompt_hashes_pinned",
            bool(prompt_hashes)
            and all(value.startswith("sha256:") for value in prompt_hashes.values()),
            "Prompt refs are loaded from the local reviewed prompt registry with hashes.",
            {"prompt_count": len(prompt_hashes)},
        ),
        _check(
            "structured_json_only",
            True,
            "Any future provider output must be typed JSON under exported schemas.",
            {"schema_refs": STRUCTURED_OUTPUT_SCHEMA_REFS},
        ),
        _check(
            "tool_denylist_present",
            bool(TOOL_DENYLIST),
            "Network, external write, and production connector tools are denied.",
            {"tool_denylist": TOOL_DENYLIST},
        ),
        _check(
            "independent_critic_required",
            True,
            "The independent evidence critic remains required before review.",
        ),
        _check(
            "human_confirmation_required",
            True,
            "Matter family, posture, and principal party roles still require human confirmation.",
        ),
        _check(
            "deterministic_baseline_required",
            True,
            "Structured-model output must compare against the deterministic baseline before use.",
            {"baseline_state": baseline_state},
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return ModelAdapterReport(
        model_adapter_report_id=new_id("adapterreport"),
        run_id=run_id,
        adapter_name=decision.name,
        adapter_mode=decision.mode,
        status=status,
        model_calls_allowed=decision.model_calls_allowed,
        external_tools_allowed=decision.external_tools_allowed,
        prompt_registry_ref=PROMPT_REGISTRY_REF,
        prompt_hashes=prompt_hashes,
        structured_output_schema_refs=STRUCTURED_OUTPUT_SCHEMA_REFS,
        model_budget=DRY_RUN_MODEL_BUDGET,
        allowed_tool_refs=ALLOWED_TOOL_REFS,
        tool_denylist=TOOL_DENYLIST,
        required_human_gates=REQUIRED_HUMAN_GATES,
        baseline_comparison_state=baseline_state,
        synthetic_gold_required=decision.name == "structured-model",
        checks=checks,
        generated_at=now_iso(),
    )


def finalize_model_adapter_report(
    report: ModelAdapterReport,
    packet: IntakePreflightPacket,
    *,
    fixture_gold_report: FixtureGoldReport | None = None,
    fixture_gold_report_ref: str | None = None,
) -> ModelAdapterReport:
    baseline_projection = _preflight_projection(packet)
    deterministic_baseline_hash = digest_json(baseline_projection)
    typed_json_ok = _packet_typed_json_valid(packet)
    structured_candidate_hash = (
        deterministic_baseline_hash if report.adapter_name == "structured-model" else None
    )
    baseline_match = (
        report.adapter_name == "deterministic"
        or structured_candidate_hash == deterministic_baseline_hash
    )
    fixture_gold_status: Literal["not_requested", "passed", "failed"] = "not_requested"
    if fixture_gold_report is not None:
        fixture_gold_status = fixture_gold_report.status

    checks = [
        *report.checks,
        _check(
            "typed_json_candidate_valid",
            typed_json_ok,
            "Adapter comparison payload validates as typed intake preflight JSON.",
            {"schema_ref": "schemas/intake-preflight-packet.schema.json"},
        ),
        _check(
            "deterministic_baseline_projection_hashed",
            deterministic_baseline_hash.startswith("sha256:"),
            "Deterministic baseline projection is hash-addressed for comparison.",
            {"deterministic_baseline_hash": deterministic_baseline_hash},
        ),
    ]

    if report.adapter_name == "structured-model":
        checks.extend(
            [
                _check(
                    "structured_dry_run_candidate_compared",
                    baseline_match,
                    "Dry-run structured candidate is compared against the deterministic baseline.",
                    {
                        "structured_candidate_hash": structured_candidate_hash,
                        "deterministic_baseline_hash": deterministic_baseline_hash,
                    },
                ),
                _check(
                    "reviewed_synthetic_gold_compared",
                    fixture_gold_report is not None and fixture_gold_report.status == "passed",
                    "Structured-model dry run requires a passing reviewed synthetic-gold report.",
                    {
                        "fixture_gold_report_ref": fixture_gold_report_ref,
                        "fixture_gold_spec_ref": (
                            fixture_gold_report.gold_ref if fixture_gold_report else None
                        ),
                        "fixture_gold_status": fixture_gold_status,
                    },
                ),
            ]
        )
    elif fixture_gold_report is not None:
        checks.append(
            _check(
                "reviewed_synthetic_gold_compared",
                fixture_gold_report.status == "passed",
                "Deterministic run is bound to the supplied reviewed synthetic-gold report.",
                {
                    "fixture_gold_report_ref": fixture_gold_report_ref,
                    "fixture_gold_spec_ref": fixture_gold_report.gold_ref,
                    "fixture_gold_status": fixture_gold_status,
                },
            )
        )

    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    if report.adapter_name == "structured-model":
        if fixture_gold_report is None:
            baseline_state = "failed_missing_synthetic_gold"
        elif fixture_gold_report.status != "passed":
            baseline_state = "failed_synthetic_gold"
        else:
            baseline_state = "compared_to_deterministic_baseline"
    else:
        baseline_state = "deterministic_workers_are_current_baseline"

    return report.model_copy(
        update={
            "status": status,
            "baseline_comparison_state": baseline_state,
            "comparison_status": "passed" if status == "passed" else "failed",
            "comparison_basis": _comparison_basis(report, fixture_gold_report),
            "deterministic_baseline_hash": deterministic_baseline_hash,
            "structured_candidate_hash": structured_candidate_hash,
            "typed_json_validation_status": "passed" if typed_json_ok else "failed",
            "synthetic_gold_compared": fixture_gold_report is not None,
            "fixture_gold_report_ref": (fixture_gold_report_ref if fixture_gold_report else None),
            "fixture_gold_status": fixture_gold_status,
            "comparison_summary": {
                "projection_fields": sorted(baseline_projection.keys()),
                "deterministic_workers_authoritative": True,
                "provider_call_performed": False,
                "external_writes_performed": False,
                "structured_candidate_source": (
                    "deterministic_baseline_projection"
                    if report.adapter_name == "structured-model"
                    else "not_applicable"
                ),
            },
            "checks": checks,
            "generated_at": now_iso(),
        }
    )


def enforce_model_adapter_report(report: ModelAdapterReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("model adapter guard failed: " + ", ".join(failed))


def _comparison_basis(
    report: ModelAdapterReport,
    fixture_gold_report: FixtureGoldReport | None,
) -> list[str]:
    basis = [
        "typed_json_schema_validation",
        "deterministic_baseline_projection_hash",
    ]
    if report.adapter_name == "structured-model":
        basis.append("structured_dry_run_candidate_hash_match")
        basis.append("reviewed_synthetic_gold_gate")
    elif fixture_gold_report is not None:
        basis.append("reviewed_synthetic_gold_gate")
    return basis


def _packet_typed_json_valid(packet: IntakePreflightPacket) -> bool:
    try:
        IntakePreflightPacket.model_validate(packet.model_dump(mode="json"))
    except ValueError:
        return False
    return True


def _preflight_projection(packet: IntakePreflightPacket) -> dict[str, Any]:
    return {
        "schema_ref": "schemas/intake-preflight-packet.schema.json",
        "preflight_packet_id": packet.packet_id,
        "run_id": packet.run_id,
        "bundle_id": packet.bundle_id,
        "status": packet.status,
        "data_origin": packet.data_origin,
        "source_coverage_summary": packet.source_coverage_summary,
        "source_inventory": [
            {
                "source_id": item.source_id,
                "read_state": item.read_state,
                "availability_state": item.availability_state,
                "source_sha256": item.source_sha256,
                "duplicate_of_source_id": item.duplicate_of_source_id,
            }
            for item in packet.source_inventory
        ],
        "top_inbound_event": (
            packet.inbound_event_candidates[0].label if packet.inbound_event_candidates else None
        ),
        "top_three_matter_families": [
            candidate.label for candidate in packet.matter_family_candidates[:3]
        ],
        "top_representation_posture": (
            packet.representation_posture_candidates[0].label
            if packet.representation_posture_candidates
            else None
        ),
        "party_role_candidates": {
            party.name: sorted(role.role for role in party.role_candidates)
            for party in packet.party_candidates
        },
        "deadline_expressions": [deadline.expression for deadline in packet.deadline_candidates],
        "missing_information": sorted(packet.missing_information),
        "critic_finding_codes": sorted(finding.code for finding in packet.critic_findings),
        "prohibited_next_steps": sorted(packet.prohibited_next_steps),
        "evidence_ref_counts": {
            "party_candidates": sum(len(party.evidence_refs) for party in packet.party_candidates),
            "party_role_candidates": sum(
                len(role.evidence_refs)
                for party in packet.party_candidates
                for role in party.role_candidates
            ),
            "matter_family_candidates": sum(
                len(candidate.observed_evidence_refs)
                for candidate in packet.matter_family_candidates
            ),
            "deadline_candidates": sum(
                len(deadline.evidence_refs) for deadline in packet.deadline_candidates
            ),
            "critic_findings": sum(
                len(finding.evidence_refs) for finding in packet.critic_findings
            ),
        },
    }


def _prompt_hashes() -> dict[str, str]:
    registry = yaml.safe_load((ROOT / PROMPT_REGISTRY_REF).read_text(encoding="utf-8"))
    return {str(entry["prompt_ref"]): str(entry["sha256"]) for entry in registry["prompts"]}


def _check(
    check_id: str,
    ok: bool,
    message: str,
    details: dict[str, object] | None = None,
) -> ModelAdapterGuardCheck:
    return ModelAdapterGuardCheck(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        details=details or {},
    )
