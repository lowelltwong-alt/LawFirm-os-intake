#!/usr/bin/env bash
# Reproduce the GitHub Actions ci.yml `test` job + governance-map-mirror job
# locally, step for step. Run from repo root. Fails fast on the first failing step.
set -euo pipefail

PY="${PYTHON:-python}"
UI_DIR="apps/legal-intake-budget"
step() { echo ""; echo "==== CI STEP: $* ===="; }

step "clean __pycache__"
find . -name __pycache__ -type d -prune -exec rm -rf {} + 2>/dev/null || true

# ---- ci.yml: UI build + browser smoke (runs unconditionally in CI) ----
step "npm ci (review UI)"
( cd "$UI_DIR" && npm ci )

step "playwright install chromium"
( cd "$UI_DIR" && npx playwright install chromium )

step "npm run build (review UI)"
( cd "$UI_DIR" && npm run build )

step "npm run smoke:browser (review UI)"
( cd "$UI_DIR" && PYTHONPATH="$(pwd)/../../src" npm run smoke:browser )

# ---- ci.yml: Python validation chain ----
step "validate_repo.py"
"$PY" scripts/validate_repo.py

step "validate_governance_dependency_map_mirror.py --mirror-updated true"
"$PY" scripts/validate_governance_dependency_map_mirror.py --mirror-updated true

step "export_schemas.py (+ verify no drift)"
"$PY" scripts/export_schemas.py
if ! git diff --quiet -- schemas; then
  echo "ERROR: export_schemas produced drift (schemas not committed):"
  git --no-pager diff --stat -- schemas
  exit 1
fi

step "ruff check src tests scripts"
"$PY" -m ruff check --no-cache src tests scripts

step "ruff format --check src tests scripts"
"$PY" -m ruff format --check --no-cache src tests scripts

step "run_full_pytest.py"
"$PY" scripts/run_full_pytest.py

step "smoke_demo.sh"
bash scripts/smoke_demo.sh

# ---- governance-map-mirror.yml: mirror unittest ----
step "governance mirror unittest"
"$PY" -m unittest discover -s tests -p 'test_governance_dependency_map_mirror.py'

echo ""
echo "==== ALL LOCAL CI STEPS PASSED ===="
