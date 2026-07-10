# TRACE-2026-07-09-stage6-review-ui-qa-crosswalk-ocg-evidence

Date: 2026-07-09
Task: Stage 6 — Review UI / QA crosswalk + OCG evidence slice
Branch: `feat/stage-6-review-ui-qa-crosswalk-ocg-evidence`
Target: intake B (`repos/LawFirm-os-intake-seed-clean-20260623`)

## Decision

Wire existing Stage 4/5 crosswalk audit and OCG rule IR adoption reports into intake B as
read-only UI/QA evidence. Port generators from stale copy A without rebuilding Stage 5 logic;
extend seed-clean `ui_review_data_bundle.py`, add `review_ui_crosswalk_ocg_evidence.py`, CLI
flags, QA readiness/product-confidence gates, React panels, and demo fixtures.

## Scope held

- Optional `--crosswalk-audit` / `--ocg-rule-ir-adoption` on `build-ui-review-data-bundle`
- Summaries embedded on `UIReviewDataBundle` when paths provided; omitted otherwise
- QA readiness blocks missing/failed crosswalk or OCG when required
- React panels: Standard Crosswalk Evidence + OCG Rule IR Adoption Evidence
- No budget math mutation; no canon promotion; no external writes

## Validation

- `python scripts/export_schemas.py` → 436 schemas
- `python scripts/validate_repo.py` → passed
- `python -m ruff check --no-cache src tests scripts` → passed
- `python scripts/run_full_pytest.py -q` → passed (3600s policy ceiling)
- `bash scripts/smoke_demo.sh` → `demo_completed`
- `npx tsc -b && npx vite build` → passed
- `npm run smoke:contract` → script not present in this package.json

## Evidence class

`candidate_learning` — UI/QA evidence wiring only; reports remain non-canon.
