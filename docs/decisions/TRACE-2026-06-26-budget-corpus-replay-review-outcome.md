# TRACE: Budget Corpus Replay Review Outcome

Date: 2026-06-26

## Decision

Add `record-budget-corpus-replay-review-outcome`, a local candidate-only command
that records a human replay review outcome as append-only evidence.

## Why

The replay review packet can ask for a human decision, but the system also needs
an append-only artifact that records that decision without mutating the review
packet or silently changing learning state.

## Scope

- Add replay review outcome record, check, and report schemas.
- Validate the outcome against the review packet decision template.
- Write `budget_corpus_replay_review_outcome_record.json`.
- Append to `budget_corpus_replay_review_outcome_history.jsonl`.
- Write `budget_corpus_replay_review_outcome_report.json` and Markdown notes.
- Support superseding outcome IDs for later corrections without overwriting the
  original outcome.

## Guardrails

- The source review packet is never mutated.
- Approved fixture binding is still not learning approval.
- Downstream learning remains blocked until reviewed learning gates, shadow eval,
  and owning-repo review complete.
- Disallowed outcomes, unknown replay cases, mismatched packet IDs, and unbound
  approved output refs fail closed.
- No calibration, profile/template/guideline mutation, budget mutation, Lake or
  SQLite write, external submission, matter opening, or silent learning occurs.

## Acceptance Evidence

- `tests/test_budget_corpus_replay_review_outcomes.py`
- Focused tests cover append-only approval recording, disallowed dry-run
  approval, unbound output rejection, and CLI report/history writing.

## Non-Goals

- Admit records to Exception Lake.
- Promote a learning candidate.
- Apply fixture binding to source fixtures.
- Mutate review packets or replay reports.
- Replace Orchestrator execution or Semantic Substrate promotion review.
