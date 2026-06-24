# Build Verification

Verified in the artifact build environment on 2026-06-24:

```text
PYTHONPATH=src python scripts/export_schemas.py
# exported 22 schemas

PYTHONPATH=src python scripts/validate_repo.py
# repository validation passed

PYTHONPATH=src python -m pytest -q
# 62 passed

PYTHONPATH=src ruff check src tests scripts
# All checks passed

PYTHONPATH=src ruff format --check src tests scripts
# 48 files already formatted

PYTHONPATH=src bash scripts/smoke_demo.sh
# completed without error
```

The monetary result is a synthetic test calculation, not a fee quote or approved budget.

The current demo also emits local `exception_lake_candidates.jsonl` files in preflight and budget outputs. These are dry-run candidates only; they are not canonical Exception Lake admissions and include no raw legal payload.

The preflight output now includes `contract_state_report.json`, which verifies the reviewed local sibling-repo lock state before source processing. The report is carried forward into the final review manifest and safety gate.

Source-bound evidence references now include segment offsets as well as source ID, segment ID, and hash. Strict evidence validation fails if a ref drifts from the cited segment.

Party-role alternatives now carry their own source-bound evidence refs, render in the intake review form, and appear as supported candidate nodes in the evidence graph.

ADR-004 records the Rust-ready ingestion boundary for future high-volume or constrained-compute document processing. Python remains the reference implementation until any Rust adapter proves golden parity.

Preflight runs now emit `ingestion_result.json` as the Python reference parity oracle for source inventory, coverage summary, segments, and segment-level evidence refs.

Preflight runs now also emit `rust_ingestion_readiness_report.json`, proving the Python ingestion artifact is a valid future Rust parity target while keeping `rust_replacement_allowed=false`.

The budget stage now emits `budget_precondition_report.json`; failed confirmation attempts write this report, a blocked ledger event, and a dry-run Exception Lake candidate before any proposal output is created. The gate requires the human confirmation to be matching, confirmed, and evidence-bound.

The budget output now includes `matter_opening_review_package.md` and `review_package_manifest.json` as the consolidated review surface for the north-star demo.

Budget runs now also emit `review_package_completeness_report.json`, proving the final review package has required artifacts, review sections, human gates, blockers, safety proof, dry-run Exception Lake readiness, run ledgers, and non-authorization boundary flags before the package is accepted.

Human-facing review Markdown now renders evidence refs inline for confirmation evidence, confirmed parties, deadlines, missing-information candidates, critic findings, conflict-search terms, and budget supports.

Budget runs now write `human_review_outcome.<confirmation_id>.json` and append it to `human_confirmation_history.jsonl` before budget preconditions run. Non-confirmed review outcomes remain blocked, and superseding corrections append new history rows instead of mutating prior outcomes.

Budget assumptions, exclusions, and unknowns now emit `budget_support_items` with evidence refs or structured refs for human review.

The budget-stage evidence graph now includes human review outcome, conflict seed packet, conflict-search term, budget line, budget support item, and structured-ref nodes with source-backed or structured-ref support edges.

Budget uncertainty now emits dry-run Exception Lake candidates for proposal unknowns, missing approved synthetic budget templates, and hours-only missing-rate states. These candidates may carry structured refs and still include no raw payload.

Unread sources now count as explicit source coverage gaps, render in review summaries, and emit `source_unread` dry-run `retrieval_miss` candidates.

Exception Lake candidate files now emit `exception_lake_readiness_report.json`, proving dry-run posture, raw-payload exclusion, promotion-required status, target runtime repo, and source/evidence ref integrity before future Lake handoff.

The budget output also includes `safety_gate_report.json`; a failed safety check raises before the final review package is accepted.

The smoke demo runs the messy north-star synthetic fixture, not the clean carrier-only fixture.

Conflict-search seed packets now require every normalized search term to carry source-bound evidence refs from the human confirmation. The packet remains a search seed only and preserves `no_conflict_conclusion`.

The safety gate now independently verifies evidence completeness for conflict-search terms, budget lines, budget support items, and proposal-level assumptions, exclusions, and unknowns before accepting the final review package.

## GitHub seed verification

Verified on 2026-06-23:

```text
origin/main: 4d3d67b0324c59aba90f9a3100dc082f19f8b84a
GitHub Actions ci run: 28054850346
status: success
```
