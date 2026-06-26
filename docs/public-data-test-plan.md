# Public Data Test Plan

## Current posture

Public data is a **planning and source-structure input**, not a live runtime input in this starter. Existing LawFirm OS boundaries prohibit real matter data in the current MVP. Public court records are still real matters.

`examples/public/catalog.yaml` is metadata-only and every entry must keep `direct_runtime_ingestion: false`. `scripts/validate_repo.py` and the starter release audit fail closed if the catalog starts allowing direct runtime ingestion, adds payload fields, or stores non-catalog public files under `examples/public/`.

Runtime source bundles with `data_origin: public_reference` are blocked by the data-scope gate before `raw_input.json`, source inventory, segmentation, review forms, or Exception Lake candidates are written.

Run `audit-public-source-methodology` before using any public source to design new synthetic fixtures. The audit requires methodology role, safe/prohibited use classes, review gates, synthetic-conversion rules, retention policy, privacy posture, and `adapter_status=not_authorized` for every catalog entry. A passing report is still only ready for human methodology review; it does not authorize a public-source adapter or runtime ingestion.

Run `plan-public-synthetic-fixture-conversion` after a ready methodology report and before any fixture work. The conversion plan records what structure may be abstracted, what identity or payload inputs are forbidden, how identities must be replaced, and which synthetic gold/red-team checks must pass. It creates no fixture files and remains blocked until human conversion review.

Run `review-public-synthetic-fixture-conversion` after the conversion plan. The review packet gives a human reviewer recommendations, why-notes, required decisions, red-team notes, and append-only decision templates. A ready packet is not fixture approval; it still does not create fixtures, create PRs, authorize adapters, or ingest public records.

## Recommended sources

### CourtListener / RECAP

Use to understand public docket, party, attorney, filing, and document metadata structures. Do not bulk-commit documents. Preserve source URLs/IDs and review licensing/terms before an adapter is built.

### Federal Judicial Center Integrated Database

Use codebooks and aggregate case metadata to understand fields such as nature of suit, disposition, dates, and procedural posture. Use for schema mapping and synthetic distribution design, not legal conclusions.

### Enron email corpus

Use only for email structure, threading, participant, signature, quote, duplicate, and messy-correspondence stress tests. It is not a legal-intake corpus and attachments are not a substitute for law-firm data.

### SEC EDGAR and other public filing systems

Potential future sources for document-structure and entity extraction tests. They do not test confidential intake, conflicts, or insurance-defense roles.

### NHTSA public crash data

Use field dictionaries and aggregate/public crash records to design auto-liability synthetic distributions and test date, location, vehicle, and participant extraction. Do not treat crash records as law-firm intake, and do not infer representation or liability.

### National Practitioner Data Bank Public Use Data File

Use only after a specific privacy and use review, primarily for aggregate medical-malpractice distribution and schema design. It cannot establish firm-specific intake accuracy, legal merits, party roles, or budget assumptions. Never use it to identify or enrich a real intake matter.

## Safe sequence

1. Catalog source, fields, terms, license, retention, and privacy risks.
2. Map fields to local candidate schemas without downloading content into the repo.
3. Generate a public synthetic fixture conversion plan.
4. Build and review the public synthetic fixture conversion review packet.
5. Create non-identifying synthetic fixtures that preserve document structure in a separate PR only after approval.
6. Run extraction and segmentation evals.
7. Compare against hand-labeled synthetic gold.
8. Seek governance approval before any direct public-record processing.

## What public data can test

- source inventory;
- docket/document structure;
- party and attorney extraction mechanics;
- entity normalization;
- date extraction;
- citation/provenance preservation;
- email threading mechanics.

## What it cannot establish

- production confidentiality controls;
- firm-specific intake accuracy;
- privilege handling;
- carrier/insured/client relationship accuracy;
- conflicts workflow correctness;
- budget template fit;
- readiness for real client data.

See `examples/public/catalog.yaml`.
