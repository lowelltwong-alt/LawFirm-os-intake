import os
from pathlib import Path

import pytest


POLICY_MARKER_ENV_VAR = "LAWFIRM_OS_VALIDATION_RUNTIME_POLICY"
POLICY_MARKER_VALUE = "intake-validation-runtime-policy.v1"


def pytest_sessionstart(session: pytest.Session) -> None:
    if os.environ.get(POLICY_MARKER_ENV_VAR) == POLICY_MARKER_VALUE:
        return

    pytest.exit(
        "Direct pytest invocation is blocked by the validation runtime policy. "
        "Use `python scripts/run_full_pytest.py` so full and focused tests receive "
        "the configured long timeout ceiling.",
        returncode=4,
    )


@pytest.fixture
def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]
