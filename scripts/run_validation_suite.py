"""Run the repository validation suite under the runtime policy."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

import yaml


sys.dont_write_bytecode = True
REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config" / "validation-runtime-policy.yaml"
sys.path.insert(0, str(REPO_ROOT / "src"))

from lawfirm_os_intake.models import (  # noqa: E402
    ValidationSuiteEvidenceReport,
    ValidationSuiteStepEvidence,
)
from lawfirm_os_intake.util import digest_json, now_iso, write_json  # noqa: E402


@dataclass(frozen=True)
class ValidationStep:
    name: str
    command_key: str
    command: tuple[str, ...]
    timeout_seconds: int


def _load_policy() -> dict[str, Any]:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        raise ValueError(f"Validation runtime policy is not a mapping: {POLICY_PATH}")
    return policy


def _policy_timeout_seconds(policy: dict[str, Any], command_key: str) -> int:
    commands = policy.get("commands", {})
    if not isinstance(commands, dict):
        raise ValueError("Validation runtime policy commands section is missing or invalid")
    command_policy = commands.get(command_key, {})
    if not isinstance(command_policy, dict):
        raise ValueError(f"Validation runtime policy {command_key} section is missing")
    timeout_seconds = int(command_policy.get("minimum_timeout_seconds", 0))
    if timeout_seconds <= 0:
        raise ValueError(
            f"Validation runtime policy {command_key} minimum_timeout_seconds must be positive"
        )
    return timeout_seconds


def validation_steps(policy: dict[str, Any] | None = None) -> list[ValidationStep]:
    loaded_policy = policy if policy is not None else _load_policy()
    python = sys.executable
    definitions: tuple[tuple[str, str, tuple[str, ...]], ...] = (
        ("validate_repo", "validate_repo", (python, "scripts/validate_repo.py")),
        ("export_schemas", "export_schemas", (python, "scripts/export_schemas.py")),
        (
            "ruff_check",
            "ruff_check",
            (python, "-m", "ruff", "check", "--no-cache", "src", "tests", "scripts"),
        ),
        (
            "ruff_format_check",
            "ruff_format_check",
            (
                python,
                "-m",
                "ruff",
                "format",
                "--check",
                "--no-cache",
                "src",
                "tests",
                "scripts",
            ),
        ),
        ("full_pytest", "full_pytest", (python, "scripts/run_full_pytest.py")),
        ("smoke_demo", "smoke_demo", ("bash", "scripts/smoke_demo.sh")),
        ("validate_repo_final", "validate_repo", (python, "scripts/validate_repo.py")),
    )
    return [
        ValidationStep(
            name=name,
            command_key=command_key,
            command=command,
            timeout_seconds=_policy_timeout_seconds(loaded_policy, command_key),
        )
        for name, command_key, command in definitions
    ]


def _validation_environment() -> dict[str, str]:
    env = dict(os.environ)
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _step_evidence_refs(step: ValidationStep) -> list[str]:
    if step.name == "validate_repo":
        return ["scripts/validate_repo.py"]
    if step.name == "validate_repo_final":
        return ["scripts/validate_repo.py", "scripts/run_validation_suite.py"]
    if step.name == "export_schemas":
        return ["scripts/export_schemas.py", "schemas/"]
    if step.name == "ruff_check":
        return ["src/", "tests/", "scripts/"]
    if step.name == "ruff_format_check":
        return ["src/", "tests/", "scripts/"]
    if step.name == "full_pytest":
        return ["scripts/run_full_pytest.py", "tests/"]
    if step.name == "smoke_demo":
        return ["scripts/smoke_demo.sh"]
    return ["scripts/run_validation_suite.py"]


def run_step_with_evidence(step: ValidationStep) -> ValidationSuiteStepEvidence:
    started_at = now_iso()
    started = time.perf_counter()
    print(
        f"Running {step.name}: {' '.join(step.command)} (timeout {step.timeout_seconds}s)",
        flush=True,
    )
    try:
        completed = subprocess.run(
            step.command,
            cwd=REPO_ROOT,
            check=False,
            env=_validation_environment(),
            timeout=step.timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        completed_at = now_iso()
        print(
            f"{step.name} exceeded validation runtime policy timeout "
            f"({step.timeout_seconds}s). Review the slow step before raising "
            f"{POLICY_PATH.relative_to(REPO_ROOT)}.",
            file=sys.stderr,
        )
        return ValidationSuiteStepEvidence(
            step_id=step.name,
            command_key=step.command_key,
            command=list(step.command),
            command_display=" ".join(step.command),
            status="timed_out",
            return_code=124,
            timeout_seconds=step.timeout_seconds,
            duration_seconds=round(time.perf_counter() - started, 3),
            started_at=started_at,
            completed_at=completed_at,
            evidence_refs=_step_evidence_refs(step),
        )
    completed_at = now_iso()
    return_code = completed.returncode
    return ValidationSuiteStepEvidence(
        step_id=step.name,
        command_key=step.command_key,
        command=list(step.command),
        command_display=" ".join(step.command),
        status="passed" if return_code == 0 else "failed",
        return_code=return_code,
        timeout_seconds=step.timeout_seconds,
        duration_seconds=round(time.perf_counter() - started, 3),
        started_at=started_at,
        completed_at=completed_at,
        evidence_refs=_step_evidence_refs(step),
    )


def run_step(step: ValidationStep) -> int:
    return run_step_with_evidence(step).return_code or 0


def _git_commit() -> str | None:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _working_tree_dirty() -> bool:
    result = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=REPO_ROOT,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    return result.returncode != 0 or bool(result.stdout.strip())


def build_validation_suite_evidence_report(
    *,
    steps: list[ValidationSuiteStepEvidence],
    policy: dict[str, Any] | None = None,
    generated_at: str | None = None,
    repo_root: Path = REPO_ROOT,
    git_commit: str | None = None,
    working_tree_dirty: bool | None = None,
) -> ValidationSuiteEvidenceReport:
    loaded_policy = policy if policy is not None else _load_policy()
    failed = [step for step in steps if step.status == "failed"]
    timed_out = [step for step in steps if step.status == "timed_out"]
    status = "blocked_by_validation_suite" if failed or timed_out else "validation_suite_passed"
    generated = generated_at or now_iso()
    report_basis = {
        "generated_at": generated,
        "status": status,
        "steps": [
            {
                "step_id": step.step_id,
                "status": step.status,
                "return_code": step.return_code,
            }
            for step in steps
        ],
    }
    return ValidationSuiteEvidenceReport(
        validation_suite_evidence_report_id="validation_suite_evidence_"
        + digest_json(report_basis).removeprefix("sha256:")[:16],
        status=status,
        policy_id=str(loaded_policy.get("policy_id") or "unknown"),
        policy_version=str(loaded_policy.get("version") or "unknown"),
        policy_ref=POLICY_PATH.relative_to(REPO_ROOT).as_posix(),
        repo_root_ref=str(repo_root),
        git_commit=git_commit if git_commit is not None else _git_commit(),
        working_tree_dirty=(
            _working_tree_dirty() if working_tree_dirty is None else working_tree_dirty
        ),
        step_count=len(steps),
        passed_step_count=sum(1 for step in steps if step.status == "passed"),
        failed_step_count=len(failed),
        timed_out_step_count=len(timed_out),
        steps=steps,
        required_next_actions=(
            ["Validation suite passed; attach this local JSON as QA evidence for the read-only UI."]
            if status == "validation_suite_passed"
            else ["Fix failed or timed-out validation steps before calling the POC QA-ready."]
        ),
        generated_at=generated,
    )


def write_validation_suite_evidence_report(
    *,
    out_path: str | Path,
    steps: list[ValidationSuiteStepEvidence],
    policy: dict[str, Any] | None = None,
    generated_at: str | None = None,
) -> ValidationSuiteEvidenceReport:
    report = build_validation_suite_evidence_report(
        steps=steps,
        policy=policy,
        generated_at=generated_at,
    )
    write_json(out_path, report.model_dump(mode="json"))
    return report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-out",
        help="Optional local JSON validation_suite_evidence_report.json output path.",
    )
    parser.add_argument(
        "--generated-at",
        help="Optional deterministic timestamp for generated report fixtures.",
    )
    args = parser.parse_args(argv)

    policy = _load_policy()
    step_evidence: list[ValidationSuiteStepEvidence] = []
    for step in validation_steps(policy):
        evidence = run_step_with_evidence(step)
        step_evidence.append(evidence)
        if evidence.return_code != 0:
            if args.report_out:
                write_validation_suite_evidence_report(
                    out_path=args.report_out,
                    steps=step_evidence,
                    policy=policy,
                    generated_at=args.generated_at,
                )
            return evidence.return_code or 1
    if args.report_out:
        write_validation_suite_evidence_report(
            out_path=args.report_out,
            steps=step_evidence,
            policy=policy,
            generated_at=args.generated_at,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
