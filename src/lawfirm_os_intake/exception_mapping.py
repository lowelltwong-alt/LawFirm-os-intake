from __future__ import annotations

from collections.abc import Iterable

from .models import (
    ExceptionLakeCandidate,
    ExceptionLakeMappingCheck,
    ExceptionLakeMappingPackage,
    ExceptionLakeMappingRule,
    IntakePreflightPacket,
)
from .util import new_id, now_iso


RULE_DEFINITIONS = [
    {
        "mapping_id": "budget_form_original_budget_formula_broken.v1",
        "issue_family": "broken_template_formula",
        "local_event_label": "budget_form_original_formula_broken",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "Carrier workbook original-budget total, phase subtotal, or task remaining formula "
            "is missing or inconsistent."
        ),
        "support_ref_kinds": ["budget_form_mapping_report", "structured_ref"],
        "structured_refs": ["docs/budget-template-checklist.md#formula-policy"],
    },
    {
        "mapping_id": "budget_form_code_mapping_missing.v1",
        "issue_family": "missing_budget_code_mapping",
        "local_event_label": "budget_form_code_mapping_missing",
        "canonical_lake_class": "retrieval_miss",
        "trigger_summary": (
            "A proposed budget L/E code cannot be mapped to exactly one workbook row/write cell."
        ),
        "support_ref_kinds": ["budget_form_mapping_report", "budget_proposal"],
        "structured_refs": ["docs/budget-template-checklist.md#utbms-row-coverage"],
    },
    {
        "mapping_id": "budget_unknown_driver_requires_review.v1",
        "issue_family": "unknown_budget_driver",
        "local_event_label": "budget_unknown_driver_requires_review",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A budget driver is unknown or only profile-defaulted and requires human review."
        ),
        "support_ref_kinds": ["budget_proposal", "structured_ref"],
        "structured_refs": ["config/budget-driver-policy.yaml#drivers"],
    },
    {
        "mapping_id": "budget_guideline_or_cap_requires_review.v1",
        "issue_family": "guideline_or_cap_issue",
        "local_event_label": "budget_guideline_or_cap_requires_review",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A synthetic guideline, cap, or unknown-guideline condition requires human review."
        ),
        "support_ref_kinds": ["budget_proposal", "structured_ref"],
        "structured_refs": ["config/budget-driver-policy.yaml#synthetic_guideline_constraints"],
    },
    {
        "mapping_id": "carrier_preapproval_required.v1",
        "issue_family": "carrier_preapproval_required",
        "local_event_label": "carrier_preapproval_required",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A synthetic carrier guideline preapproval threshold was exceeded and requires "
            "human carrier preapproval review before any carrier-facing submission."
        ),
        "support_ref_kinds": [
            "carrier_preapproval_report",
            "budget_proposal",
            "structured_ref",
        ],
        "structured_refs": [
            "config/synthetic-carrier-guideline.yaml#pre_approval_thresholds",
            "docs/carrier-rate-and-guideline-layer-design.md#d-pre-approval-thresholds--escalationexception-integration",
        ],
    },
    {
        "mapping_id": "budget_human_change_recorded.v1",
        "issue_family": "human_budget_change",
        "local_event_label": "budget_human_change_recorded",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A human budget correction, revision, or superseding decision was recorded and "
            "should be preserved as append-only evidence."
        ),
        "support_ref_kinds": [
            "budget_change_record",
            "budget_revision_report",
            "budget_proposal",
            "structured_ref",
        ],
        "structured_refs": ["docs/human-review.md#budget-review"],
    },
    {
        "mapping_id": "budget_actual_cost_variance_requires_review.v1",
        "issue_family": "budget_actual_cost_variance",
        "local_event_label": "budget_actual_cost_variance_requires_review",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "Phase-level or UTBMS-code actual cost differs from the comparison budget outside "
            "the review threshold and requires human pricing review."
        ),
        "support_ref_kinds": [
            "budget_actual_comparison_report",
            "budget_proposal",
            "structured_ref",
        ],
        "structured_refs": ["docs/legal-budget-design.md#actuals-comparison-boundary"],
    },
    {
        "mapping_id": "carrier_rejection_notice_received.v1",
        "issue_family": "carrier_rejection_capture",
        "local_event_label": "carrier_rejection_notice_received",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A carrier rejection or partial rejection notice was captured and linked to a "
            "known synthetic submission."
        ),
        "support_ref_kinds": [
            "carrier_rejection_reconciliation_report",
            "carrier_rejection_remediation_case",
        ],
        "structured_refs": [
            "docs/carrier-rejection-learning-loop-roadmap.md#candidate-rejection-classes"
        ],
    },
    {
        "mapping_id": "carrier_rejection_duplicate_notice.v1",
        "issue_family": "carrier_rejection_reconciliation",
        "local_event_label": "carrier_rejection_duplicate_notice",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "Multiple carrier notices collapsed to one logical rejection by deterministic "
            "idempotency key."
        ),
        "support_ref_kinds": [
            "carrier_rejection_reconciliation_report",
            "carrier_rejection_remediation_case",
        ],
        "structured_refs": [
            "docs/carrier-rejection-learning-loop-roadmap.md#deterministic-completeness"
        ],
    },
    {
        "mapping_id": "carrier_rejection_unlinked.v1",
        "issue_family": "carrier_rejection_reconciliation",
        "local_event_label": "carrier_rejection_unlinked",
        "canonical_lake_class": "retrieval_miss",
        "trigger_summary": (
            "A carrier rejection notice could not be linked to a known submitted budget, "
            "invoice, appeal, or portal action."
        ),
        "support_ref_kinds": [
            "carrier_rejection_reconciliation_report",
            "carrier_rejection_remediation_case",
        ],
        "structured_refs": [
            "docs/carrier-rejection-learning-loop-roadmap.md#deterministic-completeness"
        ],
    },
    {
        "mapping_id": "carrier_response_missing_after_sla.v1",
        "issue_family": "carrier_rejection_reconciliation",
        "local_event_label": "carrier_response_missing_after_sla",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "An expected carrier response was not captured by its configured review SLA."
        ),
        "support_ref_kinds": [
            "carrier_rejection_reconciliation_report",
            "carrier_rejection_remediation_case",
        ],
        "structured_refs": [
            "docs/carrier-rejection-learning-loop-roadmap.md#deterministic-completeness"
        ],
    },
    {
        "mapping_id": "carrier_appeal_result_received.v1",
        "issue_family": "carrier_rejection_appeal_result",
        "local_event_label": "carrier_appeal_result_received",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A carrier appeal result was captured as append-only outcome evidence."
        ),
        "support_ref_kinds": [
            "carrier_rejection_reconciliation_report",
            "carrier_appeal_result",
        ],
        "structured_refs": [
            "docs/carrier-rejection-learning-loop-roadmap.md#follow-up-and-appeal-workflow"
        ],
    },
    {
        "mapping_id": "carrier_rejection_learning_candidate.v1",
        "issue_family": "carrier_rejection_learning",
        "local_event_label": "carrier_rejection_learning_candidate",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A reviewed carrier rejection outcome may support a future guideline, budget-driver, "
            "template, narrative-rule, or preapproval candidate."
        ),
        "support_ref_kinds": [
            "carrier_rejection_reconciliation_report",
            "carrier_rejection_remediation_case",
        ],
        "structured_refs": ["docs/carrier-rejection-learning-loop-roadmap.md#learning-loops"],
    },
    {
        "mapping_id": "budget_invariant_violation.v1",
        "issue_family": "budget_invariant_violation",
        "local_event_label": "budget_invariant_violation",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A budget invariant report failed deterministic arithmetic, scope, scenario, "
            "or expected-value checks."
        ),
        "support_ref_kinds": ["budget_invariant_report", "budget_proposal", "structured_ref"],
        "structured_refs": [
            "docs/fable/budget-truth-kernel.md#3-invariant-table",
            "docs/decisions/TRACE-2026-07-06-bk1-budget-invariants.md",
            "docs/decisions/TRACE-2026-07-06-bk2-scenario-policy-hardening.md",
        ],
    },
    {
        "mapping_id": "scenario_policy_invalid.v1",
        "issue_family": "scenario_policy_invalid",
        "local_event_label": "scenario_policy_invalid",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "Budget scenario policy is invalid, including unknown resolution phases, "
            "non-monotonic scenario totals, or invalid probability weights."
        ),
        "support_ref_kinds": ["budget_proposal", "budget_invariant_report", "structured_ref"],
        "structured_refs": [
            "docs/fable/exception-learning-taxonomy.md#2-candidate-exception-classes-superset-taxonomy",
            "docs/decisions/TRACE-2026-07-06-bk2-scenario-policy-hardening.md",
        ],
    },
    {
        "mapping_id": "rate_resolution_ambiguous.v1",
        "issue_family": "rate_resolution_ambiguous",
        "local_event_label": "rate_resolution_ambiguous",
        "canonical_lake_class": "authority_conflict_override",
        "trigger_summary": (
            "Carrier, payer, jurisdiction, or role-rate authority is ambiguous enough that "
            "the budget must not silently price from defaults."
        ),
        "support_ref_kinds": ["budget_proposal", "structured_ref"],
        "structured_refs": [
            "docs/fable/budget-truth-kernel.md#2-where-the-system-must-block--widen--go-hours-only--require-confirmation",
            "docs/fable/exception-learning-taxonomy.md#5-severity-rules-deterministic",
        ],
    },
    {
        "mapping_id": "carrier_appeal_outcome.v1",
        "issue_family": "carrier_appeal_outcome",
        "local_event_label": "carrier_appeal_result_received",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A carrier appeal outcome was recorded and should be trended separately from "
            "the initial rejection capture event."
        ),
        "support_ref_kinds": [
            "carrier_rejection_reconciliation_report",
            "carrier_appeal_result",
        ],
        "structured_refs": [
            "docs/carrier-rejection-learning-loop-roadmap.md#follow-up-and-appeal-workflow",
            "docs/fable/exception-learning-taxonomy.md#2-candidate-exception-classes-superset-taxonomy",
        ],
    },
    {
        "mapping_id": "matter_link_ambiguity.v1",
        "issue_family": "matter_link_ambiguity",
        "local_event_label": "source_matter_link_ambiguous",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "Inbound material cannot be confidently linked to exactly one matter bundle "
            "and requires human matter-linking review."
        ),
        "support_ref_kinds": ["matter_linking_preflight_report", "structured_ref"],
        "structured_refs": [
            "docs/fable/matter-linking-hard-kernel.md#codex-handoff-pr-sized",
            "docs/integrations/upfront-intake-integration-research.md#matter-linking",
        ],
    },
    {
        "mapping_id": "matter_link_conflict.v1",
        "issue_family": "matter_link_conflict",
        "local_event_label": "source_matter_link_conflicting_identifiers",
        "canonical_lake_class": "authority_conflict_override",
        "trigger_summary": (
            "Strong matter-link identifiers conflict and block linkage until a human resolves "
            "the authority conflict."
        ),
        "support_ref_kinds": ["matter_linking_preflight_report", "structured_ref"],
        "structured_refs": [
            "docs/fable/matter-linking-hard-kernel.md#codex-handoff-pr-sized",
            "examples/synthetic/upfront/upfront-like-intake-output.conflicting-identifiers.example.json",
        ],
    },
    {
        "mapping_id": "entity_resolution_ambiguity.v1",
        "issue_family": "entity_resolution_ambiguity",
        "local_event_label": "entity_resolution_ambiguity_requires_review",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": "A source-bound entity comparison remains unresolved and requires a human decision.",
        "support_ref_kinds": ["entity_resolution_correction_report", "structured_ref"],
        "structured_refs": ["docs/fable/entity-resolution-boundary.md#4-holdreview-rules"],
    },
    {
        "mapping_id": "entity_resolution_declared_edge_correction.v1",
        "issue_family": "entity_resolution_declared_edge_correction",
        "local_event_label": "entity_resolution_declared_edge_correction",
        "canonical_lake_class": "authority_conflict_override",
        "trigger_summary": "A human correction supersedes a reviewed local alias or structural edge and requires owner review before any future use.",
        "support_ref_kinds": ["entity_resolution_correction_report", "structured_ref"],
        "structured_refs": [
            "docs/fable/entity-resolution-boundary.md#6-how-dad-learns-entity-resolution-mistakes-without-creating-canon"
        ],
    },
    {
        "mapping_id": "human_entity_resolution_correction.v1",
        "issue_family": "human_entity_resolution_correction",
        "local_event_label": "human_entity_resolution_correction",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": "A human entity-resolution correction is preserved as append-only candidate evidence without mutating the matcher.",
        "support_ref_kinds": ["entity_resolution_correction_report", "structured_ref"],
        "structured_refs": [
            "docs/fable/entity-resolution-boundary.md#6-how-dad-learns-entity-resolution-mistakes-without-creating-canon"
        ],
    },
    {
        "mapping_id": "human_correction_of_machine_output.v1",
        "issue_family": "human_correction_of_machine_output",
        "local_event_label": "human_correction_of_machine_output",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A human correction superseded a machine-generated classification, link, or "
            "budget candidate and should be counted as correction evidence."
        ),
        "support_ref_kinds": ["human_review_outcome_record", "structured_ref"],
        "structured_refs": [
            "docs/fable/exception-learning-taxonomy.md#4-dedupe-keys",
            "docs/human-review.md",
        ],
    },
    {
        "mapping_id": "qa_gate_defect.v1",
        "issue_family": "qa_gate_defect",
        "local_event_label": "qa_gate_defect",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A deterministic QA or replay gate failed on a path that previously claimed readiness."
        ),
        "support_ref_kinds": ["qa_gate_report", "structured_ref"],
        "structured_refs": [
            "docs/fable/exception-learning-taxonomy.md#7-anti-silent-learning-invariants"
        ],
    },
    {
        "mapping_id": "fixture_weakness.v1",
        "issue_family": "fixture_weakness",
        "local_event_label": "fixture_weakness",
        "canonical_lake_class": "retrieval_miss",
        "trigger_summary": (
            "A fixture, gold record, or holdout review revealed missing coverage or stale "
            "evaluation evidence."
        ),
        "support_ref_kinds": ["fixture_gold_report", "structured_ref"],
        "structured_refs": [
            "docs/fable/exception-learning-taxonomy.md#7-anti-silent-learning-invariants"
        ],
    },
    {
        "mapping_id": "workflow_discovery.v1",
        "issue_family": "workflow_discovery",
        "local_event_label": "workflow_discovery",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A structured workflow discovery or missing-step finding should be reviewed as "
            "a candidate process improvement, not silently learned."
        ),
        "support_ref_kinds": ["workflow_discovery_note", "structured_ref"],
        "structured_refs": [
            "docs/fable/exception-learning-taxonomy.md#6-routing-dad-vs-exception-lake-vs-local-intake-artifacts"
        ],
    },
]


def _candidate_ids_for_label(
    candidates: Iterable[ExceptionLakeCandidate],
    label: str,
) -> list[str]:
    return [
        candidate.candidate_id for candidate in candidates if candidate.local_event_label == label
    ]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    mapping_ids: list[str] | None = None,
) -> ExceptionLakeMappingCheck:
    return ExceptionLakeMappingCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        mapping_ids=mapping_ids or [],
    )


def build_exception_lake_mapping_package(
    *,
    packet: IntakePreflightPacket,
    candidates: list[ExceptionLakeCandidate],
) -> ExceptionLakeMappingPackage:
    rules = []
    for definition in RULE_DEFINITIONS:
        candidate_ids = _candidate_ids_for_label(candidates, str(definition["local_event_label"]))
        rules.append(
            ExceptionLakeMappingRule(
                mapping_id=str(definition["mapping_id"]),
                issue_family=definition["issue_family"],  # type: ignore[arg-type]
                local_event_label=str(definition["local_event_label"]),
                canonical_lake_class=definition["canonical_lake_class"],  # type: ignore[arg-type]
                trigger_summary=str(definition["trigger_summary"]),
                support_ref_kinds=definition["support_ref_kinds"],  # type: ignore[arg-type]
                candidate_ids=candidate_ids,
                candidate_count=len(candidate_ids),
                structured_refs=list(definition["structured_refs"]),
            )
        )

    missing_rule_ids = [
        rule.mapping_id
        for rule in rules
        if not rule.mapping_id or not rule.local_event_label or not rule.canonical_lake_class
    ]
    non_dry_run_rule_ids = [
        rule.mapping_id for rule in rules if rule.admission_state != "dry_run_not_admitted"
    ]
    promotion_rule_ids = [
        rule.mapping_id for rule in rules if rule.canonical_promotion_required is not True
    ]
    missing_support_rule_ids = [
        rule.mapping_id for rule in rules if not rule.support_ref_kinds or not rule.structured_refs
    ]
    required_issue_families = {
        "broken_template_formula",
        "missing_budget_code_mapping",
        "unknown_budget_driver",
        "guideline_or_cap_issue",
        "carrier_preapproval_required",
        "human_budget_change",
        "budget_actual_cost_variance",
        "carrier_rejection_capture",
        "carrier_rejection_reconciliation",
        "carrier_rejection_appeal_result",
        "carrier_rejection_learning",
        "budget_invariant_violation",
        "scenario_policy_invalid",
        "rate_resolution_ambiguous",
        "carrier_appeal_outcome",
        "matter_link_ambiguity",
        "matter_link_conflict",
        "entity_resolution_ambiguity",
        "entity_resolution_declared_edge_correction",
        "human_entity_resolution_correction",
        "human_correction_of_machine_output",
        "qa_gate_defect",
        "fixture_weakness",
        "workflow_discovery",
    }
    issue_families = {rule.issue_family for rule in rules}

    checks = [
        _check(
            "required_issue_families_mapped",
            required_issue_families.issubset(issue_families),
            "Mapping package covers template formulas, code mappings, drivers, guidelines, preapprovals, human changes, and actual-cost variance.",
            sorted(required_issue_families - issue_families),
        ),
        _check(
            "rule_identity_present",
            not missing_rule_ids,
            "Each mapping rule has an ID, local label, and broad Lake class.",
            missing_rule_ids,
        ),
        _check(
            "dry_run_not_admitted",
            not non_dry_run_rule_ids,
            "Mapping rules remain dry-run and do not create Lake admissions.",
            non_dry_run_rule_ids,
        ),
        _check(
            "canonical_promotion_required",
            not promotion_rule_ids,
            "Each mapping rule requires future canonical promotion or reviewed mapping.",
            promotion_rule_ids,
        ),
        _check(
            "support_refs_declared",
            not missing_support_rule_ids,
            "Each mapping rule declares supported artifact or structured-ref kinds.",
            missing_support_rule_ids,
        ),
    ]
    status = "passed" if all(check.status == "passed" for check in checks) else "failed"
    return ExceptionLakeMappingPackage(
        exception_lake_mapping_package_id=new_id("excmapping"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        stage="budget",
        status=status,
        rules=rules,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_exception_lake_mapping_package(package: ExceptionLakeMappingPackage) -> None:
    if package.status == "passed":
        return
    failed = [check.check_id for check in package.checks if check.status == "failed"]
    raise ValueError("exception lake mapping package failed: " + ", ".join(failed))
