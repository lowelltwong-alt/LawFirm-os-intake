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

Run `lawfirm-os-intake audit-labor-employment-executable-coverage --repo-root . --out-dir <dir>` to write `labor_employment_executable_coverage_report.json`. That report compares the executable fixture manifest against the full L&E fixture-family pack and makes partial executable coverage explicit. The current starter coverage intentionally shows selected executable source bundles plus missing executable pack cases so QA can prioritize fixture generation without treating planned gaps as hidden confidence.

The executable budget-fact binding manifest lives at `examples/synthetic/labor-employment/labor-employment-executable-budget-fact-bindings.json`. After the executable fixture audit, run `lawfirm-os-intake audit-labor-employment-executable-fact-binding --executable-fixture-report <labor_employment_executable_fixtures_report.json> --repo-root . --out-dir <dir>` to write `labor_employment_executable_fact_binding_report.json`. That report binds expected L&E budget-fact gaps to preflight source text, source inventory refs, and dry-run exception labels. It remains candidate-only evidence: it does not resolve facts, create an amount budget, train a model, or write Lake/SQLite records.

The L&E budget fact reviewed-gold spec lives at `examples/synthetic/gold/labor-employment-budget-fact-gold.json`. Run `lawfirm-os-intake validate-labor-employment-budget-fact-gold --repo-root . --out-dir <dir>` to write `labor_employment_budget_fact_gold_report.json`. That report replays the deterministic L&E budget fact audit against reviewed synthetic expectations for both blocked-critical-gaps and range-only-critical-ready cases. It is a QA gate for audit behavior only; it does not approve facts, rates, budgets, calibration, or production learning.

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
