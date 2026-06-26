# TRACE 2026-06-26 Budget Calibration Corpus

## Decision

Add a local candidate-only budget calibration corpus audit. The audit scans a
synthetic fixture corpus, classifies each JSON artifact by role, blocks real or
privileged data flags, blocks mutation/external-write flags, and writes a
manifest-style report for human review.

## Why

The budget loop now has proposals, human budget revisions, synthetic actuals,
carrier rejection outcomes, reviewed-learning gates, shadow evals, and owner
handoffs. Before using that evidence to improve budget behavior, the repo needs a
deterministic corpus layer that separates eligible synthetic outcome evidence
from input context, examples, blocked material, and future real-data pilots.

## Implemented

- `audit-budget-calibration-corpus` command.
- `budget_calibration_corpus_report.json` and Markdown rendering.
- `BudgetCalibrationCorpusArtifact`, `BudgetCalibrationCorpusCheck`, and
  `BudgetCalibrationCorpusReport` local schemas.
- Deterministic classification for intake fixtures, confirmations, budget-review
  changes, actuals, carrier rejection bundles, reviewed gold, learning-gate
  fixtures, and shadow-eval fixture results.
- Tests for the ready synthetic corpus, blocked production/real-data flags, CLI
  output, and persisted candidate report boundaries.

## Boundaries

- Synthetic fixture audit only.
- No real case ingestion.
- No calibration applied.
- No profile, template, budget, carrier guideline, connector, Lake, SQLite, or
  external write.
- No silent learning.
- No canonical event, route, taxonomy, or schema promotion from intake.

## Required Next Gates

- Human corpus review.
- Synthetic fixture result binding.
- Shadow eval before learning.
- Owning-repo review.
- No silent profile or template mutation.

## Follow-Up

The next useful slice is a corpus replay plan: bind each eligible corpus artifact
to the exact command chain needed to regenerate the relevant proposal, revision,
actuals comparison, carrier rejection learning report, and shadow-eval evidence.
