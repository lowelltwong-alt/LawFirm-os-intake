from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml

from .models import ModelAdapterGuardCheck, ModelAdapterReport
from .util import new_id, now_iso


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
        checks=checks,
        generated_at=now_iso(),
    )


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
