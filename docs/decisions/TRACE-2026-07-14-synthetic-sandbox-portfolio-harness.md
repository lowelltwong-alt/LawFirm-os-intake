# TRACE: Synthetic Sandbox Portfolio Harness

## Decision

Extend the existing independent synthetic workbench portfolio acceptance test to replay both complete browser-style sandbox packages through their corresponding local XLSX renderers. This turns the individual budget and rate-card sandbox checks into one portfolio-level regression surface.

## Coverage

The harness now proves, in the same controlled synthetic run:

- the budget sandbox package produces the expected $54,990.00 draft and $900.00 delta;
- the rate-card sandbox package produces the expected $6,995.00 draft rate total and $5.00 delta;
- each renderer writes its macro-free candidate workbook only under the test output directory;
- both reports retain candidate-only, no-source-mutation, no-external-write, no-Lake/SQLite-write, no-submission, no-matter-opening, and no-silent-learning states;
- the pinned budget proposal and synthetic rate-card source bytes are unchanged.

## Boundary

The harness does not make a browser filesystem write, apply a rate-card draft to a budget, import real rates, or create a new authority plane. It is a deterministic test-only composition of existing local candidate renderers.
