# TRACE: Synthetic Budget Configuration Change Package

## Decision

Add a local dry-run package that compares two synthetic budget-configuration
source trees. It reports source-hash changes and exact numeric-field deltas with
their declared math effect before any budget or projection artifact is rebuilt.

## Guardrails

- Both baseline and candidate must pass the existing synthetic configuration audit.
- The package blocks nested real-data declarations, invalid numeric values,
  added/removed configuration paths, empty changes, and source-hash changes
  that do not correspond to a numeric configuration delta.
- It does not import a worksheet, recalculate a budget, generate a submission,
  write to Lake/SQLite, or create an external side effect.

## Why

Easy editing is useful only when a reviewer can see precisely what changed and
which part of proposal or guideline math it can affect. The next gate remains a
human review followed by regeneration of affected synthetic artifacts.

## Evidence

- `src/lawfirm_os_intake/synthetic_budget_configuration_change.py`
- `tests/test_synthetic_budget_configuration_change.py`

## Non-Applicability

This is a source-delta review packet, not a budget-impact calculation. A future
runtime configuration change session must be owned by Orchestrator and bind the
reviewer, approved snapshot, selected facts, and resulting artifact hashes.
