"""LW0 — end-to-end deterministic synthetic case pipeline harness.

``run_synthetic_case_pipeline`` composes the existing modules into one canonical
chain and returns a single typed ``SyntheticCasePipelineResult`` that reconciles
every stage fail-closed:

    intake bundle -> route (deterministic router, abstain-aware)
                  -> confirm matter family FROM GENERATOR GROUND TRUTH
                  -> build_budget_proposal (deterministic dollars from governed rates)
                  -> carrier-compliant projection (typed blocked, no default carrier)
                  -> case_sizing (proportionality band, fail-closed on a missing band)
                  -> firm-Excel export (dollars per UTBMS task; role/rate/hours internal)

Boundaries (non-negotiable): dollars are ALWAYS deterministic from governed rates;
the immutable work-plan total is never overwritten by reimbursement math; every
joint is typed and a ``None`` stage (abstained route, unselected pack, missing
band) never serializes as success; the confirmation is generator ground truth,
never human review (human confirmation remains the production authority). This is
a synthetic, candidate-only review harness; it authorizes no budget, submission,
or matter action.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .budget_exporters import firm_excel_export_from_budget
from .case_sizing import (
    CASE_SIZING_POLICY_REF,
    build_case_sizing_report,
    load_case_sizing_policy,
)
from .canonical_pricing import build_canonical_priced_work_plan
from .confirmation import bind_confirmation_to_packet_evidence
from .driver_taxonomy import build_canonical_driver_profile
from .models import (
    HumanConfirmation,
    PipelineBudgetStage,
    PipelineCanonicalPricingStage,
    PipelineConfirmStage,
    PipelineExportStage,
    PipelineRouteStage,
    PipelineSizingStage,
    SyntheticCasePipelineResult,
    SyntheticCasePipelineSpec,
)
from .routing_eval import route_decision
from .util import digest_json, load_json, now_iso, write_json
from .workflow import run_budget, run_preflight


def _minor(dollars: float | None) -> int | None:
    """Exact integer minor units from a governed-rate dollar amount."""

    if dollars is None:
        return None
    return int(round(dollars * 100))


def _work_plan_total_minor_units(budget: Any) -> int:
    """Recompute the work-plan total in exact minor units from budget lines.

    Uses the same per-line rounding as the firm-Excel exporter so the export total
    reconciles to this value exactly (fail-closed cross-stage money check).
    """

    total = 0
    for line in budget.lines:
        total += int(round((line.estimated_fees or 0.0) * 100))
        total += int(round(line.estimated_expenses * 100))
    return total


def _route_stage(packet: Any, ground_truth_family: str) -> PipelineRouteStage:
    routed_family, decision, reason = route_decision(packet.matter_family_candidates)
    if decision == "route":
        return PipelineRouteStage(
            status="routed",
            ground_truth_family=ground_truth_family,
            routed_family=routed_family,
            decision_reason=reason,
            matched_ground_truth=routed_family == ground_truth_family,
        )
    return PipelineRouteStage(
        status="abstained",
        ground_truth_family=ground_truth_family,
        routed_family=None,
        decision_reason=reason,
        matched_ground_truth=False,
    )


def _confirm_stage(
    *, confirmation: HumanConfirmation, ground_truth_family: str
) -> PipelineConfirmStage:
    confirmed = confirmation.confirmed_matter_family or ""
    return PipelineConfirmStage(
        confirmation_source="generator_ground_truth",
        confirmed_matter_family=confirmed,
        ground_truth_family=ground_truth_family,
        matched_ground_truth=confirmed == ground_truth_family,
    )


def _budget_stage(budget: Any) -> PipelineBudgetStage:
    if budget.pricing_status != "priced" or budget.total_proposed_budget is None:
        return PipelineBudgetStage(
            status="blocked_no_price",
            work_plan_total_minor_units=None,
            projection_status="blocked_no_pack",
            guideline_adjusted_reimbursement_minor_units=None,
        )
    projection = budget.carrier_compliant_projection
    if projection is None or projection.status != "projected_for_human_review":
        return PipelineBudgetStage(
            status="priced",
            work_plan_total_minor_units=_work_plan_total_minor_units(budget),
            projection_status="blocked_no_pack",
            guideline_adjusted_reimbursement_minor_units=None,
        )
    return PipelineBudgetStage(
        status="priced",
        work_plan_total_minor_units=_work_plan_total_minor_units(budget),
        projection_status="projected",
        guideline_adjusted_reimbursement_minor_units=_minor(projection.compliant_total),
    )


def _sizing_stage(
    *,
    spec: SyntheticCasePipelineSpec,
    policy: dict[str, Any],
    generated_at: str,
) -> PipelineSizingStage:
    bands = policy.get("proportionality_bands", {})
    if spec.case_type not in bands:
        # Fail-closed: no declared band -> not evaluable, never a silent pass.
        return PipelineSizingStage(status="blocked_no_band", case_type=spec.case_type)
    report = build_case_sizing_report(
        case_type=spec.case_type,
        base_work_plan_total_minor_units=spec.base_work_plan_total_minor_units,
        drivers=spec.sizing_drivers,
        posture_input=spec.posture_input,
        policy=policy,
        generated_at=generated_at,
    )
    return PipelineSizingStage(
        status="sized",
        case_type=spec.case_type,
        case_sizing_report_id=report.case_sizing_report_id,
        sized_work_plan_total_minor_units=(
            report.sized_work_plan.sized_work_plan_total_minor_units
        ),
        proportionality_status=report.proportionality.status,
    )


def _export_stage(budget: Any) -> PipelineExportStage:
    if budget.pricing_status != "priced" or not budget.lines:
        return PipelineExportStage(status="not_exported")
    export = firm_excel_export_from_budget(budget)
    return PipelineExportStage(
        status="exported",
        firm_excel_export_id=export.export_id,
        firm_excel_original_total_minor_units=export.original_total_minor_units or 0,
    )


def _canonical_pricing_stage(
    spec: SyntheticCasePipelineSpec,
    sizing: PipelineSizingStage,
    *,
    root: Path,
    work_dir: Path,
) -> PipelineCanonicalPricingStage:
    """DT3: informational canonical-pricing stage riding alongside legacy sizing.

    Never blocks the chain: a failure here is a typed not_priced reason. Only the
    med-mal line is CLCM-mapped so far; other case types are typed accordingly."""

    if sizing.status != "sized":
        return PipelineCanonicalPricingStage(status="not_priced", reason="sizing_blocked")
    if spec.case_type != "medical_malpractice":
        return PipelineCanonicalPricingStage(
            status="not_priced",
            reason=f"line_not_yet_clcm_mapped:{spec.case_type}",
        )
    try:
        profile = build_canonical_driver_profile(spec.sizing_drivers, repo_root=root)
        plan = build_canonical_priced_work_plan(profile, repo_root=root)
    except Exception as exc:  # typed for review, never a silent drop or a block
        return PipelineCanonicalPricingStage(
            status="not_priced", reason=f"canonical_pricing_unavailable:{exc}"
        )
    canonical_dir = work_dir / "canonical"
    canonical_dir.mkdir(parents=True, exist_ok=True)
    write_json(canonical_dir / "canonical_priced_work_plan.json", plan.model_dump(mode="json"))
    return PipelineCanonicalPricingStage(
        status="priced_candidate",
        profile_id=profile.profile_id,
        plan_id=plan.plan_id,
        contract_digest=plan.contract_digest,
        canonical_total_minor_units=plan.total_dollars_minor_units,
        legacy_sized_total_minor_units=sizing.sized_work_plan_total_minor_units,
        neutral_assumed_driver_count=len(profile.not_elicited_driver_ids),
        required_missing_driver_ids=list(profile.required_missing_driver_ids),
    )


def run_synthetic_case_pipeline(
    spec: SyntheticCasePipelineSpec,
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> SyntheticCasePipelineResult:
    """Compose the full synthetic case pipeline into one reconciled typed result."""

    root = Path(repo_root)
    work_dir = Path(out_dir)
    stamp = generated_at or now_iso()

    profile_path = root / spec.profile_ref
    packet, preflight_dir = run_preflight(
        root / spec.inbound_ref,
        profile_path,
        work_dir / "preflight",
    )

    route = _route_stage(packet, spec.ground_truth_family)

    raw = load_json(root / spec.confirmation_template_ref)
    raw["preflight_packet_id"] = packet.packet_id
    confirmation = bind_confirmation_to_packet_evidence(
        packet, HumanConfirmation.model_validate(raw)
    )
    confirm = _confirm_stage(
        confirmation=confirmation, ground_truth_family=spec.ground_truth_family
    )

    confirmation_path = work_dir / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")
    budget, _budget_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        profile_path,
        work_dir / "budget",
    )
    budget_stage = _budget_stage(budget)

    policy = load_case_sizing_policy(root / CASE_SIZING_POLICY_REF)
    sizing = _sizing_stage(spec=spec, policy=policy, generated_at=stamp)

    export = _export_stage(budget)

    canonical = _canonical_pricing_stage(spec, sizing, root=root, work_dir=work_dir)

    blocked: list[str] = []
    if route.status != "routed":
        blocked.append(f"route:{route.decision_reason}")
    if budget_stage.status != "priced":
        blocked.append("budget:blocked_no_price")
    if budget_stage.projection_status != "projected":
        blocked.append("projection:blocked_no_pack")
    if sizing.status != "sized":
        blocked.append("sizing:blocked_no_band")
    if export.status != "exported":
        blocked.append("export:not_exported")

    digest_basis = {
        "case_id": spec.case_id,
        "ground_truth_family": spec.ground_truth_family,
        "route_status": route.status,
        "routed_family": route.routed_family,
        "confirmed_family": confirm.confirmed_matter_family,
        "budget_status": budget_stage.status,
        "work_plan_total_minor_units": budget_stage.work_plan_total_minor_units,
        "projection_status": budget_stage.projection_status,
        "reimbursement_minor_units": (budget_stage.guideline_adjusted_reimbursement_minor_units),
        "sizing_status": sizing.status,
        "sized_total_minor_units": sizing.sized_work_plan_total_minor_units,
        "proportionality_status": sizing.proportionality_status,
        "export_status": export.status,
        "export_total_minor_units": export.firm_excel_original_total_minor_units,
        "canonical_status": canonical.status,
        "canonical_total_minor_units": canonical.canonical_total_minor_units,
        "blocked": sorted(blocked),
    }
    content_digest = digest_json(digest_basis)
    pipeline_result_id = "casepipeline-" + content_digest.removeprefix("sha256:")[:16]

    return SyntheticCasePipelineResult(
        pipeline_result_id=pipeline_result_id,
        case_id=spec.case_id,
        ground_truth_family=spec.ground_truth_family,
        route=route,
        confirm=confirm,
        budget=budget_stage,
        sizing=sizing,
        export=export,
        canonical=canonical,
        status="completed" if not blocked else "blocked",
        blocking_reasons=sorted(blocked),
        content_digest=content_digest,
        generated_at=stamp,
    )
