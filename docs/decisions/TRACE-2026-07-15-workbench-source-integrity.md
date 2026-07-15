# TRACE: Workbench Source Integrity

## Decision

Fixed synthetic workbenches now treat input provenance as observable evidence,
not a self-reported boolean. Guideline projection and rejection/appeal require
reviewed digest manifests. Budget-input and configuration workbenches snapshot
their declared local source bytes before building and fail their check if a
source changes during construction.

## Why

An independent evidence-critic found literal `True` checks and reports that
could display canonical source references for hostile fixture paths. Those
patterns can make a green test look stronger than its evidence.

## Evidence And Tests

- `tests/test_synthetic_workbench_source_integrity.py` snapshots all declared
  fixed-workbench source bytes, executes each builder, and proves sources were
  unchanged.
- Guideline and rejection/appeal hostile copied fixtures retain valid syntax
  but change one byte; both workbenches block on their pinned digest check.
- The actuals hostile fixture uses its declared source reference instead of a
  canonical path label.
- Hostile tests deliberately mutate a copied source after builder entry and
  prove the budget-input and configuration snapshot checks block the result.
- The portfolio requires every shared boundary field to exist; it no longer
  defaults a missing field to a passing value. Browser smoke parses both
  sandbox change-package downloads, verifies their candidate-only provenance,
  and compares each downloaded source hash to its exact pinned workbench
  fixture value.

## Boundary

This is local synthetic validation only. It does not permit external writes,
imports, connector access, Exception Lake admission, budget mutation, or
automatic learning.
