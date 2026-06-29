"""Run pytest under the repo validation runtime policy."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config" / "validation-runtime-policy.yaml"
DEFAULT_MINIMUM_TIMEOUT_SECONDS = 900
POLICY_MARKER_ENV_VAR = "LAWFIRM_OS_VALIDATION_RUNTIME_POLICY"
POLICY_MARKER_VALUE = "intake-validation-runtime-policy.v1"


def _load_policy() -> dict[str, Any]:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        raise ValueError(f"Validation runtime policy is not a mapping: {POLICY_PATH}")
    return policy


def pytest_timeout_seconds(command_key: str = "full_pytest") -> int:
    if command_key not in {"full_pytest", "focused_pytest"}:
        raise ValueError(f"Unsupported pytest validation command key: {command_key}")

    commands = _load_policy().get("commands", {})
    if not isinstance(commands, dict):
        raise ValueError("Validation runtime policy commands section is missing or invalid")
    pytest_policy = commands.get(command_key, {})
    if not isinstance(pytest_policy, dict):
        raise ValueError(f"Validation runtime policy {command_key} section is missing or invalid")

    timeout_seconds = int(
        pytest_policy.get("minimum_timeout_seconds", DEFAULT_MINIMUM_TIMEOUT_SECONDS)
    )
    if timeout_seconds < DEFAULT_MINIMUM_TIMEOUT_SECONDS:
        raise ValueError(
            f"Validation runtime policy {command_key} minimum_timeout_seconds "
            f"must be at least {DEFAULT_MINIMUM_TIMEOUT_SECONDS}"
        )
    return timeout_seconds


def validation_environment(base_env: Mapping[str, str] | None = None) -> dict[str, str]:
    env = dict(base_env) if base_env is not None else dict(os.environ)
    env[POLICY_MARKER_ENV_VAR] = POLICY_MARKER_VALUE
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def pytest_command(pytest_args: list[str]) -> list[str]:
    return [sys.executable, "-B", "-m", "pytest", "-p", "no:cacheprovider", *pytest_args]


def main(argv: list[str] | None = None) -> int:
    pytest_args = list(argv if argv is not None else sys.argv[1:])
    command = pytest_command(pytest_args)
    command_key = "focused_pytest" if pytest_args else "full_pytest"
    timeout_seconds = pytest_timeout_seconds(command_key)

    print(
        f"Running {' '.join(command)} with validation timeout {timeout_seconds}s",
        flush=True,
    )
    try:
        completed = subprocess.run(
            command,
            check=False,
            env=validation_environment(),
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired:
        print(
            "pytest exceeded the validation runtime policy timeout "
            f"({timeout_seconds}s). Increase config/validation-runtime-policy.yaml "
            "only after reviewing why the suite got slower.",
            file=sys.stderr,
        )
        return 124
    return completed.returncode


if __name__ == "__main__":
    raise SystemExit(main())
