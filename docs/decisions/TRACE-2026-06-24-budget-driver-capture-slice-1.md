# TRACE-2026-06-24 - Budget Driver Capture (Slice 1)

## Situation

The budget engine computes `hours * synthetic_rate` over a fixed template and does not
represent the case drivers that actually move insurance-defense litigation cost
(resolution path, deposition/expert/party counts, severity, liability dispute, venue,
coverage, guideline caps). The driver-based design
(`docs/driver-based-budget-model-design.md`, merged in #1) sequences the work into
PR-sized slices, the first of which captures drivers **without changing math** so the
existing suite stays green.

## Decision

Add a standalone, deterministic driver-capture unit:

- `config/budget-driver-policy.yaml` - synthetic, versioned driver taxonomy plus
  med-mal defaults and scenario definitions; `contains_real_firm_data: false`,
  `status: candidate`.
- `src/lawfirm_os_intake/drivers.py` - `CaseDriverProfile` / `DriverValue` candidate
  models and `resolve_case_drivers(...)`, which resolves each driver with provenance
  (`human_confirmed` party counts, then `profile_default`, otherwise `unknown`).
- `tests/test_budget_drivers.py` - provenance spectrum, confirmed party counts,
  no-observed-without-source-ref, unknown listing, and determinism.

The resolver is **not** wired into `BudgetProposal`; `CaseDriverProfile.not_applied_to_math`
is `True`.

## Non-decision

This does not change budget math, rates, templates, schemas, approval state, conflict
clearance, engagement authority, submission authority, matter opening, or external
writes. It does not modify any existing file. `scripts/export_schemas.py` is unchanged;
schema registration for `CaseDriverProfile` is deferred to the slice that wires it into
the proposal.

## Authority impact

Local candidate in `LawFirm-os-intake`. The driver taxonomy and any future budget
schema remain `candidate`; promotion runs through Semantic Substrate. Runtime budget
gating remains Orchestrator's; variance/actuals learning remains Exception Lake's.

## Evidence

- `context/synthetic-profiles/insurance-defense.yaml` and `src/lawfirm_os_intake/budget.py`
  show fixed `estimated_hours` with no driver scaling.
- The demo confirmation
  (`examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json`)
  carries confirmed party roles, exercising the `human_confirmed` channel
  (2 represented defendants, 1 adverse party).
- `ScoredCandidate.source_evidence_status` already separates observed support from
  anchor-only and unknown; the provenance channel mirrors that discipline.

## Alternatives rejected

- Wire drivers into `BudgetProposal` now: rejected for slice 1; that changes the math
  path and risks regressions before the model is validated.
- Put models in `models.py`: deferred; keeping them in `drivers.py` keeps this slice
  purely additive (no edits to a hot, concurrently-developed file) and avoids merge
  conflicts. Relocation/registration accompanies the wiring slice.
- Default unknown drivers to invented numbers: rejected; unknowns stay `unknown` and
  are listed, per the no-false-precision boundary.

## Risks and rollback

Additive new files only; rollback deletes three files plus this record with no impact on
existing behavior. No `BudgetProposal` consumer reads `CaseDriverProfile` yet.

## Validation

Run in an isolated worktree with `PYTHONDONTWRITEBYTECODE=1` and `PYTHONPATH=src`:

- `python scripts/validate_repo.py` -> repository validation passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> already formatted.
- `python -m pytest -q` -> passed (existing suite unchanged; new driver tests added).
- `python scripts/export_schemas.py` -> unchanged schema set still exports.
- `bash scripts/smoke_demo.sh` -> passed.

## Human gates

Human confirmation still precedes budget generation. The budget remains
`proposed_for_human_review` and `not_authorized_for_client_submission=true`. Conflicts
clearance, engagement authorization, and matter opening remain separate blockers.
