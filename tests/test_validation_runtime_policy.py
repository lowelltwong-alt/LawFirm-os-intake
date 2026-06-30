from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import yaml

from scripts import run_full_pytest, run_validation_suite


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "config" / "validation-runtime-policy.yaml"


def _load_policy() -> dict:
    policy = yaml.safe_load(POLICY_PATH.read_text(encoding="utf-8"))
    assert isinstance(policy, dict)
    return policy


def test_validation_runtime_policy_requires_long_python_test_ceilings() -> None:
    commands = _load_policy()["commands"]

    assert commands["full_pytest"]["minimum_timeout_seconds"] >= 1800
    assert commands["focused_pytest"]["minimum_timeout_seconds"] >= 1800
    assert "scripts/run_full_pytest.py" in commands["full_pytest"]["wrapper"]
    assert "scripts/run_full_pytest.py" in commands["focused_pytest"]["wrapper"]


def test_validation_runtime_policy_requires_long_heavy_command_ceilings() -> None:
    commands = _load_policy()["commands"]

    assert commands["smoke_demo"]["minimum_timeout_seconds"] >= 1800
    assert commands["export_schemas"]["minimum_timeout_seconds"] >= 180
    assert commands["validate_repo"]["minimum_timeout_seconds"] >= 180
    assert commands["ruff_check"]["minimum_timeout_seconds"] >= 180
    assert commands["ruff_format_check"]["minimum_timeout_seconds"] >= 180
    assert "--no-cache" in commands["ruff_check"]["command"]
    assert "--no-cache" in commands["ruff_format_check"]["command"]


def test_make_test_uses_validation_runtime_policy_wrapper() -> None:
    makefile = (REPO_ROOT / "Makefile").read_text(encoding="utf-8").replace("\r\n", "\n")

    assert "\nvalidate-all:\n\tpython scripts/run_validation_suite.py\n" in f"\n{makefile}"
    assert "\ntest:\n\tpython scripts/run_full_pytest.py\n" in f"\n{makefile}"
    assert "\n\tpython -m ruff check --no-cache src tests scripts\n" in f"\n{makefile}"
    assert "\n\tpython -m ruff format --check --no-cache src tests scripts\n" in f"\n{makefile}"


def test_pytest_wrapper_reads_validation_runtime_policy() -> None:
    assert run_full_pytest.POLICY_PATH == POLICY_PATH
    assert run_full_pytest.pytest_timeout_seconds() >= 1800
    assert run_full_pytest.pytest_timeout_seconds("focused_pytest") >= 1800


def test_pytest_wrapper_sets_policy_marker() -> None:
    env = run_full_pytest.validation_environment({})

    assert env[run_full_pytest.POLICY_MARKER_ENV_VAR] == run_full_pytest.POLICY_MARKER_VALUE
    assert env["PYTHONDONTWRITEBYTECODE"] == "1"
    assert run_full_pytest.sys.dont_write_bytecode is True


def test_pytest_wrapper_disables_pytest_cache_provider() -> None:
    command = run_full_pytest.pytest_command(["tests/test_validation_runtime_policy.py", "-q"])

    assert command[1:6] == ["-B", "-m", "pytest", "-p", "no:cacheprovider"]


def test_direct_pytest_without_policy_marker_fails_closed() -> None:
    env = dict(os.environ)
    env.pop(run_full_pytest.POLICY_MARKER_ENV_VAR, None)
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "--collect-only",
            "tests/test_validation_runtime_policy.py",
        ],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        check=False,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 4
    output = f"{completed.stdout}\n{completed.stderr}"
    assert "Direct pytest invocation is blocked by the validation runtime policy" in output


def test_ci_uses_validation_runtime_policy_wrapper() -> None:
    workflow = (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "python scripts/run_full_pytest.py" in workflow
    assert "python -m pytest" not in workflow
    assert "python -m ruff check --no-cache src tests scripts" in workflow
    assert "python -m ruff format --check --no-cache src tests scripts" in workflow


def test_schema_export_and_smoke_suppress_bytecode() -> None:
    export_schemas = (REPO_ROOT / "scripts" / "export_schemas.py").read_text(encoding="utf-8")
    smoke_demo = (REPO_ROOT / "scripts" / "smoke_demo.sh").read_text(encoding="utf-8")

    assert "sys.dont_write_bytecode = True" in export_schemas
    assert 'newline="\\n"' in export_schemas
    assert "sys.dont_write_bytecode = True" in (
        REPO_ROOT / "scripts" / "run_full_pytest.py"
    ).read_text(encoding="utf-8")
    assert "sys.dont_write_bytecode = True" in (
        REPO_ROOT / "scripts" / "run_validation_suite.py"
    ).read_text(encoding="utf-8")
    assert "export PYTHONDONTWRITEBYTECODE=1" in smoke_demo
    assert '"$PYTHON_BIN" -B -m lawfirm_os_intake demo' in smoke_demo


def test_validation_suite_runs_every_heavy_step_under_policy_timeout() -> None:
    commands = _load_policy()["commands"]
    steps = run_validation_suite.validation_steps()
    steps_by_name = {step.name: step for step in steps}

    assert list(steps_by_name) == [
        "validate_repo",
        "export_schemas",
        "ruff_check",
        "ruff_format_check",
        "full_pytest",
        "smoke_demo",
        "validate_repo_final",
    ]
    for step in steps:
        expected_timeout = commands[step.command_key]["minimum_timeout_seconds"]
        assert step.timeout_seconds >= expected_timeout

    assert "scripts/run_full_pytest.py" in steps_by_name["full_pytest"].command
    assert steps_by_name["smoke_demo"].command == ("bash", "scripts/smoke_demo.sh")
