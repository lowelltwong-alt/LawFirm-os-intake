# TRACE: Budget Corpus Replay Plan

Date: 2026-06-26

## Decision

Add a candidate-only `plan-budget-corpus-replay` command that consumes
`budget_calibration_corpus_report.json` and writes a deterministic replay plan
for eligible synthetic budget calibration artifacts.

## Why

The corpus audit proves which fixtures are eligible for review, but it does not
prove how each fixture would be regenerated, compared, or routed through human
learning gates. The replay plan bridges that gap without executing commands or
applying learning.

## Scope

- Add `BudgetCorpusReplayCommand`, `BudgetCorpusReplayCase`,
  `BudgetCorpusReplayCheck`, and `BudgetCorpusReplayPlan` local candidate
  schemas.
- Add `budget_corpus_replay_plan.json` and Markdown rendering.
- Map eligible artifacts to planned command chains for:
  - human budget review changes;
  - synthetic actual-cost comparisons;
  - carrier rejection capture, review, appeal/result pressure, and learning
    gate routing;
  - reviewed gold fixture replay;
  - learning-gate promotion readiness and proposed-change drafting;
  - shadow-eval fixture replay.
- Leave supporting context artifacts unexecuted.
- Block all replay planning when the source corpus report is blocked.

## Guardrails

- Commands are planned only and are not executed by this command.
- Output paths use isolated per-case replay run directories.
- The plan records `calibration_applied=false`,
  `profile_mutation_performed=false`, `template_mutation_performed=false`,
  `budget_mutation_performed=false`,
  `carrier_guideline_mutation_performed=false`,
  `lake_write_performed=false`, `sqlite_write_performed=false`,
  `external_writes_performed=false`, and `silent_learning_performed=false`.
- No Exception Lake, SQLite, portal, email, billing, sibling repo, or canonical
  writes are authorized.
- Shadow-eval replay requires a reviewed proposed-change set from the prior
  learning-gate chain before execution.

## Acceptance Evidence

- `tests/test_budget_corpus_replay.py`
- `python -m pytest tests/test_budget_corpus_replay.py -q`
- `python -m ruff check src/lawfirm_os_intake/budget_corpus_replay.py tests/test_budget_corpus_replay.py src/lawfirm_os_intake/models.py src/lawfirm_os_intake/cli.py scripts/export_schemas.py`

## Non-Goals

- Execute replay commands.
- Calibrate budget math, profiles, templates, carrier guidelines, or models.
- Promote contracts to Semantic Substrate.
- Write Exception Lake, SQLite, sibling repo, carrier portal, email, billing, or
  matter-opening records.
- Ingest real or privileged data.
