# Fable Subagent Audit 2026-07-10

Status: candidate handoff
Scope: LawFirm OS intake canonical clone

This file records the subagent work used to continue the Fable
learning-vs-leakage buildout without starting Packet E2 coding before owner
approval. It is agent-agnostic: Cursor, Composer, GLM, Codex, or another worker
can use it if they preserve the stated effort, boundaries, and stop conditions.

## Subagents Used

| Agent id | Assigned role | Effort | Mode | Result |
|---|---|---|---|---|
| `019f49a3-7514-7a03-8432-4310469aa22a` | Cursor/Composer Phase 1 scout | `low` | read-only | Identified active Phase 1 replay-input and Stage 7 crosswalk/OCG dirty slices; recommended avoiding shared dirty surfaces before E2 coordination. |
| `019f49a3-b39f-71b2-8ec4-692391543606` | GLM 5.2 coding-readiness auditor | `medium` | read-only | Confirmed Packet E scaffold exists, Packet E2 remains owner-approval-blocked, and named concrete code/doc mismatches E2 must close. |
| `019f49da-55eb-7882-b294-7b6e12b19d13` | Cursor/Composer review-packet path scout | `low` | read-only | Verified every path in the four review-only staging templates exists and is in the intended dirty/untracked group; no missing or misgrouped paths found. |
| `019f49da-8996-7340-8c0d-5adfc984d5a0` | GLM 5.2 E2-freeze red-team reviewer | `medium` | read-only | Found no doc-level boundary regression in the current-state, landing-plan, and review-packet docs; confirmed the five E2 missing safeguards remain documented. |

## Cursor/Composer Phase 1 Findings

Cursor/Composer Phase 1 appears to be the L&E class/collective replay-input
preflight slice, not the DAD doc-port slice.

Likely Phase 1 ownership:

- `src/lawfirm_os_intake/labor_employment_budget_outcome_replay_input_pack.py`
- `tests/test_labor_employment_budget_outcome_replay_input_pack.py`
- `examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json`
- `examples/synthetic/labor-employment/replay-inputs/class-collective-clean/`
- affected UI fixture/hash files under `apps/legal-intake-budget/src/fixtures/`
- `docs/decisions/TRACE-2026-07-09-le-class-collective-replay-input-preflight-gap-matrix.md`

Likely Stage 7 ownership:

- `src/lawfirm_os_intake/crosswalks.py`
- `src/lawfirm_os_intake/review_ui_crosswalk_ocg_evidence.py`
- `schemas/crosswalk-audit-report.schema.json`
- `schemas/crosswalk-audit-summary.schema.json`
- `schemas/ui-review-data-bundle.schema.json`
- `apps/legal-intake-budget/src/App.tsx`
- `apps/legal-intake-budget/src/data-contract.ts`
- `apps/legal-intake-budget/src/types.ts`
- `tests/test_crosswalks.py`
- `tests/test_review_ui_crosswalk_ocg_evidence.py`
- `docs/decisions/TRACE-2026-07-09-stage7-crosswalk-ocg-evidence-hardening.md`

Shared dirty surfaces to avoid unless explicitly coordinated:

- `src/lawfirm_os_intake/models.py`
- `src/lawfirm_os_intake/reviewed_learning_gate.py`
- `apps/legal-intake-budget/src/fixtures/demo-ui-review-data-bundle.json`
- `apps/legal-intake-budget/src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json`
- `schemas/ui-review-data-bundle.schema.json`

## Packet E2 Readiness Findings

Packet E / PR-LL1A exists as a local scaffold. Packet E2 / PR-CL1 remains
blocked pending owner approval and coordination around active dirty files.

The future E2 worker should stay inside this surface unless the owner expands
scope:

- `src/lawfirm_os_intake/calibration/__init__.py`
- `src/lawfirm_os_intake/calibration/leakage.py`
- `src/lawfirm_os_intake/reviewed_learning_gate.py`
- `tests/test_calibration_leakage.py`
- `tests/test_calibration_reviewed_learning_gate.py`
- `examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json`
- one new Packet E2 decision trace under `docs/decisions/`

Concrete E2 gaps:

- The current calibration-gate-only accepted report can still end as ordinary
  `no_learning_candidates`. E2 must surface calibration-gate review input
  distinctly without treating it as promoted learning.
- LOMO is currently computed over grouped protected-unit values when
  `protected_unit` is `client` or `affiliate_group`. E2 must keep matter-level
  LOMO separate from protected-unit K/group privacy accounting.
- Proof digest behavior likely binds the right fields, but tests must prove
  sensitivity for matter/input identifiers, data flags, contributions,
  input-order determinism, protected-unit membership, and reconstruction metric
  changes.
- Reconstruction metrics are marked with `scaffold_only=True`, but the supplied
  synthetic scaffold basis needs an explicit tested/reportable label.
- Local proof visibility must remain repo-local and candidate-only. Do not
  create or imply canonical Substrate schema authority.

## Next Safe Action

Before E2 coding:

1. Land, snapshot, or explicitly coordinate the active Phase 1 replay-input and
   Stage 7 crosswalk/OCG dirty slices.
2. Get owner approval for Packet E2 / PR-CL1.
3. Assign a `high` effort coding worker to Packet E2 with the file surface and
   gaps above.
4. Use `high` effort red-team review after E2 implementation and before any
   Packet E3 / DP-zCDP work.

Do not start DP/zCDP, QRD, IFC, simulator consumption, Substrate promotion, or
real-data paths from this audit.

## Post-Audit Readiness Update

After the read-only subagent audits, Codex ran the required focused validation
groups and the full repo validation suite. Stage 7 crosswalk/OCG evidence
hardening was found committed at `e3eedc5`, which is both the local
`feat/stage-7-crosswalk-ocg-evidence-hardening` branch tip and
`origin/feat/stage-7-crosswalk-ocg-evidence-hardening`. A later branch-state
check found `feat/port-dad-layer-docs` at `b0f3f20`, matching
`origin/feat/port-dad-layer-docs`; that commit tracks the DAD-layer
architecture handoff docs.

Fresh validation evidence:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q
# 27 passed

python scripts\run_full_pytest.py tests\test_crosswalks.py tests\test_review_ui_crosswalk_ocg_evidence.py -q
# 25 passed

python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_reviewed_learning_gate.py -q
# 32 passed

python scripts\run_full_pytest.py tests\test_rust_fixture_manifest_scanner.py tests\test_rust_ui_bundle_source_hash.py tests\test_ui_demo_fixture_refresh.py tests\test_ui_foundation_contract.py -q
# 45 passed

python scripts\run_validation_suite.py
# full suite passed; full pytest reported 825 passed
```

The first full-suite attempt found four files needing formatting. Codex ran:

```powershell
python -m ruff format src\lawfirm_os_intake\calibration\leakage.py src\lawfirm_os_intake\reviewed_learning_gate.py tests\test_calibration_reviewed_learning_gate.py tests\test_crosswalks.py
# 4 files reformatted
```

Remaining active dirty groups after the green full suite and branch-state check:

- Phase 1 L&E replay-input preflight.
- Fable calibration/handoff scaffold, Fable kernel drafts, and current-state
  handoff docs.
- `.gitignore` DAD workspace ignore.

Packet E2 remains frozen until those remaining dirty groups are landed,
snapshotted, or explicitly coordinated and owner approval is given for
high-effort E2 coding.

## Review-Packet Readiness Update

Two additional read-only subagents reviewed the executable snapshot packets:

- Low-effort Cursor/Composer path scout
  `019f49da-55eb-7882-b294-7b6e12b19d13` confirmed all staging-template paths
  exist and are grouped correctly. `git status --short -uall` was needed to see
  individual files inside collapsed untracked directories.
- Medium-thinking GLM 5.2 red-team reviewer
  `019f49da-8996-7340-8c0d-5adfc984d5a0` found no doc-level regression in the
  Packet E2 freeze, synthetic-only/candidate-only boundary, no-DP/no-formal-
  privacy-guarantee boundary, no-real-data boundary, no-authority-promotion
  boundary, or no-child-repo-override boundary.

Current focused readiness evidence:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q
# 27 passed

python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_reviewed_learning_gate.py -q
# 32 passed

python scripts\validate_repo.py
# repository validation passed

git diff --check
# exit 0; existing CRLF warning on apps/legal-intake-budget/src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json
```

Full validation was not rerun in this readiness update because local disk space
remained under 500 MB free. The next landing or pre-E2 approval pass should
rerun the full baseline when disk space allows.
