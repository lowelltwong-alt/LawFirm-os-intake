# Marathon Goal Prompt — Public-Data → Synthetic-Silver Intake-to-Budget Learning Loop

Paste the block below into a fresh **Opus 4.8 (medium)** session as the goal. It
is designed as a governed marathon: bounded slices, human gates, hard stops.

---

You are running a governed marathon in the `lowelltwong-alt/LawFirm-os-intake`
repository. Work only in a fresh `claude/` git worktree off the real repo's
`main` (the real repo lives at `.codex-worktrees/workbench-completion-v2`, NOT
the stale top-level `LawFirm-os-intake` folder). Assume other agents work
concurrently.

GOAL: Make the intake→budget workflow run end-to-end on **synthetic intake
documents derived from public data**, and design **governed self-improvement
learning loops** evaluated against a **synthetic-silver** standard (reviewed
synthetic expected-outputs) because no gold (reviewed real outcomes) exists.

READ FIRST (front door):
1. `AGENTS.md`, `AI_WORK_START_HERE.md`, `CLAUDE.md`, `skill-agent-manifest.json`
2. `docs/ai-handoff/PLAN_2026-07-21_public_synthetic_silver_intake_budget_learning.md`
   (the full plan — follow its phases and boundaries)
3. `docs/roadmap.md` §18 (public source methodology) and §19 (calibration corpus)
4. `src/lawfirm_os_intake/public_derived_synthetic_qa_gate.py`, `gold.py`,
   `reviewed_learning_gate.py`, `learning_shadow_eval_results.py`,
   `budget_learning_loop.py`

EXECUTE, in order, one slice at a time, stopping at each human gate:
- Phase 0: run `bash scripts/smoke_demo.sh` green; reconcile the DAD canonical
  "synthetic silver" definition (via the `dad-local-graph-surfaces` MCP / DAD
  mailbox front door) against the plan §2 and write the reconciliation; produce a
  vetted public-source go/no-go list (or record "none available yet" and stop for
  human input).
- Phase 1: emit synthetic public-derived intake bundles through
  `public_derived_synthetic_qa_gate` (each: `data_origin=synthetic`, generator
  version + deterministic seed, source refs + offsets + hashes, explicit
  unknowns/blocked gates, red-team identity-reconstruction pass, cache-custody
  review) and run them through intake→budget→actuals→carrier.
- Phase 2: add a **silver tier** (reviewed synthetic expected-output labels;
  provenance, seed, reviewer, confidence, applicability/non-applicability, an
  explicit "not gold / not calibration evidence" marker); score pipeline outputs
  against silver via the existing shadow-eval machinery.
- Phase 3: design **one** candidate learning loop (recommend budget-driver drift)
  that goes replay → shadow-eval-against-silver → `reviewed_learning_gate` →
  `learning_promotion_readiness`, and STOPS there. Prove with a
  counterfactual/metamorphic test that a regressive candidate is rejected and no
  boundary is crossed.

METHOD (medium reasoning — be decisive, gate-driven, not exhaustive):
- Failing-mutation/counterfactual test first, then the code that makes it pass.
- Checkpoint per slice with a commit and a decision trace; keep the full
  validation gate green each iteration: `python scripts/validate_repo.py`,
  `python scripts/export_schemas.py`, `python -m ruff check src tests scripts`,
  `python -m ruff format --check src tests scripts`,
  `python scripts/run_full_pytest.py -q`,
  `npm run build --prefix apps/legal-intake-budget`,
  `npm run smoke:browser --prefix apps/legal-intake-budget`.
  (Run tests with `PYTHONPATH=<worktree>/src` and
  `LAWFIRM_OS_VALIDATION_RUNTIME_POLICY=intake-validation-runtime-policy.v1`;
  clean `__pycache__`/`*.egg-info` before `validate_repo.py`.)

HARD BOUNDARIES (never cross; if a slice would require it, STOP and report):
No real matter/client/rate/carrier/public-case payload data. No predictive-model
training/tuning (XGBoost is a later governed slice needing reviewed real
outcomes; silver is for pipeline/behavior only). No profile/template/guideline
mutation, budget submission, matter opening, conflict conclusion, Lake/SQLite/
external write, or silent learning. No canonical Substrate/Orchestrator changes.
No push to protected branches. DAD via the governed front door only; do not edit
DAD directly. If the DAD silver definition conflicts with the plan, the DAD
definition wins — stop and reconcile.

STOP CONDITIONS: real/privileged data appears; a required source is unavailable
or uncleared; the DAD silver definition is unreachable or conflicts; a slice
would cross a hard boundary; a human gate is reached. At each stop, emit a
decision trace + a governed DAD candidate lesson packet (observable evidence,
assumptions, applicability, non-applicability, danger-if-misapplied, no hidden
chain-of-thought) and wait for human review.

DELIVERABLES per slice: PR-sized diff on the `claude/` branch; decision trace;
exact test outputs; red-team findings incl. rejected approaches; a Codex handoff
of remaining work; a governed DAD candidate lesson packet.

---
