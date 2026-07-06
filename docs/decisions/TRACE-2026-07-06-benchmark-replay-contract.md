# TRACE 2026-07-06: Benchmark Replay Contract

## Status

Accepted as a local candidate-only intake slice.

## Context

Fable's rate benchmark kernel identified a laundering risk: public or synthetic
benchmark numbers can look like rate authority if they enter budget math without a
clear boundary. Intake may need benchmark context for review, but Legal Knowledge
Runtime owns retrieval, grading, and pinned public-source snapshots.

The repo already had `RateBenchmarkCell` and `BenchmarkSnapshotManifest` plus a
minimal helper that checked whether budget `estimate_basis_refs` pointed to cells.
It did not have a durable replay report proving that a serialized budget and pinned
benchmark snapshot obeyed the no-laundering rules.

## Decision

Add `audit-benchmark-replay` and `benchmark_replay_report.json`.

The replay validates:

- snapshot schema and pinned content hash;
- refusal of snapshots declaring real negotiated rates;
- deterministic effective-grade/staleness methodology
  `benchmark_effective_grade.v0_1`;
- benchmark cell provenance fields, hash, quote span, license note, and proxy-bias
  note;
- refusal of carrier-panel-like benchmark cells inside intake replay;
- valid/missing budget benchmark context refs;
- no budget line or calculation report may use `benchmark_cell` as rate authority;
- priced budget lines must still trace to authorized synthetic/profile rate sources;
- weak or stale cells may remain context but cannot create band-pressure flags.

## Boundary

Benchmark cells never price a budget line. They are context-only evidence for
human review. This slice does not add public retrieval, real rate ingestion, carrier
panel rates, rate calibration, benchmark blending, budget submission, matter opening,
Lake/SQLite writes, or canonical schema promotion.

The pinned synthetic snapshot in `examples/synthetic/benchmarks/` contains no public
payloads and no real rates.

## Validation

Focused validation:

```text
python scripts\export_schemas.py
python scripts\run_full_pytest.py tests\test_benchmark_replay.py tests\test_budget_coherence.py -q
python -m ruff check src tests scripts
```

The new tests cover ready replay, CLI output, missing benchmark refs, hash mismatch,
rejected context refs, real-rate refusal, carrier-panel candidate refusal,
benchmark-as-rate laundering, hours-only preservation, weak-grade context
suppression, and effective-grade staleness downgrades. The local harness is
predeclared at `harnesses/benchmark-replay.local.yaml`.

## Follow-Ups

- Wire the replay report into the UI review bundle after this artifact stabilizes.
- Let Legal Knowledge Runtime own any governed public retrieval and grading workflow.
- Keep BK5b headline normalization paused until explicit human approval.
