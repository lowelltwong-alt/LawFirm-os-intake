# TRACE 2026-07-02: DAD Review Issue Outbox

## Decision

Add a deterministic local recorder that turns complex Fable/Codex/Claude/human
review findings into candidate DAD mail under `.digital-asset/mail/outbox.jsonl`.

## Why

Hard review findings were being captured in chat or one-off notes. That loses
exception patterns, fix outcomes, and reusable lessons. The intake repo needs a
repeatable way to send classified review issues to DAD without writing to the
Exception Lake, applying learning, mutating sibling repos, or promoting a rule.

## Scope

- `record-dad-review-issue` CLI command.
- `DADReviewIssueRecord`, outbox mail, check, and report contracts.
- Synthetic Fable-style review issue fixture.
- Tests for classification, dedupe, mailbox boundary, and sensitive-text
  rejection.
- Documentation for allowed context and prohibited payloads.

## Boundaries

- Candidate mail only.
- No Lake or SQLite write.
- No external connector or sibling repo write.
- No hidden chain-of-thought capture.
- No raw private payloads, credentials, real client facts, or private firm rates.
- DAD/human review remains required before any learning rule or exception-lake
  taxonomy promotion.

## Validation

- Focused tests for DAD review issue outbox.
- Schema export.
- Full repo validation before merge.
