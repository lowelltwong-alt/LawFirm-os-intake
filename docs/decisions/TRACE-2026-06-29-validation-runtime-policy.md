# TRACE-2026-06-29 - Validation Runtime Policy

## Context

The full local pytest suite can exceed a 300 second ceiling on Windows/OneDrive
worktrees. A short ceiling creates false failure signals and forces wasteful
reruns.

## Decision

Add `config/validation-runtime-policy.yaml` and route `make test` plus front-door
instructions through `scripts/run_full_pytest.py`.

The policy requires:

- 1800 seconds or higher for full pytest;
- 1800 seconds or higher for focused pytest paths;
- 1800 seconds or higher for `scripts/smoke_demo.sh`;
- 180 seconds or higher for schema export, repo validation, and ruff checks.

## Red-Team Notes

- The wrapper does not make slow tests acceptable by itself. If the suite exceeds
  the policy ceiling, investigate the slowdown before raising the ceiling.
- Agents still need to set their outer tool timeout at or above the same policy
  ceiling.
- This policy changes validation execution posture only. It does not alter source
  data, runtime authority, budget math, Lake admission, or production readiness.

## Validation

- `python scripts/run_full_pytest.py tests/test_validation_runtime_policy.py -q`
- `python scripts/run_full_pytest.py tests/test_validation_runtime_policy.py tests/test_labor_employment_budget_facts.py -q`
- `python scripts/run_full_pytest.py` - 373 passed in 294.99s
