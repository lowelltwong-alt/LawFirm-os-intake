from __future__ import annotations

from typing import Any

from .models import (
    BudgetPreconditionReport,
    BudgetProposal,
    ConflictSeedPacket,
    FixtureGoldCheck,
    FixtureGoldReport,
    FixtureGoldSpec,
    HumanConfirmation,
    IntakePreflightPacket,
    MatterOpeningReadiness,
    SafetyGateReport,
)
from .util import new_id, now_iso


def build_fixture_gold_report(
    *,
    gold: FixtureGoldSpec,
    gold_ref: str,
    packet: IntakePreflightPacket,
    stage: str,
    evaluated_artifact_refs: dict[str, str],
    preflight_exception_candidates: list[dict[str, Any]] | None = None,
    confirmation: HumanConfirmation | None = None,
    conflict_seed: ConflictSeedPacket | None = None,
    budget: BudgetProposal | None = None,
    readiness: MatterOpeningReadiness | None = None,
    budget_exception_candidates: list[dict[str, Any]] | None = None,
    budget_precondition_report: BudgetPreconditionReport | None = None,
    safety_report: SafetyGateReport | None = None,
) -> FixtureGoldReport:
    checks: list[FixtureGoldCheck] = []
    checks.append(
        _exact(
            "gold_reviewed",
            True,
            gold.reviewed,
            "Fixture gold must be reviewed before it can gate a run.",
        )
    )
    checks.append(
        _exact(
            "gold_data_scope_synthetic_only",
            "synthetic_only",
            gold.data_scope,
            "Fixture gold may only cover synthetic data in this repo.",
        )
    )
    if gold.expected_bundle_id:
        checks.append(
            _exact(
                "bundle_id",
                gold.expected_bundle_id,
                packet.bundle_id,
                "Packet bundle ID matches reviewed gold.",
            )
        )
    if gold.expected_preflight_status:
        checks.append(
            _exact(
                "preflight_status",
                gold.expected_preflight_status,
                packet.status,
                "Preflight terminal status matches reviewed gold.",
            )
        )

    _append_source_checks(checks, gold, packet)
    _append_candidate_checks(checks, gold, packet)
    _append_preflight_exception_checks(checks, gold, preflight_exception_candidates or [])
    if gold.require_source_bound_evidence:
        checks.append(_evidence_completeness_check(packet))

    if stage == "demo":
        _append_demo_checks(
            checks,
            gold,
            confirmation=confirmation,
            conflict_seed=conflict_seed,
            budget=budget,
            readiness=readiness,
            budget_exception_candidates=budget_exception_candidates or [],
            budget_precondition_report=budget_precondition_report,
            safety_report=safety_report,
        )

    status = "passed" if all(check.status != "failed" for check in checks) else "failed"
    return FixtureGoldReport(
        fixture_gold_report_id=new_id("goldreport"),
        run_id=packet.run_id,
        preflight_packet_id=packet.packet_id,
        stage=stage,  # type: ignore[arg-type]
        gold_id=gold.gold_id,
        gold_ref=gold_ref,
        status=status,
        reviewed_gold=gold.reviewed,
        evaluated_artifact_refs=evaluated_artifact_refs,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_fixture_gold_report(report: FixtureGoldReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    raise ValueError("fixture gold evaluation failed: " + ", ".join(failed))


def _append_source_checks(
    checks: list[FixtureGoldCheck],
    gold: FixtureGoldSpec,
    packet: IntakePreflightPacket,
) -> None:
    for key, expected in gold.expected_source_coverage.items():
        checks.append(
            _exact(
                f"source_coverage_{key}",
                expected,
                packet.source_coverage_summary.get(key),
                f"Source coverage `{key}` matches reviewed gold.",
            )
        )
    inventory = {item.source_id: item for item in packet.source_inventory}
    for expected in gold.expected_source_states:
        item = inventory.get(expected.source_id)
        checks.append(
            _present(
                f"source_state_{expected.source_id}_present",
                item is not None,
                expected.source_id,
                item.source_id if item else None,
                "Expected source inventory row is present.",
            )
        )
        if item is None:
            continue
        if expected.read_state is not None:
            checks.append(
                _exact(
                    f"source_state_{expected.source_id}_read_state",
                    expected.read_state,
                    item.read_state,
                    "Source read state matches reviewed gold.",
                )
            )
        if expected.availability_state is not None:
            checks.append(
                _exact(
                    f"source_state_{expected.source_id}_availability",
                    expected.availability_state,
                    item.availability_state,
                    "Source availability state matches reviewed gold.",
                )
            )
        if expected.duplicate_of_source_id is not None:
            checks.append(
                _exact(
                    f"source_state_{expected.source_id}_duplicate_of",
                    expected.duplicate_of_source_id,
                    item.duplicate_of_source_id,
                    "Duplicate source linkage matches reviewed gold.",
                )
            )


def _append_candidate_checks(
    checks: list[FixtureGoldCheck],
    gold: FixtureGoldSpec,
    packet: IntakePreflightPacket,
) -> None:
    if gold.expected_top_three_matter_families:
        actual = [candidate.label for candidate in packet.matter_family_candidates[:3]]
        checks.append(
            _subset(
                "top_three_matter_family_recall",
                gold.expected_top_three_matter_families,
                actual,
                "Expected matter families are present in the top three candidates.",
            )
        )
    if gold.expected_top_inbound_event:
        actual = (
            packet.inbound_event_candidates[0].label if packet.inbound_event_candidates else None
        )
        checks.append(
            _exact(
                "top_inbound_event",
                gold.expected_top_inbound_event,
                actual,
                "Top inbound-event candidate matches reviewed gold.",
            )
        )
    if gold.expected_top_representation_posture:
        actual = (
            packet.representation_posture_candidates[0].label
            if packet.representation_posture_candidates
            else None
        )
        checks.append(
            _exact(
                "top_representation_posture",
                gold.expected_top_representation_posture,
                actual,
                "Top representation-posture candidate matches reviewed gold.",
            )
        )

    party_roles = {
        party.name: sorted({role.role for role in party.role_candidates})
        for party in packet.party_candidates
    }
    for party_name, expected_roles in gold.expected_party_role_candidates.items():
        checks.append(
            _subset(
                f"party_roles_{_slug(party_name)}",
                expected_roles,
                party_roles.get(party_name, []),
                "Expected party-role candidates are present.",
            )
        )
    for party_name, prohibited_roles in gold.prohibited_party_role_candidates.items():
        actual = set(party_roles.get(party_name, []))
        prohibited = sorted(set(prohibited_roles).intersection(actual))
        checks.append(
            _exact(
                f"party_roles_{_slug(party_name)}_prohibited_absent",
                [],
                prohibited,
                "Prohibited party-role candidates are absent.",
            )
        )

    if gold.expected_deadline_expressions:
        checks.append(
            _subset(
                "deadline_candidate_recall",
                gold.expected_deadline_expressions,
                [deadline.expression for deadline in packet.deadline_candidates],
                "Expected date/deadline candidates are present for human review.",
            )
        )
    if gold.expected_missing_information:
        checks.append(
            _subset(
                "missing_information_recall",
                gold.expected_missing_information,
                packet.missing_information,
                "Expected missing-information fields are present.",
            )
        )
    if gold.expected_critic_finding_codes:
        checks.append(
            _subset(
                "critic_finding_recall",
                gold.expected_critic_finding_codes,
                [finding.code for finding in packet.critic_findings],
                "Expected critic findings are present.",
            )
        )
    if gold.expected_prohibited_next_steps:
        checks.append(
            _subset(
                "prohibited_next_steps",
                gold.expected_prohibited_next_steps,
                packet.prohibited_next_steps,
                "Expected prohibited next steps are preserved.",
            )
        )


def _append_preflight_exception_checks(
    checks: list[FixtureGoldCheck],
    gold: FixtureGoldSpec,
    candidates: list[dict[str, Any]],
) -> None:
    if not gold.expected_preflight_exception_labels:
        return
    checks.append(
        _subset(
            "preflight_exception_label_recall",
            gold.expected_preflight_exception_labels,
            [str(candidate.get("local_event_label")) for candidate in candidates],
            "Expected preflight dry-run exception labels are present.",
        )
    )


def _append_demo_checks(
    checks: list[FixtureGoldCheck],
    gold: FixtureGoldSpec,
    *,
    confirmation: HumanConfirmation | None,
    conflict_seed: ConflictSeedPacket | None,
    budget: BudgetProposal | None,
    readiness: MatterOpeningReadiness | None,
    budget_exception_candidates: list[dict[str, Any]],
    budget_precondition_report: BudgetPreconditionReport | None,
    safety_report: SafetyGateReport | None,
) -> None:
    if gold.expected_confirmation_status:
        checks.append(
            _exact(
                "human_confirmation_status",
                gold.expected_confirmation_status,
                confirmation.status if confirmation else None,
                "Human confirmation status matches reviewed gold.",
            )
        )
    if gold.expected_conflict_conclusion:
        checks.append(
            _exact(
                "conflict_conclusion_boundary",
                gold.expected_conflict_conclusion,
                conflict_seed.conclusion if conflict_seed else None,
                "Conflict output remains a search seed, not a conclusion.",
            )
        )
    if gold.expected_conflict_term_groups:
        actual = (
            sorted({term.group for term in conflict_seed.normalized_search_terms})
            if conflict_seed
            else []
        )
        checks.append(
            _subset(
                "conflict_term_group_recall",
                gold.expected_conflict_term_groups,
                actual,
                "Expected conflict-search term groups are present.",
            )
        )
    if gold.expected_budget_pricing_status:
        checks.append(
            _exact(
                "budget_pricing_status",
                gold.expected_budget_pricing_status,
                budget.pricing_status if budget else None,
                "Budget pricing status matches reviewed gold.",
            )
        )
    if gold.expected_budget_approval_state:
        checks.append(
            _exact(
                "budget_approval_state",
                gold.expected_budget_approval_state,
                budget.approval_state if budget else None,
                "Budget remains a proposal for human review.",
            )
        )
    if gold.expected_budget_not_authorized_for_client_submission is not None:
        checks.append(
            _exact(
                "budget_not_authorized_for_client_submission",
                gold.expected_budget_not_authorized_for_client_submission,
                budget.not_authorized_for_client_submission if budget else None,
                "Budget client/carrier submission boundary matches reviewed gold.",
            )
        )
    if gold.expected_budget_exception_labels:
        checks.append(
            _subset(
                "budget_exception_label_recall",
                gold.expected_budget_exception_labels,
                [
                    str(candidate.get("local_event_label"))
                    for candidate in budget_exception_candidates
                ],
                "Expected budget-stage dry-run exception labels are present.",
            )
        )
    if gold.expected_budget_precondition_status:
        checks.append(
            _exact(
                "budget_precondition_status",
                gold.expected_budget_precondition_status,
                budget_precondition_report.status if budget_precondition_report else None,
                "Budget precondition status matches reviewed gold.",
            )
        )
    if gold.expected_safety_status:
        checks.append(
            _exact(
                "safety_gate_status",
                gold.expected_safety_status,
                safety_report.status if safety_report else None,
                "Safety gate status matches reviewed gold.",
            )
        )
    if gold.expected_final_boundary:
        checks.append(
            _exact(
                "final_boundary",
                gold.expected_final_boundary,
                readiness.status if readiness else None,
                "Final matter-opening boundary matches reviewed gold.",
            )
        )
    if gold.expected_readiness_blockers:
        checks.append(
            _subset(
                "readiness_blockers",
                gold.expected_readiness_blockers,
                readiness.blockers if readiness else [],
                "Expected matter-opening blockers are present.",
            )
        )
    if gold.expected_no_external_writes is not None:
        checks.append(
            _exact(
                "no_external_writes",
                gold.expected_no_external_writes,
                safety_report is not None
                and all(
                    check.check_id != "no_external_write_artifacts" or check.status == "passed"
                    for check in safety_report.checks
                ),
                "Safety gate proves artifact refs are local-only.",
            )
        )


def _evidence_completeness_check(packet: IntakePreflightPacket) -> FixtureGoldCheck:
    missing: list[str] = []
    for party in packet.party_candidates:
        if not party.evidence_refs:
            missing.append(f"party:{party.name}")
        for role in party.role_candidates:
            if not role.evidence_refs:
                missing.append(f"role:{party.name}:{role.role}")
    for candidate in (
        packet.inbound_event_candidates
        + packet.matter_family_candidates
        + packet.representation_posture_candidates
    ):
        if not candidate.observed_evidence_refs:
            missing.append(f"candidate:{candidate.label}")
    for deadline in packet.deadline_candidates:
        if not deadline.evidence_refs:
            missing.append(f"deadline:{deadline.expression}")
    for item in packet.missing_information_candidates:
        if not item.evidence_refs:
            missing.append(f"missing:{item.field_name}")
    for finding in packet.critic_findings:
        if not finding.evidence_refs:
            missing.append(f"critic:{finding.code}")
    return _exact(
        "source_bound_evidence_present",
        [],
        missing,
        "Preflight candidates and review items retain source-bound evidence refs.",
    )


def _subset(
    check_id: str,
    expected: list[Any],
    actual: list[Any],
    message: str,
) -> FixtureGoldCheck:
    missing = sorted(set(expected).difference(set(actual)))
    return FixtureGoldCheck(
        check_id=check_id,
        status="passed" if not missing else "failed",
        message=message,
        expected=expected,
        actual=actual,
    )


def _exact(check_id: str, expected: Any, actual: Any, message: str) -> FixtureGoldCheck:
    return FixtureGoldCheck(
        check_id=check_id,
        status="passed" if actual == expected else "failed",
        message=message,
        expected=expected,
        actual=actual,
    )


def _present(
    check_id: str,
    ok: bool,
    expected: Any,
    actual: Any,
    message: str,
) -> FixtureGoldCheck:
    return FixtureGoldCheck(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        expected=expected,
        actual=actual,
    )


def _slug(value: str) -> str:
    return "".join(character if character.isalnum() else "_" for character in value.casefold())
