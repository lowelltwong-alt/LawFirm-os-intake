# Legal Budget Design

## Purpose

Translate a human-confirmed intake into a transparent, reviewable budget proposal. The proposal supports internal decision-making and later approved client/carrier workflows. It is not an engagement, fee agreement, or submitted budget.

## Preconditions

- intake packet exists;
- human confirmation binds to the exact intake packet;
- human has confirmed matter family and representation posture;
- human confirmation status is `confirmed`;
- human confirmation includes source-bound decision evidence refs;
- principal party roles are confirmed or unresolved roles are explicit;
- confirmed principal party roles include source-bound evidence refs;
- an approved practice template exists;
- rate/guideline source state is known;
- conflicts and engagement remain separate blockers.

The starter persists these runtime checks in `budget_precondition_report.json`. If the gate fails, the run records a blocked ledger event and dry-run Exception Lake candidate, then stops before conflict seed, budget proposal, readiness, safety, or review package output.

The later `safety_gate_report.json` verifies that emitted budget lines and support items still carry source-bound evidence refs or structured refs before the final review package is accepted.

## Form structure

A budget proposal contains:

1. matter and posture summary;
2. template/profile identity and version;
3. phases and tasks;
4. staffing roles;
5. estimated hours;
6. rates, or explicit hours-only state;
7. deterministic fee calculation;
8. expenses;
9. contingency;
10. assumptions;
11. exclusions;
12. unknowns;
13. budget support items with evidence refs or structured refs;
14. source references;
15. human approval state.

## Avoiding false precision

- Never infer a negotiated rate.
- Never fabricate client/carrier guidelines.
- Never make a relative deadline a fixed date without a confirmed trigger.
- Use ranges or scenario branches when the number of witnesses, experts, depositions, or trial days is unknown.
- Keep expert/vendor costs distinct from law-firm fees.
- Mark all synthetic numbers.
- Assumptions, exclusions, and unknowns must have source-bound or structured support through `budget_support_items`.
- Unknowns, missing approved templates, and missing authorized rates must emit dry-run Exception Lake candidates for human/pricing review.

## External taxonomies

UTBMS/LEDES codes may be stored as `external_code_candidate` references. They are not canonical LawFirm OS values until the Semantic Substrate adopts a mapping. Client-specific code sets remain private and versioned.

## Carrier form rendering

Template-backed `.xlsx` rendering is validation-first. Before filling an existing UTBMS budget form, the renderer writes or can write `budget_form_mapping_report.json`, which records the template hash, header locations, code-to-row mappings, original-budget write cells, L/E totals, missing or duplicate codes, and original-budget formula checks.

The renderer does not repair workbook formulas. Missing or inconsistent original-budget total, phase subtotal, task remaining, header, or budget-code mapping checks block rendering before a filled workbook is created. The filled workbook remains `proposed_for_human_review` and is not authorized for carrier or client submission.

## Budget refinement loop

Future runtime:

```text
intake-confirmed baseline
-> budget proposal
-> human approval/revision
-> actuals and variance evidence
-> Exception Lake defect/lesson candidates
-> reviewed template-change proposal
-> governed promotion
```

No runtime correction automatically rewrites the template.

## Sample med-mal defense phases

The synthetic profile demonstrates:

- intake and early case assessment;
- pleadings and initial motions;
- written/fact/expert discovery;
- dispositive motions and resolution;
- trial preparation and trial.

This is a test template, not a universal legal budget.
