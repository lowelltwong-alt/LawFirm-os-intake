# Converged Plan Of Record — After Independent (Codex) Review

Status: **plan of record.** Supersedes, for v1, the marathon program
(`MARATHON_PROGRAM_waves_and_prompts.md`), the Guideline Engine v2 scope
(roadmap §22 as written), the public-gold *training* thesis for v1
(`PUBLIC_GOLD_STRATEGY_legal_budgets.md` → demoted to a later research lane), and
the new World Builder repo (`WORLD_BUILDER_BINDING_RECOMMENDATION.md` → deferred).
Those docs are retained as history, marked superseded.

Two independent reviews converged: Opus 4.8 self-critique
(`CONVERGENCE_REVIEW_redteam_premortem.md`) + Codex independent review
(handoff `dad:handoff:e88af27e-…`). Where they differed, Codex's more grounded,
code-verified findings win. Verification of Codex's decisive claims was
re-run in this repo and confirmed (OCG IR authority, sibling simulator, unsafe
applicability, non-existent factory modules).

## Decision

**Go:** one thin deterministic intake→budget→guideline-adjusted-reimbursement
vertical on the *existing* engine + HTML UI, for a firm disposition checkpoint.
**Stop (v1):** public-gold budget/rejection ML; a new Intake "GCS v2"; a new World
Builder repo. **Defer:** dozens of packs, generic overlay algebra, predictive
variance/rejection/appeal models. **Preserve:** synthetic-only, candidate status,
immutable baseline budgets, human gates, §18/§21 boundaries, DAD WIP=1, DAD
contract/factory split.

## Verified findings that forced the pivot (re-checked in this repo)
1. Intake already consumes a **Semantic-Substrate-owned OCG rule IR** and is
   prohibited from authoring canonical OCG rule IDs
   (`src/lawfirm_os_intake/ocg_rule_ir.py`: `SUBSTRATE_OWNER`,
   `OCG_IR_PROHIBITED_ACTIONS` = "do_not_author_canonical_ocg_rule_ids_in_intake";
   `OCGSharedRuleIRRule` in models.py). A new Intake GCS would violate this.
2. A sibling **`billing-guideline-simulator`** repo already has a rule IR +
   compiler (`src/billing_guideline_sim/rules/ir.py`, `compile.py`, `diff.py`).
   A new GCS ⇒ three drifting rule languages.
3. **Unsafe applicability**: `guidelines.py:_carrier_rules` returns `None` on a
   missing/wrong carrier — silent fail-open. Same class as the F1–F6 workbench
   trust findings.
4. My PLAN §1 "what already exists" listed `synthetic_factory/research/campaign`
   modules that **do not exist in the real repo** (they live in the stale
   top-level folder). World Builder is greenfield.

## The converged architecture (Codex's, adopted)
Contractual modularity **inside one repo and one active family** (not one repo per
component). The **budget core does not depend on the guideline compiler**; the
outer workflow composes two independent results. Local candidate schemas pending
Substrate review: `BudgetSnapshot` (with stable `line_id`, content hash,
prediction_as_of), `GuidelinePackEnvelopeCandidate` (pack_id/revision/hash,
applicability, effective dates, supersedes), `PackSelectionDecision`
(status = selected | blocked_missing_context | blocked_overlap | no_applicable_pack),
`GuidelineRuleCandidate`, `RuleEvaluation`
(outcome = passed | triggered | not_applicable | unsupported | not_evaluable | conflict),
`AdjustmentLedgerEntry` (ordered, non-commutative-safe attribution),
`ProjectionReport` (work_plan_total vs guideline_adjusted_reimbursement vs
unreimbursed_exposure). Exact decimal money / integer minor units — no float
strings for cross-engine conformance. First operator set only: state×role rate
cap, aggregate task×role hour cap, existing expense cap/disallowance, existing
preapproval, contingency allowed/denied. Declared attribution order: pack/effective
selection → task-hour caps → rate caps → expense caps → contingency → preapproval /
unsupported findings.

## Sequence of record
1. **Contract convergence**: freeze ML / World Builder / sibling simulator /
   pack-scale as inactive; single active family = guideline-adjusted-budget-pilot;
   register the sibling simulator as a read-only challenger only.
2. **Thin synthetic vertical**: repair the existing Guideline Projection
   Workbench — pack selection (typed blocked, no default-carrier fallback),
   stable line IDs, version+hash binding, one task-hour rule, ordered adjustment
   ledger, corrected output language (work-plan vs reimbursement vs exposure).
   Fold in the still-open trust fixes F5/F6 as part of the fail-closed pass.
3. **No-data firm checkpoint**: firm ranks carriers/programs and dispositions
   three synthetic cases ("useful" / "wrong workflow" / "missing rule"). Needs no
   firm rates or budgets. If nobody will review three synthetic cases, stop — the
   hypothesis is not validated.
4. **Contract reconciliation**: propose a candidate executable extension to the
   Substrate-owned OCG IR (local adapter + fixtures meanwhile; no parallel canon);
   run cross-engine conformance vs the sibling simulator if still useful.
5. **Production data gate**: manually encode one real firm schedule + one real
   carrier/program pack in shadow mode with human reconciliation. No silent
   ingestion or learning.
6. **Outcome capture**: record initial budget version, allowed hours/costs,
   censoring, pack version, line dispositions, reasons, appeals.
7. **ML activation (challenger, later)**: first predict phase/task *allowed hours*
   as a challenger; dollars stay deterministic from governed rates. Variance
   later; rejection only after line dispositions exist; appeal recovery last.
   Public sources (UST Appendix B, PRISM standards, LoPucki data) support schemas,
   rule-taxonomy research, extraction eval, and procedural priors — never
   relabeled as insurance-defense calibration; all ingestion via §18 + the
   production gate.

## Premortem carried forward (Codex's three, adopted)
1. Three rule languages become three incompatible truths (mitigated by step 1+4).
2. The engine is mathematically correct but operationally wrong — wrong
   carrier/program/addendum/effective selection, hidden (mitigated by step 2
   typed-blocked applicability).
3. The firm mistakes reimbursement limits for an adequate litigation plan
   (mitigated by preserving work_plan_total separately from reimbursement).

## Additions (2026-07-21, owner-approved)
- **Layered composition decision**: case_model → case_sizing → firm_rates →
  carrier_overlays → exporters; carriers/case-types/regimes are data packs
  composed at runtime (N+M+K, never N×M×K templates); Excel is exporter #1, not
  the tool. Design: `CASE_SIZING_AND_TRAINING_DESIGN.md`;
  modules: `MODULAR_ARCHITECTURE.md`.
- **case_sizing layer**: CaseCostDriver contract, proportionality gate
  (blocked_disproportionate_budget + override-with-reason), settlement-posture
  arithmetic (cost-of-risk comparison, candidate-only) — the $10k-case/$50k-budget
  guard.
- **Firm output shape grounded**: the firm's sanitized budget template (Downloads)
  is dollar-per-UTBMS-task only — no role/rate/hours — so the engine keeps the
  role×rate×hours decomposition internal (that is where guidelines bind) and
  exports down; the template's own defects (missing G33–G85 subtotal formulas,
  P85 double-count of P129) are corrected in our exporter, documented, never
  reproduced.
- **Execution vehicle**: `OPUS_MARATHON_GOAL_converged.md` (waves CW0–CW7,
  serialized, WIP=1) supersedes all earlier marathon prompts.

## What survives from the earlier work (unchanged)
F1–F4 trust fixes (committed, full-suite green); the DAD synthetic-silver
reconciliation; §18/§21 governance; the modular *principle* (as logical contracts
in one repo); the public sources as research/priors (not v1 training gold).
