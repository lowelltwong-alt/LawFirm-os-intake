# TRACE 2026-06-24: Cross-Repo Promotion Package

## Decision

The intake repo now carries a machine-readable, candidate-only cross-repo promotion package at `promotion/cross_repo_promotion_package.json`.

## Rationale

The vertical now has enough local contracts and evidence surfaces that sibling repo owners need a structured review inventory. A prose document alone is too easy to drift. The package records what should be reviewed by Semantic Substrate, Orchestrator, Exception Lake, Skills Registry, and Legal Knowledge Runtime while preserving each repo's authority boundary.

## Implementation

- Added `CrossRepoPromotionPackage` and `CrossRepoPromotionProposal` local candidate schemas.
- Added a package covering schema/event candidates, workflow and human-pause interfaces, Lake evidence mappings, skill metadata, and Legal Knowledge Runtime context-bundle refs.
- Added tests proving required target repo coverage, proposal type coverage, local artifact refs, and candidate-only/no-write flags.

## Authority Boundary

This package does not promote anything. It does not assign canonical schema IDs, route IDs, event classes, skill trust state, Lake admission rules, runtime connector authority, or Legal Knowledge Runtime contracts. Stable components still graduate only through the owning sibling repo after review.
