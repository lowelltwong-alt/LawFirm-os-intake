# Build Verification

Verified in the artifact build environment on 2026-06-23:

```text
PYTHONPATH=src python scripts/export_schemas.py
# exported 10 schemas

PYTHONPATH=src python scripts/validate_repo.py
# repository validation passed

PYTHONPATH=src python -m pytest -q
# 13 passed

PYTHONPATH=src ruff check src tests scripts
# All checks passed

PYTHONPATH=src bash scripts/smoke_demo.sh
# demo_completed
# total_proposed_budget: 202365.38 (synthetic)
# final_boundary: blocked_pending_conflicts_and_engagement
```

The monetary result is a synthetic test calculation, not a fee quote or approved budget.
