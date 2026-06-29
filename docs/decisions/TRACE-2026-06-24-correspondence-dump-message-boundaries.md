# TRACE-2026-06-24 - Correspondence Dump Message Boundaries

## Situation

Messy intake often arrives as a pasted or exported correspondence dump rather than clean individual emails. The starter already preserved normal email headers, quoted history, signatures, attachment references, offsets, and hashes, but `correspondence_dump` sources still collapsed repeated message boundaries into coarse dump items.

That made reviewer reconstruction harder and weakened the future Rust parity target for high-volume ingestion.

## Decision

Teach the deterministic segmenter to split `correspondence_dump` sources on repeated top-level `From:` message starts.

The new behavior preserves:

- dump preamble segments;
- message-indexed `email_header` segments;
- message-indexed body, attachment-reference, quoted-email, and signature segments;
- exact source offsets;
- segment hashes;
- source-instruction risk flags.

The existing fallback remains for dump text with no email-like message boundaries.

## Safety behavior

Quoted or forwarded instructions inside a dump are still untrusted source data. If they attempt to clear conflicts or open a matter, preflight emits dry-run `ExceptionLakeCandidate` records such as `prompt_injection_source_content`, `prohibited_transition_attempted_matter_opened`, and `prohibited_transition_attempted_conflicts_cleared`.

No legal, conflict, engagement, docketing, billing, external-write, matter-opening, or submission action is performed.

## Non-decision

This does not add model-based parsing, public-data ingestion, production connectors, matter routing authority, conflict conclusions, docketing, matter opening, budget approval, or Exception Lake admission.

## Authority impact

This is local deterministic source-structure preservation. Semantic Substrate remains the authority for promoted source/evidence contracts. Orchestrator remains the future runtime owner. Any future Rust ingestion adapter must match this Python reference behavior before replacement can be proposed.

## Validation

- Added `holdout-correspondence-dump-message-boundaries.json`.
- Focused tests assert message indices, structural paths, segment types, offsets, hashes, and quoted instruction-risk flags.
- Preflight coverage proves prohibited instructions in a quoted dump become dry-run exception candidates with no raw payload.
