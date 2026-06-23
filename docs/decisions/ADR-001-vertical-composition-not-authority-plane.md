# ADR-001 — Intake Is a Vertical Composition Repo, Not an Authority Plane

**Status:** Accepted

## Decision

`LawFirm-os-intake` owns the end-to-end reference workflow, fixtures, and evaluations. It does not own canonical schemas, general orchestration, evidence storage, governed skill trust, or legal source authority.

## Reason

Without this boundary, the repo would become a second Orchestrator and shadow Semantic Substrate. That would create duplicated policies, schema drift, and unclear accountability.

## Consequence

Reusable artifacts must graduate to their owning sibling repo and return here through immutable pins.
