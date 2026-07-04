# TRACE: Matter-Linking QA Gate

## Context

The Upfront-like intake path now has separate deterministic checks for
ambiguous same-sender packets, weak-only matter-link candidates, source-bound
split evidence, and append-only matter-linking review outcomes. The remaining
quality risk was that those checks could drift apart: a future change might
keep one fixture green while breaking the full matrix needed before budget or
matter-opening workflows rely on document clusters.

## Decision

Add a deterministic `audit-matter-linking-qa-gate` command that replays the
required synthetic holdouts as one gate:

- ambiguous same-sender, multi-case intake with no official matter number;
- resolved follow-up split candidate with strong source-bound evidence;
- weak-only follow-up packet that must remain blocked;
- resolved single-candidate packet that still requires human confirmation;
- conflicting external identifiers that must block linking.

The gate writes `matter_linking_qa_gate_report.json` and `.md`, exports schemas,
stages the report into the synthetic QA review run, and displays it in the
read-only legal-intake-budget UI. It also adds a conflicting-identifier
synthetic fixture so two strong matter identifiers of the same type cannot be
quietly merged into one candidate.

## Boundary

This is local synthetic QA evidence only. It does not:

- call Upfront or create a vendor screen;
- create a matter, conflict conclusion, budget amount, budget submission,
  Lake record, SQLite record, or external write;
- ingest real client, matter, carrier, or vendor data;
- finalize a matter link without human confirmation;
- promote local matter-link labels or event labels to canonical Semantic
  Substrate authority;
- silently learn from review outcomes.

## Verification

Target verification for this slice:

- `python scripts/run_full_pytest.py tests/test_matter_linking_preflight.py tests/test_matter_linking_qa_gate.py -q`
- `python scripts/run_full_pytest.py tests/test_synthetic_qa_review_run.py tests/test_ui_review_data_bundle.py -q`
- `python scripts/run_full_pytest.py tests/test_ui_foundation_contract.py tests/test_ui_review_data_bundle.py tests/test_synthetic_qa_review_run.py tests/test_matter_linking_preflight.py tests/test_matter_linking_qa_gate.py -q`
- `python scripts/export_schemas.py`
- `npm run build` from `apps/legal-intake-budget`
- `python -m ruff check src tests scripts`
- `python -m ruff format --check src tests scripts`
- `python scripts/validate_governance_dependency_map_mirror.py --base-ref origin/main`

## Remaining Work

The next matter-linking slice should add more adversarial source fixtures for
same sender, same internal reference, and same insured name across unrelated
matters. The Exception Lake owner still needs the eventual canonical event
mapping; this repo should continue emitting candidate labels and no-write QA
evidence only.
