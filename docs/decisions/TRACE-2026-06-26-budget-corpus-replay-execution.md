# TRACE: Budget Corpus Replay Execution Audit

Date: 2026-06-26

## Decision

Add `replay-budget-corpus`, a local candidate-only command that consumes
`budget_corpus_replay_plan.json` and writes
`budget_corpus_replay_execution_report.json`.

## Why

The replay plan proves which command chains should regenerate budget learning
evidence. The next gate needs to prove whether those chains are dry-run ready,
selected for execution, actually executed, skipped as support context, or
blocked with explicit reasons.

## Scope

- Add local execution/audit schemas for replay output checks, command results,
  case results, execution checks, and the execution report.
- Add dry-run mode as the default.
- Add `--execute` for selected local replay cases.
- Add `--case-id` filtering so tests and reviewers can run one replay chain
  without running the whole corpus.
- Execute existing synthetic-only intake CLI commands through argv lists, not
  shell command strings.
- Tighten learning corpus classification so downstream learning-support
  artifacts remain supporting context instead of executable learning-gate
  inputs.

## Guardrails

- The command is local only and candidate-only.
- It does not authorize calibration, profile/template/guideline mutation,
  budget submission, matter opening, Lake admission, SQLite writes, sibling repo
  writes, external connector writes, or silent learning.
- Supporting-context artifacts are skipped, not executed.
- Missing placeholders, missing inputs, unsupported commands, failed commands,
  and missing outputs produce failed or blocked report states.
- Shadow-eval replay requires a proposed-change set generated upstream or
  explicitly supplied by a reviewer.

## Acceptance Evidence

- `tests/test_budget_corpus_replay_execution.py`
- `tests/test_budget_calibration_corpus.py`
- `tests/test_budget_corpus_replay.py`
- Focused test confirms selected budget-review replay execution regenerates
  `budget_revision_report.json` and `reviewed_learning_gate_report.json`.

## Non-Goals

- Execute all future real-data replay.
- Admit records to Exception Lake or SQLite.
- Promote or mutate any learning candidate.
- Replace Orchestrator-owned execution.
- Treat generated replay output as canonical truth without human review.
