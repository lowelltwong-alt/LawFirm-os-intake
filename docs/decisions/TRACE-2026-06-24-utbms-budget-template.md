# TRACE-2026-06-24 - UTBMS Budget Template and Wired Drivers

## Situation

The synthetic budget template used invented phase codes (P100-P500) and was not wired to
the driver model, so the demo budget neither matched the structure carriers actually
require nor reflected case drivers. A sanitized real carrier budget form supplied by the
firm is built entirely on the UTBMS litigation code set (L-codes for fees, E-codes for
expenses) with an "Original Budgeted Amount" per task.

## Decision

- Restructure the synthetic insurance-defense med-mal template onto UTBMS L-codes
  (L100-L400), each task carrying `external_code_candidate` = its UTBMS code, with
  scaling metadata on count-driven tasks (L130/L340/L420 experts, L210 defendants,
  L240 dispositive motions, L310 written discovery, L330 depositions, L440/L450 trial
  days). Expert vendor cost is folded into L340 expenses; depositions carry a per-unit
  court-reporting expense.
- Wire `run_budget` to resolve case drivers (discovering `config/budget-driver-policy.yaml`
  next to the profile) and pass them to `build_budget_proposal`, so the demo budget is
  driver-scaled end to end.

## Non-decision

UTBMS/LEDES codes remain `external_code_candidate`, not LawFirm OS canon. L500 Appeal is
excluded. No model or schema change; `BudgetProposal` structure is unchanged. No rate
invention, approval-state change, conflicts, engagement, matter opening, submission, or
external write. Expenses stay folded into their related fee lines in this slice;
first-class E-code expense lines and the xlsx form renderer follow in the next slice.

## Authority impact

Local candidate template and demo wiring in `LawFirm-os-intake`. A UTBMS->canonical
mapping, if ever adopted, is Semantic Substrate's; runtime budget gating is Orchestrator's.

## Evidence

- The supplied carrier form enumerates UTBMS phases L100-L500 and expense codes E101-E124
  with an Original Budgeted Amount per task; the template mirrors the L-code fee taxonomy.
- `build_budget_proposal` (slice 2) already scales tasks that declare `scaling_driver`;
  this slice supplies a UTBMS template that uses that metadata and wires drivers into the
  demo via `run_budget`.
- The budget remains priced because every task uses a role present in
  `synthetic_hourly_rates`; expenses are folded into fee lines so no line becomes
  rate-absent.

## Alternatives rejected

- Keep P-codes: rejected; carriers budget on UTBMS and the deliverable must match.
- Add first-class E-code expense lines now: deferred to the renderer slice, where the
  fee/expense line distinction and the form mapping are designed together; adding
  rate-absent expense lines here would disturb priced/unpriced accounting.
- Pass a policy path argument through the CLI: rejected for now; discovering the policy
  next to the profile keeps the demo call sites unchanged.

## Risks and rollback

`workflow.py` and the synthetic profiles changed; the demo budget total moves (no test or
gold pins a dollar amount, hours, or phase id - verified). Rollback restores the prior
template and removes the four wiring lines. The full suite is the guard.

## Validation

Isolated worktree, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

- `python scripts/validate_repo.py` -> repository validation passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> already formatted.
- `python -m pytest -q` -> passed (UTBMS demo tests added; existing structural budget
  assertions unchanged).
- `python scripts/export_schemas.py` -> unchanged schema set still exports.
- `bash scripts/smoke_demo.sh` -> passed; demo now emits a UTBMS-coded, driver-scaled
  budget (total changes; no assertion pins it).

## Human gates

Human confirmation still precedes budget generation. The budget remains
`proposed_for_human_review` and `not_authorized_for_client_submission=true`. Conflicts
clearance, engagement authorization, and matter opening remain separate blockers.
