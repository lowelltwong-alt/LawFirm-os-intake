# TRACE: Carrier Rejection Exception Lake Admission Proposal

## Context

The carrier rejection roadmap now has capture/reconciliation, human review,
learning candidates, and an Orchestrator interface draft. The remaining boundary
is Lake admission: future records must be append-only, hashable, idempotent,
correctable by supersession, and owned by the Exception Lake runtime.

## Decision

Add `CarrierRejectionLakeAdmissionProposal` and the
`draft-carrier-rejection-lake-admission` command.

The command writes:

- `carrier_rejection_lake_admission_proposal.json`;
- `carrier_rejection_lake_admission_proposal.md`.

The proposal defines candidate record families for carrier rejection notices,
reconciliation, human review outcomes, appeal submissions, appeal results,
financial outcomes, and learning candidates.

## Boundary

This is a proposal only. It does not create SQLite tables, write SQLite, admit
Lake records, assign canonical event classes, own record hashes, store raw
payloads, or authorize intake to persist runtime evidence.

SQLite schemas, migrations, admission validation, append-only storage, record
hashes, correction records, and supersession semantics remain
Exception-Lake-owned. Orchestrator evidence packets remain the required upstream
admission unit.

## Validation

- Unit tests prove every record family uses append-only supersession.
- Tests prove every record family declares idempotency and hash fields.
- Tests prove raw payload storage and intake admission are disallowed.
- Tests prove the CLI writes JSON and Markdown proposal artifacts only.
