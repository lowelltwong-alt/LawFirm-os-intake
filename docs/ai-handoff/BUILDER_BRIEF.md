# Builder Brief

You are taking over `LawFirm-os-intake`.

## Objective

Harden and extend a synthetic-only, local-first reference workflow from inbound legal material to a human-reviewable intake packet and legal budget proposal, while preserving LawFirm OS authority boundaries.

## Current executable slice

```bash
python -m pip install -e ".[dev]"
python scripts/validate_repo.py
python scripts/export_schemas.py
python scripts/run_full_pytest.py
bash scripts/smoke_demo.sh
```

Use `config/validation-runtime-policy.yaml` for minimum local validation
timeouts; full and focused pytest and smoke runs require a 900 second ceiling.

The code currently provides deterministic/source-hint-backed mock workers. It is intentionally not a production NLP system.

## Correct end state

The workflow should make the human faster at deciding and reviewing. It should not automate final legal or external actions.

## First constraints

- keep this repo a vertical composition/eval repo;
- preserve synthetic-only gate;
- preserve source references and hashes;
- preserve human confirmation before budget;
- preserve carrier/client role separation;
- preserve no-conflict-conclusion and no-budget-submission rules;
- keep dynamic agents and connectors out;
- use PR-sized increments with tests.

## Recommended build order

1. inspect and run current tests/demo;
2. characterize failures on the synthetic fixture suite;
3. improve structural source inventory/segmentation;
4. improve candidate schemas and deterministic validators;
5. build reviewed synthetic gold and counterfactual evals;
6. only then add provider/model adapters behind interfaces;
7. promote stable contracts to sibling repos rather than expanding local authority.

## Required output from each PR

- decision trace;
- changed files;
- tests and exact results;
- safety/authority impact;
- fixtures added;
- open risks;
- graduation target if reusable.
