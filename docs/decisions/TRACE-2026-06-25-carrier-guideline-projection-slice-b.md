# TRACE: Carrier Guideline Projection Slice B

Date: 2026-06-25

## Context

Slice A resolved authorized synthetic rates by carrier, state, and title. The next
rate/guideline layer decision was to let carrier guidelines affect projected math
without silently rewriting the proposed legal budget. The controlling design is in
`docs/carrier-rate-and-guideline-layer-design.md`: keep two numbers, proposed and
carrier-compliant projection.

## Decision

Add a synthetic-only carrier guideline artifact and embed a separate
`CarrierCompliantProjection` in `legal_budget_proposal.json`.

The projection:

- applies synthetic rate caps by staffing role;
- applies synthetic expense caps by E-code;
- reports proposed total, compliant total, and deltas;
- records capped and disallowed line flags;
- preserves the original proposal lines unchanged;
- keeps `rewrites_budget=false`;
- remains `projected_for_human_review`;
- carries no client or carrier submission authority.

The insurance-defense synthetic profile points to
`config/synthetic-carrier-guideline.yaml`. That artifact is candidate-only and
must declare `data_scope: synthetic_only`; artifacts marked as real carrier
guidelines are rejected.

## Authority Boundary

This remains local candidate behavior in `LawFirm-os-intake`. It does not promote
carrier guideline schema, rate-cap semantics, expense-cap semantics, event labels,
route IDs, approval rules, or budget submission authority to canon.

No real carrier guidelines, real negotiated rates, production connectors, provider
calls, external writes, conflict clearance, engagement decision, matter opening,
billing handoff, or client/carrier budget submission are in scope.

## Validation

Added deterministic tests proving:

- proposal lines remain unchanged when projection caps apply;
- the projection shows proposed total greater than compliant total for the med-mal
  fixture;
- partner rates are capped only inside the projection;
- expert expense caps apply only inside the projection;
- review forms render the projection and no-submission boundary;
- real-carrier guideline artifacts are rejected.

Schema export now includes the carrier-compliant projection schema family.

## Non-Decisions

This slice does not implement staffing/leverage reshaping, pre-approval threshold
escalations, second-carrier counterfactuals, named timekeeper overrides, or P1
budget math fixes. Those remain separate PR-sized slices.
