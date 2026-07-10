# Fable Snapshot Review Packets 2026-07-10

Status: candidate handoff
Scope: LawFirm OS intake canonical clone

This file converts the snapshot landing plan into executable review packets.
It is not a command log, approval to stage, approval to commit, or approval to
begin Packet E2 / PR-CL1. It exists so a future agent can land the current
dirty work in small, reviewable slices without mixing boundaries.

## Operating Boundary

- Do not start Packet E2 until these dirty slices are landed, snapshotted, or
  explicitly re-coordinated by the owner.
- Do not run any component on real client, matter, carrier, privileged, or
  production intake data.
- Do not treat candidate calibration evidence, `approval:` strings, or Fable
  drafts as legal, compliance, privacy, promotion, or governance authority.
- Do not stage, commit, push, or open PRs from these templates unless the owner
  gives explicit landing permission.
- Keep `src/lawfirm_os_intake/reviewed_learning_gate.py` and
  `src/lawfirm_os_intake/calibration/` together in the calibration packet.
- Keep replay input fixtures, source code, tests, and decision trace together in
  the Phase 1 replay-input packet.

## Current Dirty-State Inventory

Recorded at this review-packet checkpoint:

- Branch: `feat/port-dad-layer-docs`
- HEAD and upstream: `ab7255c` (`Normalize ported handoff doc EOFs`)
- Nothing staged.
- `src/lawfirm_os_intake/reviewed_learning_gate.py` is a shared dirty surface
  and also part of Packet E2's future write surface.

Dirty tracked files:

- `.gitignore`
- `apps/legal-intake-budget/src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json`
- `examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json`
- `src/lawfirm_os_intake/labor_employment_budget_outcome_replay_input_pack.py`
- `src/lawfirm_os_intake/reviewed_learning_gate.py`
- `tests/test_labor_employment_budget_outcome_replay_input_pack.py`

Untracked files to land only through the packets below:

- `docs/ai-handoff/FABLE_CURRENT_STATE_AND_E2_APPROVAL_CHECKPOINT.md`
- `docs/ai-handoff/FABLE_EXECUTION_SUBAGENT_TASK_PACKETS.md`
- `docs/ai-handoff/FABLE_READINESS_SNAPSHOT_2026-07-10.md`
- `docs/ai-handoff/FABLE_SNAPSHOT_LANDING_PLAN_2026-07-10.md`
- `docs/ai-handoff/FABLE_SNAPSHOT_REVIEW_PACKETS_2026-07-10.md`
- `docs/ai-handoff/FABLE_SUBAGENT_AUDIT_2026-07-10.md`
- `docs/decisions/TRACE-2026-07-09-calibration-leakage-preflight-scaffold.md`
- `docs/decisions/TRACE-2026-07-09-calibration-proof-reviewed-learning-gate.md`
- `docs/decisions/TRACE-2026-07-09-dad-layer-doc-port.md`
- `docs/decisions/TRACE-2026-07-09-le-class-collective-replay-input-preflight-gap-matrix.md`
- `docs/fable/bounded-leakage-calibration-kernel.opus-draft.md`
- `docs/fable/codex-learning-leakage-build-packet.opus-draft.md`
- `docs/fable/cross-matter-noninterference-kernel.opus-draft.md`
- `docs/fable/learning-vs-leakage-hard-kernels.opus-draft.md`
- `examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json`
- `examples/synthetic/labor-employment/replay-inputs/class-collective-clean/budget_actuals_source.json`
- `examples/synthetic/labor-employment/replay-inputs/class-collective-clean/legal_budget_proposal.json`
- `src/lawfirm_os_intake/calibration/__init__.py`
- `src/lawfirm_os_intake/calibration/leakage.py`
- `tests/test_calibration_leakage.py`
- `tests/test_calibration_reviewed_learning_gate.py`

## Snapshot-Before-E2 Gate

Before any Packet E2 coding, the owner must either land, snapshot, or
explicitly coordinate these four active groups:

- Phase 1 replay-input snapshot.
- Fable calibration/gate scaffold snapshot.
- Fable docs/handoff snapshot.
- Housekeeping snapshot.

If any group remains dirty, Packet E2 may proceed only with explicit owner
coordination for the overlapping files and risks.

## Frozen Packet E2 Boundary

Packet E2 may touch only:

- `src/lawfirm_os_intake/calibration/`
- `src/lawfirm_os_intake/reviewed_learning_gate.py`
- calibration and reviewed-learning focused tests
- synthetic calibration fixtures
- one decision trace under `docs/decisions/`

Packet E2 must not:

- add DP or zCDP;
- choose production K, dominance, LOMO, adversary model, protected unit,
  epsilon/rho/delta, reset policy, seed custody, or real-data values;
- treat `approval:` strings as production approval;
- import privacy dependencies;
- publish calibrated values;
- touch Substrate, Orchestrator, Exception Lake, canonical schemas,
  registries, connectors, UI readiness claims, production config, or real-data
  fixtures.

## Packet E2 Missing Safeguards

The next implementation slice must add or preserve these safeguards before it
can claim PR-CL1 completion:

- Calibration-gate-only success must not collapse into ordinary
  `no_learning_candidates`; it needs a distinct visible calibration-gate
  review-input state.
- Matter-level LOMO must be separated from protected-unit K/group privacy
  accounting.
- Proof digest tests must cover matter/input identifiers, data flags,
  contributions, input-order determinism, protected-unit membership, and
  reconstruction metric changes.
- Reconstruction metrics must be explicitly labeled as supplied synthetic
  scaffold evidence unless computed adversary testing is implemented later.
- `approval:` strings must remain deterministic test evidence only, with no
  verified approval-record or attorney-role implication.

## Packet 1: Phase 1 Replay-Input Snapshot

Purpose: land the synthetic class/collective/PAGA replay-input preflight slice
as a coherent candidate snapshot.

Suggested commit message:

```text
Add class collective replay input preflight snapshot
```

Review-only staging template:

```powershell
git add -- `
  apps/legal-intake-budget/src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json `
  examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json `
  examples/synthetic/labor-employment/replay-inputs/class-collective-clean/budget_actuals_source.json `
  examples/synthetic/labor-employment/replay-inputs/class-collective-clean/legal_budget_proposal.json `
  src/lawfirm_os_intake/labor_employment_budget_outcome_replay_input_pack.py `
  tests/test_labor_employment_budget_outcome_replay_input_pack.py `
  docs/decisions/TRACE-2026-07-09-le-class-collective-replay-input-preflight-gap-matrix.md
```

Required checks for this packet:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q
python scripts\validate_repo.py
git diff --check -- `
  apps/legal-intake-budget/src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json `
  examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json `
  src/lawfirm_os_intake/labor_employment_budget_outcome_replay_input_pack.py `
  tests/test_labor_employment_budget_outcome_replay_input_pack.py `
  docs/decisions/TRACE-2026-07-09-le-class-collective-replay-input-preflight-gap-matrix.md
```

PR body checklist:

```markdown
## Summary
- Adds synthetic-only class/collective/PAGA replay-input preflight coverage.
- Updates the demo confidence-status fixture to surface missing/invalid replay
  slots without running builders.
- Records the preflight gap matrix as a candidate decision trace.

## Boundaries
- [ ] Synthetic fixtures only; no client, matter, carrier, privileged, or
      production intake data.
- [ ] Candidate preflight only; no runtime artifact, Lake record, SQLite write,
      budget submission, or learning promotion.
- [ ] Does not start Packet E2 / PR-CL1.

## Validation
- [ ] `$env:PYTHONPATH='src'; python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q`
- [ ] `python scripts\validate_repo.py`
- [ ] `git diff --check -- <packet files>`
```

## Packet 2: Fable Calibration/Gate Scaffold Snapshot

Purpose: land the candidate-only, synthetic-only calibration proof scaffold and
reviewed-learning-gate chokepoint wiring as one slice.

Suggested commit message:

```text
Add candidate calibration leakage gate scaffold
```

Review-only staging template:

```powershell
git add -- `
  examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json `
  src/lawfirm_os_intake/calibration/__init__.py `
  src/lawfirm_os_intake/calibration/leakage.py `
  src/lawfirm_os_intake/reviewed_learning_gate.py `
  tests/test_calibration_leakage.py `
  tests/test_calibration_reviewed_learning_gate.py `
  docs/decisions/TRACE-2026-07-09-calibration-leakage-preflight-scaffold.md `
  docs/decisions/TRACE-2026-07-09-calibration-proof-reviewed-learning-gate.md
```

Required checks for this packet:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_reviewed_learning_gate.py -q
python scripts\validate_repo.py
git diff --check -- `
  examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json `
  src/lawfirm_os_intake/calibration/__init__.py `
  src/lawfirm_os_intake/calibration/leakage.py `
  src/lawfirm_os_intake/reviewed_learning_gate.py `
  tests/test_calibration_leakage.py `
  tests/test_calibration_reviewed_learning_gate.py `
  docs/decisions/TRACE-2026-07-09-calibration-leakage-preflight-scaffold.md `
  docs/decisions/TRACE-2026-07-09-calibration-proof-reviewed-learning-gate.md
```

PR body checklist:

```markdown
## Summary
- Adds a homegrown, candidate-only calibration leakage proof scaffold.
- Wires calibration proof evidence through `reviewed_learning_gate.py` as the
  single reviewed-learning chokepoint.
- Adds synthetic fixture and focused tests for accepted aggregate proofs and
  refused unsafe paths.

## Boundaries
- [ ] Synthetic-only and candidate-only.
- [ ] No formal privacy guarantee is claimed.
- [ ] No DP/zCDP implementation, privacy dependency, calibrated-value
      publication, profile mutation, budget mutation, Lake mutation, or
      canonical Substrate promotion.
- [ ] `approval:` strings remain deterministic local evidence only, not
      verified production approval.
- [ ] HD-1 through HD-11 remain open owner decisions.
- [ ] Does not start Packet E2 / PR-CL1.

## Validation
- [ ] `$env:PYTHONPATH='src'; python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_reviewed_learning_gate.py -q`
- [ ] `python scripts\validate_repo.py`
- [ ] `git diff --check -- <packet files>`
```

## Packet 3: Fable Docs/Handoff Snapshot

Purpose: land the Fable architecture, kernel, subagent, and approval-boundary
handoff docs as candidate planning evidence.

Suggested commit message:

```text
Record Fable learning leakage handoff packets
```

Review-only staging template:

```powershell
git add -- `
  docs/ai-handoff/FABLE_CURRENT_STATE_AND_E2_APPROVAL_CHECKPOINT.md `
  docs/ai-handoff/FABLE_EXECUTION_SUBAGENT_TASK_PACKETS.md `
  docs/ai-handoff/FABLE_READINESS_SNAPSHOT_2026-07-10.md `
  docs/ai-handoff/FABLE_SNAPSHOT_LANDING_PLAN_2026-07-10.md `
  docs/ai-handoff/FABLE_SNAPSHOT_REVIEW_PACKETS_2026-07-10.md `
  docs/ai-handoff/FABLE_SUBAGENT_AUDIT_2026-07-10.md `
  docs/fable/bounded-leakage-calibration-kernel.opus-draft.md `
  docs/fable/codex-learning-leakage-build-packet.opus-draft.md `
  docs/fable/cross-matter-noninterference-kernel.opus-draft.md `
  docs/fable/learning-vs-leakage-hard-kernels.opus-draft.md
```

Required checks for this packet:

```powershell
python scripts\validate_repo.py
git diff --check -- `
  docs/ai-handoff/FABLE_CURRENT_STATE_AND_E2_APPROVAL_CHECKPOINT.md `
  docs/ai-handoff/FABLE_EXECUTION_SUBAGENT_TASK_PACKETS.md `
  docs/ai-handoff/FABLE_READINESS_SNAPSHOT_2026-07-10.md `
  docs/ai-handoff/FABLE_SNAPSHOT_LANDING_PLAN_2026-07-10.md `
  docs/ai-handoff/FABLE_SNAPSHOT_REVIEW_PACKETS_2026-07-10.md `
  docs/ai-handoff/FABLE_SUBAGENT_AUDIT_2026-07-10.md `
  docs/fable/bounded-leakage-calibration-kernel.opus-draft.md `
  docs/fable/codex-learning-leakage-build-packet.opus-draft.md `
  docs/fable/cross-matter-noninterference-kernel.opus-draft.md `
  docs/fable/learning-vs-leakage-hard-kernels.opus-draft.md
```

PR body checklist:

```markdown
## Summary
- Records the Fable learning-vs-leakage current state, packet plan, readiness
  snapshot, subagent audit, and hard-kernel drafts.
- Preserves Packet E2 / PR-CL1 as a future owner-approved implementation slice.
- Documents which work should be delegated to low-effort Cursor/Composer scouts
  versus medium-thinking GLM-style coding/readiness agents.

## Boundaries
- [ ] Candidate handoff only.
- [ ] No Fable draft, agent packet, or model-specific note becomes product,
      governance, legal, privacy, compliance, or promotion authority.
- [ ] Composer/Cursor and GLM references are implementation surfaces only.
- [ ] Does not start Packet E2 / PR-CL1.

## Validation
- [ ] `python scripts\validate_repo.py`
- [ ] `git diff --check -- <packet files>`
```

## Packet 4: Housekeeping Snapshot

Purpose: land private-workspace ignore rules and the DAD-layer doc-port trace
without mixing them into runtime or calibration semantics.

Suggested commit message:

```text
Record DAD handoff housekeeping trace
```

Review-only staging template:

```powershell
git add -- `
  .gitignore `
  docs/decisions/TRACE-2026-07-09-dad-layer-doc-port.md
```

Required checks for this packet:

```powershell
python scripts\validate_repo.py
git diff --check -- .gitignore docs/decisions/TRACE-2026-07-09-dad-layer-doc-port.md
```

PR body checklist:

```markdown
## Summary
- Ignores private `.ai-work/` scratch space.
- Records the DAD-layer architecture doc-port trace.

## Boundaries
- [ ] Does not stage `.ai-work/fable/CODEX_CROSS_REPO_HANDOFF.md`.
- [ ] Does not stage `.digital-asset/mail/outbox.jsonl`.
- [ ] Does not delete append-only candidate evidence.
- [ ] Does not start Packet E2 / PR-CL1.

## Validation
- [ ] `python scripts\validate_repo.py`
- [ ] `git diff --check -- .gitignore docs/decisions/TRACE-2026-07-09-dad-layer-doc-port.md`
```

## Final Pre-E2 Check

After the packets above are landed or explicitly snapshotted, run this final
gate before requesting owner approval for Packet E2:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q
python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_reviewed_learning_gate.py -q
python scripts\validate_repo.py
git diff --check
```

If disk space allows, run the full baseline:

```powershell
$env:PYTHONPATH='src'
python scripts\run_validation_suite.py
```

If any packet modifies the dirty set after the recorded 2026-07-10 evidence,
rerun that packet's focused tests. If full validation creates ignored outputs
or dependency caches, clean only ignored/generated artifacts after confirming
they are outside append-only evidence paths.

## Agent Assignment Notes

- Low-effort Cursor/Composer agents should be used for read-only grouping,
  fixture listing, checklist completeness, and drift scouting.
- Medium-thinking GLM-style coding/readiness agents should be used for bounded
  implementation or red-team reviews with explicit write ownership and no
  authority to merge, promote, or reinterpret governance.
- High-effort Packet E2 implementation remains frozen until the owner approves
  the next PR-CL1 coding slice.
