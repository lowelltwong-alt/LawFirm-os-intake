# TRACE-2026-06-24 - Evidence Completeness Report

## Situation

Strict preflight validation already rejected missing or drifted candidate evidence refs, but a passing run did not emit a durable artifact proving what was checked.

That left the v1.0 evidence-first rule partly implicit. Reviewers and future Orchestrator handoff could inspect packet JSON and tests, but the run directory did not have one local proof record for party, role, matter, posture, deadline, missing-information, and critic evidence completeness.

## Decision

Add `evidence_completeness_report.json` to every preflight run.

The report checks:

- party candidates and party-role alternatives have evidence refs;
- inbound-event, matter-family, and representation-posture candidates stay packet-bound;
- explicit unknown options remain present and source-anchored;
- deadline candidates have evidence refs and require human review;
- missing-information candidates have evidence refs;
- critic findings have evidence refs;
- every checked evidence ref matches the packet segment table by source ID, segment ID, offsets, and hash;
- human confirmation and prohibited next steps remain present.

The final review package renders the report, `ReviewPackageCompletenessReport` requires it, and the starter audit treats it as release evidence.

## Safety behavior

The report is local evaluation evidence only. It does not make classifications final, clear conflicts, accept engagement, docket deadlines, submit budgets, open matters, write externally, admit records to the Exception Lake, or promote evidence-ref doctrine into Semantic Substrate canon.

## Authority impact

This is a local intake candidate/evaluation artifact. Semantic Substrate remains the authority for promoted schemas and evidence doctrine. Orchestrator remains the future runtime owner for package assembly and gate enforcement.

## Alternatives Considered

- Keep strict validation only: rejected because successful runs should expose evidence-completeness proof to reviewers and future handoff.
- Put the proof only in fixture gold: rejected because fixture gold is optional, while evidence completeness is a baseline run invariant.
- Add a broader legal quality score: rejected because this slice should prove source/ref integrity, not claim legal correctness.

## Validation

- Added schema export for `EvidenceCompletenessReport`.
- Added preflight tests for report emission and fail-closed role-evidence drift.
- Added final package completeness drift coverage.
- Added starter audit drift coverage.
