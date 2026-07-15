# TRACE: Rejection/Appeal Case Financial Event Selection

## Decision

The synthetic rejection/appeal workbench derives a case's recovered and
write-down amounts only from `carrier_financial_outcome_recorded` ledger events.
It does not sum the separate `carrier_appeal_result_received` event for the
same `appeal_result_id`.

## Why

The append-only decision ledger intentionally preserves both the result-receipt
event and the financial-disposition event. They describe one appeal outcome at
two lifecycle stages, not two independent money movements. Summing both doubled
the first EPLI fixture's case-level values (`1800` recovered and `2400`
write-down) while the ledger correctly reported `900` and `1200`.

## Evidence And Tests

- Pinned synthetic input:
  `examples/synthetic/labor-employment/replay-inputs/epli-carrier-clean/carrier_rejection_capture_source_bundle_with_appeal_results.json`
- Reviewed synthetic expected case totals:
  `fixtures/synthetic/rejection-appeal-workbench/epli-case-financials.expected.json`
- Regression checks require exactly one financial-outcome event per declared
  appeal result and require the sum of case financials to reconcile to the
  ledger totals.
- The frozen proposal and appeal-bundle bytes are checked against a reviewed
  synthetic digest manifest before the workbench can be ready.

## Boundaries

This changes only local, synthetic, candidate-only presentation math. It does
not alter the ledger, submit an appeal, write to Exception Lake or SQLite,
mutate a budget, or authorize learning.
