# TRACE: Budget Corpus Replay Review Packet

Date: 2026-06-26

## Decision

Add `review-budget-corpus-replay`, a local candidate-only command that consumes
`budget_corpus_replay_execution_report.json` and writes a human review packet,
Markdown notes, and decision templates.

## Why

Replay execution can prove that synthetic command chains ran and emitted
expected local artifacts, but that still is not human approval. The system needs
a review packet that makes the next human decision explicit before any replay
output is treated as reviewed learning evidence.

## Scope

- Add replay review recommendation, red-team note, decision template, and packet
  schemas.
- Generate `budget_corpus_replay_review_packet.json`.
- Generate `budget_corpus_replay_review_packet.md`.
- Generate `budget_corpus_replay_review_decision_template.json`.
- Classify cases as ready for fixture-binding review, pending execution,
  needing repair, requiring shadow-eval input, selected-but-not-run, or
  supporting context.
- Require append-only human review outcomes before fixture binding or learning
  use.

## Guardrails

- A passed replay is not approval.
- Dry-run replay cannot support fixture binding.
- Failed or blocked replay cannot support learning.
- Supporting context cannot become standalone learning evidence.
- Shadow-eval replay requires a reviewed proposed-change set.
- The packet records no calibration, mutation, Lake/SQLite write, external
  submission, matter opening, or silent learning.

## Acceptance Evidence

- `tests/test_budget_corpus_replay_review.py`
- Focused tests cover dry-run review, selected executed replay review, failed
  shadow-eval input review, and CLI output files.

## Non-Goals

- Record an actual human review outcome.
- Approve fixture binding.
- Apply or promote learning.
- Write Exception Lake, SQLite, sibling repo, email, portal, billing, or matter
  records.
- Replace Orchestrator-owned execution or Semantic Substrate-owned canon.
