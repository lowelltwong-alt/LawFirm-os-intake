# TRACE: Matter-Linking Weak-Only Hardening

## Context

The synthetic QA cockpit already included an Upfront-like matter-linking
preflight for the operational pattern where one adjuster sends multiple
prospective matters before the firm has an official matter number. The next
risk was narrower: a packet with only same sender, same carrier, or sender
internal reference evidence could look like a single matter candidate even
though those signals are not matter-specific enough to merge, budget, or open a
matter.

## Decision

Add weak-only and resolved-single Upfront-like synthetic fixtures and harden the
matter-linking preflight validator so it:

- blocks weak-only matter-link candidates;
- prevents same sender, same carrier, and sender internal references from being
  promoted into strong matter-link support;
- validates negative split evidence against known source refs;
- fails closed when output-boundary contract flags are missing;
- distinguishes split-candidate states from single-candidate states;
- exposes weak-only candidate count and split-evidence requirement in schemas,
  UI types, UI contract checks, generated demo fixtures, and the read-only UI
  panel.

The synthetic QA review run now includes a `matter_linking_weak_only_holdout`
step that passes only when the weak-only fixture blocks without requiring split
evidence.

## Boundary

This remains local synthetic QA evidence only. It does not:

- call Upfront or verify an Upfront API contract;
- create a screen, matter, conflict conclusion, budget amount, budget
  submission, Lake record, SQLite record, or external write;
- ingest real client, matter, carrier, or vendor data;
- finalize a matter link without human confirmation;
- promote local matter-link labels or event labels to canonical Semantic
  Substrate authority;
- silently learn from review outcomes.

## Verification

- `python scripts/run_full_pytest.py tests/test_matter_linking_preflight.py tests/test_synthetic_qa_review_run.py tests/test_ui_foundation_contract.py tests/test_poc_qa_triage.py -q`
- `npm run build` from `apps/legal-intake-budget`
- `python -m ruff check src tests scripts`
- `python -m ruff format --check src tests scripts`

## Remaining Work

The next matter-linking slice should add a reviewer decision artifact for split,
merge, unknown, and request-more-info outcomes, then connect those outcomes to
dry-run Exception Lake owner packets without admitting Lake/SQLite records from
this repo.
