# Codex Multi-Day Marathon Runbook — Synthetic-Silver Intake Program

Reviewer/planner: Fable 5 (independent second pass over the `claude/le-replay-expansion` branch).
Executor: **Codex**, multi-day, **one task packet at a time**, human gate between milestones.
Scope: `LawFirm-os-intake` (Track A) + a new `lawfirm-synthetic-world-builder` repo (Track B).

---

## Part 1 — Independent review: issues spotted (fresh eyes)

Verified against the branch, not taken on trust. Severity: P1 blocks correctness/safety; P2 real; P3 hygiene.

- **I1 (P2) Executor mismatch.** The shipped `MARATHON_GOAL_PROMPT` targets Opus-medium as a single prose goal. A days-long Codex run needs many small, independently-verifiable packets with explicit acceptance tests and paths. → This runbook replaces it for Codex.
- **I2 (P1) Residual trust gaps left open.** Stage A fixed only F1/F2. Re-verified today: **F3 (actuals fee↔expense swap preserving row+report totals is still accepted)**; F4 (guideline `gross_reductions`/`gross_increases` both inflatable), F5 (rate-card `named_timekeeper_override_count` unvalidated), F6 (guideline/rejection builders lack the single-snapshot check actuals/input/config have). Same fail-open class the slice claims to have closed.
- **I3 (P1) Holdout exclusion is required but unenforced.** `AGENTS.md` and the silver program (control #3) demand the gold holdout be excluded from model-visible prompt assembly, yet there is **no machinery** enforcing it, and `expected_budget_output_state` already appears in a **committed, model-visible fixture (8×)**. If those become silver/gold labels, the holdout leaks.
- **I4 (P2) Dependency-ordering hazard.** Plan Phase 1 depends on the `lawfirm-synthetic-world-builder` repo, which does not exist and is unenrolled. A marathon that starts there stalls. → Two tracks; Track A never blocks on Track B.
- **I5 (P2) Factory-location ambiguity vs. DAD contract.** Plan calls intake "the factory," but DAD points the law-firm corpus factory at the litigation world / World Builder. Two factories is fine (World Builder = corpora; intake = its own budget-output silver) but must be stated so Codex builds the right thing in the right repo.
- **I6 (P1) Gold-cap not enforced.** "Capped at S1 until gold exists" is prose only; nothing stops a manifest from claiming S2 with no gold anchor. → tier-gate validator.
- **I7 (P2) No emitters/validators for the two DAD record schemas** in intake; schemas live in the hub (drift risk). → vendor + conformance test.
- **I8 (P3) Local/unpushed; CI-on-clean-checkout is the real gate.** Full pytest passed locally but the DoD publication gate is Linux CI; the Windows long-path limit must be a documented "run on Linux CI," not silently re-hit.
- **I9 (P1, standing) XGBoost temptation.** A long autonomous run drifts toward "enough data to train." Hard stop in every packet: synthetic silver is pipeline/behavior only.
- **I10 (P3) DAD surfaces degraded.** Reconciliation required reading the hub directly (surfaces stale/missing). Any DAD read step reads the **hub source of truth**, not the graph surfaces, until regenerated.

Improvements folded into the backlog below: front-load the cheap trust-parity fixes for momentum; add a holdout registry + leak test; add a tier-gate validator; split into two dependency tracks; require the `AGENTS.md` test set per packet.

## Part 2 — Gold-anchor decision (was delegated to Fable)

**Decision: the first gold anchor is the intake→budget *output-state* holdout, built in `LawFirm-os-intake`.** ~20–40 human-adjudicated synthetic cases whose ground-truth is the budget output state (`blocked_amount` / `range_or_hours_only` / `candidate_range`) and variance posture.

Why this over the alternatives:
- It is in the repo you are actively working and **does not block on the World Builder repo or Law Firm Sim**, so silver can clear S1→S2 immediately.
- The label space is a tiny closed enum → cheap, reliable human adjudication and deterministic scoring.
- It measures exactly what the first learning loop (budget-driver drift) will move.
- Chunking (DAD's recommended deterministic first pilot) is the stronger *provenance* foundation but a different domain — it belongs in the **World Builder repo** later, not here.
- Litigation-corpus foundation lives in **Law Firm Sim** — a separate repo/authority; keep it as Track B's second anchor.

Constraint carried into code (see M2): the anchor is human-adjudicated, versioned to the `release-manifest` schema, and **registered as holdout** so the leak test can enforce exclusion.

## Part 3 — Global rules for every Codex packet

1. Read `AI_WORK_START_HERE.md`, `AGENTS.md`, `skill-agent-manifest.json` first. Obey the 12-point operating contract and the "never do" list.
2. Work in a fresh `codex/` worktree off the real repo `main` (`.codex-worktrees/workbench-completion-v2` is the real repo; the top-level `LawFirm-os-intake` folder is a stale snapshot). Run tests with `PYTHONPATH=<worktree>/src` and `LAWFIRM_OS_VALIDATION_RUNTIME_POLICY=intake-validation-runtime-policy.v1`.
3. **Required tests per behavioral change** (`AGENTS.md`): synthetic fixture; expected behavior / reviewed gold; deterministic unit tests; a counterfactual context test when practice context is involved; a prohibited-transition safety test; a decision trace.
4. Failing test first, then the code that makes it pass. Keep the full validation gate green each packet (`validate_repo`, `export_schemas`, `ruff check`, `ruff format --check`, `run_full_pytest`, `npm build`, `npm smoke:browser`, `smoke_demo.sh`). The exact-head publication gate is **Linux CI on a clean checkout**; do not weaken tests to dodge the Windows long-path limit.
5. Hard boundaries (STOP + report if a packet needs one): no real data; **no predictive-model training/tuning (XGBoost waits for governed real outcomes)**; no profile/template/guideline mutation, budget submission, matter opening, conflict conclusion, Lake/SQLite/external write, silent learning; no canonical Substrate/Orchestrator change; no push to protected branches; no DAD direct edits (candidate artifacts only); no hidden chain-of-thought.
6. One packet per PR-sized commit with a decision trace. Stop at each milestone's human gate.

## Task-packet template
```
### <packet-id> — <title>
Track: A|B   Depends on: <packet-ids>   Human gate after: yes|no
Goal: <one sentence>
Files: <paths to add/change>
Steps: <ordered, deterministic>
Acceptance tests: <exact test names + what proves done>
Boundary: <the specific hard rule this packet must not cross>
Exit artifact: <what the packet leaves behind>
```

## Part 4 — Backlog (ordered; Track A runs now, Track B is gated on repo creation)

### Track A — intake-side (no external-repo dependency)

**M0 — Trust parity (close residual Stage A gaps).** Momentum, low risk, matches the merged F1/F2 pattern.
- A0.1 F3: recompute actuals row `actual_fees`/`actual_expenses` against source, not just the row total (Python model + TS `data-contract.ts` + a browser-smoke case). Failing mutation first.
- A0.2 F4: tie guideline `gross_reductions`/`gross_increases` to line-level deltas (not just their difference).
- A0.3 F5: reconcile or remove rate-card `named_timekeeper_override_count` (needs a row-level override flag to reconcile against, else drop the field).
- A0.4 F6: give guideline + rejection builders the single-captured-snapshot + end-of-build unchanged-source check that actuals/input/config already have.
- Human gate: trust-parity review.

**M1 — Silver contract adoption in intake.** Depends: M0.
- A1.1 Vendor the three DAD schemas (`synthetic-silver-{program-registry,provenance-record,release-manifest}.schema.json`) into `schemas/` + a conformance test against the hub copies (drift-detector).
- A1.2 Add `silver.py` (peer to `gold.py`) emitting `SyntheticSilverProvenanceRecord` + `SyntheticSilverReleaseManifest` models; validate the golden example.
- A1.3 **Tier-gate validator**: a release manifest claiming S2+ MUST carry a bound gold-anchor ref + holdout hash, else fail closed (fixes I6). Prohibited-transition test.
- Human gate: contract-adoption review.

**M2 — Gold anchor (intake→budget output states) + holdout enforcement.** Depends: M1.
- A2.1 Author ~20–40 synthetic cases with human-adjudicated output-state ground truth; store as a versioned gold-anchor + untouched holdout split.
- A2.2 **Holdout registry** (`config/holdout-registry.json`) + a **leak test** that fails if any holdout id/label/text appears in model-visible prompt-assembly paths (fixes I3). Include the existing `expected_budget_output_state` fixture in the audit.
- Human gate: gold adjudication sign-off.

**M3 — Silver factory S0/S1 for intake outputs.** Depends: M2.
- A3.1 Deterministic producers over existing synthetic fixtures → provenance records → an **S1** release manifest (machine-filtered, hard validators only; candidate-only). No S2 (no calibration claim) until the gold anchor is bound.
- A3.2 Wire into `learning_shadow_eval_results` as the eval target.
- Human gate: S1 release review.

**M4 — One governed learning loop (budget-driver drift).** Depends: M3.
- A4.1 replay → shadow-eval-vs-silver → `reviewed_learning_gate` → `learning_promotion_readiness` → **STOP** (proposal only). Counterfactual + prohibited-transition tests: a regressive candidate is rejected; no boundary crossed; nothing self-applies.
- Human gate: learning-gate review.

**M5 — Public-data → synthetic intake (Phase 1).** Depends: M2; gated on a vetted public source.
- A5.1 Run the go/no-go inventory through `public_derived_synthetic_qa_gate`; if a source clears, generate synthetic intake bundles (data_origin=synthetic, seed, source refs+offsets+hashes, red-team identity-reconstruction + cache-custody pass) and run intake→budget. If none clears, emit the go/no-go and stop.
- Human gate: public-source methodology review.

### Track B — World Builder repo (parallel; gated on human creation + enrollment)

**MB0 — Scaffold `lawfirm-synthetic-world-builder`** (new repo): world-definition interface, one example world, DAD front-door files, proposal-only JobManifest/JobResult producer contract layered on the Law Firm Sim kernel. See `WORLD_BUILDER_BINDING_RECOMMENDATION.md`.
**MB1 — DAD enrollment** (own wave/approval) + apply the candidate `adapter:world-builder` entry in the hub (human-gated; DAD-owner action).
**MB2 — First world corpus** at foundation scale (1 world, small artifact count) → provenance records + release manifest → feed into intake M5. Optionally add the DAD chunking-style corpus gold anchor here.

## Part 5 — Definition of done (whole project)
Silver S1 releases for intake outputs with enforced holdout + tier gate; one governed learning loop proven to propose-and-stop under silver eval; the World Builder repo enrolled and producing at least one world consumed by intake; every hard boundary intact; Linux CI green on a clean checkout. Out of scope until a later governed slice: any predictive-model training, real-data ingestion, S2+ without a bound gold anchor, and any auto-applied learning.
