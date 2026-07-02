# TRACE 2026-07-02: L&E Executable Coverage Report

## Decision

Add a candidate-only L&E executable coverage report that compares the full fixture-family pack to the executable fixture manifest.

## Why

The repo can now run selected L&E source bundles through deterministic preflight, bind expected fact gaps, and replay budget fact gold. That is useful, but it can look more complete than it is unless QA also sees which of the 32 family-pack cases are executable today. The coverage report makes partial executable coverage explicit.

## Current Starter Signal

- Full L&E fixture-family pack: 32 cases.
- Executable source bundles: 4.
- Covered pack-case links: 5.
- Missing executable pack cases: 27.

The ADA/FMLA executable source bundle intentionally covers both the missing-attachment and messy-thread pack cases, so source-bundle count and covered pack-case count are separate metrics.

## Boundaries

- Synthetic fixtures only.
- Candidate QA evidence only.
- No fixture generation.
- No calibration approval.
- No amount budget output.
- No budget submission, matter opening, conflict conclusion, Lake/SQLite write, training, or silent learning.

## Follow-Up

Use the missing pack-case IDs and family/variant gaps to prioritize the next executable fixture-generation slices, then bind those new cases through preflight, fact binding, budget fact audit, and reviewed gold.
