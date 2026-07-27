# TRACE-2026-06-24 - Rust Transition Gates

## Situation

The repo already emitted a Python `IngestionResult` parity oracle, an `IngestionVolumeProfile`, and a `RustIngestionReadinessReport`. That prepared the ingestion boundary for a future Rust adapter, but the volume profile did not explicitly say which transition gates must be satisfied before Rust can be proposed.

The user raised a realistic scale concern: a large amount of document intake may make Rust necessary when compute becomes constrained. The project should prepare for that without adding a second runtime before profiling justifies it.

## Decision

Extend `IngestionVolumeProfile` with:

- `compute_pressure_signals`;
- `required_performance_profile_dimensions`;
- `candidate_rust_hot_path_scope`;
- `rust_adapter_proposal_state`;
- `required_rust_transition_gates`.

The profile now distinguishes starter-scale runs from profile-candidate runs:

- `not_warranted` when local scale thresholds are not crossed;
- `profiling_required_before_adapter_proposal` when local thresholds are crossed.

The final review package renders the ingestion profile decision, Rust adapter proposal state, scale signals, compute pressure signals, required benchmark dimensions, candidate hot-path scope, replacement flag, and transition gates so reviewer-facing artifacts show the Rust posture without requiring a JSON inspection.

Add `docs/rust-ingestion-transition-plan.md` to define the approved boundary, forbidden scope, transition gates, future PR acceptance criteria, and rollback posture.

## Non-decision

This does not add Rust, FFI, concurrency, benchmarking, a provider call, a second parser, connector writes, legal classification, conflict clearance, engagement, docketing, matter opening, budget approval, Exception Lake admission, or platform canon.

Crossing a local volume threshold does not prove Rust is required. It only requires profiling before a Rust adapter proposal.

## Authority impact

This is a local intake candidate/evaluation contract. Semantic Substrate remains the authority for promoted contracts. Orchestrator remains the future runtime owner for adapter selection and execution. Intake remains a reference workflow and evaluation repo.

## Validation

Completed on 2026-06-24:

- `python -m ruff format src tests scripts` - passed after retrying a transient Windows file lock
- `python -m pytest tests\test_ingestion_boundary.py tests\test_review_package.py tests\test_north_star_demo.py tests\test_fixture_gold.py tests\test_hours_only.py -q` - passed
- `python scripts\export_schemas.py` - exported 26 schemas
- `python -m pytest -q` - passed
- `python -m pytest --collect-only -q` - collected 76 tests
- `python -m ruff check src tests scripts` - passed
- `python -m ruff format --check src tests scripts` - passed
- `python scripts\validate_repo.py` - passed after generated caches were cleaned
- `bash -lc 'export PATH="<python-install-dir>:$PATH"; export PYTHONDONTWRITEBYTECODE=1; export PYTHONPATH=src; bash scripts/smoke_demo.sh'` - passed
