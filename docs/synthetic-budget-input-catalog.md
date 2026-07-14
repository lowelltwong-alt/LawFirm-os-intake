# Synthetic Budget Input Catalog

## Purpose

This is the single navigation map for every editable number used by the local
synthetic intake-to-budget workbench. It is deliberately not a rate authority,
carrier guideline, or production configuration. The current files contain
invented values that make the calculations, charts, change packages, and XLSX
exports testable end to end.

Use this document before changing a number. A number must be changed at its
source, then replayed through the deterministic local reports and tests. Browser
edits are drafts only; they never write a source file.

## Editable Sources

| What changes | Source of truth | What it controls | Safe local workflow |
| --- | --- | --- | --- |
| Firm/carrier hourly rates by carrier, state, and staffing title | `config/synthetic-carrier-rate-card.yaml` | The 24 synthetic rate-card cells, aliases, effective dates, and named-timekeeper overrides | Edit the YAML; run the rate-card audit and render a candidate XLSX package. |
| Budget hours, expenses, staffing, contingency, and task/phase math | The reviewed synthetic budget proposal fixture selected by the workbench report | Budget-line calculations and the budget sandbox | Edit through a versioned synthetic fixture/change package; use the browser sandbox for a draft and local XLSX renderer for a candidate workbook. |
| Case-complexity and scenario assumptions | `config/budget-driver-policy.yaml` | Counts, intensity multipliers, scenario probabilities, and synthetic guideline constraints | Edit the policy only with a decision trace and counterfactual tests. Unknown facts must remain unknown or widen/block the output. |
| Budget eligibility facts for labor and employment | `config/labor-employment-budget-fact-needs.yaml` | Which missing facts block amount budgets or force hours-only/broad-range treatment | Edit the fact policy with a synthetic fixture, reviewed gold, and safety test. |
| Carrier-compliant projection caps and approvals | `config/synthetic-carrier-guideline.yaml` | Synthetic rate/expense caps, staffing rules, budget cadence, and preapproval thresholds | Edit the guideline YAML; compare the unchanged proposed budget with the compliant projection. |
| Budget-generation hard gates | `config/budget_policy.yaml` | Human confirmation, hours-only fallback, and prohibited actions | Treat changes as governance changes; add a decision trace and safety tests. |
| Example budget-sandbox draft | `fixtures/synthetic/budget-sandbox/synthetic-epli-hours-delta.change-package.json` | A portable, candidate-only example of a $900.00 synthetic budget change | Downloaded/browser packages must be validated before local XLSX rendering. |
| Example rate-card draft | `fixtures/synthetic/rate-card-sandbox/synthetic-rate-card-nv-partner-delta.change-package.json` | A full-card candidate package with a $5.00 synthetic delta from its pinned source | Downloaded/browser packages must be validated before local XLSX rendering. |

All synthetic value files declare their status in the file itself. The current
rate card additionally sets `real_rate_import_allowed: false`; no UI, CLI, or
export changes that setting.

## What The Workbench Lets You Do Now

The read-only review workbench provides tables, charts, comparison views, and
downloadable CSV/candidate JSON. Two local CLIs render the validated drafts as
macro-free XLSX files:

```text
lawfirm-os-intake render-synthetic-budget-sandbox-xlsx --package <draft.json> --out-dir <local-dir>
lawfirm-os-intake render-synthetic-rate-card-sandbox-xlsx --package <draft.json> --out-dir <local-dir>
```

Each renderer verifies the pinned source hash, complete line/cell identity,
money arithmetic, blocked actions, and synthetic declarations. A failed check
writes only a blocked local report. A ready workbook is still candidate-only:
it cannot apply rates, submit a budget, write a billing system, open a matter,
write the Exception Lake or SQLite, or learn silently.

## Real-Data Replacement Path

The synthetic values should be realistic-shaped test anchors, not a claim about
panel rates. Public rate material is useful only as methodology or candidate
benchmark evidence. For example, the State Bar of Texas describes its survey
data as periodic attorney research and warns that its hourly-rate data is not
intended to set appropriate fees; it cannot be used as a carrier-rate authority.
The California Bar's legal-market report and court fee matrices can similarly
inform research design, not authorize a firm/carrier price.

Before any real number can be consumed:

1. Legal Knowledge Runtime retrieves only permitted public or approved internal
   source material and creates a pinned `benchmark-snapshot-manifest` with URL,
   retrieval date, hash, quote span, licence/terms note, jurisdiction, role,
   experience band, percentile/value, and human grade.
2. A human verifies the source, scope, effective date, and whether it is a
   market benchmark, a firm standard rate, or a carrier-approved negotiated
   rate. Those categories must never be collapsed.
3. Semantic Substrate owns any promoted role, jurisdiction, or rate-source
   identifiers. Intake consumes the reviewed snapshot read-only; it does not
   fetch, normalize, or silently update rates.
4. The approved integration produces a new, versioned candidate input with a
   source hash and effective date. The old synthetic source remains replayable.
5. Existing audit, coherence, counterfactual, and no-write tests run again. A
   human must separately authorize any promotion beyond this POC.

No public case payload, purported carrier leak, or unverified web rate belongs
in this repository or a browser download. Real negotiated rate imports remain
disabled until that cross-repo contract and review gate exist.

## Maintenance Rule

When a new editable value source is added, add it to this table in the same
change. The entry must name the source file, the calculation or UI surface it
affects, the validation command or harness, and whether the data is synthetic,
candidate benchmark, or human-approved. That keeps the next person from having
to reverse-engineer where a chart number came from.
