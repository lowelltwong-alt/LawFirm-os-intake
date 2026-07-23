# Convergence Review — Red-Team + Premortem Of The Marathon Proposal

Status: adversarial self-review of the proposal in
`MARATHON_PROGRAM_waves_and_prompts.md`, `PUBLIC_GOLD_STRATEGY_legal_budgets.md`,
`PLAN_2026-07-21_…`, `WORLD_BUILDER_BINDING_RECOMMENDATION.md`, and roadmap
§22–23. Purpose: decide whether convergence/rework is needed before handing the
marathon to Codex.

## Verdict

**Convergence IS necessary before handoff.** The governance and trust scaffolding
is sound, but the *value core* — training a budget tool on public gold — rests on
a domain-transfer assumption that is currently unproven and, as written, probably
wrong for the firm's actual practice areas. Three blocking reconciliations and
four should-fix items below. Do not start W2/W6 until R1–R3 are resolved.

## Red-team findings (attacks on the design), most severe first

### RT1 — The budget-shaped gold is off-domain; the on-domain gold is rate-only. (BLOCKING)
The strongest public gold (large Chapter 11 fee applications with budgets,
staffing plans, project-category billing, fee-examiner budget-vs-actual) is
**restructuring** data: mega-firms, huge matters, different task mix and rate
economics. If the firm does insurance defense / EPLI / L&E, that gold is a
different distribution. The *on-domain* insurance-defense sources I found
(independent-counsel rate adjudications, risk-pool rate standards, Schedule P
DCC/ALAE) are **rates and ratios, not phase/task-hour budgets**. So: the gold
that is budget-shaped is the wrong domain, and the gold that is the right domain
is not budget-shaped. W6 ("phase-cost interval models evaluated on the public-gold
holdout") would evaluate the firm's domain against the wrong domain's budgets.
This is the finding most likely to make the whole ML lane invalid.

### RT2 — "Court-adjudicated" is a near-rubber-stamp, not a strong quality signal. (BLOCKING)
My own research surfaced it: courts award ~99% of amounts applied for. So
"adjudicated amount" ≈ "applied amount" ≈ "what the firm billed." The gold's
*semantic* is "what got approved," not "what a good forward budget should be." The
discriminating signal lives in the sparse ~1% cuts, the fee-examiner narratives,
and cut *reasons* — thin exactly where budget quality would be measured. Treating
adjudicated totals as budget ground truth overstates the signal.

### RT3 — The marathon violates DAD's own WIP policy. (BLOCKING, governance)
`registry/agent-family-portfolio-registry.json` sets
`maximum_active_family_builds: 1`, `maximum_active_family_pilots: 1`, owner
Lowell. My program runs World Builder + guideline-engine-v2 + firm-layer + ML + UI
with explicit parallel lanes (W2 ∥ W4). That directly contradicts DAD canon. A
solo owner cannot supervise parallel family builds at the human gates the plan
itself requires.

### RT4 — §21 forbids exactly what W6 looks like. (should-fix, reconcile)
Roadmap §21 fail-closed: "Do not train on the synthetic corpus and describe the
result as calibrated." W6 trains on silver S2 (synthetic) calibrated to public
gold. Public gold is real and historical but is **not the firm's** outcomes.
Without an explicit, enforced "reference-class, never firm-calibrated" label on
every artifact, W6 drifts into the prohibited claim. Needs a governed reference-
class lane in §21 or a hard labeling gate.

### RT5 — "Dozens of carrier guidelines as deterministic rule packs" assumes structure that may not exist. (should-fix)
Real guidelines are natural-language, internally inconsistent, and many "rules"
(especially task-hour reasonableness) are judgment calls, not clean thresholds.
The engine risks two failure modes: too rigid (false rejections that a firm would
never accept) or everything lands in the ambiguity register (no automation
payoff). The architecture (per-rule attribution + ambiguity register) is right;
the *coverage* claim ("dozens, adaptively") is the risk.

### RT6 — New World Builder repo may over-fragment; DAD hinted at the opposite. (should-fix)
DAD marked `adapter:world-builder` `target_unresolved`, "likely a generalization
of the litigation world kernel." I recommended a *new* repo. For a solo owner,
another enrollment/CI/governance surface is real overhead, and it may duplicate
Law Firm Sim. Worth re-deciding: generalize the existing kernel vs. new repo.

### RT7 — Everything is synthetic until delivery; no firm-reality checkpoint. (should-fix)
The firm hasn't specified requirements, and there is no feedback loop until the
finished pitch. Risk of building an elegant synthetic system whose carrier/budget
model the firm says isn't how they work.

### RT8 — The agent routing the marathon will rely on is reading stale data.
lesson-graph, subagent-capability-graph, and durable-entity-plan-graph are
stale/broken right now. Routing Codex subagents "through DAD" (the next ask)
depends on capability surfaces that need regeneration first.

## Premortem — it's six months later and this failed. Why?
1. The Ch.11 gold never transferred to the firm's insurance-defense budgets;
   models stayed reference-class and the firm found them irrelevant (RT1).
2. The gold couldn't discriminate good from bad budgets (99% approval) (RT2).
3. Too many parallel builds for one owner; half-finished layers, gates skipped
   (RT3).
4. The guideline engine drowned in ambiguity-register entries — no automation
   payoff — or over-rejected and lost firm trust (RT5).
5. Days of autonomous Codex produced artifacts that passed synthetic tests but
   encoded the transfer fallacy; effort spent, little firm value (RT1+RT8).
6. Built the wrong thing: no firm checkpoint until delivery (RT7).

## What is solid (do not throw out)
- The trust fixes F1–F4 are real, tested, full-suite green.
- The DAD synthetic-silver reconciliation (tiers, contract/factory split, the
  two record schemas) is sound and canon-aligned.
- The governance posture (candidate-only, human gates, §18 ingestion) is right.
- The public sources DO exist and ARE useful — for **rate ranges, rejection/cut
  statistics, and distribution anchors**, which is a narrower and defensible use
  than "budget ground truth."
- The guideline-engine architecture (versioned packs, per-rule provenance +
  severity, attributing compiler, ambiguity register) is the right shape.

## Required convergence before handoff

- **R1 (from RT1/RT2): Reframe the gold from "budget ground truth" to
  "reference-class anchors."** Split it: (a) budget-shape/structure from Ch.11
  (off-domain, use for pipeline/feature shape only), (b) rate ranges + rejection
  statistics from on-domain insurance-defense sources, (c) explicitly mark that
  firm-domain phase/task-hour budget gold does not exist until firm data. W6's
  primary targets become **rejection/reduction risk and rate reasonableness**
  (where on-domain gold exists), not phase-cost point budgets.
- **R2 (from RT3): Serialize the waves to WIP=1.** Pick ONE first family build.
  Recommendation: the **Carrier Guideline Engine v2 (W4)** first — it is the
  firm's stated hard problem, needs no gold, and is mostly deterministic. Defer
  World Builder/silver/ML until the engine proves out. Remove the parallel lanes.
- **R3 (from RT4): Add a governed reference-class ML lane to §21** with a hard
  "reference-class, never firm-calibrated" label gate on every model artifact,
  or hold W6 entirely until firm data.
- **R4 (from RT7): Insert a one-page firm-requirements checkpoint** (even
  informal: which carriers, which practice areas, which guideline documents
  exist) before W4 pack authoring, so the synthetic packs mirror real structure.
- **R5 (from RT6): Re-decide World Builder** — generalize Law Firm Sim kernel vs.
  new repo — with the WIP and solo-owner overhead in view.
- **R6 (from RT8): Regenerate the stale DAD surfaces** before relying on DAD
  agent routing for subagents.

## Net
The trust and governance layers converge. The **value core does not yet**:
the gold is off-domain-or-rate-only (R1), the program over-parallelizes against
DAD WIP=1 (R2), and W6 brushes the §21 boundary (R3). Resolve R1–R3, add R4,
then the Codex handoff is safe to run — and it should lead with the guideline
engine, not the ML.
