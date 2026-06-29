"""Run pytest under the repo validation runtime policy."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config" / "validation-runtime-policy.yaml"
DEFAULT_MINIMUM_TIMEOUT_SECONDS = 900


def _load_policy() -> dict[str, Any]:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        raise ValueError(f"Validation runtime policy is not a mapping: {POLICY_PATH}")
    return policy


def pytest_timeout_seconds() -> int:
    commands = _load_policy().get("commands", {})
    if not isinstance(commands, dict):
        raise ValueError("Validation runtime policy commands section is missing or invalid")
    full_pytest = commands.get("full_pytest", {})
    if not isinstance(full_pytest, dict):
        raise ValueError("Validation runtime policy full_pytest section is missing or invalid")

    timeout_seconds = int(
        full_pytest.get("minimum_timeout_seconds", DEFAULT_MINIMUM_TIMEOUT_SECONDS)
    )
    if timeout_seconds < DEFAULT_MINIMUM_TIMEOUT_SECONDS:
        raise ValueError(
            "Validation runtime policy full_pytest minimum_timeout_seconds "
            f"must be at least {DEFAULT_MINIMUM_TIMEOUT_SECONDS}"
        )
    return timeout_seconds


def main(argv: list[str] | None = None) -> int:
    pytest_args = list(argv if argv is not None else sys.argv[1:])
    command = [sys.executable, "-m", "pytest", *pytest_args]
    timeout_seconds = pytest_timeout_seconds()

    print(
        f"Running {' '.join(command)} with validation timeout {timeout_seconds}s",
        flush=True,
    )
    try:
        completed = subprocess.run(command, check=False, timeout=timeout_seconds)
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
