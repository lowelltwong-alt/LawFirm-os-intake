# Expected Demonstration Artifacts

These files are illustrative outputs from the synthetic carrier-assignment demo. IDs are run-specific and are not canonical identifiers.

Expected boundaries:

- conflict output is a search seed and states `no_conflict_conclusion`;
- budget state is `proposed_for_human_review`;
- budget is `not_authorized_for_client_submission`;
- matter-opening readiness is `blocked_pending_conflicts_and_engagement`.

The north-star demo fixture is `examples/synthetic/inbound/north-star-messy-intake.json` with confirmation template `examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json`. It is the acceptance fixture for one-command review-package generation.

The reviewed synthetic gold gate for that demo is `examples/synthetic/gold/north-star-messy-intake.fixture-gold.json`. Running the CLI with `--fixture-gold` writes `fixture_gold_report.json`; a passing report is local evaluation evidence only and does not create canonical labels or legal conclusions.

The hours-only budget-mode gold gate is `examples/synthetic/gold/carrier-assignment-medmal-hours-only.fixture-gold.json` with profile `context/synthetic-profiles/insurance-defense-hours-only.yaml`. It proves missing rates produce an internal hours-only proposal and `budget_hours_only_missing_rates`, not invented fees.
