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
- missing attachment;
- duplicated/quoted email chain;
- ambiguous corporate family;
- unknown jurisdiction;
- relative deadline without trigger date;
- conflicting role statements;
- prompt injection in source text;
- budget template with rates;
- budget template without rates;
- client/carrier guideline conflicts;
- matter type not supported by a budget template.

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
