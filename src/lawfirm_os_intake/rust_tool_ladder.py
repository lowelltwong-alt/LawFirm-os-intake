from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .models import (
    RustToolLadderAuditCheck,
    RustToolLadderAuditReport,
    RustToolLadderConfig,
    RustToolLadderStage,
    RustToolLadderTool,
)
from .rust_transition_policy import RUST_TRANSITION_POLICY_REF, load_rust_transition_policy
from .util import digest_json, load_json, now_iso, write_json


RUST_TOOL_LADDER_REF = "config/rust-tool-ladder.json"
RUST_TOOL_LADDER_AUDIT_REPORT_FILENAME = "rust_tool_ladder_audit_report.json"
RUST_TOOL_LADDER_AUDIT_NOTES_FILENAME = "rust_tool_ladder_audit_report.md"
RUST_TOOL_LADDER_METHODOLOGY_VERSION = "rust_tool_ladder.v0_1"

STAGE_ORDER: list[RustToolLadderStage] = [
    "s0_candidate",
    "s1_shadow",
    "s2_audit",
    "s3_cosign",
    "s4_authoritative",
]
STAGE_INDEX = {stage: index for index, stage in enumerate(STAGE_ORDER)}
SUCCESS_LABELS = ["rust_tool_ladder_review_candidate"]
FAILURE_LABELS = SUCCESS_LABELS + ["rust_tool_ladder_blocked"]
REQUIRED_NEXT_GATES = [
    "human_rust_ladder_review",
    "python_reference_oracle_preserved",
    "frozen_parity_corpus_before_audit_stage",
    "divergence_adjudication_before_cosign",
    "orchestrator_adapter_review_before_runtime_use",
    "no_semantic_or_budget_scope_in_rust",
]


def run_rust_tool_ladder_audit(
    *,
    ladder_path: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
) -> tuple[RustToolLadderAuditReport, Path]:
    repo = Path(repo_root).resolve()
    ladder_ref = _repo_ref(repo, ladder_path)
    ladder_payload = load_json(_resolve_ladder_path(repo, ladder_path))
    config, config_checks = _load_ladder_config(ladder_payload)
    policy = load_rust_transition_policy()
    checks = [
        *config_checks,
        *_policy_checks(config, policy),
    ]
    if config is not None:
        for tool in config.tools:
            checks.extend(_tool_checks(repo, tool, set(policy.forbidden_rust_scope)))
    stage_counts = _stage_counts(config.tools if config is not None else [])
    failed = [check for check in checks if check.status == "failed"]
    report = RustToolLadderAuditReport(
        rust_tool_ladder_audit_report_id="rusttoolladder_"
        + digest_json(
            {
                "ladder_ref": ladder_ref,
                "ladder_id": config.ladder_id if config is not None else None,
                "failed_checks": [check.check_id for check in failed],
                "tool_ids": [tool.tool_id for tool in config.tools] if config else [],
            }
        )[len("sha256:") : len("sha256:") + 20],
        status=("blocked_by_rust_tool_ladder" if failed else "rust_tool_ladder_ready_for_review"),
        ladder_ref=ladder_ref,
        ladder_id=config.ladder_id if config is not None else None,
        rust_transition_policy_ref=(
            config.rust_transition_policy_ref if config is not None else None
        ),
        tool_count=sum(stage_counts.values()),
        s0_candidate_count=stage_counts["s0_candidate"],
        s1_shadow_count=stage_counts["s1_shadow"],
        s2_audit_count=stage_counts["s2_audit"],
        s3_cosign_count=stage_counts["s3_cosign"],
        s4_authoritative_count=stage_counts["s4_authoritative"],
        failed_check_count=len(failed),
        checks=checks,
        candidate_exception_lake_labels=FAILURE_LABELS if failed else SUCCESS_LABELS,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / RUST_TOOL_LADDER_AUDIT_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / RUST_TOOL_LADDER_AUDIT_NOTES_FILENAME).write_text(
        render_rust_tool_ladder_audit_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def render_rust_tool_ladder_audit_report(report: RustToolLadderAuditReport) -> str:
    failed = [check for check in report.checks if check.status == "failed"]
    lines = [
        "# Rust Tool Ladder Audit",
        "",
        f"**Report ID:** {report.rust_tool_ladder_audit_report_id}",
        f"**Status:** {report.status}",
        f"**Ladder:** `{report.ladder_ref}`",
        "",
        "## Boundary",
        "",
        "- Candidate-only and non-authoritative.",
        "- Python remains the oracle until a reviewed ladder stage says otherwise.",
        "- Rust cannot own legal classification, matter routing, budget decisions, learning, connectors, Lake/SQLite writes, or canon.",
        "- No replacement, runtime adapter, external write, budget submission, or matter opening is authorized.",
        "",
        "## Stage Counts",
        "",
        f"- S0 candidate: {report.s0_candidate_count}",
        f"- S1 shadow: {report.s1_shadow_count}",
        f"- S2 audit: {report.s2_audit_count}",
        f"- S3 co-sign: {report.s3_cosign_count}",
        f"- S4 authoritative: {report.s4_authoritative_count}",
        "",
        "## Failed Checks",
        "",
    ]
    if not failed:
        lines.append("- None.")
    for check in failed:
        prefix = f"{check.tool_id}: " if check.tool_id else ""
        lines.append(f"- `{check.check_id}`: {prefix}{check.message}")
    lines.extend(
        [
            "",
            "## Required Next Gates",
            "",
            *(f"- `{gate}`" for gate in report.required_next_gates),
            "",
        ]
    )
    return "\n".join(lines)


def _load_ladder_config(
    payload: Any,
) -> tuple[RustToolLadderConfig | None, list[RustToolLadderAuditCheck]]:
    if not isinstance(payload, dict):
        return None, [
            _failed(
                "rust_tool_ladder_payload_mapping",
                "Rust tool ladder payload must be a JSON object.",
            )
        ]
    try:
        config = RustToolLadderConfig.model_validate(payload)
    except ValidationError as exc:
        return None, [
            _failed(
                "rust_tool_ladder_schema_valid",
                f"Rust tool ladder schema validation failed: {exc}",
            )
        ]
    return config, [
        _passed(
            "rust_tool_ladder_schema_valid",
            "Rust tool ladder validates against the local candidate schema.",
            evidence_refs=[config.ladder_id],
        )
    ]


def _policy_checks(
    config: RustToolLadderConfig | None, policy: Any
) -> list[RustToolLadderAuditCheck]:
    checks: list[RustToolLadderAuditCheck] = []
    checks.append(
        _passed(
            "rust_transition_policy_loaded",
            "Rust transition policy loaded as the source for forbidden scope.",
            evidence_refs=[RUST_TRANSITION_POLICY_REF],
        )
    )
    if config is None:
        return checks
    checks.append(
        _passed(
            "rust_tool_ladder_methodology_version",
            f"Rust ladder methodology is {RUST_TOOL_LADDER_METHODOLOGY_VERSION}.",
            evidence_refs=[config.methodology_version],
        )
        if config.methodology_version == RUST_TOOL_LADDER_METHODOLOGY_VERSION
        else _failed(
            "rust_tool_ladder_methodology_version",
            "Rust ladder methodology version is not supported.",
            blocking_refs=[config.methodology_version],
        )
    )
    checks.append(
        _passed(
            "rust_tool_ladder_policy_ref_matches",
            "Rust ladder references the active Rust transition policy.",
            evidence_refs=[config.rust_transition_policy_ref],
        )
        if config.rust_transition_policy_ref == RUST_TRANSITION_POLICY_REF
        else _failed(
            "rust_tool_ladder_policy_ref_matches",
            "Rust ladder must reference the active Rust transition policy.",
            blocking_refs=[config.rust_transition_policy_ref],
        )
    )
    checks.append(
        _passed(
            "rust_replacement_globally_blocked",
            "Rust replacement remains globally blocked in ladder and transition policy.",
        )
        if config.rust_replacement_allowed is False
        and policy.rust_replacement_allowed is False
        and policy.no_rust_runtime_added is True
        else _failed(
            "rust_replacement_globally_blocked",
            "Rust replacement/runtime flags must remain disabled.",
        )
    )
    return checks


def _tool_checks(
    repo: Path,
    tool: RustToolLadderTool,
    forbidden_scope: set[str],
) -> list[RustToolLadderAuditCheck]:
    checks: list[RustToolLadderAuditCheck] = []
    stage_index = STAGE_INDEX[tool.stage]
    ceiling_index = STAGE_INDEX[tool.stage_ceiling]
    checks.append(
        _passed(
            "rust_tool_stage_within_ceiling",
            "Tool stage is within its declared stage ceiling.",
            tool_id=tool.tool_id,
            evidence_refs=[tool.stage, tool.stage_ceiling],
        )
        if stage_index <= ceiling_index
        else _failed(
            "rust_tool_stage_within_ceiling",
            "Tool stage exceeds its declared stage ceiling.",
            tool_id=tool.tool_id,
            blocking_refs=[tool.stage, tool.stage_ceiling],
        )
    )
    forbidden = sorted(set(tool.scope_items) & forbidden_scope)
    checks.append(
        _passed(
            "rust_tool_forbidden_scope_absent",
            "Tool scope stays outside forbidden Rust scope.",
            tool_id=tool.tool_id,
            evidence_refs=tool.scope_items,
        )
        if not forbidden
        else _failed(
            "rust_tool_forbidden_scope_absent",
            "Tool scope intersects with forbidden Rust scope.",
            tool_id=tool.tool_id,
            blocking_refs=forbidden,
        )
    )
    checks.append(
        _passed(
            "rust_tool_history_current",
            "Latest ladder history event matches current stage.",
            tool_id=tool.tool_id,
            evidence_refs=[tool.history[-1].event_id],
        )
    )
    if not tool.review_by:
        checks.append(
            _failed(
                "rust_tool_review_by_present",
                "Tool ladder entry requires a review_by date.",
                tool_id=tool.tool_id,
            )
        )
    else:
        checks.append(
            _passed(
                "rust_tool_review_by_present",
                "Tool ladder entry has a review_by date.",
                tool_id=tool.tool_id,
                evidence_refs=[tool.review_by],
            )
        )
    stage_evidence = tool.gate_evidence.get(tool.stage, [])
    checks.append(
        _passed(
            "rust_tool_current_stage_gate_evidence_present",
            "Tool records gate evidence for its current stage.",
            tool_id=tool.tool_id,
            evidence_refs=stage_evidence,
        )
        if stage_evidence
        else _failed(
            "rust_tool_current_stage_gate_evidence_present",
            "Tool requires gate_evidence for its current stage.",
            tool_id=tool.tool_id,
            blocking_refs=[tool.stage],
        )
    )
    if tool.stage != "s0_candidate":
        checks.extend(_existing_tool_ref_checks(repo, tool))
    if stage_index >= STAGE_INDEX["s1_shadow"]:
        checks.append(
            _passed(
                "rust_tool_s1_tests_declared",
                "S1+ tool declares local test refs.",
                tool_id=tool.tool_id,
                evidence_refs=tool.test_refs,
            )
            if tool.test_refs
            else _failed(
                "rust_tool_s1_tests_declared",
                "S1+ tool requires local test refs.",
                tool_id=tool.tool_id,
            )
        )
    if stage_index >= STAGE_INDEX["s2_audit"]:
        checks.extend(_s2_checks(repo, tool))
    if stage_index >= STAGE_INDEX["s3_cosign"]:
        checks.extend(_s3_checks(repo, tool))
    if stage_index >= STAGE_INDEX["s4_authoritative"]:
        checks.extend(_s4_checks(repo, tool))
    checks.append(
        _passed(
            "rust_tool_no_replacement_authority",
            "Tool does not authorize Rust replacement or downstream Rust output consumption.",
            tool_id=tool.tool_id,
        )
        if tool.rust_replacement_allowed is False
        and (not tool.rust_output_consumed_downstream or stage_index >= STAGE_INDEX["s3_cosign"])
        else _failed(
            "rust_tool_no_replacement_authority",
            "Tool attempts to authorize Rust replacement or premature downstream consumption.",
            tool_id=tool.tool_id,
        )
    )
    return checks


def _existing_tool_ref_checks(
    repo: Path,
    tool: RustToolLadderTool,
) -> list[RustToolLadderAuditCheck]:
    checks: list[RustToolLadderAuditCheck] = []
    required_refs = {
        "rust_tool_cargo_manifest_exists": tool.cargo_manifest_ref,
        "rust_tool_wrapper_module_exists": tool.wrapper_module_ref,
    }
    for check_id, ref in required_refs.items():
        checks.append(_path_check(repo, ref, check_id, tool.tool_id))
    if tool.cli_command_ref:
        cli_path, _, command = tool.cli_command_ref.partition("#")
        checks.append(_path_check(repo, cli_path, "rust_tool_cli_ref_file_exists", tool.tool_id))
        cli_file = repo / cli_path
        if cli_file.is_file() and command:
            text = cli_file.read_text(encoding="utf-8")
            checks.append(
                _passed(
                    "rust_tool_cli_command_declared",
                    "CLI command ref appears in cli.py.",
                    tool_id=tool.tool_id,
                    evidence_refs=[tool.cli_command_ref],
                )
                if command in text
                else _failed(
                    "rust_tool_cli_command_declared",
                    "CLI command ref is missing from cli.py.",
                    tool_id=tool.tool_id,
                    blocking_refs=[tool.cli_command_ref],
                )
            )
    for ref in tool.test_refs:
        checks.append(_path_check(repo, ref, "rust_tool_test_ref_exists", tool.tool_id))
    return checks


def _s2_checks(repo: Path, tool: RustToolLadderTool) -> list[RustToolLadderAuditCheck]:
    checks = [
        _path_check(
            repo,
            tool.parity_corpus_ref,
            "rust_tool_s2_parity_corpus_exists",
            tool.tool_id,
        )
    ]
    if tool.replacement_target != "none":
        checks.append(
            _path_check(
                repo,
                tool.python_oracle_ref,
                "rust_tool_s2_python_oracle_exists",
                tool.tool_id,
            )
        )
    checks.append(
        _passed(
            "rust_tool_s2_frozen_goldens_reviewed",
            "S2+ tool has reviewed frozen parity goldens.",
            tool_id=tool.tool_id,
        )
        if tool.frozen_goldens_reviewed
        else _failed(
            "rust_tool_s2_frozen_goldens_reviewed",
            "S2+ tool requires reviewed frozen parity goldens.",
            tool_id=tool.tool_id,
        )
    )
    if not tool.ci_wiring_refs:
        checks.append(
            _failed(
                "rust_tool_s2_ci_wiring_declared",
                "S2+ tool requires CI wiring refs.",
                tool_id=tool.tool_id,
            )
        )
    else:
        for ref in tool.ci_wiring_refs:
            checks.append(_path_check(repo, ref, "rust_tool_s2_ci_wiring_declared", tool.tool_id))
    return checks


def _s3_checks(repo: Path, tool: RustToolLadderTool) -> list[RustToolLadderAuditCheck]:
    return [
        _path_check(
            repo,
            tool.adjudication_dir_ref,
            "rust_tool_s3_adjudication_dir_exists",
            tool.tool_id,
        ),
        _path_check(
            repo,
            tool.contract_lock_ref,
            "rust_tool_s3_contract_lock_exists",
            tool.tool_id,
        ),
    ]


def _s4_checks(repo: Path, tool: RustToolLadderTool) -> list[RustToolLadderAuditCheck]:
    checks = [
        _path_check(
            repo,
            tool.weekly_parity_job_ref,
            "rust_tool_s4_weekly_parity_job_exists",
            tool.tool_id,
        )
    ]
    checks.append(
        _passed(
            "rust_tool_s4_python_oracle_retained",
            "S4 tool retains Python oracle.",
            tool_id=tool.tool_id,
        )
        if tool.python_retained_as_oracle
        else _failed(
            "rust_tool_s4_python_oracle_retained",
            "S4 tool must retain Python oracle.",
            tool_id=tool.tool_id,
        )
    )
    return checks


def _path_check(
    repo: Path,
    ref: str | None,
    check_id: str,
    tool_id: str,
) -> RustToolLadderAuditCheck:
    if not ref:
        return _failed(check_id, "Required path ref is missing.", tool_id=tool_id)
    resolved = (repo / ref).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError:
        return _failed(
            check_id,
            "Path ref escapes the repository root.",
            tool_id=tool_id,
            blocking_refs=[ref],
        )
    if not resolved.exists():
        return _failed(
            check_id,
            "Required path ref does not exist.",
            tool_id=tool_id,
            blocking_refs=[ref],
        )
    return _passed(
        check_id,
        "Required path ref exists.",
        tool_id=tool_id,
        evidence_refs=[ref],
    )


def _stage_counts(tools: list[RustToolLadderTool]) -> dict[RustToolLadderStage, int]:
    counts = {stage: 0 for stage in STAGE_ORDER}
    for tool in tools:
        counts[tool.stage] += 1
    return counts


def _resolve_ref(repo: Path, path: str | Path) -> Path:
    target = Path(path)
    resolved = target.resolve() if target.is_absolute() else (repo / target).resolve()
    try:
        resolved.relative_to(repo)
    except ValueError as exc:
        raise ValueError(f"path escapes repo root: {path}") from exc
    return resolved


def _resolve_ladder_path(repo: Path, path: str | Path) -> Path:
    target = Path(path)
    return target.resolve() if target.is_absolute() else (repo / target).resolve()


def _repo_ref(repo: Path, path: str | Path) -> str:
    target = Path(path)
    resolved = target.resolve() if target.is_absolute() else (repo / target).resolve()
    try:
        return resolved.relative_to(repo).as_posix()
    except ValueError:
        return str(path)


def _passed(
    check_id: str,
    message: str,
    *,
    tool_id: str | None = None,
    evidence_refs: list[str] | None = None,
) -> RustToolLadderAuditCheck:
    return RustToolLadderAuditCheck(
        check_id=check_id,
        status="passed",
        message=message,
        tool_id=tool_id,
        evidence_refs=evidence_refs or [],
    )


def _failed(
    check_id: str,
    message: str,
    *,
    tool_id: str | None = None,
    blocking_refs: list[str] | None = None,
) -> RustToolLadderAuditCheck:
    return RustToolLadderAuditCheck(
        check_id=check_id,
        status="failed",
        message=message,
        tool_id=tool_id,
        blocking_refs=blocking_refs or [],
    )
