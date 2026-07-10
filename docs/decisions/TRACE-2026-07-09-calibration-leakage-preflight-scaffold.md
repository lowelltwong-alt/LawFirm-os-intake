# Calibration Leakage Preflight Scaffold

Date: 2026-07-09
Status: candidate-only implementation trace
Risk classification: medium, because this creates a future learning-gate proof surface; the slice remains synthetic-only and publishes no calibrated values.

## Context

Packet E / PR-LL1A asked for the aggregate/LOMO proof scaffold from the bounded-leakage calibration kernel, without a DP noise mechanism and without using real, protected, client, matter, carrier-private, or privileged data. The active worktree already contains dirty Phase 1 replay-input, UI fixture, and shared-model changes, so this slice keeps its write set disjoint.

## Decision

Add local calibration proof/request types under `src/lawfirm_os_intake/calibration/` instead of editing the shared `models.py` surface. The scaffold:

- accepts only `synthetic_candidate` and `candidate_only` requests;
- rejects attempts to publish calibrated values;
- validates synthetic fixture inputs only;
- requires protected unit, minimum K, dominance threshold, LOMO delta limit, and adversary model;
- refuses missing or failed synthetic reconstruction-test metrics;
- computes K, top-one dominance, and LOMO over the declared protected unit, not raw rows only;
- emits an aggregate-only candidate proof only when protected-unit K, dominance, reconstruction, and LOMO screens pass;
- binds the proof digest to request metadata, policy values, matter identifiers, protected-unit identifiers, data flags, contributions, and reconstruction metrics;
- refuses dominance or LOMO failures with `*_dp_path_not_implemented` reasons because this packet intentionally does not add a DP mechanism.

The test fixture policy numbers are labeled as synthetic policy placeholders and are not production privacy defaults.

## Gate Integration

Reviewed-learning-gate integration was intentionally deferred. The current gate models live in `src/lawfirm_os_intake/models.py`, which is dirty and explicitly outside this packet's safe write set. Adding `CalibrationLeakageProof` to that gate would require shared model and gate changes, so this slice exposes `build_calibration_leakage_proof()` as a proof artifact function only.

Future gate work should extend the existing reviewed-learning gate in a clean slice to require a valid `CalibrationLeakageProof` plus human approval before any calibrated parameter can be promoted.

## Validation

Focused validation target:

```powershell
$env:PYTHONPATH='src'; python scripts\run_full_pytest.py tests\test_calibration_leakage.py -q
```

High-effort red-team found and the implementation fixed two blocking issues:

- client or affiliate-group protected units could previously pass K by counting multiple matters from one protected group;
- the proof digest previously omitted policy and protected-unit membership inputs.

Regression tests now cover protected-unit K failure, digest changes for policy and grouping changes, all prohibited data flags, empty identifiers, missing policy inputs, missing reconstruction metrics, dominance/LOMO refusal, and no calibrated-value publication.

## Boundaries

No OpenDP or other privacy dependency was imported. No calibrated values are published. No profile mutation, Lake/SQLite write, network call, connector, or production policy default is introduced.
