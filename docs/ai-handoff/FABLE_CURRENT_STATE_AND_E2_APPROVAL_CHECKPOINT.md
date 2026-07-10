# Fable Current State And Packet E2 Approval Checkpoint

Status: candidate handoff
Date: 2026-07-10
Scope: LawFirm OS intake canonical clone

This file is a current-state ledger for the Fable learning-vs-leakage buildout.
It is not implementation approval, product canon, or a substitute for DAD
preflight/postflight. It exists so future agents can see what is actually
implemented before starting the next slice.

For exact remaining dirty-group landing boundaries, see
`docs/ai-handoff/FABLE_SNAPSHOT_LANDING_PLAN_2026-07-10.md`.
For executable review packets, staging templates, and PR checklist language,
see `docs/ai-handoff/FABLE_SNAPSHOT_REVIEW_PACKETS_2026-07-10.md`.

## Current Evidence

Green commands most recently run from this clone:

```powershell
$env:PYTHONPATH='src'
python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_reviewed_learning_gate.py -q
# 32 passed

python scripts\run_full_pytest.py tests\test_labor_employment_budget_outcome_replay_input_pack.py tests\test_labor_employment_budget_outcome_replay_confidence_status.py -q
# 27 passed

python scripts\run_full_pytest.py tests\test_rust_fixture_manifest_scanner.py tests\test_rust_ui_bundle_source_hash.py tests\test_ui_demo_fixture_refresh.py tests\test_ui_foundation_contract.py -q
# 45 passed

python scripts\validate_repo.py
# repository validation passed
```

`git diff --check` exited 0 with only an existing CRLF warning for
`apps/legal-intake-budget/src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json`.

Fresh readiness validation on 2026-07-10:

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
# repository validation passed
# exported 436 schemas
# ruff check passed
# ruff format --check passed after formatting four active dirty files
# full pytest: 825 passed
# smoke demo completed with final_boundary=blocked_pending_conflicts_and_engagement
# final repository validation passed
```

Read-only DAD prerequisite check on 2026-07-10 from the configured
`<dad-repo-root>`:

```powershell
$env:PYTHONPATH='<dad-repo-root>\src'
python -B -m pytest -p no:cacheprovider `
  tests/test_mail_center.py::test_cli_mail_compose_payload_file_round_trips_structured_json_with_bom_and_equals `
  tests/test_mail_center.py::test_cli_mail_compose_rejects_raw_json_in_key_value_payload_mode `
  tests/test_mail_center.py::test_cli_mail_compose_payload_json_path_round_trips_and_rejects_raw_json_payload `
  tests/test_mail_center.py::test_cli_mail_compose_lesson_payload_schema_is_warning_only `
  tests/test_mail_center.py::test_supersedes_is_envelope_field_and_renders_route_and_digest_chains -q
# 5 passed

python -m digital_asset_directory.cli roadmap check --no-update
# exit 0

python -m digital_asset_directory.cli validate
# valid=false; stale candidate-path/hash/graph evidence in current dirty DAD worktree
```

The DAD repo branch inspected was `codex/transport-operational-current`. It had
unrelated dirty transport/coverage work at inspection time, so this ledger treats
DADM1-DADM3 as file-and-focused-test evidenced, not as a fresh full-repo DAD
validation checkpoint.

## Active Worktree Caveat

Read-only subagent audits on 2026-07-10 used:

- `low` effort Cursor/Composer scout for Phase 1 and Stage 7 worktree status.
- `medium` effort GLM-style coding-readiness auditor for Packet E2 / PR-CL1.

Initial subagent audits saw Stage 7 and the DAD-layer doc port as dirty. Later
current-state checks showed current branch `feat/port-dad-layer-docs` at
`ab7255c`, matching `origin/feat/port-dad-layer-docs`. The DAD-layer doc port
ancestry includes `b0f3f20` (`Port DAD layer handoff docs`), `809b9e8`
(`Update governance mirror for DAD handoff docs`), and `ab7255c`
(`Normalize ported handoff doc EOFs`). The parent Stage 7 commit `e3eedc5`
matches `origin/feat/stage-7-crosswalk-ocg-evidence-hardening`. Stage 7 and the
DAD-layer architecture handoff docs are therefore tracked in HEAD at this
checkpoint.

The worktree still contains active dirty slices beyond the Stage 7 commit:

- Phase 1 L&E replay-input preflight work owns
  `src/lawfirm_os_intake/labor_employment_budget_outcome_replay_input_pack.py`,
  `tests/test_labor_employment_budget_outcome_replay_input_pack.py`,
  `examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json`,
  `examples/synthetic/labor-employment/replay-inputs/class-collective-clean/`,
  affected UI fixtures, and
  `docs/decisions/TRACE-2026-07-09-le-class-collective-replay-input-preflight-gap-matrix.md`.
- Stage 7 crosswalk/OCG evidence hardening is in committed checkpoint
  `e3eedc5` and owns
  `src/lawfirm_os_intake/crosswalks.py`,
  `src/lawfirm_os_intake/review_ui_crosswalk_ocg_evidence.py`,
  crosswalk/UI schemas, React review UI files, crosswalk tests, and
  `docs/decisions/TRACE-2026-07-09-stage7-crosswalk-ocg-evidence-hardening.md`.
- DAD-layer architecture handoff docs are in committed checkpoint `b0f3f20` and
  own `AI_TABLE_OF_CONTENTS.md`,
  `docs/ai-handoff/FABLE_MASTER_ARCHITECT_DAD_LAYER_PROMPT.md`,
  `docs/ai-handoff/HARD_KERNELS_FOR_FABLE_DAD_LAYER.md`,
  `docs/ai-handoff/LAW_FIRM_OS_DAD_LAYER_ARCHITECTURE_PLAN.md`, and
  `docs/ai-handoff/OPUS_4_8_DAD_LAYER_INTAKE_PROMPT.md`.
- Fable calibration/handoff work owns `src/lawfirm_os_intake/calibration/`,
  `examples/synthetic/calibration/`, focused calibration tests, Fable handoff
  docs, Fable kernel drafts, and calibration/DAD-port decision traces.
- Shared dirty surfaces now include `src/lawfirm_os_intake/reviewed_learning_gate.py`
  and `apps/legal-intake-budget/src/fixtures/demo-labor-employment-budget-outcome-replay-confidence-status-report.json`.

Do not start Packet E2 coding against shared dirty surfaces until the remaining
Phase 1 and Fable calibration/handoff slices are landed, snapshotted, or
explicitly coordinated by the owner. In particular,
`src/lawfirm_os_intake/reviewed_learning_gate.py` is dirty now and part of
Packet E2's write surface.

## Requirement Status

| Fable item | Current status | Evidence | Next action |
|---|---|---|---|
| DAD DADM1-DADM3 | Evidenced in DAD repo; not revalidated full-clean | DAD `lesson-payload.schema.json` warning-only/extensible schema, `registry/schema-registry.json`, CLI `--payload-json`/raw-JSON guidance, `supersedes` envelope behavior, focused DAD tests above | Treat DAD prerequisite as present for planning; require clean DAD repo-wide validation before relying on it as a fresh promotion checkpoint |
| PR-LL1 / CAL-DP | Partial | `src/lawfirm_os_intake/calibration/`, `tests/test_calibration_leakage.py`, `tests/test_calibration_reviewed_learning_gate.py`, `src/lawfirm_os_intake/reviewed_learning_gate.py` | Packet E2 / PR-CL1 completion |
| PR-LL2 / QRD | Not started | Draft kernels only | Build LessonIR/disclosure proof after prerequisites |
| PR-LL3 / IFC | Not started | Draft kernels only | Build label lattice/residue scanner after QRD/DAD schema |
| PR-LL4 / CHW | Not started | Draft kernels only | Needs counsel-owned adversity/CoI classes or synthetic stubs |
| PR-LL5 / EVID | Not started | Draft kernels only | Needs evidence record/authenticate slice and owner review |
| PR-LL6 / UNLRN | Not started | Draft kernels only | Depends CAL-DP and human-residue policy |
| PR-LL7 / simulators | Not started here | Cross-repo targets named only | Consume CAL-DP behind gates after intake primitive exists |
| PR-LL8 / Substrate | Not started | Promotion target named only | Candidate promotion package only after owning repo review |
| Exceptions Lake/Talent docs | Partial planning only | DAD-layer architecture docs | Owning repo docs/gates still needed |

## What Is Built

- Synthetic-only aggregate/LOMO calibration preflight scaffold.
- Candidate `CalibrationLeakageProof` object for `aggregate_only` or `refused`.
- Fail-closed reviewed-learning-gate helper for calibrated-parameter review
  inputs.
- Decision traces for the calibration scaffold, calibration gate, DAD doc port,
  and L&E replay-input preflight.
- Agent-agnostic execution packets with explicit effort levels.

## What Is Not Built

- DP mechanism, zCDP ledger, epsilon/rho/delta accounting, sealed-seed handling,
  utility floor, or DP proof path.
- Full PR-CL1 landing-zone completion.
- QRD, IFC, CHW, EVID, UNLRN, simulator consumption, or Substrate promotion.
- Verified approval-record registry or attorney/reviewer-role lookup. Current
  `approval:` strings are deterministic test evidence only, not real approval.

## Packet E2 Approval Boundary

Next implementation slice:

```text
Packet E2: PR-CL1 Completion Slice
Effort: high
Mode: coding worker only after owner approval
```

Packet E2 may touch:

- `src/lawfirm_os_intake/calibration/`
- `src/lawfirm_os_intake/reviewed_learning_gate.py`
- `tests/test_calibration_leakage.py`
- `tests/test_calibration_reviewed_learning_gate.py`
- synthetic fixtures under `examples/synthetic/calibration/`
- one decision trace under `docs/decisions/`

Packet E2 must not:

- add a DP path or zCDP ledger;
- choose production K, dominance, LOMO, adversary-model, protected-unit,
  epsilon/rho/delta, reset-policy, seed-custody, or real-data values;
- treat an `approval:` string as verified production approval;
- import privacy dependencies;
- publish calibrated values;
- touch Substrate, Orchestrator, Exception Lake, canonical schemas, registries,
  connectors, UI readiness claims, production config, or real-data fixtures.

## Packet E2 Acceptance Evidence

Packet E2 is not complete until current evidence proves:

- aggregate proof remains candidate-only and synthetic-only;
- `aggregate_only|refused` remains the only passable/nonpassable path shape;
- dominance and LOMO failures remain refused with
  `*_dp_path_not_implemented`;
- proof identity binds estimator, parameter, corpus version, screen version,
  policy values, protected-unit membership, input ids, data flags,
  contributions, and reconstruction metrics;
- protected-unit K counting is distinct from matter-level LOMO semantics;
- reconstruction metrics are labeled as supplied synthetic scaffold evidence
  unless a computed adversary test is implemented;
- reviewed-learning reports do not hide calibration-gate review input as
  ordinary `no_learning_candidates`;
- local proof visibility is available without promoting a canonical Substrate
  schema or touching global schema authority;
- focused calibration and reviewed-learning-gate tests pass through
  `scripts/run_full_pytest.py`;
- `python scripts\validate_repo.py` passes.

Known E2 gaps from the medium-effort GLM readiness audit:

- Current tests still expect a passing calibration-gate-only report to end as
  `no_learning_candidates`; E2 must surface calibration-gate review input
  distinctly without pretending it is an ordinary learning candidate.
- Current LOMO computation is over grouped protected-unit values when the
  protected unit is client or affiliate group. E2 must keep matter-level LOMO
  separate from protected-unit K/group privacy accounting unless a later
  reviewed policy changes that.
- Current proof digest coverage is stronger than the tests prove. E2 should add
  tests for matter/input identifiers, data flags, contributions, input-order
  determinism, and reconstruction metric changes.
- Current reconstruction record has `scaffold_only=True`, but E2 should make
  the supplied-synthetic-scaffold basis explicit enough for tests and reports.
- Fable draft PR-CL1 mentions separate estimator, LOMO, and reconstruction-test
  modules. The current collapsed `calibration/leakage.py` shape is acceptable
  for E2 only if the slice stays narrow and avoids architecture sprawl.

## Blockers To Surface, Not Decide

- HD-1 epsilon/rho cap and reset policy.
- HD-2 protected unit.
- HD-3 qualitative adversary model and support thresholds.
- HD-4 adversity/CoI classes.
- HD-5 evidentiary attestation standard.
- HD-6 human residue and retention policy.
- HD-7 real-data pilot approvals.
- HD-8 OSS DP library review.
- HD-9 EvidencePacket v2 graduation.
- HD-10 talent MCP boundary and vendor terms.
- HD-11 Mock Trial calibration un-weld decision.

Until those decisions are made by the correct owners, all learning-vs-leakage
components remain synthetic-only, candidate-only, and fail-closed on real data.
