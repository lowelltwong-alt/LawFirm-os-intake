# TRACE-2026-06-29 - Pytest Timeout Enforcement

## Context

The full local pytest suite has grown close enough to a 300 second ceiling that
direct pytest invocations can create false failures and waste rerun time.

## Decision

Make the validation runtime policy executable:

- `scripts/run_full_pytest.py` sets a validation-policy environment marker;
- the wrapper runs Python with `-B`, disables pytest's cache provider, and sets
  `PYTHONDONTWRITEBYTECODE=1`;
- `tests/conftest.py` blocks direct pytest invocation without that marker;
- CI uses `python scripts/run_full_pytest.py` instead of `python -m pytest`;
- schema export suppresses bytecode writes and smoke invokes Python with `-B`;
- ruff runs with `--no-cache` in policy-owned entry points;
- `scripts/run_validation_suite.py` runs the full validation sequence with the
  configured policy timeout for each heavy step;
- CI slow steps have explicit timeout ceilings matching
  `config/validation-runtime-policy.yaml`.

## Red-Team Notes

- `scripts/run_validation_suite.py` enforces the local subprocess timeouts, but
  agents still need to set any outer tool timeout to at least the same policy
  ceiling when invoking commands directly.
- The policy does not excuse slow tests. If the suite exceeds 1800 seconds,
  investigate the slowdown before raising the ceiling.
- This changes validation execution only. It does not alter legal workflow
  authority, source handling, budget math, Lake admission, or production scope.

## Validation

- `python scripts/run_full_pytest.py tests/test_validation_runtime_policy.py -q`
  - 10 passed.
- `python -m ruff check --no-cache src tests scripts`
  - passed.
- `python -m ruff format --check --no-cache src tests scripts`
  - 195 files already formatted.
- `python scripts/export_schemas.py`
  - exported 228 schemas; no schema semantics changed.
- `python scripts/run_full_pytest.py`
  - 382 passed in 328.01s.
- `bash scripts/smoke_demo.sh`
  - completed with final boundary `blocked_pending_conflicts_and_engagement`.
- `python scripts/run_validation_suite.py`
  - passed with policy timeouts for every heavy validation step.
- `python scripts/validate_repo.py`
  - repository validation passed.
