# TRACE: Budget Fixture Binding Candidates

Date: 2026-06-26

## Decision

Add `propose-budget-fixture-bindings`, a local candidate-only command that
consumes a replay review packet plus append-only replay review outcome report
and writes a fixture-binding candidate report.

## Why

Approved replay outputs should not silently change fixtures, reviewed gold,
budget profiles, carrier guideline profiles, or learning state. The workflow
needs one more explicit human-review gate between "this replay output was
approved for fixture-binding review" and "a fixture file is actually changed."

## Implementation

- Add `BudgetFixtureBindingCandidate`, `BudgetFixtureBindingCheck`, and
  `BudgetFixtureBindingCandidateReport` local candidate schemas.
- Validate the outcome report against the replay review packet by review packet
  ID, replay execution report ID, and replay case ID.
- Produce a ready candidate only when the outcome is
  `approve_fixture_binding`, fixture binding is approved, and approved output
  refs are present.
- Produce blocked reports for rejected, repair, hold, or missing-output states.
- Write only local generated outputs under the requested run directory:
  `budget_fixture_binding_candidate_report.json`,
  `budget_fixture_binding_candidates.jsonl`, and
  `budget_fixture_binding_candidate_report.md`.

## Authority

This is local candidate-surface work in `LawFirm-os-intake`. It does not promote
canon, write Exception Lake/SQLite records, apply learning, mutate source
fixtures, submit budgets, open matters, or authorize external action. Semantic
Substrate remains the canonical authority; Orchestrator remains the future
runtime owner; Exception Lake remains the append-only evidence runtime owner.

## Rejected Alternatives

- Mutate fixture files directly after approval: rejected because the reviewer
  approved candidate binding review, not an actual source-tree change.
- Treat approved replay outputs as learning evidence immediately: rejected
  because reviewed learning gates and shadow evals still need to run.
- Store the binding decision only in Markdown: rejected because downstream
  validation and review need typed JSON.

## Tests

- Approved replay review outcome becomes one ready fixture-binding candidate.
- Non-approved outcome produces a blocked candidate and no ready binding.
- Approval without approved output refs fails closed.
- CLI writes JSON, JSONL, and Markdown outputs while preserving no-mutation and
  no-write flags.
