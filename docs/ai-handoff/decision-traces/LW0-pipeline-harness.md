# Decision Trace — LW0 End-to-End Deterministic Pipeline Harness

Wave: LW0 of the Synthetic Learning-Loop marathon
(`docs/ai-handoff/SYNTHETIC_LEARNING_LOOP_MARATHON.md`). Branch:
`claude/lw0-pipeline-harness`, stacked on `main`. Candidate-only, synthetic-only,
deterministic. **Dollars always deterministic from governed rates.**

## Situation

CW0–CW7 built the intake → route → drivers → sized budget pieces as separate
modules. LW0 composes them into one canonical end-to-end chain with a single
typed result reconciling every stage fail-closed, so LW1–LW4 (scaled generator,
batch eval, ML shadow probe, delivery) all drive one composition instead of
re-mini-composing (the seam `firm_checkpoint._case` already hinted at — P7).

## Pre-execution red-team amendment (binding)

Before writing code, the plan was amended with premortem findings P1–P12
(committed to the plan of record). LW0 is bound by **P6** (every joint typed;
a `None` stage never serializes as success), **P7** (single canonical
composition; `firm_checkpoint` stays the 3-case packet), **P8** (confirmation is
generator ground truth, never human review), and **P11** (exact integer minor
units; stage totals reconcile exactly).

## Decision

An additive `case_pipeline` module — `run_synthetic_case_pipeline(spec) ->
SyntheticCasePipelineResult` — composing the **real** existing stages:

1. **Route** — `run_preflight` (canonical intake) then the deterministic,
   abstain-aware `route_decision` over `packet.matter_family_candidates`. Typed
   `routed | abstained`; records whether the routed family matched ground truth.
   Routing does not gate the budget — deterministic rules + human confirmation are
   the authority; here confirmation is generator truth.
2. **Confirm (generator ground truth, P8)** — binds the synthetic confirmation
   template to the packet and records `confirmation_source="generator_ground_truth"`,
   `is_human_review=False`; fail-closed unless the confirmed family equals the
   spec ground-truth family. It is never mistakable for human review.
3. **Budget + carrier projection** — `run_budget` produces the deterministic
   dollars-from-rates budget and the carrier-compliant projection. Typed
   `priced | blocked_no_price` and `projected | blocked_no_pack` (an unselected
   pack is a typed block, never a default-carrier fallback). The immutable
   work-plan total is recomputed in exact minor units; the guideline-adjusted
   **reimbursement** is a SEPARATE field, never overwriting the work-plan total.
4. **Case sizing** — `build_case_sizing_report` when a proportionality band is
   declared for the case type; a missing band is a typed `blocked_no_band`
   (fail-closed, never a silent pass — P4/P6).
5. **Firm-Excel export** — `firm_excel_export_from_budget` (extract-refactor of
   the existing projection-report exporter so it maps an in-memory budget). The
   export total must equal the deterministic work-plan total in exact minor units.

`SyntheticCasePipelineResult` reconciles all of this in one `model_validator`:
typed joints, cross-stage minor-unit money reconciliation, `completed` only when
every joint succeeded (otherwise typed `blocked` with recorded reasons), and a
content digest over the deterministic stage outputs (not run ids/timestamps).

## Result

On the medmal synthetic case the chain **completes**: routed →
`medical_malpractice_defense` (matched), confirmed from ground truth, priced
(work-plan **$140,930.00** deterministic), projected (reimbursement
**$122,531.50**, kept distinct from the work plan), sized (within band), exported
(export total == work-plan total, exactly). A case with an undeclared case type
blocks fail-closed at sizing and the overall status is typed `blocked`.

## Non-decision

- No new rule language; no change to `classify_matter`, `run_budget`,
  `build_budget_proposal`, `guidelines`, or `case_sizing`.
- No ML; dollars are 100% deterministic from governed rates.
- `firm_checkpoint` unchanged — it remains the 3-case packet; `case_pipeline` is
  the single canonical composition it and later waves build on.

## Authority impact

Local candidate work; two new candidate schemas
(`synthetic-case-pipeline-spec`, `synthetic-case-pipeline-result`) and one added
synthetic proportionality band (`medical_malpractice`). No canonical/promoted
contract change; no cross-repo write.

## Evidence

- `tests/test_case_pipeline.py` — 9 tests (failing-test-first): end-to-end
  completion; generator-ground-truth confirmation provenance (not human review);
  cross-run determinism (P9); export↔work-plan minor-unit reconciliation (P11);
  reimbursement kept separate from work plan; missing-band fail-closed block
  (P4/P6); tampered export total rejected; tampered status rejected; a `routed`
  stage with a `None` family cannot serialize.
- Two exported schemas; full validation suite green.

## Alternatives rejected

- **Re-mini-compose per wave (like `firm_checkpoint._case`).** Rejected (P7): one
  canonical composition, one reconciled contract.
- **Reconcile the export against `total_proposed_budget`.** Rejected: recompute
  the work-plan total from budget lines with the exporter's own per-line rounding
  so the export↔work-plan check is exact and fail-closed, not float-fragile (P11).
- **Let a missing band pass silently or crash.** Rejected: typed `blocked_no_band`
  (P4/P6).

## Risks and rollback

- Risk: the pipeline currently drives from the existing synthetic inbound +
  confirmation fixtures. Contained: LW1's scaled generator extends the spec source
  without changing the reconciliation contract. Rollback is a single-branch revert;
  the module is additive.

## Validation

`validate_repo.py` passed; `export_schemas.py` idempotent (two new schemas); ruff
check + format clean; `run_full_pytest.py` full suite green; smoke demo green. No
UI change this wave (npm build + smoke:browser not required).

## Human gates

LW0 human gate: **pipeline-contract review**. Opened by the agent; it does not
merge its own PR and does not push `main`.

## DAD

Per-wave preflight/midflight/lesson/postflight through the canonical daemon-era
`asset-dir` pipeline. Preflight session `dad:session:01fc1c5d-7141-4046-be70-6955689a8a9d`.
