# TRACE: Synthetic L&E Pilot Review Story

## Decision

Add one typed, deterministic pilot dossier that composes existing synthetic L&E
artifacts into a source-bound review path. The dossier uses a clean EPLI
assignment because it exercises the core first-practice-area problem: carrier,
TPA, payer, insured, prospective represented client, claimant, and opposing
counsel must remain separate candidates while the firm still needs a practical
budget review packet.

## Why This Slice

The repository already had strong individual artifacts for L&E fact coverage,
matter-link review, candidate budgets, carrier rejection/appeal evidence, and
owner handoff proof. They appeared as separate QA surfaces. A human pilot
reviewer needs to see their dependency order for one assignment without being
asked to infer that order from many reports.

The new report therefore shows:

1. exact synthetic source identities and hashes;
2. a resolved single candidate matter link with no official matter number;
3. explicit candidate-role separation;
4. retained proposed budget math that is withheld pending link and role review;
5. no carrier-compliant projection when a matching pinned candidate guideline
   IR is unavailable;
6. synthetic rejection and appeal outcome evidence as review input only;
7. no actuals and therefore no learning candidate; and
8. a generic owner-contract proof clearly labeled as a boundary proof, not
   matter evidence.

## Boundaries

- All source material and outcome records are synthetic.
- The dossier does not call Upfront, a carrier portal, email, billing, or a
  connector.
- It does not open a matter, clear conflicts, submit a budget or appeal, write
  to the Exception Lake/SQLite, or change a benchmark, profile, template, or
  policy.
- The carrier projection is intentionally `not_available` rather than inferred
  from a different carrier's candidate rule IR.
- Budget-to-actual learning is intentionally `not_observed` until a source-bound
  actuals artifact exists.

## Acceptance Evidence

- `build-pilot-review-story` emits only local run-directory JSON and markdown.
- The report validates against `PilotReviewStoryReport` and records source
  hashes, a candidate-only matter state, the withheld-budget gate, missing
  projection gate, synthetic carrier lifecycle amounts, and no-write flags.
- Tests prove deterministic replay, generic-proof scope separation, and all
  prohibited authority flags remain false.

## Red Team

- A passed generic cross-repo proof can be accidentally read as proof of a
  particular matter. The dossier names its scope explicitly and keeps the proof
  stage separate from case evidence.
- A priced synthetic budget could look actionable. The dossier displays the
  number only with the withheld-budget gate and never marks it submittable.
- Rejection/appeal amounts can tempt silent guideline or template changes. The
  actuals-and-learning stage stays unavailable until a source-bound actuals
  artifact and reviewed owner process exist.
- A carrier guideline excerpt is not a pinned rule IR. The projection stage
  stays unavailable instead of producing a mismatched delta.
