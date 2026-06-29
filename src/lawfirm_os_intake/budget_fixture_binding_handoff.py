from __future__ import annotations

from pathlib import Path

from .models import (
    BudgetFixtureBindingCandidate,
    BudgetFixtureBindingCandidateReport,
    BudgetFixtureBindingHandoffItem,
    BudgetFixtureBindingHandoffReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


BUDGET_FIXTURE_BINDING_HANDOFF_REPORT_FILENAME = "budget_fixture_binding_handoff_report.json"
BUDGET_FIXTURE_BINDING_HANDOFF_NOTES_FILENAME = "budget_fixture_binding_handoff_report.md"
BUDGET_FIXTURE_BINDING_HANDOFF_ITEMS_FILENAME = "budget_fixture_binding_handoff_items.jsonl"

BUDGET_FIXTURE_BINDING_HANDOFF_REQUIRED_NEXT_GATES = [
    "human_fixture_update_review",
    "separate_fixture_update_pr_if_accepted",
    "append_only_fixture_update_record",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_or_guideline_mutation",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _disposition(candidate: BudgetFixtureBindingCandidate) -> str:
    if candidate.status == "candidate_ready_for_fixture_update_review":
        return "ready_for_human_fixture_update_review"
    if candidate.status == "blocked_missing_approved_outputs":
        return "blocked_missing_approved_outputs"
    return "blocked_pending_approved_outcome"


def _owner_actions(candidate: BudgetFixtureBindingCandidate) -> list[str]:
    if candidate.status == "candidate_ready_for_fixture_update_review":
        return [
            "Inspect approved replay output refs and source fixture refs before any fixture edit.",
            "Decide whether a separate fixture-update PR is warranted.",
            "If accepted, update fixtures in a separate reviewed change and rerun regression checks.",
            "Keep learning blocked until reviewed learning gate and shadow eval evidence exist.",
        ]
    if candidate.status == "blocked_missing_approved_outputs":
        return [
            "Do not update fixtures.",
            "Record a superseding replay review outcome with explicit approved output refs.",
            "Rerun fixture-binding proposal and handoff generation after outputs are bound.",
        ]
    return [
        "Do not update fixtures.",
        "Obtain an append-only approve_fixture_binding outcome before fixture update review.",
        "Keep learning, profile, template, budget, and guideline mutation blocked.",
    ]


def _why(candidate: BudgetFixtureBindingCandidate) -> list[str]:
    lines = [
        f"Source fixture-binding candidate `{candidate.fixture_binding_candidate_id}` is `{candidate.status}`.",
        f"Proposed binding action is `{candidate.proposed_binding_action}` for `{candidate.source_artifact_ref}`.",
    ]
    if candidate.status == "candidate_ready_for_fixture_update_review":
        lines.extend(
            [
                "The candidate has approved replay output refs and target fixture refs.",
                "This handoff prepares human fixture-update review but does not change any fixture.",
            ]
        )
    elif candidate.status == "blocked_missing_approved_outputs":
        lines.append(
            "The candidate is blocked because fixture binding was approved without approved replay output refs."
        )
    else:
        lines.append(
            "The candidate is blocked because the human replay review did not approve fixture binding."
        )
    return lines


def _red_team_notes(candidate: BudgetFixtureBindingCandidate) -> list[str]:
    notes = [
        "A fixture update can accidentally encode a regression as reviewed gold if the approved output is not inspected.",
        "Fixture binding is not learning approval and cannot mutate profiles, templates, budgets, or carrier guidelines.",
        "The source fixture may contain synthetic assumptions that should not be promoted as general LawFirm OS canon.",
    ]
    if candidate.status != "candidate_ready_for_fixture_update_review":
        notes.append(
            "Blocked fixture-binding candidates must not be batched into a fixture update PR."
        )
    return notes


def _build_item(
    *,
    report: BudgetFixtureBindingCandidateReport,
    candidate: BudgetFixtureBindingCandidate,
) -> BudgetFixtureBindingHandoffItem:
    return BudgetFixtureBindingHandoffItem(
        handoff_item_id=_stable_id(
            "budgetfixturehandoffitem",
            f"{report.fixture_binding_candidate_report_id}|{candidate.fixture_binding_candidate_id}",
        ),
        fixture_binding_candidate_id=candidate.fixture_binding_candidate_id,
        fixture_binding_candidate_report_id=report.fixture_binding_candidate_report_id,
        review_packet_id=candidate.review_packet_id,
        review_outcome_report_id=candidate.review_outcome_report_id,
        replay_execution_report_id=candidate.replay_execution_report_id,
        replay_case_id=candidate.replay_case_id,
        source_artifact_ref=candidate.source_artifact_ref,
        artifact_kind=candidate.artifact_kind,
        approved_output_refs=candidate.approved_output_refs,
        proposed_target_fixture_refs=candidate.proposed_target_fixture_refs,
        proposed_binding_action=candidate.proposed_binding_action,
        source_candidate_status=candidate.status,
        disposition=_disposition(candidate),  # type: ignore[arg-type]
        recommended_owner_actions=_owner_actions(candidate),
        why=_why(candidate),
        red_team_notes=_red_team_notes(candidate),
        required_next_gates=BUDGET_FIXTURE_BINDING_HANDOFF_REQUIRED_NEXT_GATES,
    )


def _report_status(items: list[BudgetFixtureBindingHandoffItem]) -> str:
    if not items:
        return "no_fixture_binding_handoff_candidates"
    ready = [item for item in items if item.disposition == "ready_for_human_fixture_update_review"]
    if ready and len(ready) == len(items):
        return "fixture_binding_handoff_ready_for_human_review"
    return "fixture_binding_handoff_blocked"


def build_budget_fixture_binding_handoff_report(
    *,
    candidate_report: BudgetFixtureBindingCandidateReport,
    candidate_report_ref: str,
) -> BudgetFixtureBindingHandoffReport:
    items = [
        _build_item(report=candidate_report, candidate=candidate)
        for candidate in candidate_report.candidates
    ]
    ready_count = sum(
        1 for item in items if item.disposition == "ready_for_human_fixture_update_review"
    )
    return BudgetFixtureBindingHandoffReport(
        fixture_binding_handoff_report_id=_stable_id(
            "budgetfixturehandoffreport",
            candidate_report.fixture_binding_candidate_report_id,
        ),
        source_fixture_binding_candidate_report_id=(
            candidate_report.fixture_binding_candidate_report_id
        ),
        source_fixture_binding_candidate_report_ref=candidate_report_ref,
        source_fixture_binding_candidate_report_status=candidate_report.status,
        status=_report_status(items),  # type: ignore[arg-type]
        item_count=len(items),
        ready_item_count=ready_count,
        blocked_item_count=len(items) - ready_count,
        handoff_items=items,
        required_next_gates=BUDGET_FIXTURE_BINDING_HANDOFF_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_fixture_binding_handoff_report(
    report: BudgetFixtureBindingHandoffReport,
) -> str:
    lines = [
        "# Budget Fixture Binding Handoff Report",
        "",
        f"**Report ID:** {report.fixture_binding_handoff_report_id}",
        f"**Status:** {report.status}",
        f"**Source candidate report:** `{report.source_fixture_binding_candidate_report_ref}`",
        f"**Items:** {report.item_count}",
        f"**Ready items:** {report.ready_item_count}",
        f"**Blocked items:** {report.blocked_item_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Non-authoritative: {report.non_authoritative}",
        f"- Synthetic only: {report.synthetic_only}",
        f"- Fixture update authorized: {report.fixture_update_authorized}",
        f"- Fixture update PR created: {report.fixture_update_pr_created}",
        f"- Fixture files mutated: {report.fixture_files_mutated}",
        f"- Fixture binding applied: {report.fixture_binding_applied}",
        f"- Downstream learning gate allowed: {report.downstream_learning_gate_allowed}",
        f"- Calibration applied: {report.calibration_applied}",
        f"- Profile mutation performed: {report.profile_mutation_performed}",
        f"- Template mutation performed: {report.template_mutation_performed}",
        f"- Budget mutation performed: {report.budget_mutation_performed}",
        f"- Carrier guideline mutation performed: {report.carrier_guideline_mutation_performed}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Handoff Items",
        "",
    ]
    if not report.handoff_items:
        lines.append("- none")
    for item in report.handoff_items:
        lines.extend(
            [
                f"### {item.handoff_item_id}",
                "",
                f"- Candidate: `{item.fixture_binding_candidate_id}`",
                f"- Disposition: {item.disposition}",
                f"- Artifact: `{item.source_artifact_ref}`",
                f"- Proposed action: {item.proposed_binding_action}",
                f"- Approved outputs: {len(item.approved_output_refs)}",
                f"- Target fixture refs: {len(item.proposed_target_fixture_refs)}",
                "- Why:",
                *(f"  - {reason}" for reason in item.why),
                "- Recommended owner actions:",
                *(f"  - {action}" for action in item.recommended_owner_actions),
                "- Red-team notes:",
                *(f"  - {note}" for note in item.red_team_notes),
                "",
            ]
        )
    lines.extend(
        [
            "## Required Next Gates",
            "",
            *(f"- {gate}" for gate in report.required_next_gates),
            "",
            "This handoff is local review evidence only. It does not update fixtures, apply learning, write Lake/SQLite records, submit budgets, open matters, create a PR, or perform external writes.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_fixture_binding_handoff(
    *,
    fixture_binding_candidate_report_path: str | Path,
    out_dir: str | Path,
) -> tuple[BudgetFixtureBindingHandoffReport, Path]:
    source_path = Path(fixture_binding_candidate_report_path)
    candidate_report = BudgetFixtureBindingCandidateReport.model_validate(load_json(source_path))
    report = build_budget_fixture_binding_handoff_report(
        candidate_report=candidate_report,
        candidate_report_ref=str(source_path),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    items_path = run_dir / BUDGET_FIXTURE_BINDING_HANDOFF_ITEMS_FILENAME
    if items_path.exists():
        items_path.unlink()
    for item in report.handoff_items:
        append_jsonl(items_path, item.model_dump(mode="json"))
    report = report.model_copy(update={"handoff_item_output_ref": str(items_path)})
    write_json(
        run_dir / BUDGET_FIXTURE_BINDING_HANDOFF_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_FIXTURE_BINDING_HANDOFF_NOTES_FILENAME).write_text(
        render_budget_fixture_binding_handoff_report(report),
        encoding="utf-8",
    )
    return report, run_dir
