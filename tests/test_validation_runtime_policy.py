from __future__ import annotations

from pathlib import Path

import yaml

from scripts import run_full_pytest


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config" / "validation-runtime-policy.yaml"


def _load_policy() -> dict:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(policy, dict)
    return policy


def test_validation_runtime_policy_requires_long_python_test_ceilings() -> None:
    commands = _load_policy()["commands"]

    assert commands["full_pytest"]["minimum_timeout_seconds"] >= 900
    assert commands["focused_pytest"]["minimum_timeout_seconds"] >= 900
    assert "scripts/run_full_pytest.py" in commands["full_pytest"]["wrapper"]
    assert "scripts/run_full_pytest.py" in commands["focused_pytest"]["wrapper"]


def test_validation_runtime_policy_requires_long_heavy_command_ceilings() -> None:
    commands = _load_policy()["commands"]

    assert commands["smoke_demo"]["minimum_timeout_seconds"] >= 900
    assert commands["export_schemas"]["minimum_timeout_seconds"] >= 180
    assert commands["validate_repo"]["minimum_timeout_seconds"] >= 180
    assert commands["ruff_check"]["minimum_timeout_seconds"] >= 180
    assert commands["ruff_format_check"]["minimum_timeout_seconds"] >= 180


def test_make_test_uses_validation_runtime_policy_wrapper() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8").replace("\r\n", "\n")

    assert "\ntest:\n\tpython scripts/run_full_pytest.py\n" in f"\n{makefile}"


def test_pytest_wrapper_reads_validation_runtime_policy() -> None:
    assert run_full_pytest.POLICY_PATH == POLICY_PATH
    assert run_full_pytest.pytest_timeout_seconds() >= 900
