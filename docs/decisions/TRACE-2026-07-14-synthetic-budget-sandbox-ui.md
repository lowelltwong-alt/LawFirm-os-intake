# TRACE: Synthetic Budget Sandbox UI

## Decision

Add an in-browser-only sandbox for the pinned eight-line synthetic EPLI candidate budget. The sandbox exposes every numeric line driver used by this selected budget: hours, hourly rate, expenses, and contingency. It recomputes fees and totals locally and exports an Excel-compatible CSV or a candidate JSON change package. The existing rate-card workbench remains an excluded-context reference; it is not applied to the budget in this sandbox.

## Boundaries

- The draft is React memory only and resets on refresh or explicit reset.
- The sandbox reads checked-in synthetic UI fixtures only.
- Exported files are candidate drafts, not source changes, rate authority, approved budgets, or submission artifacts.
- No source file writes, connector calls, Lake/SQLite writes, matter opening, conflict conclusion, submission, or silent learning are available.

## Verification

The browser smoke test changes line 1 from six to eight hours and requires the total to change from $54,090.00 to $54,990.00 with a +$900.00 delta. It separately changes a rate and contingency, reads both generated download bodies, checks candidate-only/no-write fields, and requires reset-to-baseline behavior. The static contract test prohibits local storage and browser fetch calls in the sandbox component. A mobile check requires the sandbox itself to fit without horizontal overflow.

## Independent Review Corrections

An independent peer review found that the first implementation incorrectly offered a rate-card apply action even though the input report classifies the rate card as excluded context. That action was removed. The review also found a masked contingency omission and a precision mismatch between displayed and exported values. Draft totals now include contingency and monetary values are normalized to cents before display and export. A filename-only download test was upgraded to assert CSV arithmetic and JSON candidate/no-write fields.

## Deliberate Deferral

The browser exports Excel-compatible CSV rather than a dynamic XLSX because a fully dynamic workbook needs a reviewed local export service or a client-side workbook contract. The existing CLI remains the owner of macro-free audited XLSX generation from pinned source files.
