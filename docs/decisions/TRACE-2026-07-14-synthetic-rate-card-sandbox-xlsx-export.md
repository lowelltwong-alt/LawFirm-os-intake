# TRACE: Synthetic Rate Card Sandbox XLSX Export

## Decision

Add a browser-memory-only sandbox for every audited synthetic rate-card cell and a local CLI that validates the downloaded candidate package before rendering a macro-free XLSX workbook. The sandbox is a catalog what-if tool. It does not apply a rate to a matter, budget, carrier submission, or source configuration.

## Inputs And Outputs

- Browser input: the pinned `SyntheticRateCardWorkbenchReport` fixture, which is sourced from `config/synthetic-carrier-rate-card.yaml`.
- Browser output: Excel-ready CSV or a full `synthetic_rate_card_sandbox_change_package` JSON draft.
- Local CLI: `lawfirm-os-intake render-synthetic-rate-card-sandbox-xlsx --package ... --out-dir ...`.
- CLI outputs: `synthetic_rate_card_sandbox_xlsx_export_report.json` and, only after validation succeeds, `synthetic_rate_card_sandbox_candidate.xlsx`.

## Validation And Boundaries

The renderer requires a source rate card that is still an audited synthetic candidate catalog. It checks the source hash, synthetic declaration, blocked actions, complete ordered cell identity, positive cent-precision candidate rates, pinned and candidate totals, delta, and changed-cell count. Malformed JSON, a stale source, declared real rates, missing cells, duplicate or reordered cells, invalid rates, or inconsistent totals write only a blocked local report.

The XLSX contains no formulas, macros, external links, or connections. It is candidate-only local evidence and cannot write configuration, import real rates, apply a rate to a budget, submit a budget, write the Exception Lake or SQLite, open a matter, or learn silently.

## Verification

The synthetic fixture changes only `synthetic-carrier-a | NV | partner` from $450.00 to $455.00, moving the catalog rate total from $6,990.00 to $6,995.00. Focused tests verify the macro-free workbook, exact source preservation, stale-lineage and hostile-rate blocking, real-source declaration blocking, malformed JSON handling, and CLI no-write flags. Browser smoke verifies the inline counterfactual, CSV and candidate JSON contents, reset behavior, and mobile fit.

## Independent Review Corrections

An independent Terra review found four P2 gaps. The renderer now reports a missing or unreadable pinned source as a blocked local artifact instead of raising before evidence exists. The browser rejects sub-cent and non-finite rates, displays an inline error, and disables exports until a valid rate replaces the bad value. The browser smoke now proves that contained table-scroll regions do not escape the viewport rather than treating internal table width as a global layout pass. Finally, the smoke feeds the actual downloaded browser JSON package to the Python CLI and requires a ready-for-review XLSX replay.

## Future Replacement

Real firm, carrier, or benchmark rates remain outside this vertical. A governed Legal Knowledge Runtime snapshot and Semantic Substrate contract would be required before any future reviewed data can be consumed read-only. That later work must not repurpose this local synthetic sandbox as an import path.
