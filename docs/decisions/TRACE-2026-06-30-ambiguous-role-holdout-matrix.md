# TRACE-2026-06-30 - Ambiguous Role Holdout Matrix

## Context

The fixture-expansion manifest had one ambiguous-role holdout that proved a
misleading carrier sender did not become observed client identity. The remaining
Phase 1 safety gap was broader carrier/client separation across sender, payer,
third-party administrator, insured, affiliate, driver, and claimant roles.

## Decision

Add `holdout-carrier-client-role-matrix.json` and register it as a second
`ambiguous_roles` holdout. The fixture uses synthetic source text plus
candidate-only role hints to keep these roles separate:

- carrier / payer / instructing source;
- third-party administrator / instructing source;
- insured / prospective represented client;
- affiliate / document custodian;
- driver witness / insured driver;
- claimant / adverse party.

The regression test verifies that the carrier sender is not emitted as a
prospective represented client, that every role alternative has source-bound
evidence refs, and that role ambiguity becomes only a dry-run workflow
escalation for human confirmation.

## Red-Team Notes

- Carrier, payer, and TPA labels must not silently become client identity.
- Insured, affiliate, driver, and claimant labels must not clear conflicts,
  authorize representation, open a matter, or authorize budget submission.
- Ambiguous role candidates are evidence pressure, not a representation decision.
- The fixture remains synthetic, candidate-only, and non-authoritative.

## Validation

- `python scripts/run_full_pytest.py tests/test_source_inventory_and_review.py tests/test_synthetic_fixture_expansion.py -q`
- `python scripts/validate_repo.py`
