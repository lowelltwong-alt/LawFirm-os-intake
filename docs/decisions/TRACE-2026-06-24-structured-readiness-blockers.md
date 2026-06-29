# TRACE-2026-06-24 - Structured Readiness Blockers

## Situation

The final review package already showed that the workflow ended in `blocked_pending_conflicts_and_engagement`, but the blocker reasons were mostly plain string codes. That made the blocked posture visible, but not fully supported in the same way as budget assumptions, conflict-search terms, and exception records.

The north-star demo should tell a reviewer exactly why the workflow is blocked from opening a matter, creating a workspace, accepting engagement, clearing conflicts, or submitting a budget.

## Decision

Extend `MatterOpeningReadiness` with:

- `blocker_details`;
- `prohibited_action_details`.

Blocker details use structured workflow-policy refs because these boundaries are governance and workflow facts, not observed source facts. Prohibited-action guardrails use structured refs to `workflow/prohibited-transitions.yaml`.

The final review package renders those details inline, the evidence graph adds matter-opening blocker and prohibited-action guardrail nodes, and the safety gate fails closed if blockers or prohibited actions lose structured support.

Export `matter-opening-readiness.schema.json` so the readiness packet is a candidate contract surface rather than an implied JSON convention.

## Non-decision

This does not clear conflicts, approve engagement, approve a budget, open a matter, create an iManage workspace, submit a budget, write to billing, docket deadlines, write to Exception Lake, or promote canonical platform schema.

This also does not move matter-opening authority into intake. Orchestrator remains the future runtime owner, and Semantic Substrate remains the authority for promoted schemas and controlled vocabularies.

## Validation

Unit coverage now verifies:

- normal budget runs include structured blocker and prohibited-action details;
- the safety gate fails when blocker support is removed;
- the safety gate fails when prohibited-action support is removed;
- review package completeness fails if the final Markdown stops rendering blocker support refs.

North-star and smoke coverage require blocker details, prohibited-action details, structured policy refs, and evidence-graph node/relationship visibility.
