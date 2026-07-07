# Real Work Shadow Mode Readiness

Status: Intake-local mirror of Substrate real-work gate; no real-work pilot is
authorized.

## Authority

This repo consumes the Substrate gate read-only:

- `../LawFirm-os-semantic-substrate/governance/REAL_WORK_SHADOW_MODE_PILOT_GATES.md`
- `../LawFirm-os-semantic-substrate/governance/LITIGATION_SIMULATION_ADAPTER_BOUNDARY.md`

`LawFirm-os-intake` may compose and evaluate synthetic intake-to-budget flows.
It may not approve a real-work pilot, ingest real client or matter data, make a
conflict conclusion, open a matter, approve or submit a budget, write to an
external connector, write to the Exception Lake or SQLite, or create canonical
schema, route, event, or taxonomy authority.

## Local Readiness Checklist

Before any owner asks for a real-work shadow-mode Intake pilot, the work must
show:

- Substrate real-work gate decision packet;
- owner, attorney, privacy, and compliance approval;
- jurisdiction, practice area, and workflow scope;
- data-class inventory;
- privilege and access-control review;
- reviewer checklist and escalation path;
- eval baseline from synthetic fixtures;
- blocked downstream actions;
- rollback and kill-switch plan;
- branch-protection or compensating-control decision for the Intake repo.

## Stop Conditions

Stop immediately if a request asks Intake to:

- use real client or matter data before the Substrate gate is approved;
- send anything to a client, carrier, court, billing system, DMS, or portal;
- clear conflicts or create an engagement decision;
- approve or submit a budget;
- treat model, simulator, or workflow output as legal advice;
- persist raw legal payloads to Lake, SQLite, or a long-lived local cache;
- bypass the upstream governance dependency map or local mirror.
