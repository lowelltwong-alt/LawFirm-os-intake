# TRACE-2026-06-25 - Carrier x State x Title Rate Resolution (Rate/Guideline Layer Slice A)

## Situation

Rates were a flat per-role map (`synthetic_hourly_rates`) consumed once in
`budget.py`. Insurance-defense billing is carrier-, state-, and title-specific (a partner
in CA under Carrier A bills a different rate than an associate in TX under Carrier B), and
the firm needs to eventually plug in real carrier rate cards and guidelines. This is the
foundation slice (A) of that layer: deterministic rate resolution. Guideline caps,
staffing/leverage reshaping, and the proposed-vs-compliant projection are deferred to
later slices (see `docs/carrier-rate-and-guideline-layer-design.md`).

## Decision

- Add `config/synthetic-carrier-rate-card.yaml`: a synthetic carrier registry with
  per-carrier `schedule[state][title]` rates, carrier `aliases`, `jurisdiction_aliases`,
  `effective_date`, and `default_carrier_id`/`default_state`. `contains_real_firm_data:
  false`, `status: candidate`.
- Add `src/lawfirm_os_intake/rates.py`: `resolve_role_rates(profile, confirmation,
  rate_card)` returns a `RoleRateResolution` (per-title rates plus provenance for the
  carrier and state dimensions). Carrier is matched from the confirmed insurance-carrier
  party; state from the confirmed jurisdiction. Missing carrier/state or no card falls
  back to the practice-profile flat rates.
- `build_budget_proposal` gains an optional `rate_resolution` parameter; when present its
  `role_rates` replace the flat map, and a rate-basis assumption is recorded. `run_budget`
  discovers the profile's `rate_card_ref` and resolves rates for the demo.
- `insurance-defense.yaml` references the card; its NV schedule reproduces the prior flat
  rates, so the demo budget is unchanged.

## Non-decision

The rate card is the firm/carrier-**authorized** rate schedule, **not** a guideline rate
cap; no rate is capped, reshaped, or rewritten in this slice. No named-timekeeper
override, staffing/leverage, or proposed-vs-compliant projection yet. Rates remain
synthetic (`rate_is_synthetic=True`, `rate_source="synthetic_profile"`); no real
firm/carrier rates are committed. No model or schema change (provenance is recorded via
existing assumption/support fields). When `rate_resolution` is omitted, output is
identical to before; back-compat is covered by the existing suite plus an unchanged demo
total.

## Authority impact

Local candidate in `LawFirm-os-intake`. The rate card and any future guideline artifact
are `candidate`, synthetic, and promote through Semantic Substrate. The budget remains
`proposed_for_human_review` and `not_authorized_for_client_submission`.

## Evidence

- `budget.py` previously read `profile.synthetic_hourly_rates` directly; rates now resolve
  through `rate_resolution.role_rates` with a flat fallback.
- The demo confirmation carries an `insurance_carrier` party ("Harbor Point Insurance")
  and `confirmed_jurisdiction` ("Synthetic State Court"); the card maps these to
  carrier `synthetic-carrier-a` and state `NV`, whose rates equal the prior flat rates.
- `tests/test_carrier_rates.py` asserts resolution by carrier and state, the default-
  carrier fallback, the no-card flat fallback, and determinism.

## Alternatives rejected

- Apply guideline rate caps in this slice: rejected; caps belong to the
  proposed-vs-compliant projection layer (B), not to the authorized rate schedule.
- Add a `BudgetLine.timekeeper`/`rate_source` enum value now: deferred; named-timekeeper
  overrides and the timekeeper model come with the guideline layer to keep this slice
  additive and the schema unchanged.
- Resolve the rate card path inside `build_budget_proposal`: rejected; `build_budget_proposal`
  performs no IO. `run_budget` discovers and resolves, mirroring the driver-policy wiring.

## Risks and rollback

`budget.py`, `workflow.py`, and `insurance-defense.yaml` change; the parameter is optional
and defaulted, and the demo total is unchanged. Rollback removes `rates.py`, the card, the
parameter, and the `rate_card_ref`.

## Validation

Isolated worktree, `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src`:

- `python scripts/validate_repo.py` -> repository validation passed.
- `python -m ruff check src tests scripts` -> all checks passed.
- `python -m ruff format --check src tests scripts` -> already formatted.
- `python -m pytest -q` -> passed (rate-resolution tests added; demo unchanged).
- `python scripts/export_schemas.py` -> unchanged schema set still exports.
- `bash scripts/smoke_demo.sh` -> passed; demo budget total unchanged (NV card rates equal
  the prior flat rates).

## Human gates

Human confirmation still precedes budget generation. Rates are synthetic and not
authorized for billing. The budget remains `proposed_for_human_review` and
`not_authorized_for_client_submission`. Conflicts clearance, engagement authorization, and
matter opening remain separate blockers.
