> **PORTED 2026-07-09 from the stale intake snapshot ("copy A") — CORRECTIONS APPLY:**
> 1. The canonical intake repo is THIS repo (seed-clean B). Copy A is archived; never edit it.
> 2. This document was authored against copy A (~74 schemas) and UNDERSTATES this repo
>    (~420 schemas): the learning loop it proposes ALREADY EXISTS here
>    (budget-learning-loop-*, carrier-rejection-learning-*, reviewed-learning-gate-*,
>    learning-promotion-readiness-*, learning-shadow-eval-*, learning-owner-handoff-*).
>    Read it for the DAD pattern and hard kernels, not as a gap analysis.
> Orchestration home: 04_Digital_Assett_Directory/orchestration/ (ARCHITECTURE_PACKET.md).

# Hard Kernels For Fable: DAD-Style LawFirm OS Layer

Status: candidate architecture list
Purpose: focus Fable on the hardest, highest-leverage problems only.

Routine work such as simple CRUD, UI layout, basic JSON schemas, docs cleanup,
and fixture plumbing should not be treated as a Fable kernel. These kernels are
for problems where a strong implementation agent can still make a subtle
governance, privacy, legal-ops, or evidence mistake.

## Kernel 1: Cross-Matter Learning Non-Interference

Problem:

Learning from one matter can quietly affect another matter through examples,
thresholds, corrections, prompts, retrieval memories, asset scores, or workflow
defaults.

Why hard:

- The leak may be statistical rather than textual.
- The leak may arrive through aggregate learning, not direct data reuse.
- The implementation may pass ordinary synthetic tests while still allowing
  matter-specific pressure to shape future runs.

Candidate solution:

- Separate matter-scoped facts from aggregate candidates.
- Require every learning candidate to declare source matter isolation,
  aggregation level, small-cell risk, dominance risk, and permitted reuse scope.
- Block promotion when K, adversary model, conflict class, or dominance rule is
  undeclared by a human owner.
- Keep candidate learning out of runtime defaults until reviewed promotion.

Owning repos:

- Intake: candidate learning packet and synthetic tests.
- Exception Lake: append-only pressure/correction evidence.
- Semantic Substrate: promoted non-interference rule.
- Orchestrator: runtime enforcement once promoted.

First build artifact:

- `learning-candidate-packet` with `reuse_scope`, `matter_isolation`,
  `small_cell_status`, `dominance_status`, `promotion_target`, and
  `blocked_reason` fields.

Must not build yet:

- real-data aggregation;
- automatic threshold updates;
- production learning memory.

## Kernel 2: Authority Laundering Prevention

Problem:

AI output, reviewer notes, rejected carrier messages, or local convenience rules
can become treated as legal, compliance, governance, rate, or OCG authority.

Why hard:

- The same text can be evidence in one context and authority in another.
- Model proposals often look polished enough to be mistaken for policy.
- Local fixtures can calcify into de facto canon.

Candidate solution:

- Use an evidence-class lattice:
  - source fact;
  - model proposal;
  - deterministic inference;
  - human confirmation;
  - candidate learning;
  - promoted canon.
- Require every downstream handoff to preserve the evidence class.
- Validators fail if a lower class is consumed as a higher class.

Owning repos:

- Intake: local evidence class on review packets and learning packets.
- Semantic Substrate: canonical evidence-class definitions.
- Orchestrator: run-time transition enforcement.
- Skills Registry: skill output authority labels.

First build artifact:

- validator that blocks `model_proposal` or `candidate_learning` from being
  marked as `promoted_canon`.

Must not build yet:

- automatic canon promotion;
- production legal advice generation.

## Kernel 3: Minimal Digital Asset Disclosure

Problem:

LawFirm OS needs enough DAD-style assets to be useful, but exposing the full DAD
catalog gives away private intellectual property and operational strategy.

Why hard:

- Useful asset metadata can reveal private workflows even when payloads are
  removed.
- Asset names, scores, dependencies, paths, and usage patterns may disclose too
  much.
- A small demo can become a backdoor catalog if fields are copied blindly.

Candidate solution:

- Build a LawFirm OS asset-card facade with only public-safe fields:
  `asset_id`, `purpose`, `workflow_surface`, `data_class`, `authority_level`,
  `owner_repo`, `promotion_target`, `blocked_uses`, `synthetic_fixture_refs`,
  `validation_refs`.
- Exclude private DAD path, private score, private dependency graph, private
  owner notes, internal asset rank, and non-public asset lineage.
- Use derivative capability cards instead of direct DAD asset cards.

Owning repos:

- Intake: initial candidate asset registry and fixtures.
- Semantic Substrate: promoted asset-card schema if generalized.
- DAD: remains private source of broader asset intelligence.

First build artifact:

- seven LawFirm OS candidate asset cards using only synthetic/public-safe refs.

Must not build yet:

- DAD catalog import;
- DAD hub sync;
- private asset scoring.

## Kernel 4: Append-Only Evidence With Retroactive Screens

Problem:

Exception evidence should be append-only, but later privacy, conflict, or
compliance screens may require suppression, quarantine, or changed access.

Why hard:

- Deleting breaks audit integrity.
- Keeping everything visible can violate privacy or privilege boundaries.
- Later screens may apply to older evidence after new facts appear.

Candidate solution:

- Preserve immutable evidence identity and hashes.
- Add append-only screen overlays:
  - quarantine overlay;
  - redaction overlay;
  - access-policy overlay;
  - supersession overlay;
  - reviewer rationale.
- Treat projections as views, not mutations.

Owning repos:

- Exception Lake: overlay records and evidence projection.
- Semantic Substrate: overlay types and policy semantics.
- Orchestrator: runtime access checks.
- Intake: dry-run package that can model overlays without writing.

First build artifact:

- dry-run evidence package with `screen_overlay_candidates` and
  `not_authorized_for_lake_write=true`.

Must not build yet:

- deletion;
- production Lake writes from intake.

## Kernel 5: Tool-Chain Authority Passport

Problem:

MCP tools, local scripts, model adapters, and future connectors can accidentally
compose permissions. A harmless tool plus another harmless tool may together
cross an authority boundary.

Why hard:

- Authority becomes transitive unless explicitly bounded.
- Logs often show individual calls, not full chain authority.
- The unsafe action may occur several hops after the decision.

Candidate solution:

- Every run carries an authority passport:
  - permitted data classes;
  - permitted write targets;
  - permitted external actions;
  - legal/compliance authority level;
  - human gate requirements;
  - repo ownership boundary;
  - no-transitive-authority flag.
- Each tool call must consume and return the passport with reduced or equal
  authority.

Owning repos:

- Orchestrator: runtime passport enforcement.
- Semantic Substrate: passport schema and authority classes.
- Intake: candidate passport fields in local dry-run evidence.
- Skills Registry: skill capability declarations.

First build artifact:

- candidate passport in intake handoff packets, with tests proving no external
  writes are permitted.

Must not build yet:

- live connector chain;
- automatic tool grant escalation.

## Kernel 6: Replay Across Model And Provider Deprecation

Problem:

Legal evidence and workflow decisions may need later review, but model/provider
behavior, prompts, and dependency versions change.

Why hard:

- Exact model replay may be impossible.
- A merely stored answer is not enough evidence.
- Re-running a changed model can create false confidence.

Candidate solution:

- Persist deterministic run packets:
  - source refs;
  - hashes;
  - schema versions;
  - prompt hashes;
  - adapter version;
  - model class;
  - deterministic post-processing;
  - human decisions;
  - output evidence class.
- Define replay as equivalence testing against declared criteria, not exact
  hidden-state reproduction.

Owning repos:

- Intake: candidate run packet and synthetic replay fixtures.
- Orchestrator: durable run ledger.
- Exception Lake: append-only evidence records.
- Skills Registry: prompt/model package metadata.
- Semantic Substrate: replay/equivalence policy.

First build artifact:

- synthetic replay fixture that proves a candidate can be reviewed without the
  original model call.

Must not build yet:

- production model dependency;
- hidden chain-of-thought storage.

## Kernel 7: Carrier Rejection, Appeal, And Actual-Variance Learning

Problem:

Carrier rejections, appeals, and actuals are high-value feedback, but they can
easily mutate budgets, rates, OCG rules, or templates without authorized review.

Why hard:

- Feedback is operationally valuable and tempting to auto-apply.
- Rejection text may be wrong, strategic, incomplete, or carrier-specific.
- Actual variance may reflect facts, staffing, court behavior, or poor initial
  modeling; the system must not learn the wrong lesson.

Candidate solution:

- Treat each rejection, appeal outcome, and variance as evidence plus a
  candidate lesson.
- Separate:
  - observed rejection;
  - proposed reason family;
  - human-confirmed reason family;
  - budget impact;
  - guideline/rate/template implication;
  - promotion target.
- Require named approver, version, effective date, and supersession before any
  private profile, rate, or guideline changes.

Owning repos:

- Intake: candidate learning and review packet.
- Exception Lake: evidence/correction stream.
- Legal Knowledge Runtime: source context, if public/legal context is needed.
- Semantic Substrate: promoted OCG/shared-rule IR.
- Orchestrator: approval workflow.

First build artifact:

- carrier rejection learning fixture with no mutation flags and explicit human
  review outcome.

Must not build yet:

- real carrier profile mutation;
- negotiated rate updates;
- appeal submission.

## Kernel 8: Public-Structure-To-Synthetic Conversion Without Reconstruction

Problem:

LawFirm OS should learn from real workflow shapes, public legal data structures,
and public corpora without importing identifiable public-record facts or making
fixtures reconstructable.

Why hard:

- Public data can still be sensitive or identifying.
- Structure can leak origin when too many fields are preserved.
- Synthetic fixtures can accidentally become lightly redacted real records.

Candidate solution:

- Use public data only as structure.
- Track conversion manifests, not public payloads.
- Require non-reconstruction checks:
  - no real party names;
  - no direct docket facts;
  - no unique date/location/case combinations;
  - no source text copied into runtime fixtures;
  - synthetic origin declaration.

Owning repos:

- Intake: synthetic fixtures and conversion specs.
- Legal Knowledge Runtime: source refs and public-source handling.
- Semantic Substrate: data-origin and conversion policy if promoted.

First build artifact:

- conversion-spec fixture that maps public source structure to synthetic
  workflow data without tracked raw payload.

Must not build yet:

- committed public payload corpus;
- production public-record ingestion.

