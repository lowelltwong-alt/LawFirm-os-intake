# Opus Marathon Goal — Converged Plan To 100% (Serialized Waves, WIP=1)

Paste the block below into an Opus 4.8 (medium) session as the standing goal.
It executes `CONVERGED_PLAN_OF_RECORD.md` + `CASE_SIZING_AND_TRAINING_DESIGN.md`
to completion. One wave at a time; every wave is one PR-sized unit ending at a
named gate. This supersedes all earlier marathon prompts.

---

GOAL: Complete the converged plan of record for `lowelltwong-alt/LawFirm-os-intake`
100%: a thin deterministic intake→budget→guideline-adjusted-reimbursement vertical
with case sizing and settlement-posture economics, exported to the firm's Excel
shape, validated for a firm checkpoint — then contract reconciliation, regime
seam, and hardening. Serialized waves, WIP=1, one PR per wave, stop at every gate.

OPERATING RULES (every wave):
- Working directory: `<worktree-root>` — the `claude/le-replay-expansion`
  branch. It holds all planning docs AND the committed F1–F4 trust fixes, and it
  is a worktree of the REAL repo (`.codex-worktrees/workbench-completion-v2`), so
  it shares git/origin. The top-level `LawFirm-os-intake` folder is a stale
  snapshot — never read or edit it. CW0 pushes THIS branch and opens the PR;
  after it merges, later waves branch off the new `main` and rebase at wave start.
- Read first: `docs/ai-handoff/CONVERGED_PLAN_OF_RECORD.md`,
  `CASE_SIZING_AND_TRAINING_DESIGN.md`, `MODULAR_ARCHITECTURE.md`, `AGENTS.md`,
  `CLAUDE.md`. The superseded docs (MARATHON_PROGRAM…, PUBLIC_GOLD_STRATEGY…) are
  history, not instructions.
- Failing test first; modular contract-first (versioned contracts + dependency
  fixtures); exact decimal money; every serialized derived value recomputed or
  rule-attributed (fail-closed); typed blocked states, never silent None/default.
- Full gate before any PR: validate_repo, export_schemas, ruff check+format,
  `python scripts/run_full_pytest.py -q`
  (PYTHONPATH=<worktree>/src, LAWFIRM_OS_VALIDATION_RUNTIME_POLICY=
  intake-validation-runtime-policy.v1), npm build + smoke:browser. Push branch,
  open PR, wait for CI green; never merge your own PR; never push main.
- Boundaries: synthetic-only; candidate-only; no real client/rate/carrier data;
  no §21 violations (no "calibrated" claims from synthetic; no v1 money ML); no
  new rule language (reconcile with the Substrate-owned OCG IR; the sibling
  billing-guideline-simulator is a read-only challenger); no new repos; no DAD
  writes beyond candidate mail-outbox lesson packets; budget core never depends
  on the guideline compiler; work-plan total is never overwritten by
  reimbursement math.
- End every wave: decision trace + DAD candidate lesson packet (outbox,
  metadata+pointer) + stop at the wave's human gate.

WAVE CW0 — Trust closeout + publish. Implement F5 (row-level
named_timekeeper_override flag populated from the rate-card YAML; reconcile
named_timekeeper_override_count in the Python validator + data-contract.ts;
refresh fixtures/schemas) and F6 (guideline + rejection builders: single captured
source snapshot, end-of-build source_inputs_unchanged_during_build check,
monkeypatched mid-build-mutation tests mirroring
tests/test_synthetic_workbench_source_integrity.py). Then push the accumulated
branch work and open the PR. GATE: human PR review/merge.

WAVE CW1 — Fail-closed core of the thin vertical. In the existing engine/workbench:
(1) PackSelectionDecision — typed selection with confirmed carrier/program/
jurisdiction/as-of, considered-packs + exclusion reasons, selected revision +
content hash; missing/wrong carrier ⇒ blocked_missing_context, NEVER None or
default-carrier fallback (fix guidelines.py:_carrier_rules call path). (2) Stable
line_id on BudgetLine + projection lines + UI keys. (3) Ordered AdjustmentLedger:
declared attribution order (pack/effective selection → task-hour caps → rate caps
→ expense caps → contingency → preapproval/unsupported), one entry per rule
effect (before/after/delta/rule_id/span); per-rule deltas must sum to category
deltas and total_delta (recomputed in the model validator, fail-closed). (4) One
aggregate task×role hour-cap rule end-to-end. (5) Output language split:
work_plan_total vs guideline_adjusted_reimbursement vs unreimbursed_exposure —
rendered in the UI with the existing candidate banners. GATE: contract review.

WAVE CW2 — Case sizing + settlement economics v0. Implement per
CASE_SIZING_AND_TRAINING_DESIGN.md: CaseCostDriver contract with 3–5 drivers
(party_count, injury severity band, liability clarity, exposure band, venue)
wired through the existing drivers.py/BudgetDriverEffect machinery and nonlinear
template math; proportionality gate (budget-to-exposure bands per case type ⇒
blocked_disproportionate_budget with human-override-with-reason); settlement-
posture arithmetic (settle-now vs defend-settle vs try on declared synthetic
inputs ⇒ ranked postures, candidate recommendation, envelope). Golden +
metamorphic suite (party+1 ⇒ non-decreasing; E↓ ⇒ envelope non-increasing;
S≪defense ⇒ settle recommended). All outputs candidate-only, human gates intact.
GATE: sizing/economics contract review.

WAVE CW3 — Exporter seam + firm-Excel renderer. Exporter plugin boundary (model →
renderer); firm-Excel exporter matching the sanitized template shape
(C:\path\to\carrier-budget-template.xlsx): UTBMS phase/task
rows, Original/Billed/Remaining/New columns, CORRECT phase-subtotal + grand-total
formulas (do not reproduce the template's missing G33–G85 formulas or the P85
double-count of P129 — document both deviations), role/rate/hours decomposition
kept internal with dollars-per-task exported. Round-trip test: export → re-read →
totals reconcile to the model exactly. UI: sizing + posture + exposure panels.
GATE: export-shape review vs the firm template.

WAVE CW4 — Routing eval harness. In-repo synthetic fixture factory (the deferred
World Builder stays deferred — this is ordinary versioned fixtures): generate
intake bundles WITH ground-truth case-spec labels (family, drivers, exposure);
frozen holdout + adversarial set (mixed signals, quoted-thread noise, missing
attachment, injection-as-text); router evaluation report (per-family accuracy +
abstention correctness) for the existing deterministic
matter_family_candidates→confirmation flow. No ML router in this wave. GATE:
routing-eval review.

WAVE CW5 — Firm checkpoint packet. Three synthetic cases end-to-end (small
slip-and-fall that recommends settle posture + trips the proportionality gate;
mid-size EPLI with the expert-preapproval trip; one L&E family case), each:
intake → routed → sized → priced → overlaid → exported Excel + UI view +
disposition sheet ("useful / wrong workflow / missing rule"). Package for the
firm. GATE: HARD STOP — human presents to firm; do not proceed on any wave
until firm dispositions return.

WAVE CW6 — Contract reconciliation. Candidate executable extension proposal to
the Substrate-owned OCG rule IR covering the rule kinds the vertical needs
(task-hour allowance, ordered attribution, applicability envelope); Intake keeps
a local adapter + fixtures, authors no canonical IDs; run read-only conformance
of the sibling billing-guideline-simulator against CW1 outputs and record
divergences. GATE: Substrate owner review.

WAVE CW7 — Regime seam + hardening + delivery. EconomicRegimeProfile
(insurance-defense profile active; white-shoe stub proving the seam, incl.
corporate-OCG-as-pack note); hostile-fixture sweep over every new serialized
artifact (ledger, selection decision, sizing outputs, export) using the
workbench trust-suite methodology; differential + monotonicity fuzz across packs;
delivery packet (capabilities, boundaries, synthetic status, firm-data
recalibration path). GATE: delivery review. END OF PROGRAM.

---
