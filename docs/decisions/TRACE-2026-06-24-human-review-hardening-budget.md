# TRACE 2026-06-24: Human Review Hardening For Budget Package

## Decision

The intake budget path now makes driver profile provenance, scenario comparison, workbook mapping posture, and unresolved budget assumptions first-class human-review surfaces.

## Rationale

The budget proposal is still a synthetic, review-only candidate. A reviewer must see which budget drivers came from observed or human-confirmed data, which came from synthetic profile defaults, which remain unknown, and whether any carrier workbook mapping has actually been validated before relying on a filled form.

## Implementation

- `case_driver_profile.json` is written in the budget run directory.
- `BudgetProposal` embeds `BudgetDriverProfileSummary`.
- `legal_budget_review_form.md` renders driver profile summary, scenario comparison, workbook mapping status, and unresolved budget assumptions.
- `matter_opening_review_package.md` renders the same hardening sections inside the budget proposal review.
- `ReviewPackageCompletenessReport` requires those sections and verifies the case-driver artifact linkage, non-observed-fact boundaries, workbook non-submission posture, and unresolved assumption visibility.

## Authority Boundary

This is local candidate review hardening only. It does not promote driver taxonomy, budget taxonomy, workbook mapping, event labels, or schemas to Semantic Substrate canon. It does not submit a budget, approve a budget, repair a workbook, write to a carrier portal, or create Exception Lake admissions.

## Verification

Focused tests:

```text
python -m pytest tests/test_review_package.py tests/test_review_package_completeness.py -q
```

Expected status: passed.
