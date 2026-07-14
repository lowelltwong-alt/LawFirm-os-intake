from __future__ import annotations

from hashlib import sha256
from pathlib import Path
from typing import Any

from .budget_actuals import run_budget_actual_comparison
from .matter_linking_preflight import run_matter_linking_preflight
from .models import (
    BudgetActualsSource,
    BudgetProposal,
    CarrierRejectionCaptureSourceBundle,
    CrossRepoContractProofReport,
    PilotReviewStoryReport,
    PilotReviewStoryStage,
    SourceBundle,
)
from .util import digest_json, load_json, now_iso, write_json


PILOT_REVIEW_STORY_REPORT_FILENAME = "pilot_review_story_report.json"
PILOT_REVIEW_STORY_NOTES_FILENAME = "pilot_review_story_report.md"


def run_pilot_review_story(
    *,
    story_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[PilotReviewStoryReport, Path]:
    """Assemble one synthetic pilot narrative without authorizing a case action.

    The selected-matter linkage is deliberately a local candidate.  The generic
    cross-repo proof remains a platform-boundary proof and is never presented as
    evidence about the synthetic matter itself.
    """

    fixture_path = Path(story_path).resolve()
    payload = _object(load_json(fixture_path), "pilot review story fixture")
    root = fixture_path.parents[3]
    source_bundle_path = _resolve_fixture_ref(payload, "source_bundle_ref", root)
    budget_proposal_path = _resolve_fixture_ref(payload, "budget_proposal_ref", root)
    actuals_source_path = _resolve_fixture_ref(payload, "actuals_source_ref", root)
    carrier_rejection_path = _resolve_fixture_ref(payload, "carrier_rejection_ref", root)
    contract_proof_path = _resolve_fixture_ref(payload, "cross_repo_contract_proof_ref", root)

    source_bundle = SourceBundle.model_validate(load_json(source_bundle_path))
    budget = BudgetProposal.model_validate(load_json(budget_proposal_path))
    actuals_source = BudgetActualsSource.model_validate(load_json(actuals_source_path))
    carrier_bundle = CarrierRejectionCaptureSourceBundle.model_validate(
        load_json(carrier_rejection_path)
    )
    contract_proof = CrossRepoContractProofReport.model_validate(load_json(contract_proof_path))
    _validate_inputs(
        payload=payload,
        source_bundle=source_bundle,
        budget=budget,
        actuals_source=actuals_source,
        carrier_bundle=carrier_bundle,
        contract_proof=contract_proof,
    )

    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    matter_link_input = _build_matter_link_input(payload=payload, source_bundle=source_bundle)
    matter_link_input_path = write_json(
        run_dir / "pilot_review_story_matter_link_input.json", matter_link_input
    )
    matter_link_report, _ = run_matter_linking_preflight(
        input_path=matter_link_input_path,
        out_dir=run_dir / "matter-linking",
        generated_at=generated_at or now_iso(),
    )
    if matter_link_report.status != "matter_linking_preflight_resolved_candidate_requires_review":
        raise ValueError(
            "pilot review story requires a resolved candidate that remains review-bound"
        )
    if any(check.status == "failed" for check in matter_link_report.checks):
        raise ValueError("pilot review story matter-linking preflight contains failed checks")
    actuals_report, actuals_dir = run_budget_actual_comparison(
        budget_path=budget_proposal_path,
        actuals_path=actuals_source_path,
        out_dir=run_dir / "actuals",
        run_id="pilotactuals_"
        + digest_json(
            {
                "fixture": payload["pilot_review_story_id"],
                "budget_proposal_id": budget.budget_proposal_id,
                "actuals_source_id": actuals_source.actuals_source_id,
            }
        ).split(":", 1)[1][:20],
        comparison_report_id="pilotactualcomparison_"
        + digest_json(
            {
                "fixture": payload["pilot_review_story_id"],
                "budget_proposal_id": budget.budget_proposal_id,
                "actuals_source_id": actuals_source.actuals_source_id,
            }
        ).split(":", 1)[1][:20],
    )
    if actuals_report.status != "variance_review_required":
        raise ValueError("pilot review story requires review-gated synthetic actuals variance")

    source_hashes = _source_hashes(source_bundle)
    rejected_amount = sum(float(notice.amount_rejected) for notice in carrier_bundle.notices)
    recovered_amount = sum(
        float(result.recovered_amount) for result in carrier_bundle.appeal_results
    )
    write_down_amount = sum(
        float(result.write_down_amount) for result in carrier_bundle.appeal_results
    )
    stages = _stages(
        source_bundle_path=source_bundle_path,
        budget_proposal_path=budget_proposal_path,
        actuals_source_path=actuals_source_path,
        actuals_report_id=actuals_report.budget_actual_comparison_report_id,
        carrier_rejection_path=carrier_rejection_path,
        contract_proof_path=contract_proof_path,
        repo_root=root,
    )
    report = PilotReviewStoryReport(
        pilot_review_story_id="pilotreviewstory_"
        + digest_json(
            {
                "fixture": payload.get("pilot_review_story_id"),
                "source_bundle": digest_json(source_bundle.model_dump(mode="json")),
                "budget": budget.budget_proposal_id,
                "actuals": actuals_source.actuals_source_id,
                "carrier": carrier_bundle.bundle_id,
            }
        ).split(":", 1)[1][:20],
        status="ready_for_human_review",
        story_fixture_ref=_repo_ref(fixture_path, root),
        source_bundle_id=source_bundle.bundle_id,
        source_bundle_sha256=digest_json(source_bundle.model_dump(mode="json")),
        source_count=len(source_bundle.sources),
        source_hashes_by_id=source_hashes,
        selected_candidate_matter_label=str(payload["selected_candidate_matter_label"]),
        matter_linking_preflight_report_id=matter_link_report.matter_linking_preflight_report_id,
        matter_linking_state="resolved_single_candidate_pending_human_confirmation",
        official_matter_number_status="not_available",
        budget_proposal_id=budget.budget_proposal_id,
        budget_proposal_total=float(budget.total_proposed_budget),
        budget_pricing_status=budget.pricing_status,
        budget_display_state="withheld_pending_matter_link_and_role_review",
        carrier_projection_state="not_available_without_pinned_candidate_guideline",
        carrier_rejection_notice_count=len(carrier_bundle.notices),
        carrier_rejected_amount=rejected_amount,
        carrier_appeal_result_count=len(carrier_bundle.appeal_results),
        carrier_recovered_amount=recovered_amount,
        carrier_write_down_amount=write_down_amount,
        actuals_learning_state="synthetic_actuals_variance_requires_human_review_no_learning",
        actuals_source_id=actuals_source.actuals_source_id,
        actuals_source_ref=_repo_ref(actuals_source_path, root),
        budget_actual_comparison_report_id=actuals_report.budget_actual_comparison_report_id,
        actuals_total=float(actuals_report.total_actual),
        actuals_variance_amount=float(actuals_report.total_variance_amount),
        actuals_variance_percent=float(actuals_report.total_variance_percent),
        actuals_variance_status=actuals_report.status,
        cross_repo_contract_proof_status=contract_proof.status,
        cross_repo_contract_proof_scope="generic_synthetic_boundary_proof_not_case_evidence",
        stage_count=len(stages),
        stages=stages,
        candidate_exception_lake_labels=sorted(
            {
                *matter_link_report.candidate_exception_lake_labels,
                "budget_amount_withheld_pending_matter_link_and_role_review",
                "carrier_projection_missing_pinned_candidate_guideline",
                "carrier_rejection_observed_synthetic",
                "carrier_appeal_result_observed_synthetic",
                "labor_employment_actual_variance_candidate",
                "budget_actual_cost_variance_requires_review",
            }
        ),
        required_next_gates=[
            "human_matter_linking_review",
            "human_principal_party_role_confirmation",
            "human_budget_range_review",
            "pinned_candidate_guideline_before_carrier_projection",
            "owner_review_before_exception_lake_admission",
            "human_actuals_variance_review",
            "reviewed_learning_gate_before_candidate_changes",
        ],
        red_team_notes=[
            "The proposed budget is retained as synthetic candidate math, but its display is withheld until matter linkage and principal roles are confirmed.",
            "The synthetic carrier rejection and appeal records are observed outcome fixtures, not permission to submit, appeal, or learn from a live carrier response.",
            "Synthetic phase and code actuals produce a variance-review candidate only; they cannot calibrate a budget, rate, guideline, or model without a reviewed learning gate.",
            "No Granite Shield candidate guideline IR is pinned, so the dossier refuses to fabricate a carrier-compliant projection or a rate delta.",
            "The cross-repo contract proof verifies a generic synthetic no-write path only; it is not evidence about this pilot matter.",
        ],
        generated_at=generated_at or now_iso(),
    )
    write_json(run_dir / PILOT_REVIEW_STORY_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / PILOT_REVIEW_STORY_NOTES_FILENAME).write_text(
        render_pilot_review_story(report), encoding="utf-8"
    )
    return report, run_dir


def render_pilot_review_story(report: PilotReviewStoryReport) -> str:
    lines = [
        "# Pilot Review Story",
        "",
        f"**Story ID:** {report.pilot_review_story_id}",
        f"**Status:** {report.status}",
        f"**Candidate matter:** {report.selected_candidate_matter_label}",
        "",
        "## Review Path",
        "",
    ]
    for stage in report.stages:
        lines.append(f"- **{stage.label}:** {stage.status}. {stage.summary}")
    lines.extend(["", "## Required Gates", ""])
    lines.extend(f"- {gate}" for gate in report.required_next_gates)
    lines.extend(
        [
            "",
            "This is synthetic, candidate-only review evidence. It does not open a matter, clear conflicts, "
            "submit a budget or appeal, write to the Exception Lake/SQLite, or update a model or policy.",
            "",
        ]
    )
    return "\n".join(lines)


def _object(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object")
    return value


def _resolve_fixture_ref(payload: dict[str, Any], key: str, root: Path) -> Path:
    value = payload.get(key)
    if not isinstance(value, str) or not value:
        raise ValueError(f"pilot review story requires {key}")
    path = (root / value).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(f"pilot review story {key} must stay inside the repository") from exc
    if not path.is_file():
        raise ValueError(f"pilot review story {key} is missing: {path}")
    return path


def _repo_ref(path: Path, root: Path) -> str:
    """Keep emitted evidence portable across clean worktrees and CI runners."""

    return path.resolve().relative_to(root.resolve()).as_posix()


def _validate_inputs(
    *,
    payload: dict[str, Any],
    source_bundle: SourceBundle,
    budget: BudgetProposal,
    actuals_source: BudgetActualsSource,
    carrier_bundle: CarrierRejectionCaptureSourceBundle,
    contract_proof: CrossRepoContractProofReport,
) -> None:
    required = {
        "pilot_review_story_id",
        "selected_candidate_matter_label",
        "source_bundle_ref",
        "budget_proposal_ref",
        "carrier_rejection_ref",
        "cross_repo_contract_proof_ref",
    }
    missing = sorted(key for key in required if not payload.get(key))
    if missing:
        raise ValueError(f"pilot review story is missing required fields: {', '.join(missing)}")
    if (
        payload.get("data_origin") != "synthetic"
        or payload.get("candidate_only") is not True
        or payload.get("non_authoritative") is not True
    ):
        raise ValueError("pilot review story fixture must be synthetic and candidate-only")
    if source_bundle.data_origin != "synthetic" or any(
        (
            source_bundle.contains_real_client_data,
            source_bundle.contains_real_matter_data,
            source_bundle.contains_privileged_data,
        )
    ):
        raise ValueError("pilot review story accepts synthetic no-real-data source bundles only")
    if budget.matter_family != "epli_carrier_assignment":
        raise ValueError("pilot review story requires an EPLI carrier-assignment budget")
    if budget.approval_state != "proposed_for_human_review":
        raise ValueError("pilot review story budget must remain proposed for human review")
    if not budget.not_authorized_for_client_submission:
        raise ValueError("pilot review story budget must remain non-submittable")
    if actuals_source.budget_proposal_id not in {
        None,
        "__BUDGET_PROPOSAL_ID__",
        budget.budget_proposal_id,
    }:
        raise ValueError("pilot review story actuals source must match the EPLI budget proposal")
    if not actuals_source.actuals_by_phase or not actuals_source.actuals_by_code:
        raise ValueError("pilot review story requires phase and code actuals for review")
    if not carrier_bundle.data_origin == "synthetic" or any(
        (
            carrier_bundle.contains_real_client_data,
            carrier_bundle.contains_real_matter_data,
            carrier_bundle.contains_privileged_data,
        )
    ):
        raise ValueError("pilot review story accepts synthetic no-real-data carrier evidence only")
    if not carrier_bundle.notices or not carrier_bundle.appeal_results:
        raise ValueError(
            "pilot review story requires synthetic rejection and appeal-result evidence"
        )
    notice_ids = [notice.notice_id for notice in carrier_bundle.notices]
    if len(set(notice_ids)) != len(notice_ids):
        raise ValueError("pilot review story refuses duplicate carrier rejection notices")
    appeal_ids = [result.appeal_result_id for result in carrier_bundle.appeal_results]
    if len(set(appeal_ids)) != len(appeal_ids):
        raise ValueError("pilot review story refuses duplicate carrier appeal results")
    if any(result.related_notice_id not in notice_ids for result in carrier_bundle.appeal_results):
        raise ValueError(
            "pilot review story appeal result must reference an observed rejection notice"
        )
    if not all(result.append_only for result in carrier_bundle.appeal_results):
        raise ValueError("pilot review story appeal results must remain append-only")
    if contract_proof.status != "passed_candidate_contract_proof":
        raise ValueError("pilot review story requires a passed generic candidate contract proof")


def _source_hashes(source_bundle: SourceBundle) -> dict[str, str]:
    return {
        source.source_id: "sha256:" + sha256(source.text.encode("utf-8")).hexdigest()
        for source in source_bundle.sources
    }


def _build_matter_link_input(
    *, payload: dict[str, Any], source_bundle: SourceBundle
) -> dict[str, Any]:
    source_ids = {source.source_id for source in source_bundle.sources}
    required_ids = {
        "syn-pilot-epli-assignment-email-001",
        "syn-pilot-epli-followup-001",
        "syn-pilot-epli-guideline-001",
    }
    if not required_ids.issubset(source_ids):
        raise ValueError("pilot source bundle is missing required matter-link evidence sources")
    text_by_id = {source.source_id: source.text for source in source_bundle.sources}
    required_evidence = {
        "syn-pilot-epli-assignment-email-001": [
            "GS-EPLI-2026-1042",
            "Brightline Foods Inc.",
            "Talia Nguyen",
        ],
        "syn-pilot-epli-followup-001": ["GS-EPLI-2026-1042", "UPF-SYN-EPLI-2270"],
    }
    missing_evidence = [
        f"{source_id}:{term}"
        for source_id, terms in required_evidence.items()
        for term in terms
        if term not in text_by_id[source_id]
    ]
    if missing_evidence:
        raise ValueError(
            "pilot source bundle is missing declared matter-link evidence: "
            + ", ".join(missing_evidence)
        )
    hashes = _source_hashes(source_bundle)
    inventory = [
        {
            "source_id": source.source_id,
            "source_kind": source.source_type,
            "file_name": source.filename,
            "source_hash": hashes[source.source_id],
            "coverage_state": "read",
            "document_cluster_candidate_ids": ["cluster.epli-brightline"],
        }
        for source in source_bundle.sources
    ]
    return {
        "schema_version": "0.1",
        "artifact_id": f"{payload['pilot_review_story_id']}.matter-link-input.v0_1",
        "artifact_type": "upfront_like_intake_output_candidate",
        "status": "resolved_candidate_requires_human_confirmation",
        "data_origin": "synthetic",
        "candidate_only": True,
        "synthetic_only": True,
        "non_authoritative": True,
        "source_system": {
            "system_name": "Upfront-like intake output",
            "real_upfront_export": False,
            "api_contract_verified": False,
        },
        "intake_request": {
            "intake_request_id": "UPF-SYN-EPLI-2270",
            "request_channel": "email_forwarded_to_intake",
        },
        "source_inventory": inventory,
        "external_references": [
            {
                "reference_type": "carrier_claim_number",
                "reference_value": "GS-EPLI-2026-1042",
                "strength": "strong",
                "source_ref": "syn-pilot-epli-assignment-email-001:body",
            },
            {
                "reference_type": "upfront_like_request_id",
                "reference_value": "UPF-SYN-EPLI-2270",
                "strength": "strong",
                "source_ref": "syn-pilot-epli-followup-001:body",
            },
        ],
        "matter_linking": {
            "official_matter_number_status": "not_available",
            "overall_link_state": "resolved_single_candidate_pending_human_confirmation",
            "requires_human_confirmation": True,
            "requires_sender_followup": False,
            "candidate_clusters": [
                {
                    "cluster_id": "cluster.epli-brightline",
                    "link_state": "resolved_candidate_pending_human_confirmation",
                    "match_strength": "resolved_high_evidence_candidate_not_authorized",
                    "proposed_short_label": payload["selected_candidate_matter_label"],
                    "source_ids": [
                        "syn-pilot-epli-assignment-email-001",
                        "syn-pilot-epli-followup-001",
                        "syn-pilot-epli-guideline-001",
                    ],
                    "supporting_signals": [
                        {
                            "signal_type": "carrier_claim_number",
                            "signal_value": "GS-EPLI-2026-1042",
                            "source_refs": ["syn-pilot-epli-assignment-email-001:body"],
                            "weight_class": "strong",
                        },
                        {
                            "signal_type": "party_pair",
                            "signal_value": "Brightline Foods Inc. / Talia Nguyen",
                            "source_refs": ["syn-pilot-epli-assignment-email-001:body"],
                            "weight_class": "strong",
                        },
                        {
                            "signal_type": "upfront_like_request_id",
                            "signal_value": "UPF-SYN-EPLI-2270",
                            "source_refs": ["syn-pilot-epli-followup-001:body"],
                            "weight_class": "strong",
                        },
                    ],
                    "negative_signals": [],
                }
            ],
            "weak_signals_not_sufficient_for_merge": [
                {
                    "signal_type": "same_sender",
                    "signal_value": "claimsdesk@granite-shield-epli.example",
                    "source_refs": ["syn-pilot-epli-assignment-email-001:headers"],
                    "reason": "A shared claims desk can send unrelated assignments.",
                },
                {
                    "signal_type": "same_carrier",
                    "signal_value": "Granite Shield EPLI",
                    "source_refs": ["syn-pilot-epli-assignment-email-001:body"],
                    "reason": "Carrier identity does not identify a firm matter.",
                },
            ],
        },
        "candidate_exception_lake_labels": [
            "source_matter_link_resolved_candidate",
            "missing_official_matter_number",
            "human_matter_linking_confirmation_required",
        ],
        "output_boundaries": {
            "upfront_connector_implemented": False,
            "vendor_api_called": False,
            "external_write_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "matter_opening_authorized": False,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "conflict_conclusion_emitted": False,
            "screen_created": False,
            "silent_learning_performed": False,
        },
        "required_next_gates": [
            "human_matter_linking_review",
            "conflict_seed_review",
            "no_budget_amount_until_cluster_and_roles_confirmed",
            "no_matter_opening_without_official_authority",
            "no_lake_or_sqlite_write_from_matter_linking_preflight",
        ],
    }


def _stages(
    *,
    source_bundle_path: Path,
    budget_proposal_path: Path,
    actuals_source_path: Path,
    actuals_report_id: str,
    carrier_rejection_path: Path,
    contract_proof_path: Path,
    repo_root: Path,
) -> list[PilotReviewStoryStage]:
    return [
        PilotReviewStoryStage(
            stage_id="source_inventory",
            label="Source Inventory",
            status="passed",
            summary="Four synthetic assignment sources are hashed and retained as local review evidence.",
            artifact_ref=_repo_ref(source_bundle_path, repo_root),
            evidence_refs=["syn-pilot-epli-assignment-email-001", "syn-pilot-epli-followup-001"],
        ),
        PilotReviewStoryStage(
            stage_id="matter_linking",
            label="Matter Link",
            status="ready_for_human_review",
            summary="A source-bound EPLI assignment candidate is resolved, but it has no official firm matter number.",
            artifact_ref="run://pilot-review/matter-linking-input.json",
            evidence_refs=["GS-EPLI-2026-1042", "UPF-SYN-EPLI-2270"],
            required_next_gate="human_matter_linking_review",
        ),
        PilotReviewStoryStage(
            stage_id="party_roles",
            label="Party Roles",
            status="blocked",
            summary="Carrier, payer, TPA, insured, prospective client, claimant, and opposing counsel remain separate candidate roles.",
            artifact_ref=_repo_ref(source_bundle_path, repo_root),
            evidence_refs=["syn-pilot-epli-assignment-email-001"],
            required_next_gate="human_principal_party_role_confirmation",
        ),
        PilotReviewStoryStage(
            stage_id="budget",
            label="Budget Proposal",
            status="blocked",
            summary="Synthetic proposed math is preserved, but its display is withheld until matter linkage and principal roles are reviewed.",
            artifact_ref=_repo_ref(budget_proposal_path, repo_root),
            evidence_refs=["le-budget-epli-carrier-clean.v0_1"],
            required_next_gate="human_budget_range_review",
        ),
        PilotReviewStoryStage(
            stage_id="carrier_projection",
            label="Carrier Projection",
            status="not_available",
            summary="No matching pinned candidate guideline IR exists, so the dossier does not invent a carrier-compliant total or delta.",
            artifact_ref=_repo_ref(source_bundle_path, repo_root),
            evidence_refs=["syn-pilot-epli-guideline-001"],
            required_next_gate="pinned_candidate_guideline_before_carrier_projection",
        ),
        PilotReviewStoryStage(
            stage_id="carrier_rejection",
            label="Rejection And Appeal",
            status="ready_for_human_review",
            summary="Synthetic portal/email response evidence is classified for review; no appeal is submitted by this workflow.",
            artifact_ref=_repo_ref(carrier_rejection_path, repo_root),
            evidence_refs=["le-notice-epli-staffing-4001", "le-notice-epli-preapproval-4002"],
            required_next_gate="owner_review_before_exception_lake_admission",
        ),
        PilotReviewStoryStage(
            stage_id="actuals_learning",
            label="Actuals And Learning",
            status="ready_for_human_review",
            summary="Synthetic phase and code actuals exceed review thresholds in discovery and mediation; the variance remains a no-learning candidate.",
            artifact_ref="run://pilot-review/actuals/budget_actual_comparison_report.json",
            evidence_refs=[
                _repo_ref(actuals_source_path, repo_root),
                actuals_report_id,
            ],
            required_next_gate="human_actuals_variance_review",
        ),
        PilotReviewStoryStage(
            stage_id="owner_handoff",
            label="Owner Handoff Boundary",
            status="passed",
            summary="A separate generic synthetic proof confirms owner validators preserve a no-write, owner-gated handoff boundary.",
            artifact_ref=_repo_ref(contract_proof_path, repo_root),
            evidence_refs=["passed_candidate_contract_proof"],
        ),
    ]
