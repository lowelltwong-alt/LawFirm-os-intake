# TRACE-2026-06-24 - Review Package Completeness Report

## Context

The budget run produced a consolidated matter-opening review package, manifest, safety gate, Exception Lake readiness report, evidence graph, ledgers, conflict seed, and budget proposal. Those artifacts were individually tested, but there was no final deterministic report proving the package was complete before acceptance.

The v1.0 goal needs one north-star package that a lawyer can review without guessing whether required artifacts, sections, blockers, human gates, and non-authorization boundaries survived assembly.

## Decision

Add `ReviewPackageCompletenessReport` and write `review_package_completeness_report.json` during the budget stage after the review package and manifest are written.

The report verifies:

- required artifact keys are present in the manifest;
- referenced local files exist, except the report being written;
- the manifest links the human-readable package, manifest file, and completeness report;
- required review sections and final boundary text appear in the markdown package;
- required human gates remain present;
- final blockers remain conflicts, engagement, and matter-opening approval;
- prohibited actions still bar iManage, matter creation, and budget submission;
- boundary flags preserve no conflict conclusion, no client submission, no raw payload, and no external writes;
- the safety gate passed with the blocked final boundary;
- Exception Lake readiness remains passed and dry-run;
- both preflight and budget run ledgers are linked.

## Scope

This adds a local candidate model, schema export, workflow output, tests, smoke checks, and docs. It does not create canonical substrate schema, route IDs, event classes, production connectors, Exception Lake admission, conflict clearance, engagement approval, docketing, billing, matter opening, or budget submission.

## Alternatives Considered

- Rely on the manifest alone: rejected because the manifest lists artifacts but does not prove package completeness.
- Rely on tests only: rejected because every run should emit local proof for reviewer and future orchestrator handoff.
- Promote a platform contract directly: rejected because this repo remains a vertical proving ground and must propose, not promote, candidate contracts.

## Validation

- Unit coverage proves normal budget runs write a passing completeness report.
- Unit coverage proves missing required artifact keys fail the report.
- Unit coverage proves missing markdown review sections fail the report.
- Smoke coverage requires the report in the north-star demo.
