# TRACE-2026-07-18: Replay-Aware L&E Workbench Evidence

## Decision

Expose the current Labor/Employment replay input-pack audit in the read-only budget
workbench and regenerate the upstream replay evidence fixtures from pinned synthetic
manifests. Do not create a parallel UI-only evidence contract.

## Why

The committed execution and confidence fixtures predated the current replay-scope and
case-bound confirmation contracts. The stale execution fixture no longer validated
because every case now requires an explicit `replay_scope`. The prior UI therefore
showed aggregate replay status without the newer confirmation refs, source-bundle refs
and hashes, Unicode-codepoint offset policy, or exact remaining input gaps.

## Implementation

- Regenerated learning-fixture, readiness, execution, builder-binding, input-pack, and
  confidence evidence from the pinned synthetic manifests.
- Committed the input-pack report as a read-only UI fixture.
- Added fail-closed browser-side checks for report counts, input-pack and executable
  manifest provenance, complete source-confirmation anchors, resolvable tracked refs,
  and no-write boundaries.
- Hash-pinned the input-pack manifest and propagated its digest through the reconciled
  builder-binding and confidence reports; those reports also pin the exact input-pack
  report digest. Builder reconciliation re-hashes the manifest, and confidence rejects
  a builder/input-pack ID, status, report-hash, or manifest-hash mismatch.
- Removed ignored replay-slot paths from input-pack evidence refs. The report now cites
  tracked manifests, replay inputs, confirmation artifacts, and source bundles.
- Added a dense review panel showing 35/79 ready inputs, four anchored cases,
  15 source-confirmed budget input anchors, zero invalid inputs, and unresolved
  case/loop blockers.
- Updated browser smoke and Python UI contract tests.

## Invariants

- Fixture confirmations are `synthetic_fixture_only`; they do not complete a runtime
  human gate.
- Stable evidence identity remains source ID, Unicode-codepoint offsets, and SHA-256.
- Confirmed fixture roles remain constrained to source-declared role alternatives.
- Missing inputs remain visible; partial cases are not presented as ready.
- No budget submission, matter opening, conflict conclusion, Lake/SQLite write,
  external write, calibration, or silent learning is authorized.

## Red Team

A polished panel can make synthetic confirmation look operational. The panel therefore
states the fixture-only scope at its top and repeats blocked runtime actions at its
boundary. It shows missing inputs beside each case and reports zero invalid inputs
separately from completeness.

The original UI fixtures used transient `C:\tmp` refs and stale slot counts. The
regenerated committed fixtures use repository-relative source refs where the report
contract permits them. An independent review found that input-pack evidence still
inherited ignored generated slot refs and did not hash-pin its controlling manifest.
Both findings were fixed before publication. A follow-up review then found that the
downstream reports carried hashes without comparing them and that browser validation
checked existence without proving Git tracking. Equality checks, stale/mixed negative
tests, and a tracked-file check were added before publication. Generated slots remain
visible only in the upstream execution/binding evidence where they describe candidate
placeholders, not as portable input-pack source evidence.

## Validation

- Focused UI Python contract suite via the enforced 3,600-second runner: passed, 45
  tests.
- Current replay input-pack, builder-binding, and confidence JSON artifacts validate
  against their Pydantic contracts; input-pack evidence contains no ignored generated
  refs, and direct stale/mixed-hash probes fail closed.
- Ruff check and format check: passed.
- Schema export: passed. Local repository validation reached the Rust tool-ladder
  audit, then the Windows sandbox denied its temporary-directory write; GitHub Linux
  CI is required for that environment-sensitive check.
- TypeScript build and JavaScript syntax checks: passed.
- The first exact-head Linux CI run completed 1,109 tests and identified two stale
  generated-fixture expectations rather than runtime defects: the reconciled replay
  gap count remained asserted as 51 instead of 21, and the Rust fixture manifest did
  not yet pin the refreshed UI bundle sources. The expectation was corrected and the
  UI bundle plus Rust manifest were regenerated with the deterministic fixture-refresh
  command; the refreshed manifest verifies 38 source files.
- The focused local rerun passed all 50 tests that do not request `tmp_path`. Seven
  `tmp_path` tests could not enter setup because the Windows sandbox denied traversal
  of both global and explicitly created base-temp directories after pytest assumed
  ownership. Exact-head Linux CI remains the merge gate for those seven tests.
- The browser trust assertion permits only the existing
  `validation_suite_evidence_passed_with_dirty_worktree` blocker and fails on any
  additional contract failure; a clean validation receipt remains a later gate.
- Local Vite bundling: environment-blocked after TypeScript by Windows child-process
  `spawn EPERM`; GitHub Linux browser CI is required on the final head.
- DAD preflight was attempted and failed because the central DAD decision-trace ledger
  denied writes. No DAD repository or central ledger was modified.

## Authority

LawFirm-os-intake owns only this synthetic candidate/evaluation evidence and read-only
presentation. Semantic Substrate remains canonical authority; Orchestrator owns runtime
human pauses and execution; Exception Lake owns admission and persistence.
