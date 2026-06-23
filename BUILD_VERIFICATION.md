# Build Verification

Verified in the artifact build environment on 2026-06-23:

```text
PYTHONPATH=src python scripts/export_schemas.py
# exported 16 schemas

PYTHONPATH=src python scripts/validate_repo.py
# repository validation passed

PYTHONPATH=src python -m pytest -q
# 33 passed

PYTHONPATH=src ruff check src tests scripts
# All checks passed

PYTHONPATH=src bash scripts/smoke_demo.sh
# completed without error
```

The monetary result is a synthetic test calculation, not a fee quote or approved budget.

The current demo also emits local `exception_lake_candidates.jsonl` files in preflight and budget outputs. These are dry-run candidates only; they are not canonical Exception Lake admissions and include no raw legal payload.

The preflight output now includes `contract_state_report.json`, which verifies the reviewed local sibling-repo lock state before source processing. The report is carried forward into the final review manifest and safety gate.

Source-bound evidence references now include segment offsets as well as source ID, segment ID, and hash. Strict evidence validation fails if a ref drifts from the cited segment.

ADR-004 records the Rust-ready ingestion boundary for future high-volume or constrained-compute document processing. Python remains the reference implementation until any Rust adapter proves golden parity.

The budget output now includes `matter_opening_review_package.md` and `review_package_manifest.json` as the consolidated review surface for the north-star demo.

Budget assumptions, exclusions, and unknowns now emit `budget_support_items` with evidence refs or structured refs for human review.

The budget output also includes `safety_gate_report.json`; a failed safety check raises before the final review package is accepted.

The smoke demo runs the messy north-star synthetic fixture, not the clean carrier-only fixture.

## GitHub seed verification

Verified on 2026-06-23:

```text
origin/main: 4d3d67b0324c59aba90f9a3100dc082f19f8b84a
GitHub Actions ci run: 28054850346
status: success
```
