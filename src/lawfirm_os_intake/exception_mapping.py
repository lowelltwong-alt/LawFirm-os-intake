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
        "mapping_id": "budget_human_change_recorded.v1",
        "issue_family": "human_budget_change",
        "local_event_label": "budget_human_change_recorded",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "A human budget correction, revision, or superseding decision was recorded and "
            "should be preserved as append-only evidence."
        ),
        "support_ref_kinds": ["budget_change_record", "budget_proposal", "structured_ref"],
        "structured_refs": ["docs/human-review.md#budget-review"],
    },
    {
        "mapping_id": "budget_actual_cost_variance_requires_review.v1",
        "issue_family": "budget_actual_cost_variance",
        "local_event_label": "budget_actual_cost_variance_requires_review",
        "canonical_lake_class": "workflow_escalation",
        "trigger_summary": (
            "Phase-level actual cost differs from the proposed budget outside the review "
            "threshold and requires human pricing review."
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
        "human_budget_change",
        "budget_actual_cost_variance",
        "carrier_rejection_capture",
        "carrier_rejection_reconciliation",
        "carrier_rejection_appeal_result",
        "carrier_rejection_learning",
    }
    issue_families = {rule.issue_family for rule in rules}

    checks = [
        _check(
            "required_issue_families_mapped",
            required_issue_families.issubset(issue_families),
            "Mapping package covers template formulas, code mappings, drivers, guidelines, human changes, and actual-cost variance.",
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
