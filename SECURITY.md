# Security

This repository contains a synthetic-only, local-first reference workflow. It is not a production
legal system and holds no real client, matter, employee, carrier, or firm-confidential data.

## Data boundary

Do not place in this repository:

- secrets, credentials, API keys, or tokens;
- real client, matter, party, or claim records;
- privileged material or attorney work product;
- negotiated rates, carrier submission authorization state, or firm-confidential guidelines;
- production endpoints or connector configuration.

Use an approved secret manager for secrets and keep only non-secret references in tracked files.
`.gitignore` blocks `context/firm-private/`, `secrets/`, `.env*`, `*.pem`, and `*.key`; treat that
as a convenience, not as access control.

## Synthetic-data assertion

Every fixture under `examples/` is synthetic. Contact identifiers in fixtures use reserved,
non-resolvable domains (`.example`, `.test`, `.invalid`) or appear deliberately as negative-test
inputs for the synthetic-identity guard (`tests/test_rust_synthetic_identity_guard.py`), which
asserts that non-reserved identifiers are rejected.

## Scope limits

This repository does not submit budgets, deliver documents to a client or carrier, write to a
production system, dock deadlines, or reach a conflicts conclusion. Model output is proposal-only
and requires accountable human review before it means anything.

## Reporting

Report security issues by opening an issue that describes the problem without including private
data or exploit payloads beyond what is needed for local reproduction. If a report would require
disclosing sensitive material, say so in the issue and request a private channel instead of pasting
it.
