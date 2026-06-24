# TRACE-2026-06-23 - Party Role Evidence Refs

## Context

The preflight packet already required source-bound evidence refs for party candidates, matter candidates, posture candidates, deadlines, missing-information candidates, and critic findings. `RoleCandidate` still carried only a role label and confidence, which made a role alternative less auditable than the party candidate it belonged to.

## Decision

Add source-bound `evidence_refs` to every `RoleCandidate`. Role alternatives now:

- cite packet segments by source ID, segment ID, offsets, and hash;
- fail strict preflight validation if those refs drift;
- render in the intake review form with their supporting refs;
- appear in the evidence graph as `party_role_candidate` nodes with `supports_party_role_candidate` edges.

## Safety Boundary

This does not make any role final. Role alternatives remain candidates until a human confirms principal party roles. The carrier/client separation rule remains unchanged.

This does not promote party-role taxonomies into Semantic Substrate canon.

## Authority

This is local candidate-surface behavior in `LawFirm-os-intake`. Semantic Substrate remains the authority for any promoted party-role taxonomy, schema, route, or lifecycle policy.

## Validation

- Unit coverage proves role candidates carry evidence refs.
- Segment-provenance coverage validates role refs against source IDs, offsets, and hashes.
- Strict validation fails closed when a role-candidate evidence ref drifts.
- Review package coverage proves role candidate nodes and support edges appear in the evidence graph.
