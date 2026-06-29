# TRACE: Structured Model Comparison Gate

Date: 2026-06-24

## Context

The intake CLI already accepted `--adapter structured-model` and emitted a dry-run
`model_adapter_report.json` with prompt hashes, zero model calls, denied tools,
typed JSON requirements, independent critic requirement, and human gates.

That proved the provider boundary but did not yet prove the roadmap requirement
that a structured-model adapter be compared against deterministic output and
reviewed synthetic gold.

## Decision

Keep `structured-model` as a synthetic-only dry-run adapter. Do not add a live
provider call, network access, external writes, production connector access, real
data approval, or model authority.

After preflight packet assembly, finalize `model_adapter_report.json` with:

- typed JSON validation against the intake preflight packet model;
- deterministic baseline projection hash;
- structured dry-run candidate hash;
- comparison status and basis;
- reviewed synthetic-gold report status;
- fail-closed behavior when `--adapter structured-model` is selected without a
  passing `--fixture-gold` report.

The structured candidate is a local deterministic projection for boundary
testing only. Deterministic workers remain authoritative.

## Authority Boundary

This remains local candidate behavior in `LawFirm-os-intake`. Semantic Substrate
remains the authority for promoted schemas and model/provider policy.
Orchestrator remains the future runtime owner for model routing and execution.
Skills Registry remains the future owner for promoted skill trust records.

## Out Of Scope

This does not add live model calls, provider credentials, network access,
external writes, production connectors, real data, conflict clearance, budget
approval, budget submission, matter opening, docketing, canonical schema IDs,
route IDs, event classes, or sibling repo writes.

## Verification

- `python -m pytest tests/test_model_adapter_report.py -q` - passed
- `python -m ruff check src tests scripts` - passed

