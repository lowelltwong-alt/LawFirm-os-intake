# Modular Architecture — Contract-First Seams So Every Component Is Worked On Separately

Status: design principle adopted (owner direction 2026-07-21). Supersedes the
feature-layer framing of the marathon where they conflict; the marathon waves
should be re-expressed as one module per packet during convergence.

## The rule (one sentence)

Every component is a **module with a versioned, typed contract and its own test
suite**; a module depends only on other modules' *contracts*, never their
internals, and ships with fixtures/stubs of those contracts so it can be built and
tested with the other modules absent.

Why this is the right move here:
- **Satisfies DAD WIP=1** (the convergence review's RT3): one module = one
  buildable unit; you build/gate one at a time, and its contract lets the next
  one be stubbed. No parallel family builds required.
- **Separable work**: different sessions/agents/days can own different modules
  because the seam is a contract + fixtures, not shared code.
- **Independently testable**: each module is golden/contract-tested against its
  own fixtures; a break is localized.
- **Replaceable**: the ML challenger, a new carrier pack, or a new rule kind
  drops in behind an existing contract without touching the rest.

## Dependency direction (must stay acyclic)

```
guideline_contract  (pure schemas: pack, rule types, provenance, severity)
      ^        ^                ^                    ^
      |        |                |                    |
rule_evaluators  pack_registry  firm_rate_contract   (data + leaf contracts)
      ^              ^                 ^
      |              |                 |
     overlay_compiler  <----  overlay_algebra
      ^
      |
budget_engine (existing intake->budget) --> compliant projection
      ^                                            ^
      |                                            |
   workflow_capture                          budget_ml (consumer/challenger only)
      ^
      |
   ui / data-contract (depends only on exported contracts)

world_builder (separate repo) --> emits synthetic inputs + silver records; depends
on NOTHING above (it produces inputs, it does not consume the engine)
```

Arrows point from dependent to dependency. Nothing points back up. `budget_ml`,
`ui`, and `world_builder` are all leaves that depend on contracts and are depended
on by nothing — so they can be built last or in isolation.

## The Carrier Guideline Engine as modules (the one you named)

| Module | Responsibility | Contract it exposes | Built/tested with |
|---|---|---|---|
| `guideline_contract` | GCS v2 schemas: `GuidelinePack`, rule types (rate_cap, task_hour_allowance, staffing_ratio, expense_cap, activity_rule, preapproval_trigger), `RuleProvenance`, severity | the schemas themselves (versioned, effective-dated) | schema round-trip + golden pack examples |
| `rule_evaluators` | one pure evaluator per rule kind: `(rule, budget_context) -> RuleFinding[]` | `RuleEvaluator` protocol + a registry | per-evaluator golden + metamorphic (tighten cap -> finding never weakens); needs only `guideline_contract` |
| `pack_registry` | load/validate carrier packs (each carrier = a data-only pack file) | `load_pack(id, version) -> GuidelinePack` | fixture packs; a new carrier is a new data file, not code |
| `overlay_algebra` | precedence + conflict surfacing across stacked overlays | `order(overlays) -> ordered, conflicts` | precedence unit tests; needs only `guideline_contract` |
| `overlay_compiler` | pack + evaluators + budget -> compliant projection + per-rule delta attribution + ambiguity register | `compile(budget, packs) -> CompliantProjection` | stubbed evaluators + fixture packs; the seam that makes the rest pluggable |

Adding a new **rule kind** = new evaluator module + registry entry (no compiler
change). Adding a new **carrier** = new pack data file (no code change). Those two
are the axes that must scale to "dozens," and modularity is what makes them cheap.

The existing `guidelines.py` monolith (`build_carrier_compliant_projection` with
inline rate/expense/task handling) is refactored by **extracting each inline rule
into a `rule_evaluators` module** behind the registry, leaving the compiler as the
orchestrator. Same outputs, seams added — a safe, test-guarded refactor first.

## The other components as modules

- `firm_rate_contract` + `firm_rate_resolution`: firm rate card (firm/office/
  state/role/timekeeper, versioned) and the resolver (rate card × pack × state ->
  resolved rate + binding rule). Depends on `guideline_contract` only. Built with
  synthetic/sandbox rate cards; `real_rate_import_allowed` stays gated.
- `world_builder` (own repo): corpus generation + silver provenance/manifest
  emitters. Depends on the DAD record schemas (read-only) and nothing in this
  repo — the strongest separation.
- `budget_ml`: features derived from engine outputs + public reference-class
  anchors; models are **consumers/challengers**, never depended on by the engine.
  Built against a frozen feature-contract + fixtures.
- `workflow_capture`: trace packets over stage contracts; depends on the stage
  I/O contracts, not stage internals.
- `ui` (`apps/legal-intake-budget`): depends only on the exported TS
  data-contract. Already the pattern; keep it.
- `case_sizing` (added 2026-07-21): proportionality gate + CaseCostDriver
  contract + settlement-posture arithmetic; sits between the case model and
  firm-rate resolution; extends the existing drivers.py / nonlinear-template
  machinery. See `CASE_SIZING_AND_TRAINING_DESIGN.md`.
- `exporters` (added 2026-07-21): pluggable renderer boundary — firm-Excel
  (the sanitized template shape, with corrected formulas), LEDES, PDF; the
  structured model is the source of truth, Excel is exporter #1, never the tool.
- `economic_regime` (added 2026-07-21): data-only profile selecting payer, rate
  source, constraint packs (carrier guidelines vs corporate OCGs — same rule IR),
  proportionality policy, staffing norms; insurance-defense active, white-shoe
  stub. Layers compose at runtime: N carriers + M case types + K regimes stay
  N+M+K artifacts, never N×M×K spreadsheets.

## The seam mechanism (how "worked on separately" actually works)
For each module ship three things: (1) the versioned contract; (2) a fixtures
module providing valid + hostile examples of its *dependencies'* contracts, so it
builds with those dependencies absent; (3) contract tests asserting it honors its
own contract. A module is "done" when its contract tests pass against fixtures —
independent of whether its real dependencies exist yet.

## Consequence for the marathon
Re-express the waves as **one module per packet**, ordered by the dependency
graph, WIP=1: `guideline_contract` -> `rule_evaluators` -> `overlay_compiler`
(+`pack_registry`,`overlay_algebra`) -> `firm_rate_resolution` -> `budget_ml`
(reference-class only, per the convergence review) -> `workflow_capture` -> `ui`;
`world_builder` any time (independent). Each packet ends at a contract-review
human gate. This is the concrete form of convergence R2 (serialize) + the owner's
modularity direction.
