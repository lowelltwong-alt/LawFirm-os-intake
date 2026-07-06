# TRACE 2026-07-06: EX1/EX2 Exception Metadata And Mapping

## Decision

Add deterministic identity, severity, recurrence, and holdout metadata to dry-run Exception Lake candidates, and register the Fable exception-learning taxonomy families as versioned local mapping rules.

## Rationale

Exception candidates need stable keys before they can be counted, deduplicated, routed to DAD as lessons, or reviewed by the Exception Lake runtime. The key and severity must be deterministic and must not depend on model confidence. This slice adds metadata without changing existing candidate labels, Lake classes, or dry-run behavior.

## Scope

- Added additive `ExceptionLakeCandidate` fields: `identity_key`, `severity`, `occurrence_hint`, and `holdout_origin`.
- Derived identity keys from label/class plus stable structured, source, evidence, and blocked-state subject refs, excluding run IDs and packet IDs.
- Derived severity from deterministic rules for authority conflicts, prompt/prohibited transitions, invariant failures, scenario-policy blocks, matter-link conflicts, and review-with-budget events.
- Added versioned mapping rules for budget invariant violations, scenario policy invalidity, rate ambiguity, carrier appeal outcomes, matter-link ambiguity/conflict, human corrections, QA defects, fixture weakness, and workflow discovery.
- Added a failed invariant-report exception-candidate helper for invariant and scenario-policy failure packages.

## Non-Goals

- No Lake admission, SQLite write, external connector, DAD lesson generation, or automatic learning.
- No change to existing candidate emission semantics, labels, or broad Lake classes.
- No canonical taxonomy promotion from this repo.
- No matter-linking, rate-resolution, or human-correction producer rewrite beyond mapping readiness.
