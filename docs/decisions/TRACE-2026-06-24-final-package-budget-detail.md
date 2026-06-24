# TRACE-2026-06-24 - Final Package Budget Detail

## Context

The final matter-opening review package showed the proposed budget scenario, pricing status, total, and support items. A reviewer still had to open the structured budget JSON to see the line items, hours, rates, fees, expenses, and calculation summary.

The north-star package should explain the proposed budget scenario enough for human review without turning it into an approved or submittable budget.

## Decision

Add budget detail subsections to `matter_opening_review_package.md`:

- `### Calculation Summary`;
- `### Budget Lines`;
- `### Budget Supports`.

Budget lines render phase, task, staffing role, hours/range, rate, rate source, synthetic-rate label, fees, expenses, assumptions, evidence refs, and calculation formula where present.

The review package completeness report now requires these budget subsections before package acceptance.

## Scope

This is a human-review rendering and completeness change. It does not approve a budget, authorize client/carrier submission, authorize rates, bill, create external billing records, change schemas, or write externally.

## Validation

- Review-package tests require calculation summary, budget lines, synthetic-rate labeling, and budget supports in the final package.
- North-star demo and smoke checks require budget line details.
- Completeness metadata requires the budget detail subsections.
