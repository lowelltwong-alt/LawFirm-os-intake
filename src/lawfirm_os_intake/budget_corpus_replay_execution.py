from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from glob import glob
from hashlib import sha256
import io
from pathlib import Path
import re
from typing import Literal

from .models import (
    BudgetCorpusReplayCase,
    BudgetCorpusReplayCaseResult,
    BudgetCorpusReplayCommand,
    BudgetCorpusReplayCommandResult,
    BudgetCorpusReplayExecutionCheck,
    BudgetCorpusReplayExecutionReport,
    BudgetCorpusReplayOutputCheck,
    BudgetCorpusReplayPlan,
    BudgetCorpusReplayRunMode,
)
from .util import load_json, new_id, now_iso, write_json


BUDGET_CORPUS_REPLAY_EXECUTION_REPORT_FILENAME = "budget_corpus_replay_execution_report.json"
BUDGET_CORPUS_REPLAY_EXECUTION_NOTES_FILENAME = "budget_corpus_replay_execution_report.md"

REPLAY_EXECUTION_REQUIRED_NEXT_GATES = [
    "human_corpus_replay_review",
    "inspect_regenerated_outputs",
    "verify_fixture_result_binding",
    "reviewed_learning_gate_before_candidate_changes",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_template_or_guideline_mutation",
]

_COMMAND_ID_RE = re.compile(r"_cmd_\d{2}_(?P<slug>.+)$")


def _excerpt(value: str, limit: int = 1200) -> str | None:
    if not value:
        return None
    return value[-limit:]


def _sha256(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _slug(command: BudgetCorpusReplayCommand) -> str | None:
    match = _COMMAND_ID_RE.search(command.command_id)
    if match is None:
        return None
    return match.group("slug")


def _resolve_text(
    value: str,
    *,
    replay_root: Path,
    proposed_change_set_path: str | None,
) -> str:
    resolved = value.replace("{replay_run_dir}", str(replay_root))
    if proposed_change_set_path is not None:
        resolved = resolved.replace(
            "{required_learning_proposed_change_set_json}",
            proposed_change_set_path,
        )
    return resolved


def _path_from_ref(ref: str, *, repo_root: Path) -> Path | None:
    if "{" in ref or "}" in ref:
        return None
    if "://" in ref:
        return None
    path = Path(ref)
    if path.is_absolute():
        return path
    return repo_root / path


def _output_check(
    output_ref: str,
    *,
    replay_root: Path,
    repo_root: Path,
    proposed_change_set_path: str | None = None,
) -> BudgetCorpusReplayOutputCheck:
    resolved_ref = _resolve_text(
        output_ref,
        replay_root=replay_root,
        proposed_change_set_path=proposed_change_set_path,
    )
    path = _path_from_ref(resolved_ref, repo_root=repo_root)
    if path is not None and any(char in str(path) for char in ("*", "?", "[")):
        matches = [Path(match) for match in sorted(glob(str(path)))]
        file_matches = [match for match in matches if match.is_file()]
        if file_matches:
            path = file_matches[0]
    if path is None or not path.exists() or not path.is_file():
        return BudgetCorpusReplayOutputCheck(
            output_ref=output_ref,
            resolved_output_path=resolved_ref,
            exists=False,
        )
    return BudgetCorpusReplayOutputCheck(
        output_ref=output_ref,
        resolved_output_path=str(path),
        exists=True,
        sha256=_sha256(path),
        size_bytes=path.stat().st_size,
    )


def _case_dir(case: BudgetCorpusReplayCase, replay_root: Path) -> Path:
    return replay_root / "cases" / case.replay_case_id


def _arg_path(ref: str, *, repo_root: Path) -> str:
    path = Path(ref)
    if path.is_absolute():
        return str(path)
    return str(repo_root / path)


def _command_argv(
    *,
    case: BudgetCorpusReplayCase,
    command: BudgetCorpusReplayCommand,
    replay_root: Path,
    repo_root: Path,
    proposed_change_set_path: str | None,
) -> tuple[list[str] | None, list[str]]:
    slug = _slug(command)
    case_dir = _case_dir(case, replay_root)
    if slug == "baseline_demo":
        if not (
            case.baseline_input_ref
            and case.baseline_practice_profile_ref
            and case.baseline_confirmation_ref
        ):
            return None, ["baseline_refs_missing"]
        argv = [
            "demo",
            "--input",
            _arg_path(case.baseline_input_ref, repo_root=repo_root),
            "--practice-profile",
            _arg_path(case.baseline_practice_profile_ref, repo_root=repo_root),
            "--confirmation-template",
            _arg_path(case.baseline_confirmation_ref, repo_root=repo_root),
            "--out-dir",
            str(case_dir / "baseline"),
            "--adapter",
            "deterministic",
            "--strict-evidence",
        ]
        if case.artifact_kind == "reviewed_gold_fixture" or "--fixture-gold" in command.command:
            argv.extend(
                ["--fixture-gold", _arg_path(case.source_artifact_ref, repo_root=repo_root)]
            )
        return argv, []
    if slug == "record_budget_review":
        return [
            "record-budget-review",
            "--budget",
            str(case_dir / "baseline" / "budget" / "legal_budget_proposal.json"),
            "--review",
            _arg_path(case.source_artifact_ref, repo_root=repo_root),
            "--out-dir",
            str(case_dir / "budget-review"),
        ], []
    if slug == "compare_actuals":
        return [
            "compare-budget-actuals",
            "--budget",
            str(case_dir / "baseline" / "budget" / "legal_budget_proposal.json"),
            "--actuals",
            _arg_path(case.source_artifact_ref, repo_root=repo_root),
            "--out-dir",
            str(case_dir / "actuals"),
        ], []
    if slug == "capture_rejections":
        return [
            "capture-carrier-rejections",
            "--budget",
            str(case_dir / "baseline" / "budget" / "legal_budget_proposal.json"),
            "--source-bundle",
            _arg_path(case.source_artifact_ref, repo_root=repo_root),
            "--out-dir",
            str(case_dir / "carrier-rejections"),
        ], []
    if slug == "review_rejections":
        return [
            "review-carrier-rejections",
            "--reconciliation-report",
            str(case_dir / "carrier-rejections" / "carrier_rejection_reconciliation_report.json"),
            "--out-dir",
            str(case_dir / "carrier-rejection-review"),
        ], []
    if slug == "propose_rejection_learning":
        return [
            "propose-carrier-rejection-learning",
            "--review-packet",
            str(case_dir / "carrier-rejection-review" / "carrier_rejection_review_packet.json"),
            "--out-dir",
            str(case_dir / "carrier-rejection-learning"),
        ], []
    if slug == "review_learning_gate":
        argv = ["review-learning-gate", "--out-dir", str(case_dir / "learning-gate")]
        if case.artifact_kind == "budget_review_fixture":
            argv.extend(
                [
                    "--budget-revision-report",
                    str(case_dir / "budget-review" / "budget_revision_report.json"),
                ]
            )
        elif case.artifact_kind == "actuals_fixture":
            argv.extend(
                [
                    "--budget-actual-comparison-report",
                    str(case_dir / "actuals" / "budget_actual_comparison_report.json"),
                ]
            )
        elif case.artifact_kind == "carrier_rejection_fixture":
            argv.extend(
                [
                    "--carrier-learning-report",
                    str(
                        case_dir
                        / "carrier-rejection-learning"
                        / "carrier_rejection_learning_report.json"
                    ),
                ]
            )
        else:
            return None, [f"unsupported_review_learning_gate_kind={case.artifact_kind}"]
        return argv, []
    if slug == "promotion_readiness":
        return [
            "audit-learning-promotion-readiness",
            "--reviewed-learning-gate-report",
            _arg_path(case.source_artifact_ref, repo_root=repo_root),
            "--out-dir",
            str(case_dir / "promotion-readiness"),
        ], []
    if slug == "draft_proposed_changes":
        return [
            "draft-learning-proposed-changes",
            "--shadow-eval-plan",
            str(case_dir / "promotion-readiness" / "learning_shadow_eval_plan.json"),
            "--promotion-readiness-report",
            str(case_dir / "promotion-readiness" / "learning_promotion_readiness_report.json"),
            "--out-dir",
            str(case_dir / "proposed-changes"),
        ], []
    if slug == "run_shadow_eval":
        if proposed_change_set_path is None:
            return None, ["required_learning_proposed_change_set_json_missing"]
        return [
            "run-learning-shadow-eval",
            "--proposed-change-set",
            proposed_change_set_path,
            "--fixture-result",
            _arg_path(case.source_artifact_ref, repo_root=repo_root),
            "--out-dir",
            str(case_dir / "shadow-eval"),
        ], []
    return None, [f"unsupported_command_slug={slug or 'unknown'}"]


def _input_failures(argv: list[str], repo_root: Path) -> list[str]:
    flags_with_path_values = {
        "--input",
        "--practice-profile",
        "--confirmation-template",
        "--fixture-gold",
        "--budget",
        "--review",
        "--actuals",
        "--source-bundle",
        "--reconciliation-report",
        "--review-packet",
        "--carrier-learning-report",
        "--budget-revision-report",
        "--budget-actual-comparison-report",
        "--reviewed-learning-gate-report",
        "--shadow-eval-plan",
        "--promotion-readiness-report",
        "--proposed-change-set",
        "--fixture-result",
    }
    failures: list[str] = []
    for index, token in enumerate(argv[:-1]):
        if token not in flags_with_path_values:
            continue
        value = argv[index + 1]
        path = _path_from_ref(value, repo_root=repo_root)
        if path is not None and not path.exists():
            failures.append(f"missing_input:{token}={value}")
    return failures


def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    from .cli import main

    stdout = io.StringIO()
    stderr = io.StringIO()
    try:
        with redirect_stdout(stdout), redirect_stderr(stderr):
            return_code = main(argv)
    except SystemExit as exc:
        code = exc.code if isinstance(exc.code, int) else 1
        return code, stdout.getvalue(), stderr.getvalue()
    except Exception as exc:  # pragma: no cover - exercised through report output
        return 1, stdout.getvalue(), f"{type(exc).__name__}: {exc}"
    return return_code, stdout.getvalue(), stderr.getvalue()


def _command_result(
    *,
    case: BudgetCorpusReplayCase,
    command: BudgetCorpusReplayCommand,
    execution_mode: BudgetCorpusReplayRunMode,
    replay_root: Path,
    repo_root: Path,
    proposed_change_set_path: str | None,
    status: str,
    return_code: int | None = None,
    stdout: str = "",
    stderr: str = "",
    blocking_reasons: list[str] | None = None,
) -> BudgetCorpusReplayCommandResult:
    resolved_command = _resolve_text(
        command.command,
        replay_root=replay_root,
        proposed_change_set_path=proposed_change_set_path,
    )
    return BudgetCorpusReplayCommandResult(
        command_id=command.command_id,
        replay_case_id=case.replay_case_id,
        status=status,  # type: ignore[arg-type]
        execution_mode=execution_mode,
        planned_command=command.command,
        resolved_command=resolved_command,
        return_code=return_code,
        stdout_excerpt=_excerpt(stdout),
        stderr_excerpt=_excerpt(stderr),
        output_checks=[
            _output_check(
                output_ref,
                replay_root=replay_root,
                repo_root=repo_root,
                proposed_change_set_path=proposed_change_set_path,
            )
            for output_ref in command.expected_output_refs
        ],
        blocking_reasons=blocking_reasons or [],
    )


def _execute_case(
    *,
    case: BudgetCorpusReplayCase,
    replay_root: Path,
    repo_root: Path,
    proposed_change_set_path: str | None,
) -> tuple[BudgetCorpusReplayCaseResult, str | None]:
    command_results: list[BudgetCorpusReplayCommandResult] = []
    prior_failed = False
    current_proposed_change_set_path = proposed_change_set_path
    for command in case.command_chain:
        if prior_failed:
            command_results.append(
                _command_result(
                    case=case,
                    command=command,
                    execution_mode="execute",
                    replay_root=replay_root,
                    repo_root=repo_root,
                    proposed_change_set_path=current_proposed_change_set_path,
                    status="blocked_prior_command_failed",
                    blocking_reasons=["prior_command_failed"],
                )
            )
            continue
        argv, reasons = _command_argv(
            case=case,
            command=command,
            replay_root=replay_root,
            repo_root=repo_root,
            proposed_change_set_path=current_proposed_change_set_path,
        )
        if argv is None:
            status = (
                "blocked_missing_placeholder"
                if any("required_learning_proposed_change_set" in reason for reason in reasons)
                else "blocked_unsupported_command"
            )
            command_results.append(
                _command_result(
                    case=case,
                    command=command,
                    execution_mode="execute",
                    replay_root=replay_root,
                    repo_root=repo_root,
                    proposed_change_set_path=current_proposed_change_set_path,
                    status=status,
                    blocking_reasons=reasons,
                )
            )
            prior_failed = True
            continue
        input_failures = _input_failures(argv, repo_root)
        if input_failures:
            command_results.append(
                _command_result(
                    case=case,
                    command=command,
                    execution_mode="execute",
                    replay_root=replay_root,
                    repo_root=repo_root,
                    proposed_change_set_path=current_proposed_change_set_path,
                    status="blocked_missing_input",
                    blocking_reasons=input_failures,
                )
            )
            prior_failed = True
            continue
        return_code, stdout, stderr = _run_cli(argv)
        result = _command_result(
            case=case,
            command=command,
            execution_mode="execute",
            replay_root=replay_root,
            repo_root=repo_root,
            proposed_change_set_path=current_proposed_change_set_path,
            status="executed_passed" if return_code == 0 else "executed_failed",
            return_code=return_code,
            stdout=stdout,
            stderr=stderr,
            blocking_reasons=[] if return_code == 0 else [f"return_code={return_code}"],
        )
        command_results.append(result)
        if return_code != 0 or any(not check.exists for check in result.output_checks):
            prior_failed = True
        for check in result.output_checks:
            if check.exists and check.output_ref.endswith("learning_proposed_change_set.json"):
                current_proposed_change_set_path = check.resolved_output_path

    all_output_checks = [check for result in command_results for check in result.output_checks]
    if any(
        result.status
        in {
            "executed_failed",
            "blocked_missing_input",
            "blocked_prior_command_failed",
            "blocked_unsupported_command",
            "blocked_missing_placeholder",
        }
        for result in command_results
    ):
        status = "executed_failed"
    elif any(not check.exists for check in all_output_checks):
        status = "executed_failed"
    else:
        status = "executed_passed"
    return (
        BudgetCorpusReplayCaseResult(
            replay_case_id=case.replay_case_id,
            source_artifact_ref=case.source_artifact_ref,
            artifact_kind=case.artifact_kind,
            status=status,  # type: ignore[arg-type]
            command_results=command_results,
            output_checks=all_output_checks,
            blocking_reasons=[
                reason for result in command_results for reason in result.blocking_reasons
            ],
        ),
        current_proposed_change_set_path,
    )


def _dry_run_case(
    *,
    case: BudgetCorpusReplayCase,
    replay_root: Path,
    repo_root: Path,
    proposed_change_set_path: str | None,
) -> BudgetCorpusReplayCaseResult:
    command_results = [
        _command_result(
            case=case,
            command=command,
            execution_mode="dry_run",
            replay_root=replay_root,
            repo_root=repo_root,
            proposed_change_set_path=proposed_change_set_path,
            status="planned_only_not_executed",
        )
        for command in case.command_chain
    ]
    return BudgetCorpusReplayCaseResult(
        replay_case_id=case.replay_case_id,
        source_artifact_ref=case.source_artifact_ref,
        artifact_kind=case.artifact_kind,
        status="dry_run_ready",
        command_results=command_results,
        output_checks=[check for result in command_results for check in result.output_checks],
    )


def _non_executed_case(
    *,
    case: BudgetCorpusReplayCase,
    status: Literal["skipped_not_selected", "skipped_supporting_context", "blocked"],
    blocking_reasons: list[str],
) -> BudgetCorpusReplayCaseResult:
    return BudgetCorpusReplayCaseResult(
        replay_case_id=case.replay_case_id,
        source_artifact_ref=case.source_artifact_ref,
        artifact_kind=case.artifact_kind,
        status=status,
        command_results=[],
        output_checks=[],
        blocking_reasons=blocking_reasons,
    )


def _check(
    check_id: str,
    status: str,
    message: str,
    *,
    case_ids: list[str] | None = None,
    command_ids: list[str] | None = None,
) -> BudgetCorpusReplayExecutionCheck:
    return BudgetCorpusReplayExecutionCheck(
        check_id=check_id,
        status=status,  # type: ignore[arg-type]
        message=message,
        case_ids=case_ids or [],
        command_ids=command_ids or [],
    )


def build_budget_corpus_replay_execution_report(
    plan: BudgetCorpusReplayPlan,
    *,
    replay_plan_ref: str,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    execution_mode: BudgetCorpusReplayRunMode = "dry_run",
    selected_case_ids: list[str] | None = None,
    proposed_change_set_path: str | Path | None = None,
) -> BudgetCorpusReplayExecutionReport:
    run_dir = Path(out_dir)
    replay_root = run_dir / "replay-output"
    replay_root.mkdir(parents=True, exist_ok=True)
    repo_path = Path(repo_root).resolve()
    selected = set(selected_case_ids or [])
    proposed_change_set = str(proposed_change_set_path) if proposed_change_set_path else None
    selected_cases = [
        case
        for case in plan.cases
        if case.status == "planned_for_replay" and (not selected or case.replay_case_id in selected)
    ]
    cases: list[BudgetCorpusReplayCaseResult] = []
    for case in plan.cases:
        if plan.status != "replay_plan_ready_for_review":
            cases.append(
                _non_executed_case(
                    case=case,
                    status="blocked",
                    blocking_reasons=[f"replay_plan_status={plan.status}"],
                )
            )
            continue
        if selected and case.replay_case_id not in selected:
            cases.append(
                _non_executed_case(
                    case=case,
                    status="skipped_not_selected",
                    blocking_reasons=["case_not_selected"],
                )
            )
            continue
        if case.status == "supporting_context_only":
            cases.append(
                _non_executed_case(
                    case=case,
                    status="skipped_supporting_context",
                    blocking_reasons=["supporting_context_only"],
                )
            )
            continue
        if case.status == "blocked_from_replay":
            cases.append(
                _non_executed_case(
                    case=case,
                    status="blocked",
                    blocking_reasons=case.blocking_reasons or ["blocked_from_replay"],
                )
            )
            continue
        if execution_mode == "dry_run":
            cases.append(
                _dry_run_case(
                    case=case,
                    replay_root=replay_root,
                    repo_root=repo_path,
                    proposed_change_set_path=proposed_change_set,
                )
            )
            continue
        case_result, proposed_change_set = _execute_case(
            case=case,
            replay_root=replay_root,
            repo_root=repo_path,
            proposed_change_set_path=proposed_change_set,
        )
        cases.append(case_result)

    dry_run_count = sum(1 for case in cases if case.status == "dry_run_ready")
    executed_count = sum(1 for case in cases if case.status == "executed_passed")
    failed_count = sum(1 for case in cases if case.status == "executed_failed")
    blocked_count = sum(1 for case in cases if case.status == "blocked")
    skipped_count = sum(
        1 for case in cases if case.status in {"skipped_not_selected", "skipped_supporting_context"}
    )
    command_results = [command for case in cases for command in case.command_results]
    failed_commands = [
        command for command in command_results if command.status == "executed_failed"
    ]
    blocked_commands = [
        command
        for command in command_results
        if command.status
        in {
            "blocked_missing_input",
            "blocked_prior_command_failed",
            "blocked_unsupported_command",
            "blocked_missing_placeholder",
        }
    ]
    missing_outputs = [
        command.command_id
        for command in command_results
        if command.status == "executed_passed"
        and any(not check.exists for check in command.output_checks)
    ]
    checks = [
        _check(
            "replay_plan_ready",
            "passed" if plan.status == "replay_plan_ready_for_review" else "failed",
            f"Replay plan status is {plan.status}.",
        ),
        _check(
            "selected_cases_present",
            "passed" if selected_cases else "warning",
            "At least one planned case is selected for replay audit.",
            case_ids=[case.replay_case_id for case in selected_cases],
        ),
        _check(
            "commands_failed_closed",
            "passed" if not failed_commands and not blocked_commands else "failed",
            "Executed commands passed or were blocked with explicit reasons.",
            command_ids=[
                *[command.command_id for command in failed_commands],
                *[command.command_id for command in blocked_commands],
            ],
        ),
        _check(
            "expected_outputs_present",
            "passed" if not missing_outputs else "failed",
            "Expected outputs for executed commands are present.",
            command_ids=missing_outputs,
        ),
        _check(
            "no_learning_or_external_writes",
            "passed",
            "Replay audit performs local synthetic commands only and records no calibration, mutation, Lake, SQLite, external write, or silent learning.",
        ),
    ]
    if plan.status != "replay_plan_ready_for_review":
        status = "blocked_by_plan"
    elif not selected_cases:
        status = "no_executable_cases"
    elif execution_mode == "dry_run":
        status = "dry_run_ready_for_review"
    elif failed_count or blocked_count or failed_commands or blocked_commands or missing_outputs:
        status = "execution_failed"
    elif executed_count:
        status = "execution_passed_for_review"
    else:
        status = "no_executable_cases"
    return BudgetCorpusReplayExecutionReport(
        replay_execution_report_id=new_id("budgetcorpusreplayexec"),
        replay_plan_id=plan.replay_plan_id,
        replay_plan_ref=replay_plan_ref,
        execution_mode=execution_mode,
        status=status,  # type: ignore[arg-type]
        replay_run_root=str(replay_root),
        selected_case_ids=sorted(selected),
        case_count=len(cases),
        executed_case_count=executed_count,
        dry_run_case_count=dry_run_count,
        skipped_case_count=skipped_count,
        blocked_case_count=blocked_count,
        failed_case_count=failed_count,
        command_count=len(command_results),
        executed_command_count=sum(
            1 for command in command_results if command.status == "executed_passed"
        ),
        failed_command_count=len(failed_commands),
        cases=cases,
        checks=checks,
        required_next_gates=REPLAY_EXECUTION_REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_corpus_replay_execution_report(
    report: BudgetCorpusReplayExecutionReport,
) -> str:
    lines = [
        "# Budget Corpus Replay Execution Report",
        "",
        f"**Report ID:** {report.replay_execution_report_id}",
        f"**Status:** {report.status}",
        f"**Mode:** {report.execution_mode}",
        f"**Replay plan:** {report.replay_plan_ref}",
        f"**Replay root:** {report.replay_run_root}",
        f"**Cases:** {report.case_count}",
        f"**Executed:** {report.executed_case_count}",
        f"**Dry-run:** {report.dry_run_case_count}",
        f"**Skipped:** {report.skipped_case_count}",
        f"**Blocked:** {report.blocked_case_count}",
        f"**Failed:** {report.failed_case_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Synthetic only: {report.synthetic_only}",
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
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in report.required_next_gates),
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
    lines.extend(["", "## Cases", ""])
    for case in report.cases:
        lines.append(
            f"- `{case.source_artifact_ref}`: {case.status}; "
            f"kind={case.artifact_kind}; commands={len(case.command_results)}"
        )
        for reason in case.blocking_reasons:
            lines.append(f"  - blocked: {reason}")
        for command in case.command_results:
            lines.append(
                f"  - {command.command_id}: {command.status}; return_code={command.return_code}"
            )
            for output in command.output_checks:
                lines.append(f"    - output `{output.output_ref}` exists={output.exists}")
    lines.extend(
        [
            "",
            "This replay report is local candidate evidence only. It does not authorize calibration, profile/template/guideline mutation, budget submission, Lake or SQLite admission, external writes, or real-data use.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_corpus_replay_execution(
    *,
    replay_plan_path: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    execute: bool = False,
    case_ids: list[str] | None = None,
    proposed_change_set_path: str | Path | None = None,
) -> tuple[BudgetCorpusReplayExecutionReport, Path]:
    plan_path = Path(replay_plan_path)
    plan = BudgetCorpusReplayPlan.model_validate(load_json(plan_path))
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report = build_budget_corpus_replay_execution_report(
        plan,
        replay_plan_ref=str(plan_path),
        out_dir=run_dir,
        repo_root=repo_root,
        execution_mode="execute" if execute else "dry_run",
        selected_case_ids=case_ids or [],
        proposed_change_set_path=proposed_change_set_path,
    )
    write_json(
        run_dir / BUDGET_CORPUS_REPLAY_EXECUTION_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_CORPUS_REPLAY_EXECUTION_NOTES_FILENAME).write_text(
        render_budget_corpus_replay_execution_report(report),
        encoding="utf-8",
    )
    return report, run_dir
