# Intensity Normalization Approved Signoff

- Signoff ID: `intensitysignoff_a9bdeb90874951b6`
- Status: `approved_for_baseline_relative`
- Policy: `synthetic-budget-driver-policy`
- Mode before: `raw`
- Mode after: `baseline_relative`
- Requires human approval: `true`
- Candidate-only, synthetic-only, and not authorized for client submission.

## Decision

Approved by the human owner in the Codex thread on 2026-07-07 after reviewing before/after default products and canonical demo budget totals. Candidate-only; not authorized for client submission.

## auto_liability_defense

- Template: `synthetic-auto-bi-defense-utbms-v1`
- Baseline source: `family_defaults`
- Baseline tiers: `{"liability_dispute": "disputed", "severity_tier": "significant", "venue_difficulty": "neutral"}`

| Phase | Default Product Before | Default Product After |
|---|---:|---:|
| L100 | 1.0000 | 1.0000 |
| L200 | 1.0500 | 1.0000 |
| L300 | 1.1340 | 1.0000 |
| L400 | 1.0800 | 1.0000 |

| Demo Case | Before | After | Delta |
|---|---:|---:|---:|
| carrier-assignment-auto-bi | 68627.79 | 63227.80 | -5399.99 |

## medical_malpractice_defense

- Template: `synthetic-medmal-defense-utbms-v1`
- Baseline source: `family_defaults`
- Baseline tiers: `{"liability_dispute": "disputed", "severity_tier": "significant", "venue_difficulty": "neutral"}`

| Phase | Default Product Before | Default Product After |
|---|---:|---:|
| L100 | 1.0000 | 1.0000 |
| L200 | 1.0500 | 1.0000 |
| L300 | 1.1340 | 1.0000 |
| L400 | 1.0800 | 1.0000 |

| Demo Case | Before | After | Delta |
|---|---:|---:|---:|
| carrier-assignment-medmal | 162027.66 | 148406.00 | -13621.66 |
