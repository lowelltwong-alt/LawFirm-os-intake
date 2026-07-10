# Fable Readiness Snapshot 2026-07-10

Status: candidate handoff
Scope: LawFirm OS intake canonical clone

This snapshot records the current validated state before any Packet E2 / PR-CL1
coding. It does not approve E2 implementation.

See `docs/ai-handoff/FABLE_SNAPSHOT_LANDING_PLAN_2026-07-10.md` for the
remaining dirty-group landing boundaries before Packet E2.

## Current Git State

- Current branch: `feat/port-dad-layer-docs`
- Current HEAD and upstream: `ab7255c`
  (`Normalize ported handoff doc EOFs`)
- DAD-layer doc-port ancestry includes `b0f3f20`
  (`Port DAD layer handoff docs`) and `809b9e8`
  (`Update governance mirror for DAD handoff docs`)
- Stage 7 commit present as parent: `e3eedc5`
- `ab7255c` matches `origin/feat/port-dad-layer-docs`
- `e3eedc5` also matches `origin/feat/stage-7-crosswalk-ocg-evidence-hardening`
  and local `feat/stage-7-crosswalk-ocg-evidence-hardening`
- No files staged at the time of this snapshot

Stage 7 crosswalk/OCG evidence hardening is no longer merely dirty worktree
state; it is a tracked commit:

```text
e3eedc5 Harden Stage 7 crosswalk evidence: dual human review and unverified standard-code display.
```

DAD-layer architecture handoff docs are also tracked in HEAD:

```text
ab7255c Normalize ported handoff doc EOFs
809b9e8 Update governance mirror for DAD handoff docs
b0f3f20 Port DAD layer handoff docs
```

## Remaining Dirty Groups

Phase 1 L&E replay-input preflight:

- `apps/legal-intake-budget/src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json`
- `examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json`
- `examples/synthetic/labor-employment/replay-inputs/class-collective-clean/`
- `src/lawfirm_os_intake/labor_employment_budget_outcome_replay_input_pack.py`
- `tests/test_labor_employment_budget_outcome_replay_input_pack.py`
- `docs/decisions/TRACE-2026-07-09-le-class-collective-replay-input-preflight-gap-matrix.md`

Fable calibration and handoff scaffold:

- `src/lawfirm_os_intake/calibration/`
- `src/lawfirm_os_intake/reviewed_learning_gate.py`
- `tests/test_calibration_leakage.py`
- `tests/test_calibration_reviewed_learning_gate.py`
- `examples/synthetic/calibration/`
- `docs/fable/*.opus-draft.md`
- `docs/ai-handoff/FABLE_CURRENT_STATE_AND_E2_APPROVAL_CHECKPOINT.md`
- `docs/ai-handoff/FABLE_EXECUTION_SUBAGENT_TASK_PACKETS.md`
- `docs/ai-handoff/FABLE_READINESS_SNAPSHOT_2026-07-10.md`
- `docs/ai-handoff/FABLE_SUBAGENT_AUDIT_2026-07-10.md`
- `docs/decisions/TRACE-2026-07-09-calibration-*.md`
- `docs/decisions/TRACE-2026-07-09-dad-layer-doc-port.md`

Housekeeping:

- `.gitignore` adds `.ai-work/` as a private AI workspace ignore.

## Validation Evidence

Focused validation:

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
```

Full validation:

```powershell
$env:PYTHONPATH='src'
python scripts\run_validation_suite.py
# validate_repo passed
# export_schemas exported 436 schemas
# ruff check passed
# ruff format --check passed
# full pytest: 825 passed in 739.67s
# smoke demo completed
# final validate_repo passed
```

The first full-suite run failed only on formatting. The following mechanical
formatting command was applied, then the full suite passed:

```powershell
python -m ruff format src\lawfirm_os_intake\calibration\leakage.py src\lawfirm_os_intake\reviewed_learning_gate.py tests\test_calibration_reviewed_learning_gate.py tests\test_crosswalks.py
# 4 files reformatted
```

`git diff --check` exited 0 with CRLF warnings on existing dirty files.

Fresh pre-E2 packet readiness validation:

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

The full validation suite was not rerun in this packet-readiness pass because
local disk space remained under 500 MB free. The last full-suite evidence above
still proves the broader baseline for the recorded dirty set, and packet-local
focused tests were rerun after the snapshot review packet edits.

## Packet E2 Gate

Packet E2 / PR-CL1 is still not approved for coding from this snapshot. Before
starting E2:

1. Land, snapshot, or explicitly coordinate the remaining Phase 1 replay-input
   and Fable calibration/handoff dirty groups.
2. Re-check the current branch and worktree; do not assume `e3eedc5` remains
   HEAD.
3. Get owner approval for high-effort Packet E2 coding.
4. Assign a high-effort coding worker to the Packet E2 write surface.
5. Assign high-effort red-team review after E2 implementation.

Do not start DP/zCDP, QRD, IFC, simulator consumption, Substrate promotion, or
real-data paths from this snapshot.

## Disk Cleanup Note

After the full validation suite, the local `C:` drive reached `0` bytes free and
DAD postflight initially failed with `OperationalError: database or disk is
full`. Codex removed only ignored/generated local outputs:

- `.lawfirm-os-intake/` validation/runtime output tree.
- `.ruff_cache/`.
- `rust/fixture-boundary-checker/target/`.
- `apps/legal-intake-budget/dist/`.
- `apps/legal-intake-budget/tsconfig.tsbuildinfo`.
- `apps/legal-intake-budget/node_modules/`.

Preserved record-like ignored files:

- `.digital-asset/mail/outbox.jsonl`.
- `.ai-work/fable/CODEX_CROSS_REPO_HANDOFF.md`.

If the review UI needs to run locally again, reinstall frontend dependencies
from `apps/legal-intake-budget/package-lock.json` with `npm ci` from
`apps/legal-intake-budget/`.
