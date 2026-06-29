# TRACE-2026-06-24 - Public Data Catalog Boundary

## Situation

The starter Definition of Done requires public data to be cataloged but not directly ingested. The repo already documented that posture in `docs/public-data-test-plan.md`, `examples/public/README.md`, `examples/public/catalog.yaml`, and `config/data_policy.yaml`.

That was still too easy to drift: a future edit could mark a public catalog entry as directly ingestible or add downloaded public payload files under `examples/public/` while the north-star demo still passed.

## Decision

Add deterministic public-data boundary validation.

The validator now requires:

- `config/data_policy.yaml` to stay in `synthetic_only` runtime mode;
- allowed runtime origins to remain only `synthetic`;
- `public_data_posture.status=planning_only`;
- `public_data_posture.direct_ingestion_allowed=false`;
- `examples/public/catalog.yaml` to stay `planning_only`;
- every public catalog entry to have `direct_runtime_ingestion=false`;
- catalog entries to remain metadata records without raw payload fields;
- `examples/public/` to contain only the README and catalog.

`scripts/validate_repo.py` runs this check before tests. The starter release audit also emits `public_data_catalog_is_metadata_only`, so the release smoke proves Definition of Done item 17 with the generated north-star artifacts.

The data-scope gate remains the runtime enforcement point: `data_origin: public_reference` blocks before `raw_input.json`, source inventory, segmentation, review forms, Exception Lake candidates, or budget-stage outputs.

## Non-decision

This does not add public-data ingestion, public-record processing, public-source connectors, legal retrieval, production corpora, external writes, real party records, real matter records, real client data, or Exception Lake admission.

Public data remains a planning input for source structure and synthetic fixture design only.

## Authority impact

This is a local intake validation and audit invariant. Semantic Substrate remains the authority for promoted data-scope policy. Legal Knowledge Runtime remains the future owner for any governed public/legal retrieval adapter. Orchestrator remains the future owner for runtime gate ordering and adapter selection.

## Validation

- Focused tests validate the current catalog and fail a catalog entry that allows direct runtime ingestion.
- Focused preflight coverage proves `public_reference` source bundles block at the data-scope gate before raw input storage.
- Repo validation, starter audit, and smoke coverage require the metadata-only public-data boundary.
