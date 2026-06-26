# TRACE: Learning Owner Handoff Packages

Date: 2026-06-26

## Decision

Add a candidate-only owner handoff layer after local learning shadow-eval
results.

## Why

The learning loop needs a review package that routes passed, failed, and blocked
learning candidates to the correct owning repo without letting intake promote,
implement, or mutate anything. Shadow-eval results alone show local evidence;
they do not tell each sibling repo which items are ready for review, failed, or
still blocked.

## Implemented Surface

- `build-learning-owner-handoffs` command.
- `LearningOwnerHandoffItem`, `LearningOwnerHandoffPackage`, and
  `LearningOwnerHandoffReport` candidate schemas.
- Per-owner JSON/Markdown handoff packages under `owner_handoffs/`.
- Tests for ready, blocked, failed, no-candidate, and CLI paths.

## Boundary

The handoff packages are review material only. They do not approve, promote,
implement, or apply any learning change. They perform no sibling-repo write,
Lake write, SQLite write, external write, profile/template/budget/guideline
mutation, or silent learning.

## Red-Team Notes

- Passing shadow-eval evidence can still be overfit to synthetic fixtures.
- Failed or blocked candidates must remain separated from ready candidates so a
  mixed owner package cannot create false readiness.
- Owning repos still decide whether any implementation work is warranted.
- Canonical schema IDs, event classes, route IDs, and lifecycle decisions remain
  Semantic Substrate authority.

## Validation Plan

- Export schemas.
- Run focused learning handoff tests.
- Run full repo tests, lint, formatting, smoke demo, and front-door validators.
