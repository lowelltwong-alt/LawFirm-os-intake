# TRACE-2026-06-24-front-door-reference-validation

## Decision

Make AI/front-door local file references self-validating and add the missing Claude-for-legal lessons document.

## Context

The README and `AI_WORK_START_HERE.md` required builders to read `docs/claude-for-legal-lessons.md`, but that file was absent. `AI_TABLE_OF_CONTENTS.md` also pointed completion readers at `VALIDATION_REPORT.md`, while the current repo uses `BUILD_VERIFICATION.md`.

Broken front-door references undermine the starter goal that a new builder can identify the repo role, authority order, first command, and prohibited actions from root files.

## Change

- Added `docs/claude-for-legal-lessons.md` as local orientation guidance for Claude-style agent loops in the legal intake vertical.
- Updated `AI_TABLE_OF_CONTENTS.md` to reference `BUILD_VERIFICATION.md`.
- Extended `scripts/validate_repo.py` to verify local file refs in the README Start Here section, `AI_WORK_START_HERE.md` required reading order, `AI_TABLE_OF_CONTENTS.md`, and `CLAUDE.md`.
- Added tests proving the current front-door refs resolve and synthetic broken refs fail.

## Authority Impact

This is orientation and validation only. It does not promote platform canon, expand tool authority, add connectors, change runtime behavior, call model providers, or authorize legal/external actions.

## Validation

- `tests/test_repo_validation.py` covers current front-door refs and a missing-ref failure.
- `python scripts/validate_repo.py` now fails closed if front-door local refs point to missing files or directories.

## Follow-Up

If additional AI front-door files become required, add them to the validator's front-door reference file list so stale orientation links cannot return.
