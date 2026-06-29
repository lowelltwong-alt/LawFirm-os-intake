# Decision Trace: Exception Lake Handoff Manifest

## Context

The intake workflow already emitted dry-run `ExceptionLakeCandidate` rows and readiness reports. That proved candidate safety, but reviewers still had to inspect JSONL rows to understand which local labels mapped to broad future Lake classes, what support mode each label had, and whether the workflow had accidentally crossed into persistence.

The v1.0 goal needs exception-aware review packages. It also needs a clear answer to the SQLite question: Intake can prepare evidence for a future Lake, but SQLite admission and append-only storage belong to `LawFirm-os-exceptions-lake-runtime`.

## Decision

Add `ExceptionLakeHandoffManifest` as a local, non-authoritative artifact.

The manifest records:

- actual local exception labels emitted in the run;
- broad Lake class for each label;
- candidate counts and IDs;
- source-inventory, source-evidence, structured-ref, and blocked-state support modes;
- candidate file refs and paired readiness report ref;
- target runtime owner;
- `mapping_review_required=true`;
- `canonical_promotion_required=true`;
- `sqlite_write_performed=false`;
- `external_writes_performed=false`.

Write the manifest in three paths:

- preflight;
- confirmed budget package with combined preflight and budget candidates;
- failed budget-precondition path before raising, without emitting budget outputs.

Surface the confirmed-budget manifest in the final review package and make it a required package artifact.

## Authority Impact

This remains a local intake candidate/evaluation artifact. It does not promote canonical event classes, route IDs, Lake schemas, SQLite tables, admission policy, or persistence authority.

Semantic Substrate remains the canonical authority for promoted labels and mapping doctrine. Orchestrator remains the future runtime handoff owner. Exception Lake remains the append-only evidence and SQLite/admission owner.

## Alternatives Considered

- Use only `exception_lake_readiness_report.json`: rejected because readiness checks prove safety but do not summarize local label/class/support coverage for reviewers.
- Write a SQLite file from intake: rejected because it would invert the evidence-plane boundary and create persistence authority in the vertical repo.
- Add a broad new canonical exception taxonomy here: rejected because this repo owns candidate/eval surfaces only.

## Tests

Planned and run for this slice:

- focused manifest tests for preflight, budget-combined, and blocked-budget paths;
- north-star package assertions for manifest refs and review text;
- schema export;
- full repo tests and smoke demo.
