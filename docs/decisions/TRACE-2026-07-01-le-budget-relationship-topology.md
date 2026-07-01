# TRACE-2026-07-01 - L&E Budget Relationship Topology

## Context

Labor/employment budgets depend on more than whether a source names a person and a
company. The reviewer needs to see whether the packet can distinguish employee or
claimant, employer or defendant entity, payer/carrier posture, individual
supervisors or managers, and joint-employer or affiliate structures before relying
on budget math.

## Decision

Extend the existing candidate-only L&E budget fact audit with a deterministic
relationship topology summary. The summary records source-bound relationship
coverage, person and organization candidate counts, unresolved relationship fact
IDs, human relationship questions, critical relationship blockers, and a budget
treatment recommendation.

The topology is derived only from the existing synthetic manifest and local
fact-needs policy. It does not create canonical party roles, confirm representation,
clear conflicts, approve a budget, or mutate any budget driver.

## Red-Team Notes

- A source-bound role candidate is not a human-confirmed fact.
- A synthetic assignment wrapper cannot become observed representation evidence.
- Missing supervisors, managers, HR actors, affiliates, joint employers, staffing
  agencies, PEOs, franchises, unions, agencies, insurers, or payers must remain
  visible as relationship gaps instead of being silently defaulted.
- If the policy adds a new entity-relationship fact without a topology bucket, the
  audit fails closed.
- The report still performs no public ingestion, training, budget submission,
  conflict conclusion, matter opening, Lake/SQLite write, external write, or silent
  learning.

## Validation

- Focused L&E budget fact tests.
- Existing L&E budget precondition gate tests.
- Repository validation suite before merge.
