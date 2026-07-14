# TRACE: Synthetic Guideline Projection Workbench

## Decision

Add a read-only, synthetic-only workbench that compares one frozen medical-malpractice budget proposal against two synthetic guideline scenarios. The artifact labels the result a guideline projection, never a carrier-compliant or approved budget.

## Why

Budget inputs, candidate rate schedules, guideline caps, staffing reshapes, expense caps, and preapproval thresholds need to be inspectable before any future editable or real-data workflow is considered. A single headline delta is insufficient because staffing rules can increase a line while other rules reduce the total.

## Guardrails

- Hash every source input and retain the immutable proposal snapshot hash.
- Display gross reductions, gross increases, and signed net delta separately.
- Require complete numeric preapproval thresholds and evaluable driver facts; unknown status blocks readiness.
- Require a resolved synthetic carrier/state/title schedule for staffing reshapes.
- Reconcile line totals, contingency, leverage percentages, and the signed delta.
- Emit local JSON, Markdown, and macro-free XLSX only. No external write, Lake/SQLite write, approval, submission, calibration, or browser-side calculation is allowed.

## Evidence

- `tests/test_synthetic_guideline_projection_workbench.py`
- `apps/legal-intake-budget/scripts/ui-browser-smoke.mjs`
- `config/synthetic-carrier-guideline.yaml`
- `config/synthetic-carrier-rate-card.yaml`

## Non-Applicability

This is not a real carrier guideline interpreter. Real rate or guideline ingestion requires a separate governed Legal Knowledge Runtime research and review path, and runtime workflow ownership belongs to the Orchestrator.
