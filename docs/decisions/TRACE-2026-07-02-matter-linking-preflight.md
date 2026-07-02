# TRACE 2026-07-02 Matter-Linking Preflight

## Decision

Add a deterministic `audit-matter-linking-preflight` command for Upfront-like
intake output before any connector or budget workflow relies on document
clusters.

## Why

Insurance adjusters and other repeat senders can send multiple unrelated
prospective matters in one channel. Same sender, same carrier, or same inbox
thread is not enough to merge documents into one matter. When no official firm
matter number exists, the system must preserve candidate clusters, source-bound
positive and negative signals, and explicit human/sender follow-up gates.

## Scope

- Reads a local synthetic Upfront-like JSON artifact.
- Writes `matter_linking_preflight_report.json` and
  `matter_linking_preflight_report.md` under the requested run directory.
- Verifies synthetic/candidate-only posture, no verified Upfront API contract,
  no connector/write side effects, explicit missing official matter number,
  human review gates, rejected weak merge signals, source-bound strong support,
  negative split evidence, and candidate Exception Lake labels.

## Boundaries

The audit does not call Upfront, create a screen, clear conflicts, output a
budget amount, open a matter, write Lake/SQLite records, submit a budget, or
learn from reviewer corrections. It is candidate-only evidence for a future
Orchestrator-owned workflow and Exception Lake owner review.

## Follow-Ups

- Add a resolving fixture where a later email supplies a trusted claim number or
  Upfront-like request ID.
- Add a human review artifact for split, merge, unknown, and request-more-info
  decisions.
- Add read-only UI panels for unmatched, ambiguous, and conflicting clusters.
