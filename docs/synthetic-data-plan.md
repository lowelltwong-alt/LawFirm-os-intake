# Synthetic Data Plan

## Purpose

Synthetic data tests full legal workflow behavior that public data cannot safely or accurately provide.

## Fixture families

- carrier assignment with one or multiple insureds;
- coverage inquiry versus defense assignment;
- demand received;
- complaint/summons notice;
- private help request;
- random correspondence dump;
- party list with aliases and unknown roles;
- missing or unread attachment;
- duplicated/quoted email chain;
- ambiguous corporate family;
- unknown jurisdiction;
- relative deadline without trigger date;
- conflicting role statements;
- prompt injection in source text;
- high-volume ingestion proxy for source/segment scale profiling;
- budget template with rates;
- budget template without rates;
- client/carrier guideline conflicts;
- matter type not supported by a budget template.
- north-star messy bundle combining duplicate text, missing attachment, role ambiguity, prompt injection, missing fields, deadline candidates, conflict seed, budget proposal, safety gate, and final blockers.
- labor/employment budget fixture-family pack covering discrimination/harassment, retaliation/wrongful termination, wage-hour, ADA/FMLA, restrictive covenant, EPLI carrier assignment, class/collective/PAGA-style, and administrative-exhaustion families across clean, messy-thread, missing-attachment, and adversarial variants.

## Gold labels

Gold should be reviewed and versioned for:

- source boundaries;
- party strings and aliases;
- acceptable role candidates;
- top-three matter candidates;
- mandatory missing-information fields;
- escalation triggers;
- human-confirmed end state;
- conflict seed terms;
- budget arithmetic;
- assumptions and exclusions.
- north-star review package completeness.

Reviewed synthetic gold files live under `examples/synthetic/gold/`. They are local evaluation gates only. `fixture_gold_report.json` proves whether a specific run matched reviewed expectations; it does not promote labels, roles, event classes, or budgets into canon. The current reviewed gold set includes the north-star priced demo and a carrier-assignment hours-only budget-mode fixture.

The L&E fixture-family pack lives at `examples/synthetic/labor-employment/labor-employment-budget-fixture-family-pack.json`. Run `lawfirm-os-intake audit-labor-employment-fixture-family-pack --out-dir <dir>` to write `labor_employment_fixture_family_pack_report.json`. That report checks family/variant coverage, configured fact needs, budget-driver dimensions, blocked/range-only expectations, adversarial holdout exclusion, and no-write/no-calibration boundaries.

The first executable L&E fixture manifest lives at `examples/synthetic/labor-employment/labor-employment-executable-fixtures-manifest.json`. Run `lawfirm-os-intake audit-labor-employment-executable-fixtures --repo-root . --out-dir <dir>` to write `labor_employment_executable_fixtures_report.json`. That report runs selected synthetic source bundles through deterministic preflight and checks pack links, source-signal terms, missing/duplicate source inventory, prompt-injection/prohibited-transition exception labels, and no-write boundaries. It does not perform L&E budget fact extraction or authorize amount budgeting; it proves that the selected inbound fixture files are executable preflight inputs before the next fixture-binding slice.

## Data generation rules

- clearly label all names/domains/claims as synthetic;
- never transform a real client matter by simple name replacement;
- avoid copying real demand letters or client guidelines;
- generate adversarial variants separately from gold;
- keep hidden holdout fixtures outside model-visible public prompts when evaluating;
- record generator version and seed;
- inspect for accidental real-person or real-company collisions before release.

## Same-input counterfactual suite

Run identical source text under multiple practice profiles. The suite must assert that evidence is stable while rankings may change.
