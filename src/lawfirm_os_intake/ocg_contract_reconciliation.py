"""CW6 — contract reconciliation with the Substrate-owned OCG rule IR.

Proposes a candidate executable extension covering the rule kinds the vertical
needs (task-hour allowance, ordered attribution, applicability envelope), keeps a
LOCAL adapter + fixtures that author no canonical IDs, and runs read-only
conformance of the sibling billing-guideline-simulator (a read-only challenger)
against CW1 outputs — recording divergences, or a typed unavailable status when
the sibling is absent. Substrate-owner review is required before any promotion.
"""

from __future__ import annotations

from pathlib import Path

from .guidelines import (
    build_carrier_compliant_projection,
    load_carrier_guideline,
    select_pack,
)
from .models import (
    BudgetProposal,
    OCGContractReconciliationReport,
    OCGProposedRuleKind,
    OCGRuleKindExtensionProposal,
    OCGSharedRuleIR,
    OCGSharedRuleIRRule,
    SiblingConformanceReport,
)
from .ocg_rule_ir import (
    SUBSTRATE_OWNER,
    OCG_IR_PROHIBITED_ACTIONS,
    RULE_ID_PREFIX,
    build_ocg_rule_ir_adoption_report,
)
from .util import digest_json, load_json, now_iso

LOCAL_ADAPTER_REF = "src/lawfirm_os_intake/ocg_contract_reconciliation.py"
SIBLING_REPO_REF = "billing-guideline-simulator (sibling; read-only challenger)"
_DEFAULT_BUDGET_REF = "examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/legal_budget_proposal.json"
_GUIDELINE_REF = "config/synthetic-carrier-guideline.yaml"


def build_extension_proposal() -> OCGRuleKindExtensionProposal:
    kinds = [
        OCGProposedRuleKind(
            proposed_kind="task_hour_allowance",
            rationale=(
                "The vertical needs an aggregate task x role hour allowance rule; the current "
                "OCG IR expresses rate/expense caps but not a task-hour allowance action."
            ),
            nearest_existing_family="staffing",
            candidate_local_marker="intake-candidate::extension::task_hour_allowance",
        ),
        OCGProposedRuleKind(
            proposed_kind="ordered_attribution",
            rationale=(
                "The vertical needs a declared, non-commutative attribution order for stacked "
                "rule effects; the current OCG IR has no ordering contract."
            ),
            nearest_existing_family="metadata",
            candidate_local_marker="intake-candidate::extension::ordered_attribution",
        ),
        OCGProposedRuleKind(
            proposed_kind="applicability_envelope",
            rationale=(
                "The vertical needs a typed applicability envelope (carrier/program/"
                "jurisdiction/as-of) so a missing context blocks fail-closed; the current OCG IR "
                "does not carry applicability selection."
            ),
            nearest_existing_family="metadata",
            candidate_local_marker="intake-candidate::extension::applicability_envelope",
        ),
    ]
    basis = {"kinds": [kind.proposed_kind for kind in kinds]}
    return OCGRuleKindExtensionProposal(
        proposal_id="ocgext-" + digest_json(basis).removeprefix("sha256:")[:16],
        proposed_kinds=kinds,
        local_adapter_ref=LOCAL_ADAPTER_REF,
    )


def build_local_adapter_ir(projection, *, generated_at: str) -> OCGSharedRuleIR:
    """Express the vertical's rules as a candidate OCG IR with local, non-canonical IDs."""

    basis = projection.basis
    rules: list[OCGSharedRuleIRRule] = []
    for role, cap in sorted(basis.rate_caps.items()):
        rules.append(
            OCGSharedRuleIRRule(
                rule_id=f"{RULE_ID_PREFIX}rate_cap::{role}",
                rule_family="rate_cap",
                label=f"Candidate rate cap for {role}",
                action_type="cap_rate",
                impact_bucket="rate_cap_delta",
                applies_to={"role": role, "cap": cap},
            )
        )
    for code, cap in sorted(basis.expense_caps.items()):
        rules.append(
            OCGSharedRuleIRRule(
                rule_id=f"{RULE_ID_PREFIX}expense_cap::{code}",
                rule_family="expense_cap",
                label=f"Candidate expense cap for {code}",
                action_type="cap_expense",
                impact_bucket="expense_cap_delta",
                applies_to={"expense_code": code, "cap": cap},
            )
        )
    # The three proposed extension kinds are carried as candidate metadata rules that
    # point at the proposed Substrate extension — never as canonical rules.
    for kind in ("task_hour_allowance", "ordered_attribution", "applicability_envelope"):
        rules.append(
            OCGSharedRuleIRRule(
                rule_id=f"{RULE_ID_PREFIX}extension::{kind}",
                rule_family="metadata",
                label=f"Proposed extension marker: {kind}",
                action_type="metadata_only",
                impact_bucket="metadata_only",
                applies_to={"proposed_extension": kind, "requires_substrate_owner_review": True},
            )
        )
    return OCGSharedRuleIR(
        rule_ir_id="intake-candidate-ocg-ir-adapter",
        source_owner=SUBSTRATE_OWNER,
        source_artifact_ref=_GUIDELINE_REF,
        source_version_or_date=generated_at,
        retrieved_at=generated_at,
        rules=rules,
        prohibited_actions=list(OCG_IR_PROHIBITED_ACTIONS),
    )


def run_sibling_conformance(
    *, repo_root: str | Path, checked_refs: list[str]
) -> SiblingConformanceReport:
    """Read-only conformance vs the sibling simulator; fail-closed if it is absent."""

    root = Path(repo_root)
    candidate_paths = [
        root.parent / "billing-guideline-simulator" / "src" / "billing_guideline_sim",
        root / "src" / "billing_guideline_sim",
    ]
    sibling_path = next((path for path in candidate_paths if path.exists()), None)
    if sibling_path is None:
        return SiblingConformanceReport(
            sibling_repo_ref=SIBLING_REPO_REF,
            sibling_available=False,
            status="blocked_sibling_unavailable",
            checked_cw1_output_refs=checked_refs,
            divergences=[],
            recorded_reason=(
                "Sibling billing-guideline-simulator is not present in this workspace; read-only "
                "conformance is recorded as blocked rather than assumed passing. The CW1 outputs "
                "above are the frozen inputs a future conformance run must diff against."
            ),
        )
    # If the sibling is present, a future runner would compile its IR and diff against
    # the CW1 outputs. Until that runner is wired, record availability without asserting
    # a passing result.
    return SiblingConformanceReport(
        sibling_repo_ref=str(sibling_path),
        sibling_available=True,
        status="blocked_sibling_unavailable",
        checked_cw1_output_refs=checked_refs,
        divergences=[],
        recorded_reason=(
            "Sibling present but the cross-engine diff runner is not wired in this wave; "
            "recorded as blocked rather than assumed passing."
        ),
    )


def build_ocg_contract_reconciliation_report(
    *, repo_root: str | Path, generated_at: str | None = None
) -> OCGContractReconciliationReport:
    root = Path(repo_root)
    generated = generated_at or now_iso()
    budget = BudgetProposal.model_validate(load_json(root / _DEFAULT_BUDGET_REF))
    guideline = load_carrier_guideline(root / _GUIDELINE_REF)
    selection = select_pack(guideline, carrier_id="synthetic-carrier-a")
    projection = build_carrier_compliant_projection(
        budget,
        guideline=guideline,
        guideline_ref=_GUIDELINE_REF,
        carrier_id=selection.selected_pack_id,
    )
    if projection is None:
        raise ValueError("contract reconciliation requires a resolved CW1 projection")

    adapter_ir = build_local_adapter_ir(projection, generated_at=generated)
    adoption = build_ocg_rule_ir_adoption_report(budget, projection, adapter_ir)
    proposal = build_extension_proposal()
    conformance = run_sibling_conformance(
        repo_root=root,
        checked_refs=[
            f"carrier_compliant_projection:{budget.budget_proposal_id}:{selection.selected_pack_id}",
            f"adjustment_ledger:{budget.budget_proposal_id}:{selection.selected_pack_id}",
            f"pack_selection:{selection.selected_pack_id}",
        ],
    )

    basis = {"proposal": proposal.proposal_id, "adapter": adapter_ir.rule_ir_id}
    return OCGContractReconciliationReport(
        report_id="ocgrecon-" + digest_json(basis).removeprefix("sha256:")[:16],
        extension_proposal=proposal,
        adapter_rule_ir_id=adapter_ir.rule_ir_id,
        adapter_canonical_rule_id_violation_count=adoption.canonical_rule_id_violation_count,
        adapter_source_owner_violation_count=adoption.source_owner_violation_count,
        adapter_blocker_count=sum(
            1 for finding in adoption.findings if finding.severity == "blocker"
        ),
        sibling_conformance=conformance,
        generated_at=generated,
    )
