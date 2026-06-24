# TRACE-2026-06-24 - Driver-Based Budget Model Design

## Situation

The budget engine (`src/lawfirm_os_intake/budget.py`) computes `hours * synthetic_rate`
over a fixed per-matter-family template. Newer work added hour ranges, a calculation
report, support-item provenance, and a `scenario_name` field, but task hours remain
frozen constants. The output does not scale on the factors that actually drive
insurance-defense litigation cost (resolution path, deposition and expert counts,
party count, severity/exposure, liability dispute, venue, coverage posture, and carrier
billing-guideline constraints), so a budget is internally consistent but not rooted in
case economics, and it presents a single number where path risk dominates.

## Decision

Adopt a design (see `docs/driver-based-budget-model-design.md`) that:

- treats a budget as a **scenario set** (early resolution / standard / through trial)
  via base-template truncation at a declared `resolution_phase`;
- scales task hours and expenses on a typed **driver taxonomy**
  (`hours = base * Π multipliers * count_factor`), deterministically;
- carries **driver provenance** (`observed_support` / `human_confirmed` /
  `profile_default` / `unknown`) so defaults never masquerade as observed facts and
  unknowns widen ranges instead of inventing values;
- stores the taxonomy/multipliers/scenarios in a new versioned, hashed
  `config/budget-driver-policy.yaml`, with per-matter-family defaults and base templates
  in practice profiles;
- generalizes across litigation types by sharing one engine and varying only base
  templates + default driver values;
- ships as seven PR-sized slices, the first of which captures drivers **without
  changing the math** so the current suite stays green.

This commit adds the design document and this trace only.

## Non-decision

This does not change budget math, schemas, rates, templates, approval state, conflict
clearance, engagement authority, client/carrier submission authority, billing, matter
opening, deadline docketing, or external writes. No code under `src/` changed. No
canonical taxonomy or schema is mutated. Public data is not ingested.

## Authority impact

Local design artifact in `LawFirm-os-intake`, which owns no platform canon. The driver
taxonomy, scenario vocabulary, and any budget schema remain `candidate` and would be
promoted only through Semantic Substrate; runtime budget gating and approval routing
remain Orchestrator's; variance/actuals learning remains Exception Lake's. Until
promoted, all new vocabulary is pinned locally as candidate.

## Evidence

- `src/lawfirm_os_intake/budget.py` and `context/synthetic-profiles/insurance-defense.yaml`
  show fixed `estimated_hours` per task with no driver scaling.
- `BudgetProposal` already carries `scenario_name`; `BudgetLine` already carries
  `estimated_hours_min/max`; `ScoredCandidate.source_evidence_status` already separates
  observed support from anchor-only and unknown — the design reuses these channels.
- `docs/legal-budget-design.md` already requires ranges/scenario branches when counts
  are unknown and requires expert/vendor costs kept distinct from fees.
- `src/lawfirm_os_intake/public_data.py` enforces the planning-only public-data boundary
  the calibration plan relies on.

## Alternatives rejected

- Keep the flat template and only widen ranges: rejected; ranges around a frozen
  constant still do not reflect deposition/expert/severity/resolution-path economics.
- Let a model estimate hours: rejected; violates deterministic-math and
  no-model-chosen-numbers boundaries.
- Encode drivers in code: rejected; drivers must live in versioned, hashed policy like
  practice context, reviewable and diff-able.
- Single expected-value output: rejected; hides path risk, the dominant cost lever.

## Risks and rollback

The design is documentation only; rollback deletes two Markdown files with no code
impact. Implementation risk (multiplier blowup, default-as-evidence bias, cross-type
leakage) is addressed in the design's red-team section and gated behind per-slice tests;
slice 1 deliberately changes no math.

## Validation

- No code changed; existing suite was green at HEAD before this change
  (`python -m pytest -q` -> 127 passed).
- Design artifacts are Markdown only; no schema export or smoke run is affected.

## Human gates

Human confirmation still precedes budget generation. The budget remains
`proposed_for_human_review` and `not_authorized_for_client_submission=true`. Conflicts
clearance, engagement authorization, and matter opening remain separate blockers.
