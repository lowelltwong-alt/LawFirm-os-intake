# Build Verification

Verified in the artifact build environment on 2026-06-23:

```text
PYTHONPATH=src python scripts/export_schemas.py
# exported 13 schemas

PYTHONPATH=src python scripts/validate_repo.py
# repository validation passed

PYTHONPATH=src python -m pytest -q
# 25 passed

PYTHONPATH=src ruff check src tests scripts
# All checks passed

PYTHONPATH=src bash scripts/smoke_demo.sh
# demo_completed
# total_proposed_budget: 202365.38 (synthetic)
# final_boundary: blocked_pending_conflicts_and_engagement
```

The monetary result is a synthetic test calculation, not a fee quote or approved budget.

The current demo also emits local `exception_lake_candidates.jsonl` files in preflight and budget outputs. These are dry-run candidates only; they are not canonical Exception Lake admissions and include no raw legal payload.

The budget output now includes `matter_opening_review_package.md` and `review_package_manifest.json` as the consolidated review surface for the north-star demo.

Budget assumptions, exclusions, and unknowns now emit `budget_support_items` with evidence refs or structured refs for human review.

## GitHub seed verification

Verified on 2026-06-23:

```text
origin/main: 4d3d67b0324c59aba90f9a3100dc082f19f8b84a
GitHub Actions ci run: 28054850346
status: success
```
