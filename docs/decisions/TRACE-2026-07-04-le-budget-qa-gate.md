# TRACE 2026-07-04: L&E budget QA gate

## Context

The synthetic L&E chain already produced three separate budget-readiness views:

- executable fixture coverage;
- blocked-driver impact review for cases that must not output amount budgets;
- budget-output expectations for blocked, range/hours-only, and reviewed candidate-range cases.

The read-only UI could show those reports independently, but it did not have a
single deterministic gate proving that the budget QA surface had all required
states represented before reviewers treated the demo as coherent.

## Decision

Add `audit-labor-employment-budget-qa-gate` as a local aggregate report over the
three existing L&E reports. The report:

- preserves the upstream report IDs and source refs;
- fails closed when the budget-output report and blocked-driver review do not
  share the same driver-impact/blocked-review lineage;
- fails closed when executable coverage fixture IDs do not match the
  budget-output expectation case IDs;
- partitions executable cases into blocked, range/hours-only, and candidate
  range-after-review buckets;
- checks that blocked cases have blocked-driver review evidence;
- checks that nonblocking selected cases have review coverage;
- proves all required L&E families are represented by executable QA evidence;
- carries candidate Exception Lake labels and required next gates without
  writing to the Lake.

The one-command synthetic QA run now stages the report, the synthetic QA bundle
requires it, the UI review data bundle exposes it, and the frontend renders a
read-only panel for the gate.

## Boundaries

This is local synthetic QA evidence only. It does not:

- calculate dollar budgets;
- authorize budget submission;
- open a matter;
- clear conflicts;
- call carrier, Upfront, email, billing, court, or Lake systems;
- write SQLite records;
- mutate fixtures from review results;
- promote canonical L&E budget taxonomy;
- perform silent learning.

## Verification

The implementation is covered by deterministic unit tests, UI fixture contract
tests, schema export, smoke-demo integration, and the governance dependency map
mirror. The acceptance state is `labor_employment_budget_qa_gate_ready_for_review`;
failed aggregate checks return `blocked_by_labor_employment_budget_qa_gate`.
