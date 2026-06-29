# TRACE: Public Synthetic Fixture PR Package

## Context

The public conversion review outcome records whether a human approved a
structure-only conversion spec for a separate fixture PR, but it does not tell a
fixture author exactly what guardrails must travel into that PR. Without a
package artifact, the next step could lose the approved spec's forbidden-input,
identity replacement, gold-check, and red-team requirements.

## Decision

Add `build-public-synthetic-fixture-pr-package`.

The command consumes:

- `public_synthetic_fixture_conversion_review_outcome_report.json`;
- the matching `public_synthetic_fixture_conversion_plan.json`.

It writes:

- `public_synthetic_fixture_pr_package_report.json`;
- `public_synthetic_fixture_pr_package_report.md`;
- `public_synthetic_fixture_pr_package_items.jsonl` when an approved outcome
  requires a manual package item.

## Boundary

The package is manual review evidence only. It does not create fixtures, create a
PR, ingest public records, commit raw public payloads, authorize adapters, write
Lake/SQLite records, perform external writes, or apply learning.

## Red-Team Notes

- Approval can be overread as permission to use real public records. The package
  must preserve structure-only use and forbidden inputs.
- Rare field combinations can reconstruct public matters even when names are
  synthetic.
- A package item is not a patch; the actual fixture work must happen in a
  separate reviewed PR.
- Legal Knowledge Runtime owner review is still required before any adapter.

## Validation Plan

- Approved outcome creates one manual package item.
- Needs-more-information outcome creates no package item.
- Mismatched conversion plan blocks.
- CLI output proves no PR creation, no fixture mutation, no public ingestion, no
  adapter authorization, no Lake/SQLite writes, and no silent learning.
