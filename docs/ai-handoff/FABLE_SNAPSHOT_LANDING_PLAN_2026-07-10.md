# Fable Snapshot Landing Plan 2026-07-10

Status: candidate handoff
Scope: LawFirm OS intake canonical clone

This plan records the remaining dirty groups that must be landed, snapshotted,
or explicitly coordinated before high-effort Packet E2 / PR-CL1 coding begins.
It does not approve Packet E2 implementation.

Executable review packets, staging templates, commit-message suggestions, and
PR checklists are recorded in
`docs/ai-handoff/FABLE_SNAPSHOT_REVIEW_PACKETS_2026-07-10.md`.

## Current Branch State

- Current branch: `feat/port-dad-layer-docs`
- Branch tracks: `origin/feat/port-dad-layer-docs`
- Current HEAD and upstream: `ab7255c` (`Normalize ported handoff doc EOFs`).
- DAD-layer doc port ancestry includes `b0f3f20`
  (`Port DAD layer handoff docs`), `809b9e8`
  (`Update governance mirror for DAD handoff docs`), and `ab7255c`.
- Stage 7 crosswalk/OCG evidence hardening is tracked at parent commit
  `e3eedc5`.
- No files were staged when this plan was updated.

## Subagent Review

| Agent id | Effort | Mode | Finding |
|---|---|---|---|
| `019f49cb-76d2-7bb3-ab90-c526bdd417b0` | `low` | read-only snapshot boundary scout | Remaining work can be grouped as Phase 1 replay-input, Fable calibration/gate scaffold, Fable docs/handoff, and housekeeping. |
| `019f49cb-a685-7bd1-a01d-0dc37ccf26ec` | `medium` | read-only snapshot risk review | No hard semantic blocker to candidate snapshots, but `reviewed_learning_gate.py` must land with the calibration package and tests; replay input files must land together. |

## Snapshot Groups

### 1. Phase 1 Replay-Input Snapshot

Land as one coherent slice:

- `apps/legal-intake-budget/src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json`
- `examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json`
- `examples/synthetic/labor-employment/replay-inputs/class-collective-clean/budget_actuals_source.json`
- `examples/synthetic/labor-employment/replay-inputs/class-collective-clean/legal_budget_proposal.json`
- `src/lawfirm_os_intake/labor_employment_budget_outcome_replay_input_pack.py`
- `tests/test_labor_employment_budget_outcome_replay_input_pack.py`
- `docs/decisions/TRACE-2026-07-09-le-class-collective-replay-input-preflight-gap-matrix.md`

Boundary:

- Preflight-only.
- Adds class/collective/PAGA actuals replay inputs.
- Shows the next missing or invalid replay slots without running builders.
- Keeps reports candidate-only and non-authoritative.
- Must not create runtime artifacts, Lake records, SQLite writes, budget
  submissions, or silent learning.

### 2. Fable Calibration/Gate Scaffold Snapshot

Land as one coherent slice:

- `examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json`
- `src/lawfirm_os_intake/calibration/__init__.py`
- `src/lawfirm_os_intake/calibration/leakage.py`
- `src/lawfirm_os_intake/reviewed_learning_gate.py`
- `tests/test_calibration_leakage.py`
- `tests/test_calibration_reviewed_learning_gate.py`
- `docs/decisions/TRACE-2026-07-09-calibration-leakage-preflight-scaffold.md`
- `docs/decisions/TRACE-2026-07-09-calibration-proof-reviewed-learning-gate.md`

Boundary:

- Candidate-only, synthetic-only scaffold.
- `reviewed_learning_gate.py` imports `.calibration`, so it must not land
  without the calibration package and focused tests.
- Valid `CalibrationLeakageProof` plus an `approval:`-form string is local
  deterministic evidence only; it is not verified production approval.
- No DP/zCDP path, no calibrated value publication, no profile/budget/Lake/canon
  mutation, and no Packet E2 completion claim.

### 3. Fable Docs/Handoff Snapshot

Land as a docs-only candidate handoff:

- `docs/ai-handoff/FABLE_CURRENT_STATE_AND_E2_APPROVAL_CHECKPOINT.md`
- `docs/ai-handoff/FABLE_EXECUTION_SUBAGENT_TASK_PACKETS.md`
- `docs/ai-handoff/FABLE_READINESS_SNAPSHOT_2026-07-10.md`
- `docs/ai-handoff/FABLE_SUBAGENT_AUDIT_2026-07-10.md`
- `docs/ai-handoff/FABLE_SNAPSHOT_LANDING_PLAN_2026-07-10.md`
- `docs/ai-handoff/FABLE_SNAPSHOT_REVIEW_PACKETS_2026-07-10.md`
- `docs/fable/bounded-leakage-calibration-kernel.opus-draft.md`
- `docs/fable/codex-learning-leakage-build-packet.opus-draft.md`
- `docs/fable/cross-matter-noninterference-kernel.opus-draft.md`
- `docs/fable/learning-vs-leakage-hard-kernels.opus-draft.md`

Boundary:

- Candidate handoff only.
- Must keep Packet E2 frozen until owner approval.
- Must keep Composer/Cursor/GLM references as implementation surfaces, not
  authority sources.

### 4. Housekeeping Snapshot

Land separately or attach to the docs snapshot only if the reviewer agrees:

- `.gitignore`
- `docs/decisions/TRACE-2026-07-09-dad-layer-doc-port.md`

Boundary:

- `.gitignore` adds `.ai-work/` as private AI workspace scratch.
- Do not include `.digital-asset/mail/outbox.jsonl`; it is ignored but
  append-only candidate mailbox evidence.
- Do not include `.ai-work/fable/CODEX_CROSS_REPO_HANDOFF.md`; it is ignored
  private handoff context and was intentionally preserved.

## Required Checks Before Landing

Minimum focused checks:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q
python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_reviewed_learning_gate.py -q
python scripts\validate_repo.py
git diff --check
```

For the final pre-E2 checkpoint, run the full validation suite when disk space
allows:

```powershell
$env:PYTHONPATH='src'
python scripts\run_validation_suite.py
```

Previously recorded evidence on 2026-07-10: focused tests passed, full
validation suite passed with `825 passed`, and smoke ended at
`blocked_pending_conflicts_and_engagement`. Re-run before landing if the dirty
set changes.

## Packet E2 Risks To Carry Forward

- Calibration-gate-only success can still report `no_learning_candidates`; E2
  must surface calibration-gate review input more explicitly.
- LOMO currently runs over grouped protected-unit contributions in the scaffold;
  E2 must separate matter-level LOMO from protected-unit K/group privacy
  accounting.
- Proof digest tests need stronger coverage for identifiers, data flags,
  contribution changes, input order, protected-unit membership, and
  reconstruction metrics.
- `approval:` strings are deterministic test evidence only.
- Reconstruction metrics are scaffold-only and supplied-synthetic unless a later
  approved slice implements computed adversary testing.
