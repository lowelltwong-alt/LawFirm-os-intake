# TRACE: Synthetic Budget Sandbox XLSX Export

## Decision

Accept the browser's downloaded sandbox JSON only as an untrusted synthetic candidate package. A local CLI validates the package against the pinned proposal hash, a schema-valid synthetic-rate source proposal, candidate declarations, blocked actions, complete line identity, Decimal half-up cent arithmetic, nonnegative amounts, contingency, and total delta before rendering a macro-free XLSX.

## Authority

The CLI writes a report and workbook only under the caller-supplied local output directory. It never mutates the source proposal or configuration, imports real rates, submits a budget, opens a matter, writes the Lake or SQLite, or learns silently. A failed validation writes only the blocked report and no workbook.

## Verification

The synthetic fixture changes line 1 from six to eight hours, producing a $54,990.00 candidate total. Tests prove source bytes are unchanged, the workbook contains that candidate arithmetic without formulas, and contains no macros, external links, or connections. Hostile candidate structures, negative values, stale source lineage, malformed JSON, and a source proposal with a non-synthetic rate all block rendering. The CLI reports every no-write state.

## Independent Review Corrections

An independent review found that a matching proposal hash alone was insufficient, malformed `blocked_actions` could raise instead of fail closed, float rounding could diverge from the browser's positive-money half-up convention, and negative candidate amounts could reach a workbook. The renderer now validates the source through `BudgetProposal`, requires every source line to retain `rate_is_synthetic=true`, type-checks the blocked-action list, uses `Decimal` with `ROUND_HALF_UP`, and emits a blocked report without a workbook for malformed packages or invalid values.
