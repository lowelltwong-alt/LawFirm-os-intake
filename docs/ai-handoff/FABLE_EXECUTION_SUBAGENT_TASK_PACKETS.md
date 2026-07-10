# Fable Execution Subagent Task Packets

Status: candidate handoff
Date: 2026-07-09
Scope: LawFirm OS intake, canonical clone

Canonical working tree:

```text
<lawfirm-os-intake-repo-root>
```

This file is agent-agnostic. "Cursor" and "GLM" name likely implementation
surfaces only. Any future agent can run these packets if it preserves the stated
reasoning effort, scope, validation, and stop conditions.

## Universal Rules

- Run this repo's front door and DAD preflight before material work.
- Use `python scripts\run_full_pytest.py ...` for focused pytest; direct pytest
  is blocked by policy.
- Everything is synthetic-only and candidate-only.
- Extend existing gates; do not fork `reviewed_learning_gate`.
- No real client, matter, privileged, carrier-private, negotiated-rate, or
  production intake data.
- No connectors, network actions, email sends, carrier portal actions, billing
  writes, court writes, iManage writes, conflict clearance, matter opening,
  budget submission, appeal submission, profile mutation, Lake writes, SQLite
  writes, or silent learning.
- Add a decision trace for output-changing work.
- Keep every subagent write set disjoint from other active subagents.
- Do not revert Cursor, Codex, user, or other-agent edits. Work with them.

## Effort Scale

Use the actual tool effort setting where available:

- `low`: read-only scouting, inventory, status comparison, doc extraction.
- `medium`: bounded coding with existing patterns, synthetic fixtures, focused
  tests, and no architecture invention.
- `high`: cross-cutting contract work touching validators, schemas, and gates.
- `xhigh`: hard-kernel architecture/red-team only; no broad code edits unless a
  human explicitly approves the implementation scope.

## Packet A: Cursor-Low Phase 1 Scout

Effort: `low`

Mode: read-only.

Task:

- Identify Cursor-started Phase 1 files.
- Confirm whether the slice is the L&E replay-input preflight slice or the DAD
  asset-layer doc slice.
- Report dirty files, untracked files, tests already run, missing decision
  traces, and whether any real/private data appears.

Allowed reads:

- `git status --short --branch`
- `docs/fable/`
- `docs/decisions/`
- `examples/synthetic/labor-employment/`
- `src/lawfirm_os_intake/labor_employment_budget_outcome_replay_input_pack.py`
- `tests/test_labor_employment_budget_outcome_replay_input_pack.py`
- `apps/legal-intake-budget/src/fixtures/`

Forbidden:

- edits;
- cleanup;
- test artifact deletion;
- root aggregate repo writes.

## Packet B: GLM-Medium Phase 1 Replay-Input Finisher

Effort: `medium`

Mode: coding worker.

Write ownership:

- `src/lawfirm_os_intake/labor_employment_budget_outcome_replay_input_pack.py`
- `tests/test_labor_employment_budget_outcome_replay_input_pack.py`
- `examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json`
- `examples/synthetic/labor-employment/replay-inputs/class-collective-clean/`
- affected read-only UI demo fixture hashes under
  `apps/legal-intake-budget/src/fixtures/`
- one decision trace under `docs/decisions/`

Task:

- Finish the class/collective/PAGA actuals-variance replay input preflight
  slice.
- Keep the report preflight-only.
- Show next missing replay slots without running builders.
- Preserve no-write/no-submission/no-promotion flags.

Required checks:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py -q
python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q
python scripts\run_full_pytest.py tests\test_rust_fixture_manifest_scanner.py tests\test_rust_ui_bundle_source_hash.py tests\test_ui_demo_fixture_refresh.py tests\test_ui_foundation_contract.py -q
```

Do not:

- implement replay builders;
- mutate review outcomes;
- mark cases ready by weakening missing-input checks;
- create Lake or SQLite records.

## Packet C: Cursor-Low DAD Packet Port Scout

Effort: `low`

Mode: read-only.

Task:

- Compare DAD-layer handoff docs in the stale root intake copy against this
  canonical clone.
- Report exactly which docs are missing from this clone.
- Recommend a PR-0 doc-port file list, but do not edit.

Inputs:

- `..\..\LawFirm-os-intake\docs\ai-handoff\*DAD*`
- `..\..\LawFirm-os-intake\AI_TABLE_OF_CONTENTS.md`
- this clone's `AI_TABLE_OF_CONTENTS.md`
- this clone's `docs/ai-handoff/`

## Packet D: GLM-Medium DAD Packet Port

Effort: `medium`

Mode: coding worker.

Write ownership:

- this clone's `docs/ai-handoff/*DAD*`
- this clone's `AI_TABLE_OF_CONTENTS.md`
- optional decision trace under `docs/decisions/`

Task:

- Port the DAD-layer architecture handoff packet from the stale root intake copy
  into the canonical clone.
- Mark the packet as candidate handoff only.
- Preserve the Opus/Fable/Composer/GLM builder expectations.
- Do not add runtime behavior.

Required checks:

```powershell
$env:PYTHONPATH='src'
python scripts\validate_repo.py
```

Do not:

- copy private DAD catalog data, private paths, scores, ranks, or strategy notes;
- create a digital asset registry yet;
- change runtime code.

## Packet E: GLM-Medium PR-LL1A Calibration Preflight Scaffold

Effort: `medium`

Mode: coding worker after Phase 1 is clean.

Status note:

- This packet is a scaffold only. It is not full PR-CL1 completion and is not a
  stable landing zone for DP/zCDP until Packet E2 below is accepted.

Write ownership:

- new files under `src/lawfirm_os_intake/calibration/`
- new tests under `tests/test_calibration_leakage.py` or equivalent focused
  test file
- synthetic fixtures under an approved synthetic path
- `reviewed_learning_gate` integration only if the proof object already exists
  and can be validated without real data

Task:

- Implement only the aggregate/LOMO proof scaffold from the CAL-DP build packet.
- No DP noise mechanism yet.
- No real-data path.
- Fail closed when protected unit, K, dominance threshold, delta limit, or
  adversary model is missing.

Required Fable basis:

- `docs/fable/bounded-leakage-calibration-kernel.opus-draft.md`
- `docs/fable/codex-learning-leakage-build-packet.opus-draft.md`

Do not:

- choose epsilon/rho/K/dominance policy values as production defaults;
- import OpenDP or any OSS privacy dependency;
- publish calibrated values;
- weaken `reviewed_learning_gate`.

## Packet E2: High-Effort PR-CL1 Completion Slice

Effort: `high`

Mode: coding worker only after owner approval.

Dependency:

- Packet E / PR-LL1A scaffold exists and its focused tests are green.
- The active Phase 1 replay-input slice and Fable calibration/handoff slice are
  landed, snapshotted, or explicitly coordinated by the owner. A 2026-07-10
  readiness check found Stage 7 crosswalk/OCG evidence hardening committed at
  `e3eedc5`, but future workers must re-check current state before coding.
  This matters because `src/lawfirm_os_intake/reviewed_learning_gate.py` is
  currently dirty and is also in Packet E2's write set.

Write ownership:

- `src/lawfirm_os_intake/calibration/`
- `src/lawfirm_os_intake/reviewed_learning_gate.py`
- `tests/test_calibration_leakage.py`
- `tests/test_calibration_reviewed_learning_gate.py`
- synthetic fixtures under `examples/synthetic/calibration/`
- one decision trace under `docs/decisions/`

Task:

- Complete the aggregate/LOMO proof landing zone before DP/zCDP work.
- Keep the proof local, candidate-only, synthetic-only, and non-promoting.
- Preserve `aggregate_only|refused`; do not add a passable `dp` path yet.
- Make the aggregate proof stable, gate-consumable, and locally schema-visible
  without promoting a canonical schema or changing Substrate-owned surfaces.
- Keep dominance and LOMO failures refused with `*_dp_path_not_implemented`
  reasons until Packet E3.
- Ensure reviewed-learning reports surface calibration-gate review inputs and do
  not hide a passing calibration gate as ordinary `no_learning_candidates`.
- Bind proofs to estimator id, parameter, corpus version, screen version,
  policy values, protected-unit membership, input identifiers, data flags,
  contributions, and reconstruction metrics.
- Keep protected-unit K counting separate from matter-level LOMO semantics:
  matter/client/affiliate grouping is for privacy accounting, while LOMO remains
  leave-one-matter-out unless a later reviewed policy changes it.
- Label reconstruction metrics as scaffold/supplied synthetic evidence unless a
  computed adversary test is implemented in this same approved slice.
- Add tests proving digest sensitivity for matter/input identifiers, data flags,
  contributions, input-order determinism, protected-unit membership, and
  reconstruction metric changes.
- Add a local proof-visibility surface only if it remains repo-local and
  candidate-only; do not create or imply a canonical Substrate schema.

Known current gaps to close:

- `tests/test_calibration_reviewed_learning_gate.py` currently expects a
  calibration-gate-only accepted report to end as `no_learning_candidates`.
  Packet E2 must make calibration-gate review input visible without treating it
  as ordinary promoted learning.
- `calibration/leakage.py` currently computes LOMO over grouped protected-unit
  values when the protected unit is client or affiliate group. Packet E2 must
  separate matter-level LOMO from protected-unit K/group privacy accounting.
- `CalibrationReconstructionRecord.scaffold_only=True` exists, but the supplied
  synthetic scaffold basis needs a stronger tested/reportable label.

Required checks:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_reviewed_learning_gate.py -q
python scripts\validate_repo.py
```

Do not:

- add a DP mechanism, zCDP ledger, epsilon/rho/delta policy, or sealed-seed path;
- choose production K, dominance, LOMO, adversary-model, or protected-unit
  values;
- treat an `approval:` string as real production approval or reviewer-role
  verification;
- import OpenDP, Tumult, Google DP, diffprivlib, Opacus, or any OSS privacy
  dependency;
- publish calibrated values or mark calibration outputs as exact;
- touch Substrate, Orchestrator, Exception Lake, canonical schemas, registries,
  connectors, production config, UI readiness claims, or real-data fixtures.

Stop conditions:

- a fix requires deciding protected unit, K, dominance threshold, LOMO delta
  limit, adversary model, approval authority, seed custody, epsilon/rho/delta,
  reset policy, or real-data eligibility;
- the change would make a DP path passable;
- the change would promote local candidate proof fields to canonical authority.

## Packet E3: High-Effort PR-LL1B / PR-CL2 DP-zCDP Primitives

Effort: `high`

Mode: coding worker only after Packet E2 is accepted and owner approval is
given.

Write ownership:

- `src/lawfirm_os_intake/privacy/__init__.py`
- `src/lawfirm_os_intake/privacy/dp_mechanism.py`
- `src/lawfirm_os_intake/privacy/zcdp_ledger.py`
- narrowly scoped additions to `src/lawfirm_os_intake/calibration/leakage.py`
  only when needed to represent refused or candidate DP-path metadata
- `tests/test_calibration_dp_primitives.py`
- focused additions to `tests/test_calibration_leakage.py`
- synthetic fixtures under `examples/synthetic/calibration/`
- one decision trace under `docs/decisions/`

Task:

- Implement inert, homegrown Gaussian/zCDP primitives and synthetic-only tests.
- Keep DP releases non-production and non-promoting until human policy decisions
  and approval-record semantics exist.
- Prove group privacy accounting by largest protected group, not raw matter
  count alone.
- Refuse missing rho cap, missing delta, missing clip norm, budget exhaustion,
  utility-floor breach, seed material in payloads, real-data flags, and any
  attempt to present DP-noised values as exact.

Required fixtures:

- `calib-dp-epsilon-bound`
- `calib-group-privacy`
- `calib-utility-floor`
- `calib-budget-exhausted`
- negative fixtures for missing rho cap, missing delta, missing clip norm,
  seed material present, real-data flags, and unverified approval records

Required checks:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_calibration_dp_primitives.py -q
python scripts\validate_repo.py
```

Do not:

- choose production epsilon/rho/delta, K, dominance, utility-floor, or reset
  defaults;
- store or commit a DP seed; fixtures may carry only seed hashes;
- import OSS privacy dependencies before HD-8/license/security/privacy review;
- wire DP outputs as promotable without verified human approval records;
- mutate canon, cross-repo files, Lake/SQLite records, profiles, budgets,
  templates, carrier guidance, or UI readiness claims.

## Packet F: High-Effort Red-Team And Premortem

Effort: `high`

Mode: review worker.

Task:

- Review the active Phase 1 diff and any Packet D/E changes for:
  - governance drift;
  - hidden real/private data;
  - authority laundering;
  - weakened missing-input gates;
  - UI claims that overstate readiness;
  - fixtures treated as independent high-value assets without lineage.
- Report findings with file paths and exact test gaps.

Do not edit unless separately assigned a concrete fix.

## Packet G: XHigh Fable-Kernel Architect

Effort: `xhigh`

Mode: architecture/red-team only.

Task:

- Reconcile the hard kernels across:
  - `cross-matter-noninterference-kernel.opus-draft.md`
  - `bounded-leakage-calibration-kernel.opus-draft.md`
  - `learning-vs-leakage-hard-kernels.opus-draft.md`
  - `codex-learning-leakage-build-packet.opus-draft.md`
- Decide the safest next code PR after Phase 1:
  - PR-LL1A aggregate/LOMO scaffold;
  - PR-CL1 completion before DP/zCDP;
  - PR-LL1B DP/zCDP ledger only after PR-CL1 completion;
  - PR-QL1 LessonIR;
  - PR-IFC1 label lattice/residue scanner.
- Return file-scoped build instructions and blockers.

Do not:

- implement code;
- set human policy values;
- mark architecture complete without mapping blockers.
