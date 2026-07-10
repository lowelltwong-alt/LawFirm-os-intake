# Calibration Proof Reviewed-Learning Gate

Date: 2026-07-09
Status: candidate-only implementation trace
Risk classification: medium, because this extends the reviewed-learning gate promotion surface while the surrounding worktree is dirty.

## Context

The Fable learning-vs-leakage build packet requires `reviewed_learning_gate` to refuse a calibrated parameter without a valid `CalibrationLeakageProof` plus `approval_id`. The active worktree also contains unrelated Stage 6, Phase 1, and UI changes, including dirty shared model and CLI surfaces.

## Decision

Add a narrow helper to `src/lawfirm_os_intake/reviewed_learning_gate.py` instead of changing shared `models.py` or `cli.py`.

The helper `validate_calibrated_parameter_gate()`:

- fails when no proof is supplied;
- validates the local `CalibrationLeakageProof` scaffold;
- binds the proof to the requested estimator, parameter, corpus version, and screen version;
- fails if the proof is refused, has refusal reasons, failed reconstruction, failed dominance/LOMO screens, missing deterministic rebuild evidence, or published calibrated values;
- fails without an explicit reviewed-form `approval_id`;
- rejects whitespace, synthetic-placeholder, and unqualified approval strings;
- returns a `ReviewedLearningGateCheck` only, and performs no mutation, promotion, Lake/SQLite write, external write, profile update, template update, budget update, or canonical contract change.

The gate is also wired into `build_reviewed_learning_gate_report()` through `calibrated_parameter_gate_requests`, so the reviewed-learning report itself can fail closed when a calibrated-parameter promotion review lacks a valid proof or approval id.

`check_calibration_leakage_proof_for_promotion()` remains as a convenience wrapper, but callers must supply the expected estimator, parameter, corpus version, and screen version. It does not self-bind to the proof's own identity.

High-effort red-team found and this slice fixed:

- side-helper-only integration that did not affect the report builder;
- proof self-binding through the wrapper;
- truthy/synthetic approval strings;
- non-validating constructed proof objects;
- forged or self-inconsistent proof dictionaries.

The test approval id uses a reviewed-form string for deterministic unit coverage only. It does not authorize real calibration or production promotion, and synthetic-placeholder approval strings are explicitly rejected.

## Validation

Focused validation target:

```powershell
$env:PYTHONPATH='src'; python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py -q
```

## Boundaries

No OpenDP or other privacy dependency was imported. No calibrated value publication path was added. CLI and shared model schema integration remain a later clean slice after the active Stage 6/Phase 1 dirty work is stabilized.
