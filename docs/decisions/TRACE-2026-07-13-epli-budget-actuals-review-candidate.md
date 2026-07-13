# Trace: EPLI Budget-To-Actuals Review Candidate

## Decision

Add a deterministic, synthetic-only EPLI phase/code actuals fixture to the existing budget-actual comparison and variance-ledger path. Surface its result in the pilot dossier and read-only workbench as a human-review candidate, not as calibration or an approved budget conclusion.

## Why

The EPLI pilot already demonstrated intake linkage ambiguity, a withheld proposed budget, carrier rejections, and an append-only appeal outcome. It did not demonstrate that a proposed budget could later be compared with actual costs while preserving the same no-write and no-silent-learning boundaries.

## Evidence And Math

- Candidate proposal: `$54,090` (`$49,990` fees and `$4,100` expenses).
- Synthetic actuals: `$60,350` (`$54,150` fees and `$6,200` expenses).
- Total variance: `$6,260` (about `11.57%`).
- Discovery and mediation phase/code variance exceed the existing review threshold. Phase and code amounts reconcile exactly.

The fixture is source-marked `synthetic`, has no real client, matter, privileged, or billing-connector data, and remains `non_authoritative`.

## Boundaries

- Intake reads a local synthetic JSON fixture only.
- The dossier writes only to its requested local run directory.
- No billing connector, carrier portal, DAD runtime, Exception Lake, SQLite, matter opening, conflict clearance, budget submission, calibration, profile mutation, template mutation, guideline mutation, or silent learning occurs.
- The candidate exception labels are not Lake admissions. The Exception Lake runtime remains the owner of any future append-only admission.

## Red Team

- A variance is not proof that the proposal was wrong or that any driver should change.
- Carrier rejection dollars are separate from actual-cost variance and are not combined.
- The generic cross-repo proof remains boundary evidence, not evidence about this synthetic matter.
- The workbench must display the actuals as synthetic and review-pending, never as a recovered production billing record.

## Validation

- Focused pilot-story, outcome-replay, and UI contract tests.
- Schema export and repository validation.
- Full deterministic suite with the repository long timeout policy.
