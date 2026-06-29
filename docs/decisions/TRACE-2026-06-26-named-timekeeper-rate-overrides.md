# Decision Trace

## Situation

Carrier guideline and rejection loops need a place to distinguish title rates
from approved individual timekeeper rates. Without that distinction, a later
carrier rejection for a named timekeeper could be misclassified as a generic
role-rate problem.

## Decision

Add a local candidate `NamedTimekeeperRate` model, synthetic
`named_timekeeper_overrides` in `config/synthetic-carrier-rate-card.yaml`, and
budget-line support for optional synthetic `timekeeper_id` values.

Resolution precedence is:

1. named timekeeper override for a matching synthetic task `timekeeper_id`;
2. carrier x state x title rate;
3. carrier title default when present;
4. practice-profile flat fallback;
5. absent rate / hours-only.

The default demo templates do not name timekeepers, so north-star budget totals
remain role-rate based. A dedicated synthetic test opts into a fake timekeeper ID
and proves the named override wins for that task only.

## Non-decision

This does not add real firm timekeepers, real negotiated rates, billing
authority, a private rate store, carrier submission, Lake admission, connector
reads or writes, or canonical rate contracts.

## Authority impact

This is local candidate/eval work in `LawFirm-os-intake`. Semantic Substrate
owns any promoted rate/timekeeper contract. Orchestrator owns future runtime
private-profile resolution. Exception Lake owns admitted rejection or correction
evidence.

## Evidence

- `NamedTimekeeperRate` is exported as a local schema.
- `config/synthetic-carrier-rate-card.yaml` marks all rates as synthetic and adds
  fake named-timekeeper overrides.
- `tests/test_carrier_rates.py` verifies state-filtered override resolution.
- `tests/test_named_timekeeper_rates.py` verifies task-level named override
  precedence and ordinary role-rate fallback.

## Alternatives rejected

- Apply named timekeepers to the default demo template: rejected because it would
  churn the north-star totals and hide the behavior inside the main fixture.
- Store real approved rates: rejected because real firm/carrier rate data is
  prohibited in this repo.
- Treat named-timekeeper rejection learning as automatic profile mutation:
  rejected because learning remains candidate-only and owner-reviewed.

## Risks and rollback

The risk is that a reviewer mistakes synthetic named overrides for production
rate governance. The data is fake, the schema is candidate-only, and default
workflows remain role-rate based unless a synthetic task opts in. Rollback is
limited to removing the model field, synthetic config entries, tests, and docs.

## Validation

Run focused rate and named-timekeeper tests, then full repo validation before
push.

## Human gates

Human PR review remains required. Real named timekeepers, private rate storage,
profile mutation, billing use, or carrier submission require owning-repo
governance and runtime approval.
