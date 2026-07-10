from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from .models import (
    BudgetProposal,
    CarrierCompliantProjection,
    OCGRuleIRAdoptionFinding,
    OCGRuleIRAdoptionReport,
    OCGRuleImpactLine,
    OCGSharedRuleIR,
    OCGSharedRuleIRRule,
    RunEvent,
)
from .util import append_jsonl, load_json, now_iso, write_json


OCG_RULE_IR_ADOPTION_REPORT_FILENAME = "ocg_rule_ir_adoption_report.json"
SUBSTRATE_OWNER = "LawFirm-os-semantic-substrate"
RULE_ID_PREFIX = "ocg_ir_candidate:"

OCG_IR_PROHIBITED_ACTIONS = [
    "do_not_author_canonical_ocg_rule_ids_in_intake",
    "do_not_treat_candidate_ocg_ir_as_carrier_guideline_canon",
    "do_not_rewrite_budget_proposal_from_ocg_ir",
    "do_not_submit_budget_or_open_matter",
    "do_not_ingest_real_carrier_guidelines_or_real_rates",
    "do_not_write_exception_lake_or_dad_mail_from_this_report",
]

CANONICAL_RULE_ID_PATTERNS = [
    re.compile(r"^https?://", re.IGNORECASE),
    re.compile(r"^(?:ocg|guideline|rule):", re.IGNORECASE),
    re.compile(r"^OCG[-_][A-Z0-9]", re.IGNORECASE),
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{sha256(value.encode('utf-8')).hexdigest()[:12]}"


def load_ocg_rule_ir(path: str | Path) -> OCGSharedRuleIR:
    return OCGSharedRuleIR.model_validate(load_json(path))


def _finding(
    finding_id: str,
    issue: str,
    *,
    rule_id: str | None = None,
    severity: str = "blocker",
) -> OCGRuleIRAdoptionFinding:
    return OCGRuleIRAdoptionFinding(
        finding_id=finding_id,
        severity=severity,
        issue=issue,
        rule_id=rule_id,
    )


def _looks_canonical(rule_id: str) -> bool:
    stripped = rule_id.strip()
    if not stripped.startswith(RULE_ID_PREFIX):
        return True
    candidate_suffix = stripped[len(RULE_ID_PREFIX) :]
    if not candidate_suffix:
        return True
    return any(pattern.search(candidate_suffix) for pattern in CANONICAL_RULE_ID_PATTERNS)


def _rule_findings(rule: OCGSharedRuleIRRule) -> list[OCGRuleIRAdoptionFinding]:
    findings: list[OCGRuleIRAdoptionFinding] = []
    if _looks_canonical(rule.rule_id):
        findings.append(
            _finding(
                "canonical_or_unprefixed_ocg_rule_id",
                (
                    "OCG rule IDs consumed by intake must be explicit candidate IDs; "
                    "canonical rule IDs belong to Semantic Substrate."
                ),
                rule_id=rule.rule_id,
            )
        )
    if rule.candidate_only is not True or rule.not_canonical_rule_id is not True:
        findings.append(
            _finding(
                "ocg_rule_claims_non_candidate_authority",
                "OCG rule entries must stay candidate-only and not_canonical_rule_id=true.",
                rule_id=rule.rule_id,
            )
        )
    if rule.rewrites_budget is not False:
        findings.append(
            _finding(
                "ocg_rule_attempts_budget_rewrite",
                "OCG rule entries may explain compliant projection impact but cannot rewrite budget math.",
                rule_id=rule.rule_id,
            )
        )
    if rule.no_real_guideline_text is not True or rule.no_real_rate_value is not True:
        findings.append(
            _finding(
                "ocg_rule_contains_real_guideline_or_rate_material",
                "OCG rule entries in this repo must not contain real guideline text or real rates.",
                rule_id=rule.rule_id,
            )
        )
    return findings


def _top_level_findings(rule_ir: OCGSharedRuleIR) -> list[OCGRuleIRAdoptionFinding]:
    findings: list[OCGRuleIRAdoptionFinding] = []
    if rule_ir.source_owner != SUBSTRATE_OWNER:
        findings.append(
            _finding(
                "ocg_ir_source_owner_not_substrate",
                (
                    f"OCG shared rule IR source_owner={rule_ir.source_owner!r}; "
                    f"expected {SUBSTRATE_OWNER!r}."
                ),
            )
        )
    if rule_ir.read_only_consumption is not True:
        findings.append(
            _finding(
                "ocg_ir_not_read_only",
                "Intake may consume shared OCG rule IR read-only; it cannot author or mutate it.",
            )
        )
    if rule_ir.candidate_only is not True or rule_ir.not_promoted_canon is not True:
        findings.append(
            _finding(
                "ocg_ir_claims_canonical_authority",
                "Local OCG rule IR fixtures must stay candidate-only and not_promoted_canon=true.",
            )
        )
    if rule_ir.data_origin != "synthetic":
        findings.append(
            _finding(
                "ocg_ir_data_origin_not_synthetic",
                "Intake fixtures may only contain synthetic OCG rule IR examples.",
            )
        )
    if (
        rule_ir.no_real_guidelines is not True
        or rule_ir.no_real_rates is not True
        or rule_ir.contains_real_firm_data is not False
        or rule_ir.contains_real_carrier_data is not False
    ):
        findings.append(
            _finding(
                "ocg_ir_contains_real_guideline_or_rate_material",
                "OCG IR examples here must contain no real carrier guideline, firm, or rate data.",
            )
        )
    return findings


def _amount_from_projection(
    rule: OCGSharedRuleIRRule,
    projection: CarrierCompliantProjection,
) -> OCGRuleImpactLine:
    bucket = rule.impact_bucket
    refs: list[str] = []
    proposed_amount: float | None = None
    compliant_amount: float | None = None
    delta_amount: float | None = None
    note = "OCG rule impact is recorded as candidate metadata only."

    if bucket == "rate_cap_delta":
        refs = [
            f"carrier_compliant_projection.lines[{index}]"
            for index, line in enumerate(projection.lines)
            if getattr(line, "capped_rate", line.rate_cap_applied)
            or line.delta_breakdown.get("rate_cap_delta", 0) != 0
        ]
        proposed_amount = round(sum(line.proposed_fees or 0 for line in projection.lines), 2)
        compliant_amount = (
            None
            if projection.compliant_subtotal_fees is None
            else round(projection.compliant_subtotal_fees, 2)
        )
        delta_amount = round(projection.rate_cap_delta, 2)
        note = "Rate-cap impact is read from the already-built carrier projection."
    elif bucket == "expense_cap_delta":
        refs = [
            f"carrier_compliant_projection.lines[{index}]"
            for index, line in enumerate(projection.lines)
            if getattr(line, "capped_expense", line.expense_cap_applied)
        ]
        proposed_amount = round(projection.proposed_subtotal_expenses, 2)
        compliant_amount = round(projection.compliant_subtotal_expenses, 2)
        delta_amount = round(projection.expense_cap_delta, 2)
        note = "Expense-cap impact is read from the already-built carrier projection."
    elif bucket == "disallowed_delta":
        refs = [
            f"carrier_compliant_projection.lines[{index}]"
            for index, line in enumerate(projection.lines)
            if line.disallowed
        ]
        proposed_amount = round(
            sum((line.proposed_fees or 0) + line.proposed_expenses for line in projection.lines),
            2,
        )
        compliant_amount = round(
            sum((line.compliant_fees or 0) + line.compliant_expenses for line in projection.lines),
            2,
        )
        delta_amount = round(projection.disallowed_delta, 2)
        note = "Disallowance impact is read from the already-built carrier projection."
    elif bucket == "contingency_delta":
        refs = ["carrier_compliant_projection.contingency_delta"]
        proposed_amount = projection.proposed_contingency_amount
        compliant_amount = projection.compliant_contingency_amount
        delta_amount = round(projection.contingency_delta, 2)
        note = "Contingency impact is read from the already-built carrier projection."
    elif bucket == "staffing_delta":
        refs = [
            f"carrier_compliant_projection.lines[{index}]"
            for index, line in enumerate(projection.lines)
            if getattr(line, "staffing_reshaped", line.staffing_rule_applied)
        ]
        proposed_amount = round(sum(line.proposed_fees or 0 for line in projection.lines), 2)
        compliant_amount = (
            None
            if projection.compliant_subtotal_fees is None
            else round(projection.compliant_subtotal_fees, 2)
        )
        delta_amount = round(
            getattr(projection, "staffing_delta", projection.staffing_rule_delta),
            2,
        )
        note = "Staffing impact is read from the already-built carrier projection."
    elif bucket == "preapproval_dry_run":
        preapproval_candidates = getattr(projection, "preapproval_dry_run_candidates", [])
        refs = [
            f"carrier_compliant_projection.preapproval_dry_run_candidates[{index}]"
            for index, _candidate in enumerate(preapproval_candidates)
        ]
        note = "Pre-approval impact is a dry-run escalation candidate, not a math rewrite."
    elif bucket == "metadata_only":
        refs = ["carrier_compliant_projection.basis"]
        note = "Metadata-only OCG context has no budget math effect."

    return OCGRuleImpactLine(
        rule_id=rule.rule_id,
        rule_family=rule.rule_family,
        impact_bucket=bucket,
        matched_projection_refs=refs,
        proposed_amount=proposed_amount,
        compliant_amount=compliant_amount,
        delta_amount=delta_amount,
        note=note,
    )


def build_ocg_rule_ir_adoption_report(
    budget: BudgetProposal,
    projection: CarrierCompliantProjection,
    rule_ir: OCGSharedRuleIR,
) -> OCGRuleIRAdoptionReport:
    findings = _top_level_findings(rule_ir)
    for rule in rule_ir.rules:
        findings.extend(_rule_findings(rule))

    projection_budget_id = getattr(projection, "budget_proposal_id", None)
    if projection_budget_id is not None and projection_budget_id != budget.budget_proposal_id:
        findings.append(
            _finding(
                "projection_budget_id_mismatch",
                "Carrier projection does not reference the supplied budget proposal.",
            )
        )
    if projection.proposed_total != budget.total_proposed_budget:
        findings.append(
            _finding(
                "projection_proposed_total_mismatch",
                "Carrier projection proposed_total must match the baseline budget proposal total.",
            )
        )
    lines_preserved = getattr(projection, "proposed_lines_preserved", None)
    if lines_preserved is None:
        lines_preserved = projection.basis.proposal_lines_unchanged is True
    if projection.rewrites_budget is not False or lines_preserved is not True:
        findings.append(
            _finding(
                "projection_rewrites_budget_or_lines_not_preserved",
                "Carrier projection must preserve proposed budget lines and declare rewrites_budget=false.",
            )
        )

    has_blocker = any(finding.severity == "blocker" for finding in findings)
    impact_lines = [_amount_from_projection(rule, projection) for rule in rule_ir.rules]
    candidate_rule_count = sum(
        1 for rule in rule_ir.rules if rule.rule_id.startswith(RULE_ID_PREFIX)
    )
    canonical_rule_id_violation_count = sum(
        1 for finding in findings if finding.finding_id == "canonical_or_unprefixed_ocg_rule_id"
    )
    source_owner_violation_count = sum(
        1 for finding in findings if finding.finding_id == "ocg_ir_source_owner_not_substrate"
    )
    read_only_violation_count = sum(
        1 for finding in findings if finding.finding_id == "ocg_ir_not_read_only"
    )
    rewrite_budget_violation_count = sum(
        1
        for finding in findings
        if finding.finding_id
        in {
            "ocg_rule_attempts_budget_rewrite",
            "projection_rewrites_budget_or_lines_not_preserved",
        }
    )
    real_guideline_or_rate_violation_count = sum(
        1
        for finding in findings
        if finding.finding_id
        in {
            "ocg_ir_contains_real_guideline_or_rate_material",
            "ocg_rule_contains_real_guideline_or_rate_material",
        }
    )
    budget_projection_mismatch_count = sum(
        1
        for finding in findings
        if finding.finding_id
        in {
            "projection_budget_id_mismatch",
            "projection_proposed_total_mismatch",
        }
    )
    seed = "|".join(
        [
            rule_ir.rule_ir_id,
            budget.budget_proposal_id,
            projection.projection_id,
            str(len(rule_ir.rules)),
            str(canonical_rule_id_violation_count),
            str(read_only_violation_count),
            str(rewrite_budget_violation_count),
            str(real_guideline_or_rate_violation_count),
            str(budget_projection_mismatch_count),
        ]
    )
    return OCGRuleIRAdoptionReport(
        report_id=_stable_id("ocgiradopt", seed),
        generated_at=now_iso(),
        status="blocked" if has_blocker else "accepted_as_read_only_candidate",
        acceptance_gate_status="blocked" if has_blocker else "accepted_with_restrictions",
        rule_ir_id=rule_ir.rule_ir_id,
        source_owner=rule_ir.source_owner,
        source_artifact_ref=rule_ir.source_artifact_ref,
        budget_proposal_id=budget.budget_proposal_id,
        carrier_projection_id=projection.projection_id,
        carrier=getattr(projection, "carrier", projection.basis.carrier_id),
        proposed_total_before=budget.total_proposed_budget,
        proposed_total_after=budget.total_proposed_budget,
        carrier_compliant_total=projection.compliant_total,
        projection_total_delta=projection.total_delta,
        rule_count=len(rule_ir.rules),
        impact_line_count=len(impact_lines),
        candidate_rule_id_count=candidate_rule_count,
        canonical_rule_id_violation_count=canonical_rule_id_violation_count,
        source_owner_violation_count=source_owner_violation_count,
        read_only_violation_count=read_only_violation_count,
        rewrite_budget_violation_count=rewrite_budget_violation_count,
        real_guideline_or_rate_violation_count=real_guideline_or_rate_violation_count,
        budget_projection_mismatch_count=budget_projection_mismatch_count,
        findings=findings,
        impact_lines=impact_lines,
        display_banner={
            "warning": (
                "OCG rule IR is a synthetic, candidate-only, read-only consumption proof. "
                "It is not carrier guideline canon and is not authorized for budget rewrite, "
                "client submission, matter opening, or Lake write."
            ),
            "source_owner_required": SUBSTRATE_OWNER,
            "candidate_only": True,
            "accepted_with_restrictions": not has_blocker,
            "blocked_actions": [
                "canonical_ocg_authoring",
                "budget_rewrite",
                "client_submission",
                "matter_opening",
                "lake_write",
                "real_guideline_ingestion",
            ],
        },
        prohibited_actions=OCG_IR_PROHIBITED_ACTIONS,
        proposed_budget_preserved=not any(
            finding.finding_id == "projection_proposed_total_mismatch" for finding in findings
        ),
        projection_rewrites_budget=projection.rewrites_budget,
        read_only_consumption=rule_ir.read_only_consumption,
        candidate_only=rule_ir.candidate_only,
        not_promoted_canon=rule_ir.not_promoted_canon,
    )


def run_ocg_rule_ir_adoption_report(
    budget_proposal_path: str | Path,
    carrier_projection_path: str | Path,
    ocg_rule_ir_path: str | Path,
    out_dir: str | Path,
) -> tuple[OCGSharedRuleIR, OCGRuleIRAdoptionReport, Path]:
    budget = BudgetProposal.model_validate(load_json(budget_proposal_path))
    projection = CarrierCompliantProjection.model_validate(load_json(carrier_projection_path))
    rule_ir = load_ocg_rule_ir(ocg_rule_ir_path)
    report = build_ocg_rule_ir_adoption_report(budget, projection, rule_ir)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / OCG_RULE_IR_ADOPTION_REPORT_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    append_jsonl(
        run_dir / "run_ledger.jsonl",
        RunEvent(
            run_id=report.report_id,
            step_index=0,
            step_name="ocg_rule_ir_adoption_report_built",
            status="completed" if report.status != "blocked" else "blocked",
            timestamp=now_iso(),
            input_refs=[
                str(budget_proposal_path),
                str(carrier_projection_path),
                str(ocg_rule_ir_path),
            ],
            output_refs=[str(report_path)],
        ).model_dump(mode="json"),
    )
    return rule_ir, report, run_dir
