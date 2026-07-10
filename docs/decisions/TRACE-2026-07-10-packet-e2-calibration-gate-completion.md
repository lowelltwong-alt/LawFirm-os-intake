# Packet E2 Calibration Gate Completion

Date: 2026-07-10
Status: candidate-only implementation trace
Risk classification: high, because this corrects privacy-facing calibration semantics and extends the single reviewed-learning chokepoint.
Owner authorization: the owner approved the four prerequisite snapshots and the narrow Packet E2 / PR-CL1 completion slice in the Codex task.

## Scope

Packet E2 completes the bounded aggregate-only calibration scaffold without adding differential privacy, zCDP accounting, production policy, external dependencies, real-data access, or promotion authority. The write set is limited to the local calibration package, reviewed_learning_gate.py, focused tests, the existing synthetic fixture family, and this trace.

## Decisions

- Keep aggregate_only or refused as the only path shape. Dominance or LOMO failures still refuse with a dp_path_not_implemented reason.
- Compute LOMO over matter-level contributions even when K, group size, and top-one leverage use client or affiliate-group protected-unit accounting.
- Publish methodology record calibration-aggregate-preflight-v0.2 in each proof. It names the inputs, arithmetic-mean aggregation, matter-level LOMO formula, protected-unit top-one formula, threshold source, normalization, deterministic ordering, uncertainty handling, and output range.
- Label reconstruction values as supplied_synthetic_scaffold_metrics. No adversary computation is claimed, and formal_privacy_guarantee_claimed remains false.
- Bind proof identity to request identity, estimator, parameter, corpus and screen versions, policy values, matter and protected-unit identifiers, prohibited-data flags, contributions, protected-unit aggregation, matter aggregation, and reconstruction values.
- Bind the complete versioned methodology descriptor into the same digest so a methodology change cannot silently retain an old proof identity.
- Canonicalize the complete matter payload before hashing so input order cannot change proof identity.
- Require the synthetic preflight request at the reviewed-learning gate, rebuild the proof, and compare its digest, proof ID, and full content other than generated_at. A self-consistent proof payload cannot pass independently of the request used by the gate.
- Require a separately supplied expected aggregate-input digest from the calling evidence context. The proof digest, rebuilt request digest, and expected digest must all match, so a matching forged proof/request pair cannot replace the anchored request unnoticed.
- Surface a calibration-only review input as candidate_learning_gate_ready with zero ordinary learning candidates and a visible calibration_gate_review_inputs_visible check.
- Treat approval-prefixed strings as deterministic candidate evidence identifiers only. The gate validates identifier shape but does not verify an approval registry, reviewer identity, attorney role, or reviewer role.

## Corrected Prior Statement

TRACE-2026-07-09-calibration-leakage-preflight-scaffold.md recorded that LOMO was computed over the declared protected unit. That was the initial scaffold behavior. Packet E2 corrects it: matter-level LOMO is now separate from protected-unit K and group-privacy accounting. The earlier trace remains historical evidence and is not deleted.

## Premortem And Rollback

- A grouped-client LOMO implementation could hide one matter's influence. Regression coverage compares client-group and matter-protected proofs and requires identical matter-level LOMO.
- A passing calibration-only gate could be mistaken for an ordinary learning candidate. The report keeps candidate_count equal to zero, adds an explicit visibility check, and performs no promotion or mutation.
- Supplied reconstruction numbers could be described as a computed privacy test. Typed proof fields require scaffold-only evidence and prohibit a formal privacy-guarantee claim.
- An approval-shaped string could be mistaken for verified attorney approval. Messages and required-gate labels explicitly state that only identifier shape was checked.
- Digest drift could produce order-dependent proof IDs. Reversed-input coverage requires byte-identical digests and proof IDs.
- A forged proof could replace its digest and derive a matching proof ID. The gate now rebuilds from the supplied synthetic preflight request and refuses digest, ID, or content mismatches.
- A forged request and matching forged proof could still agree with each other. The gate now requires an expected digest supplied independently by the calling evidence context and rejects any three-way mismatch.

Rollback criterion: revert this Packet E2 commit if any focused test permits non-synthetic data, changes the path set, hides calibration review input as no_learning_candidates, computes LOMO over protected-unit aggregates, or implies verified approval/privacy authority.

Current limitation: Packet E2 validates the shape and three-way consistency of the expected digest, request, and proof; it does not authenticate the calling evidence context, production corpus, approval registry, or cross-repo evidence authority. The expected digest must come from a separately governed artifact/evidence context in any future integration. Production trust remains blocked behind future owner-controlled contract pins and promotion review.

## Validation

    $env:PYTHONPATH='src'
    python scripts\run_full_pytest.py tests\test_calibration_leakage.py tests\test_calibration_reviewed_learning_gate.py tests\test_reviewed_learning_gate.py -q
    # 46 passed

Repository validation and final diff checks are required before the Packet E2 checkpoint is reported.

Final baseline on the exact Packet E2 implementation:

    $env:PYTHONPATH='src'
    python scripts\run_validation_suite.py
    # repository validation passed
    # exported 436 schemas
    # ruff check passed
    # ruff format --check: 328 files already formatted
    # full pytest: 839 passed
    # smoke demo: demo_completed
    # final_boundary: blocked_pending_conflicts_and_engagement
    # final repository validation passed

## Human Decisions Still Open

HD-1 through HD-11 remain open. In particular, this slice does not choose a protected unit, K, dominance threshold, LOMO limit, adversary model, privacy budget, reset policy, seed custody, real-data approval, external privacy library, or canonical promotion route.
