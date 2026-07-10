# TRACE: ER3 Entity Correction Exceptions

## Decision

Add a local, append-only human entity-resolution correction artifact. It validates both compared observed-name spans and hashes against a synthetic source bundle, emits only dry-run Exception Lake candidates, and writes a non-emitted DAD lesson draft.

## Boundary

The artifact cannot mutate `config/matter-link-policy.yaml`, infer aliases, assert persistent identity, write to the Exception Lake or SQLite, mail DAD, clear conflicts, open matters, or change the matcher from correction outcomes. Candidate table changes require human review and owner adoption.

## Tests

- source-bound suffix-conflict correction produces candidate-only exception evidence;
- altered evidence hashes fail closed;
- CLI writes local JSON artifacts only.
