# Claude Handoff: Workbench Trust Audit And L&E Replay Expansion

Date: 2026-07-21
Target repository: `lowelltwong-alt/LawFirm-os-intake`
Target branch after merge: create a fresh `claude/` branch from current remote `main`

## Objective

Independently verify the completed serialized-workbench trust-hardening slice, then build the next bounded synthetic-data slice. Do not weaken fail-closed behavior to make fixtures pass. Do not ingest real matters, real rates, carrier payloads, or public-case payload text.

## Required Front Door

Before editing, read:

1. `AGENTS.md`
2. `AI_WORK_START_HERE.md`
3. `skill-agent-manifest.json`
4. `docs/decisions/TRACE-2026-07-18-serialized-workbench-trust-hardening.md`
5. `docs/roadmap.md`, especially sections 19 and 20
6. `examples/synthetic/labor-employment/labor-employment-budget-outcome-replay-input-pack.json`
7. `examples/synthetic/labor-employment/labor-employment-budget-learning-fixtures.json`

Use a fresh branch/worktree from remote `main`. Assume other agents may be working concurrently. Do not edit DAD directly; use the governed DAD front door if available.

## Stage A: Independent Trust Audit

Review, do not initially edit:

- `src/lawfirm_os_intake/models.py`
- `src/lawfirm_os_intake/synthetic_actuals_workbench.py`
- `apps/legal-intake-budget/src/data-contract.ts`
- `apps/legal-intake-budget/src/types.ts`
- `apps/legal-intake-budget/scripts/ui-browser-smoke.mjs`
- `tests/test_synthetic_workbench_serialized_coherence.py`
- `tests/test_synthetic_workbench_source_integrity.py`

Attempt fresh mutations, not copies of existing assertions:

- alter a derived rate summary while preserving rows;
- swap configuration effect buckets while preserving the total count;
- alter rejection/appeal case money while preserving report headlines;
- corrupt any nested `*_sha256` field;
- mutate actual fees while preserving row and report totals;
- mutate one actual alternate view while preserving the other;
- mutate a guideline line, subtotal, and total coherently while preserving its reported delta;
- insert null pricing into a `priced` projection;
- mutate a source between capture and parse.

Expected result: every ready artifact rejects the inconsistency; intentionally blocked actuals artifacts remain serializable with explicit failed checks. Report findings first with file/line evidence. Do not rubber-stamp based only on existing green tests.

## Stage B: Build The Next Synthetic Replay Slice

Only after Stage A is clean or its defects are fixed, add deterministic replay coverage for:

1. retaliation / wrongful termination;
2. restrictive covenant / trade secret;
3. administrative exhaustion;
4. one missing-attachment case;
5. one non-ADA adversarial case.

Then add one materially different proposal, preferably wage/hour or class/collective, to budget-input and actuals test coverage. Keep EPLI as the carrier rejection/appeal chain.

For each new case require:

- `data_origin=synthetic`;
- generator version and deterministic seed;
- source refs, segment refs, offsets, and hashes where applicable;
- explicit unknowns and blocked gates;
- expected status and reviewed synthetic gold;
- at least one counterfactual or metamorphic assertion;
- at least one prohibited-transition assertion;
- holdout content excluded from model-visible prompt assembly;
- no connector, Lake, SQLite, submission, matter-opening, conflict-conclusion, or silent-learning write.

## Acceptance Criteria

- All eight declared L&E families have executable replay evidence.
- At least one missing-attachment case reaches replay and blocks or widens output for the stated reason.
- At least two distinct L&E families have adversarial replay cases.
- Budget input and actuals are exercised against at least two materially different proposal families.
- Fixtures are not accepted merely because they match their own generated output.
- The UI remains read-only and clearly candidate-only/synthetic-only.
- Existing CLI commands and candidate-only authority boundaries remain stable.

## Required Validation

Run with the repository's long ceiling:

```powershell
python scripts/validate_repo.py
python scripts/export_schemas.py
python -m ruff check src tests scripts
python -m ruff format --check src tests scripts
python scripts/run_full_pytest.py -q
npm run build --prefix apps/legal-intake-budget
npm run smoke:browser --prefix apps/legal-intake-budget
bash scripts/smoke_demo.sh
```

If Windows temp ACLs interfere, use an authorized unsandboxed run or Linux CI; do not weaken tests or bypass `scripts/run_full_pytest.py`.

## Deliverables

- PR-sized code and fixture changes.
- Decision trace with before/after coverage matrix.
- Exact test outputs and any environmental limitations.
- Red-team findings, including rejected approaches.
- A Codex handoff listing remaining work and code hints.
- A governed DAD candidate lesson/asset packet containing observable evidence, assumptions, applicability, non-applicability, danger if misapplied, and no hidden chain-of-thought.

## XGBoost Boundary

Do not train or tune XGBoost from this synthetic corpus. Synthetic fixtures may test feature-shape and pipeline behavior, but they cannot establish predictive calibration. A later governed slice may propose a versioned feature/target contract for phase cost, variance, or rejection risk, with temporal splits, leakage checks, prediction intervals, SHAP review, and a deterministic baseline challenger. Training waits for governed reviewed historical outcomes.

Stop after this slice. Do not modify production connectors, canonical Semantic Substrate contracts, Orchestrator persistence, real-rate calibration, Rust replacement, or predictive-model training.
