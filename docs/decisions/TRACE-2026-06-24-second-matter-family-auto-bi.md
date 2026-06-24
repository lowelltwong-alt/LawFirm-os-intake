# TRACE: Second Matter Family - Auto/BI Defense

## Context

The roadmap required a second synthetic litigation family to prove the intake-to-budget engine was not med-mal-specific. Before this slice, `auto_liability_defense` existed as a candidate classifier label and practice prior, but the profile had no approved synthetic budget template or driver defaults for it.

## Decision

Add `auto_liability_defense` as a second synthetic budget family in the insurance-defense profile.

- Add `synthetic-auto-bi-defense-utbms-v1` under `context/synthetic-profiles/insurance-defense.yaml`.
- Add auto/BI driver defaults in `config/budget-driver-policy.yaml`.
- Add `carrier-assignment-auto-bi.json` and a matching human confirmation fixture.
- Cover the full preflight -> human confirmation binding -> driver resolution -> budget -> final package path in tests.

## Authority Boundary

This remains local candidate behavior in `LawFirm-os-intake`. It does not promote matter-family taxonomy, UTBMS mappings, driver defaults, budget templates, route IDs, event classes, or workflow authority to canon. It does not use real cases, real rates, real carrier guidelines, connectors, external writes, conflict clearance, engagement authorization, matter opening, docketing, billing, budget approval, or Exception Lake admission.

## Validation

- Added deterministic tests proving the auto/BI fixture ranks `auto_liability_defense` from observed source text.
- Added tests proving the auto/BI budget uses auto defaults/template and still emits scenario set, driver effects, guideline flags, review package, and non-submission boundary.
- Focused verification passed:
  - `python -m ruff format src tests scripts`
  - `python -m ruff check src tests scripts`
  - `python -m pytest tests/test_second_matter_family.py -q`

## Residual Risk

The auto/BI template is intentionally synthetic and minimal. Future work should add broader fixture coverage and cross-repo promotion proposals before any matter-family taxonomy or budget template is treated as platform canon.
