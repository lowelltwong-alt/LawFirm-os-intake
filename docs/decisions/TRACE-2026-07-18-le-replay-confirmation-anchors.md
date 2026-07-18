# Decision Trace: L&E Replay Confirmation Anchors

## Decision

Bind every L&E replay budget proposal to both a source-bound synthetic human-confirmation artifact and the exact `SourceBundle` declared by the governed executable-fixture manifest.

Replay evidence identity is the stable tuple `(source_id, start_offset, end_offset, sha256)` using `offset_encoding=unicode_codepoint_v1`. Runtime `segment_id` values remain compatible metadata but are not replay identities because segmentation currently assigns UUIDs.

## Why

The prior input pack could prove that a budget artifact existed, but not that its confirmed matter family, posture, and party roles came from the fixture source assigned to that case. Merely parsing any local source bundle would also permit a plausible swapped bundle. The builder-binding report now pins the executable manifest reference, ID, and canonical JSON SHA-256; the input-pack audit must match that independent provenance. This binding and the stable evidence coordinates close both gaps without claiming a real operational human gate.

## Validation Rules

- The confirmation must be `confirmed` and identify the exact proposal, preflight, matter family, and posture.
- Decision evidence and each confirmed party must have valid source-bound evidence.
- Party names use Unicode NFC normalization, case folding, and word boundaries; `Ann` does not match `Annette`.
- Evidence offsets and hashes must reproduce the cited source text exactly.
- The input-pack manifest must match the executable-manifest reference and SHA-256 pinned by the builder-binding report.
- The entry's `source_bundle_ref` must equal that pinned manifest's mapping for its `executable_fixture_id`.
- Missing confirmation or source references remain schema-compatible but fail the audit with explicit findings.
- Missing downstream loop inputs remain `partially_ready`; an anchor failure cannot be silently skipped.

## Authority Boundary

Generated confirmations are synthetic review fixtures. Reports state `confirmation_scope=synthetic_fixture_only` and `runtime_human_gate_completed=false`. They do not authorize budget submission, matter opening, conflict clearance, docketing, connector use, Lake/SQLite writes, calibration, silent learning, or canonical promotion.

## Red-Team Findings Applied

Independent review found that random UUID segment IDs were unsuitable persisted anchors, arbitrary parseable source bundles could be substituted, substring party matching could collide, and Python/Rust offset semantics could diverge. The implementation therefore uses stable source coordinates and hashes, exact fixture-manifest source binding, boundary-aware normalized name checks, field-aware exact case-token extraction, and an explicit Unicode-codepoint offset version.

## Verification Evidence

- In-memory confirmation generation matches all four committed fixture digests without writing files.
- Confirmation generation is deterministic for unchanged fixture inputs.
- Manual drift checks cover swapped IDs, family, posture, evidence hash/offset, party names, reviewer scope, source bundles, and missing references.
- Unicode normalization and `Ann`/`Annette` boundary cases pass.
- A full in-memory input-pack replay remains `partially_ready` only for seven genuinely absent downstream inputs; all 15 budget items carry confirmation/source provenance and all governed checks pass.

Linux CI remains the authoritative full-suite environment because the local restricted Windows token cannot create pytest's private temporary directories. Rust parity must preserve `unicode_codepoint_v1` semantics before this validator can move across the language boundary.