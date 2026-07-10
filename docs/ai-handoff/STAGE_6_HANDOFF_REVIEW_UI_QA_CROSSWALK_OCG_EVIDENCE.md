# Stage 6 Handoff: Review UI / QA Evidence For Crosswalk + OCG Adoption

Status: ready for Cursor / GLM implementation.
Date: 2026-07-09.
Prerequisites: Stage 4, Stage 4.5, and Stage 5 complete.

## Cursor Prompt

You are working in `LawFirm-os-intake`. Read `AI_WORK_START_HERE.md`,
`AGENTS.md`, `skill-agent-manifest.json`, and the Semantic Substrate front-door
registry before editing.

Implement Stage 6 as a PR-sized read-only UI/QA evidence slice. Do not rebuild
Stage 5 and do not create canonical crosswalk, OCG, SALI, LEDES, UTBMS, carrier
guideline, or rate authority. Intake remains a vertical workflow/evaluation repo.

Goal: wire the existing crosswalk audit report and OCG rule IR adoption report
into read-only UI review data and QA readiness/product-confidence evidence so a
reviewer can see standard-crosswalk status, OCG adoption status, source owner,
as-of dates, blocked actions, and proposed-vs-carrier-compliant impact without
turning either artifact into budget logic or canon.

## Current Ground Truth

Crosswalk audit currently passes:

- 4 crosswalks
- 51 entries
- 46 mapped
- 5 explicit unmapped
- 0 canonical claims
- 0 guessed mappings
- 0 unverified pinned-target violations
- 0 workflow dependency violations
- `acceptance_gate_status=accepted_with_restrictions`

OCG adoption currently passes:

- `status=accepted_as_read_only_candidate`
- `source_owner=LawFirm-os-semantic-substrate`
- `rule_count=6`
- `impact_line_count=6`
- no canonical rule ID, rewrite, real guideline/rate, or projection mismatch
  violations

## Required Scope

### 1. Extend Local Models

Extend existing Pydantic models, do not replace them.

Add summary models or fields sufficient for UI/QA display:

- Crosswalk audit summary:
  - report id/status/acceptance gate
  - crosswalk count, entry count, mapped/unmapped counts
  - violation counts
  - display banner
  - prohibited actions
  - no-authority flags
- OCG adoption summary:
  - report id/status/acceptance gate
  - rule IR id/source owner/source artifact ref
  - carrier projection id/budget proposal id
  - proposed total, compliant total, total delta
  - violation counts
  - display banner
  - impact line count
  - no-authority flags

Recommended targets:

- `src/lawfirm_os_intake/models.py`
- `schemas/*.schema.json` via `scripts/export_schemas.py`

### 2. Extend UI Review Bundle Inputs

Add optional inputs to the existing local bundle builders:

- `crosswalk_audit_path`
- `ocg_rule_ir_adoption_path`

Recommended targets:

- `src/lawfirm_os_intake/ui_review_bundle.py`
- `src/lawfirm_os_intake/cli.py`

The generated `UIReviewDataBundle` and `UIReviewCaseIndex` should preserve
existing behavior when these inputs are omitted.

When present, the UI bundle must include summaries and source refs for:

- `crosswalk_audit_report.json`
- `ocg_rule_ir_adoption_report.json`

It must not run crosswalk or OCG logic as budget math. It may only read already
generated local reports or build them as separate workflow steps when explicitly
provided by flags.

### 3. Extend QA Readiness

Add QA readiness checks that pass only when:

- crosswalk audit is `passed`;
- crosswalk acceptance gate is `accepted_with_restrictions`;
- crosswalk report has zero canonical claims, guessed mappings, pinned-target
  violations, target-prefix violations, and workflow-dependency violations;
- OCG adoption is `accepted_as_read_only_candidate`;
- OCG source owner is `LawFirm-os-semantic-substrate`;
- OCG adoption has zero canonical rule ID, rewrite, real guideline/rate, and
  budget/projection mismatch violations;
- both reports preserve no-write/no-authority flags.

Recommended targets:

- `src/lawfirm_os_intake/qa_readiness.py`
- `src/lawfirm_os_intake/qa_product_confidence.py`
- relevant CLI flags in `src/lawfirm_os_intake/cli.py`

### 4. Extend Read-Only React UI

The React app should show two new evidence sections from local fixture JSON:

- Standard Crosswalk Evidence
- OCG Rule IR Adoption Evidence

The UI must show:

- status and acceptance gate;
- source owner / source system;
- counts and violation counts;
- display banner warning;
- blocked actions;
- proposed vs compliant totals for OCG adoption;
- explicit wording that these are candidate-only/read-only and not canon.

Recommended targets:

- `apps/legal-intake-budget/src/App.tsx`
- `apps/legal-intake-budget/src/styles.css`
- `apps/legal-intake-budget/src/fixtures/*.json` only as generated local
  candidate fixture outputs.

Do not add connector calls, mutation buttons, carrier submission, matter
opening, conflict clearance, Lake writes, or DAD writes.

## Hard Constraints From Crosswalk Review

Keep these as tests or explicit guardrails:

1. High-confidence crosswalk entries must not be accepted unless both the entry
   and its provenance are `human_reviewed`. The current fixtures have zero high
   confidence entries; preserve that.
2. UTBMS-like strings inside candidate labels such as `task-L310-family-*`
   must remain visibly unverified candidate families, not exact standard codes.
   Prefer adding UI language such as `exact_standard_code_verified=false` if you
   introduce a display summary.
3. Crosswalks and OCG adoption reports must not become dependencies for budget,
   guideline, rejection, benchmark, workflow, or worker business logic. They are
   review/evidence metadata only.

## Acceptance Tests

Add or update tests covering:

- UI bundle includes crosswalk and OCG summaries when provided.
- UI bundle remains backward compatible when they are omitted.
- QA readiness blocks missing or failed crosswalk audit.
- QA readiness blocks failed OCG adoption.
- QA product confidence gates include crosswalk/OCG status.
- React UI source contains visible sections for crosswalk and OCG evidence.
- No blocked action disappears from the UI bundle.
- No report is treated as canon or authorized for external submission.

Recommended test files:

- `tests/test_ui_review_data_bundle.py`
- `tests/test_qa_readiness_report.py`
- `tests/test_qa_product_confidence_report.py`
- `tests/test_review_ui_scaffold.py`
- Add a small focused `tests/test_review_ui_crosswalk_ocg_evidence.py` if that
  keeps the change easier to review.

## Validation Commands

Use the longer timeout ceiling for full pytest.

```powershell
$env:PYTHONPATH='src'
python scripts\export_schemas.py
python scripts\validate_repo.py
python -m ruff check --no-cache src tests scripts
python -m ruff format --check src tests scripts
python -m pytest -q tests\test_crosswalks.py tests\test_ocg_rule_ir_adoption.py
python -m pytest -q
python scripts\smoke_demo.py
cd apps\legal-intake-budget
npm run build
npm run smoke:contract
```

## Stop Conditions

Stop and report instead of patching if:

- you need real SALI, LEDES, UTBMS, carrier OCG, or rate data;
- you are tempted to promote local candidate labels to canon;
- you need to mutate budget math based on crosswalk or OCG reports;
- you need a live connector, external write, Lake write, DAD write, or carrier
  portal action;
- you cannot keep UI fixtures local, synthetic, read-only, and candidate-only.

## Deliverable

One PR-sized implementation with:

- schema/model extensions;
- CLI optional flags;
- generated UI fixture updates;
- QA/readiness/product-confidence gates;
- React read-only display;
- tests and schemas regenerated;
- decision trace under `docs/decisions/`;
- this handoff updated with actual changed files and validation results.

## Implementation Record (2026-07-09 / intake B)

Branch: `feat/stage-6-review-ui-qa-crosswalk-ocg-evidence`

### Changed / added files

- Ported (not rebuilt) Stage 4/5 generators: `src/lawfirm_os_intake/crosswalks.py`,
  `src/lawfirm_os_intake/ocg_rule_ir.py` (+ B projection-model adapters)
- New Stage 6 evidence module: `src/lawfirm_os_intake/review_ui_crosswalk_ocg_evidence.py`
- Extended: `src/lawfirm_os_intake/ui_review_data_bundle.py`, `src/lawfirm_os_intake/models.py`,
  `src/lawfirm_os_intake/cli.py`, `scripts/export_schemas.py`
- Fixtures: `fixtures/synthetic/crosswalks/*`,
  `fixtures/synthetic/ocg/shared-rule-ir/harbor-point-alpha.ocg-rule-ir.json`
- UI: `apps/legal-intake-budget/src/App.tsx`, `data-contract.ts`, `types.ts`,
  `fixtures/demo-crosswalk-audit-report.json`,
  `fixtures/demo-ocg-rule-ir-adoption-report.json`,
  refreshed `demo-ui-review-data-bundle.json` + `demo-rust-fixture-manifest-report.json`
- Tests: `tests/test_crosswalks.py`, `tests/test_ocg_rule_ir_adoption.py`,
  `tests/test_review_ui_crosswalk_ocg_evidence.py` (+ count updates in UI bundle tests)
- Schemas: 16 new crosswalk/OCG/QA schemas; UI bundle schemas regenerated
- Trace: `docs/decisions/TRACE-2026-07-09-stage6-review-ui-qa-crosswalk-ocg-evidence.md`

### Validation results

| Command | Result |
|---|---|
| `python scripts/export_schemas.py` | passed (436 schemas) |
| `python scripts/validate_repo.py` | passed |
| `python -m ruff check --no-cache src tests scripts` | passed |
| `python -m ruff format --check` (Stage 6 touched files) | passed |
| `python scripts/run_full_pytest.py -q tests/test_crosswalks.py tests/test_ocg_rule_ir_adoption.py` | passed |
| `python scripts/run_full_pytest.py -q` | passed (full suite, 3600s ceiling) |
| `bash scripts/smoke_demo.sh` | passed (`demo_completed`) |
| `npx tsc -b && npx vite build` (apps/legal-intake-budget) | passed |
| `npm run smoke:contract` | **not present** in this repo's `package.json` (only `dev`/`build`/`preview`) |

### Invariants held

- Crosswalk + OCG reports remain candidate-only / read-only evidence; no budget math rewrite.
- UI bundle backward compatible when `--crosswalk-audit` / `--ocg-rule-ir-adoption` omitted.
- No external writes, Lake writes, or canon promotion.
