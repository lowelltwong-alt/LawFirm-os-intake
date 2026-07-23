# Decision Trace — LW4 Improvement Capture + Hardening + Delivery (END)

Wave: LW4 of the Synthetic Learning-Loop marathon — the **final wave**. Branch:
`claude/lw4-delivery`, stacked on the LW3 branch. Candidate-only, synthetic-only,
deterministic.

## Situation

The program's capstone: track improvement across revisions, harden every new
serialized artifact, and package the deliverable with its boundaries and the
firm-data path. The premortem binds P5 (Goodhart-safe capture) and P7 (composition
seam).

## Decision

An additive `learning_capture` module with three deliverables:

1. **Improvement capture** — `build_learning_capture_report(entries)` walks the LW2
   capture ledger, computing a `compute_metric_delta` for each consecutive pair and
   aggregating into a `LearningCaptureReport`. Only single-axis differences are
   comparable; a regression becomes a typed
   `metric_regression_requires_review` review event listed in
   `regressions_requiring_review` — never auto-blocked, never collapsed into a
   single scalar (P5). `monotonic_improvement` means zero comparable regressions,
   recomputed fail-closed. This satisfies the acceptance criterion: the ledger
   shows a tracked metrics-delta across two generator revisions.
2. **Hostile-fixture sweep** — `run_hostile_fixture_sweep` builds each new
   serialized artifact from LW0–LW4 and tampers one reconciled field via a generic
   `_rejects_on_tamper(model_cls, payload, field_path, new_value)`; every artifact
   must fail closed on revalidation. `LearningLoopHostileSweepReport` rejects a
   report where any artifact survived, and `HostileSweepArtifactResult` cannot even
   be constructed for a survivor.
3. **Delivery packet** — `build_delivery_packet` enumerates the five waves'
   capabilities, the boundaries (candidate/synthetic-only; dollars deterministic;
   ML reference_class_only + shadow-only; work-plan never overwritten by
   reimbursement; no new rule language/repo), the firm-data recalibration lane
   (real actuals enter only through the §18 gate with human reconciliation), the
   open human gates, the **composition seam** (`case_pipeline` is canonical;
   `firm_checkpoint` is the 3-case packet — P7), and the **deferred full-XGBoost
   (LW5)** note. It fails closed if any of capabilities/boundaries/recalibration
   lane/deferred note/seam/hostile-artifacts is missing.

## Result

The hostile sweep proves all **9** new artifacts fail closed on tamper (pipeline
result, generated case, corpus manifest, eval report, metric delta, probe report,
target result, capture report, delivery packet). The capture report tracks a
single-axis (generator_version) delta across two revisions with typed
improvement/regression status. The delivery packet enumerates all five waves and
their boundaries.

## Non-decision

- No promotion; the ML challenger stays shadow-only; dollars stay deterministic.
- LW5 (full XGBoost) stays deferred behind its own gates.
- No change to any prior wave's logic (the sweep only reads + tampers copies).

## Authority impact

Local candidate work; three new candidate schemas (`learning-capture-report`,
`learning-loop-hostile-sweep-report`, `learning-loop-delivery-packet`). No
canonical/promoted contract change; no cross-repo write.

## Evidence

- `tests/test_learning_capture.py` — 8 tests (failing-test-first): capture tracks a
  delta across two generator revisions; regression typed for review (not
  auto-blocked); multi-axis `not_comparable`; capture fail-closed reconciliation;
  hostile sweep covers every new artifact and all fail closed; a survivor cannot be
  recorded; delivery packet complete + fail-closed; deferred-XGBoost + seam recorded.

## Alternatives rejected

- **Collapse metrics into one improvement score.** Rejected (P5): metrics stay
  separate; regressions are surfaced, not hidden.
- **Auto-block on any regression.** Rejected (P5): regressions are typed for human
  review, not silently gated.
- **Re-mini-compose the pipeline for the sweep.** Rejected (P7): the sweep drives
  `case_pipeline`, the canonical composition.

## Risks and rollback

- Risk: the hostile sweep is only as strong as each model's validator. Contained by
  the failing-test-first coverage (each artifact tests its own tamper) and the
  earlier waves' per-model fail-closed tests. Rollback is a single-branch revert.

## Validation

`validate_repo.py` passed; `export_schemas.py` idempotent (three new schemas); ruff
check + format clean; `run_full_pytest.py` full suite green; smoke demo green. No
UI change this wave.

## Human gate

LW4 human gate: **delivery review**. END of the program. The agent does not merge
its own PR and does not push `main`.

## DAD

Per-wave preflight/midflight(acks)/lesson/asset-use/postflight through the
daemon-era `asset-dir` pipeline.
