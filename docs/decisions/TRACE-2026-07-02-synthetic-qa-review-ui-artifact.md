# Synthetic QA Review Run UI Artifact

## Context

The one-command synthetic QA review run emits a 15-step local report, but the
read-only UI bundle previously exposed only the manifest, L&E QA matrix, and
blocked-driver review. That made the frontend less useful as a product
confidence cockpit because the main recipe evidence was not visible as a
first-class artifact.

## Decision

Add `synthetic_qa_review_run_report.json` as an optional UI detail report and a
manifest/quality-gate artifact. The lower-level `build-synthetic-qa-bundle`
command remains valid when the recipe report is absent. The full
`build-synthetic-qa-review-run` command refreshes the UI manifest and UI data
bundle after writing its report so the richer frontend input includes the
recipe steps.

The demo frontend now renders a Synthetic QA Review Run panel showing step
count, failed count, step statuses, artifact refs, and no-write boundaries.

## Authority Boundary

This is local, candidate-only, synthetic-only review evidence. It does not
create connectors, write the Exception Lake or SQLite, mutate fixtures, apply
calibration, submit budgets, open matters, or promote canonical schema meaning.

## Acceptance

- UI data bundle treats the recipe report as optional for lower-level commands.
- The full recipe emits a final UI data bundle with the recipe report present.
- The frontend fixture contract validates the report counts and side-effect
  boundaries.
- The UI build stays read-only and local-JSON only.
