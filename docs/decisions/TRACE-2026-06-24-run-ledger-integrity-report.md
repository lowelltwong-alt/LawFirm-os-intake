# TRACE-2026-06-24 - Run Ledger Integrity Report

## Situation

The starter workflow already wrote preflight and budget `run_ledger.jsonl` files, but reviewers still had to infer whether required gates appeared in order, whether outputs existed, whether blocked budget attempts stopped correctly, and whether refs stayed local.

As the intake-to-budget vertical grows, that inference should be deterministic and visible in the final review package.

## Decision

Add `RunLedgerIntegrityReport` and write `run_ledger_integrity_report.json` for:

- preflight runs;
- confirmed budget runs;
- blocked budget attempts.

The report verifies:

- ledger events exist;
- all events use one run ID;
- step indices strictly increase;
- required gate steps appear in order;
- the expected terminal step and status match the stage;
- failed and blocked events appear only where allowed;
- artifact refs are local and not connector or external refs;
- output refs exist on disk when the report is written;
- no external writes occurred.

The consolidated review package renders both preflight and budget integrity reports, and package completeness requires both reports to pass for confirmed budget packages.

When a budget directory contains a prior blocked attempt followed by a superseding confirmed correction, the ledger is not erased. The integrity report validates the latest budget attempt segment beginning at the most recent `budget_run_started` event, while the full ledger and confirmation history retain the earlier blocked attempt for audit.

## Non-decision

This does not make intake the execution-plane owner. Orchestrator remains the future owner of execution passports, canonical run-ledger policy, human pauses, and evidence-packet assembly.

This also does not write to Exception Lake, SQLite, production connectors, billing, conflicts, docketing, iManage, email, or court systems.

## Authority impact

`RunLedgerIntegrityReport` is local intake evaluation evidence. If it becomes a shared contract, Semantic Substrate must promote the schema and Orchestrator must own runtime enforcement.

## Validation

Unit tests cover:

- preflight report emission and pass status;
- confirmed budget package report refs and completeness checks;
- blocked budget report terminal status;
- enforcement failure when a required gate is missing.

Smoke coverage requires both preflight and budget integrity reports and verifies the blocked-budget integrity report remains blocked.
