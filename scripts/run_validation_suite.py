"""Run the repository validation suite under the runtime policy."""

from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


sys.dont_write_bytecode = True
REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config" / "validation-runtime-policy.yaml"


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


def run_step(step: ValidationStep) -> int:
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
        print(
            f"{step.name} exceeded validation runtime policy timeout "
            f"({step.timeout_seconds}s). Review the slow step before raising "
            f"{POLICY_PATH.relative_to(REPO_ROOT)}.",
            file=sys.stderr,
        )
        return 124
    return completed.returncode


def main() -> int:
    for step in validation_steps():
        return_code = run_step(step)
        if return_code != 0:
            return return_code
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
