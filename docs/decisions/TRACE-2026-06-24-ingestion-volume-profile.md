# TRACE-2026-06-24 - Ingestion Volume Profile

## Situation

High-volume intake may eventually make deterministic document walking, source inventory, segmentation, hashing, and evidence-ref emission expensive enough to justify a Rust hot-path adapter. The repo already emits `ingestion_result.json` as the Python parity oracle and `rust_ingestion_readiness_report.json` as a per-run parity-readiness check.

That still left a gap: there was no machine-readable per-run signal showing whether source and segment scale had grown enough to require profiling before a Rust proposal.

## Decision

Add `IngestionVolumeProfile` and write `ingestion_volume_profile.json` during preflight.

The profile records:

- source count and source character volume;
- segment count and segment character volume;
- source type, source state, and segment type counts;
- local profiling thresholds;
- scale signals that require profiling before any Rust adapter proposal;
- `rust_adapter_proposal_state`;
- required Rust transition gates;
- `rust_replacement_allowed=false` in every case.

The profile is also carried into the final review manifest and package completeness checks.

## Non-decision

This does not add Rust, FFI, concurrency, benchmarking, model calls, provider adapters, connector writes, legal classification, conflict clearance, budget approval, Exception Lake admission, or canonical platform authority.

This also does not claim that any threshold proves Rust is required. Thresholds only say that profiling is required before proposing Rust.

## Authority impact

This is a local intake candidate artifact. Semantic Substrate remains the canonical authority for promoted contracts. Orchestrator remains the future runtime owner. Intake remains a reference workflow and evaluation repo.

## Evidence

- ADR-004 already says Rust must wait until profiling shows ingestion is the bottleneck.
- The Python reference ingestion artifact already carries the source inventory, coverage summary, segments, and segment evidence refs needed for deterministic scale profiling.
- The new synthetic high-volume proxy fixture crosses the local source-count profiling threshold without introducing real data or a second runtime.

## Alternatives rejected

- Add Rust now: rejected because profiling has not shown ingestion is the bottleneck and a second runtime would increase review burden.
- Use wall-clock timings in the preflight artifact: rejected because CI and local machines vary; this slice needs deterministic acceptance evidence.
- Leave volume pressure as prose only: rejected because future Rust decisions need machine-readable run evidence.

## Risks and rollback

The main risk is treating a local threshold as production proof. The artifact text and fields avoid that by requiring profiling and keeping `rust_replacement_allowed=false`.

Rollback removes the profile artifact, manifest key, schema export, smoke checks, and tests. The existing Python parity oracle and Rust readiness report would remain intact.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - 1 file reformatted, 48 files left unchanged
- `python -m pytest tests/test_ingestion_boundary.py tests/test_review_package.py tests/test_north_star_demo.py -q` - passed
- `python scripts/export_schemas.py` - exported 23 schemas
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 69 tests
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - 49 files already formatted
- `python scripts/validate_repo.py` - passed after generated test/lint caches were cleaned
- `bash -lc 'export PATH="/c/Users/lowel/AppData/Local/Programs/Python/Python312:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed

## Human gates

The profile does not authorize Rust replacement, legal conclusions, conflict clearance, engagement, docketing, billing, budget submission, matter opening, connector writes, or Exception Lake admission.
