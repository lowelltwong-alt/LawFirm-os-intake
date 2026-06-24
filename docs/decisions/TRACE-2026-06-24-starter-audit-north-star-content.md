# TRACE-2026-06-24-starter-audit-north-star-content

## Decision

Harden the local starter release audit so it proves the north-star demo contains meaningful intake-to-budget content, not only expected files.

## Context

The north-star objective names concrete deliverables: source inventory, evidence graph, party/matter/posture candidates, conflict-search seed, budget proposal, exception/escalation records, run ledger, and a human-readable review package that explains why no unauthorized action occurred.

The existing audit already checked many safety invariants, but several deliverables were still accepted mostly by file presence or by narrower downstream checks.

## Change

- Added content-level starter audit checks for source coverage states, candidate surface completeness, evidence-graph node and edge coverage, human-readable package story coverage, and full preflight/budget ledger steps.
- Added fail-closed tests for hollow matter-family candidates, missing budget-line graph nodes, and a review package that loses the Candidate Alternatives section.
- Updated smoke coverage to require the new audit check IDs.

## Authority Impact

This remains a local evaluation artifact only. It does not promote schemas, define canonical route IDs, admit Exception Lake records, clear conflicts, authorize engagement, docket deadlines, approve budgets, submit budgets, open matters, create workspaces, or write to external systems.

## Validation

- Focused starter audit tests cover the passing north-star report and the three new fail-closed drift cases.
- Smoke coverage requires the new content-level checks to appear in `starter_release_audit_report.json`.

## Follow-Up

Future graduation metrics should replace these starter-level checks with attorney-reviewed thresholds for extraction accuracy, reviewer touch time, escalation recall, budget accuracy, and abstention quality.
