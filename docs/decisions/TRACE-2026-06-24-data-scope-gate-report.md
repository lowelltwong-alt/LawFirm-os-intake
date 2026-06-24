# TRACE-2026-06-24 - Data-Scope Gate Report

## Situation

The starter workflow already rejected non-synthetic source bundles, but the proof was implicit in runtime control flow. As the repo prepares for larger document intake and a possible future Rust ingestion hot path, the authorization boundary needs to be explicit, typed, reviewable, and checked before raw input storage or derived ingestion artifacts are written.

## Decision

Add a local `DataScopeGateReport` and emit `data_scope_gate_report.json` during preflight before `raw_input.json`.

The report records:

- `synthetic_only` runtime mode;
- source `data_origin`;
- real client, real matter, and privileged-data flags;
- public-data direct-ingestion posture;
- `raw_payload_written=false` at the gate;
- `external_writes_performed=false`;
- policy refs and deterministic checks.

If any check fails, preflight writes the blocked gate report and a blocked `data_origin_gate` ledger event, then stops before raw input storage, source inventory, segmentation, candidate extraction, review-form generation, Exception Lake candidates, or budget-stage outputs.

Passing reports are carried into the preflight packet, budget manifest, final review package, safety gate, review-package completeness report, starter audit, CLI output, and schema export.

## Non-decision

This does not authorize real client data, real matter data, privileged data, public-data runtime ingestion, production connectors, provider calls, Exception Lake admission, SQLite writes, conflict clearance, engagement decisions, matter opening, docketing, budget submission, or canonical platform promotion.

This also does not add Rust. It prepares the boundary a future Rust ingestion adapter would have to respect.

## Rust impact

Python remains the reference runtime. Any future Rust worker may run only after a passing `DataScopeGateReport`, may cover only deterministic ingestion mechanics, and must prove parity with the Python `IngestionResult` on source inventory, coverage, structural segments, offsets, hashes, and segment evidence refs before replacement can be proposed.

## Authority impact

This is a local intake candidate/evaluation artifact. Semantic Substrate remains the authority for promoted data-scope contracts and governance. Orchestrator remains the future runtime owner for gate ordering, execution passports, and adapter selection. Exception Lake remains the future owner for admitted evidence persistence.

## Validation

- Unit coverage proves synthetic bundles pass the gate and non-synthetic bundles fail before raw input or packet output.
- Review-package, completeness, safety-gate, north-star, CLI, preflight, starter-audit, schema-export, and smoke coverage now require the report to be present and carried forward.
