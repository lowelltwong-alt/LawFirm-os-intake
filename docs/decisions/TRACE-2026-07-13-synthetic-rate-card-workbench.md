# TRACE: Synthetic Rate Card Workbench

## Decision

Add a deterministic local workbench for the checked-in synthetic rate card. It renders
an audited JSON report, a macro-free `.xlsx` catalog, a Markdown trace, and a read-only
UI panel. It does not resolve a rate for a matter and it never accepts a real rate import.

## Why

The POC needs a place where budget inputs can be inspected and changed deliberately
without presenting invented numbers as carrier panel rates. The editable source is
`config/synthetic-carrier-rate-card.yaml`; generated artifacts are evidence of that
source at a specific hash, not editable authority.

## Inputs And Outputs

- Input: `config/synthetic-carrier-rate-card.yaml`, which must declare `data_origin:
  synthetic`, `candidate_only: true`, `not_promoted_canon: true`, and every
  `contains_real_*` flag as false.
- Command: `lawfirm-os-intake build-synthetic-rate-card-workbench --out-dir <local-dir>`.
- Outputs: `synthetic_rate_card_workbench_report.json`,
  `synthetic_rate_card_workbench.md`, and (only after every audit check passes)
  `synthetic_rate_card_workbench.xlsx`.
- UI fixture: `apps/legal-intake-budget/src/fixtures/demo-synthetic-rate-card-workbench-report.json`.

## Guardrails

The workbench refuses an incomplete, non-candidate, real-data-declared, or malformed
catalog by emitting a blocked report and omitting the workbook. It never accepts an
arbitrary file via the CLI. It excludes named-timekeeper overrides from aggregate role
comparisons. Every workbook sheet repeats the synthetic/candidate-only boundary.

Matter-specific pricing remains separate: a missing, unmatched, or ambiguous confirmed
carrier role, or an unmapped confirmed jurisdiction, produces an hours-only resolution
pending human review. A default carrier schedule cannot fill that gap.

## Authority And Future Replacement

Public sources can inform methodology only. Exact carrier panel rates, negotiated
firm rates, and real benchmark retrieval remain outside this repository. Legal Knowledge
Runtime must retrieve, grade, hash, and pin any future reviewed snapshot; Intake may
consume a reviewed snapshot read-only only after the owning Semantic Substrate contract
exists. This local workbench cannot promote rates to canon, billing authority, carrier
submission, Exception Lake, SQLite, calibration, or silent learning.

## Verification

- `tests/test_synthetic_rate_card_workbench.py`
- `tests/test_carrier_rates.py::test_missing_carrier_role_party_requires_hours_only_review`
- generated workbook cells equal audited report rows; all workbook formulas are absent
- UI contract asserts the same source hash, row count, candidate boundary, and local-only
  side-effect flags.
