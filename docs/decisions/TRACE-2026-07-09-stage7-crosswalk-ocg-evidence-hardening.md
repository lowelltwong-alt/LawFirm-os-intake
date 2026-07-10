# Decision Trace: Stage 7 Crosswalk and OCG Evidence Hardening

Date: 2026-07-09

## Decision

Harden Stage 6 crosswalk audit and UI/QA evidence after the Stage 4.5 safety gate
and Stage 6 review UI wiring. Crosswalk evidence remains candidate-only and
must not become budget, guideline, rejection, or workflow logic.

## Guardrails Added

1. **Dual human review for high confidence** — mapped entries with
   `confidence=high` are blocked unless both `entry.review_status` and
   `provenance.review_status` are `human_reviewed`. Synthetic fixtures retain
   zero high-confidence entries.
2. **Explicit unverified standard-code display** — `CrosswalkAuditReport` and
   summaries carry `exact_standard_code_verified=false` plus a counted
   `utbms_like_candidate_family_label_count` for mnemonic labels such as
   `task-L310-family-*`.
3. **UI/QA visibility** — React evidence panel and QA readiness checks surface
   candidate-family labels as not exact SALI/LEDES/UTBMS canon.

## Boundary

No canon promotion, no crosswalk-driven budget logic, no public standard payload
ingestion. OCG adoption behavior from Stage 6 is unchanged; only crosswalk audit
hardening and evidence display are in scope.

## Tests

- `tests/test_crosswalks.py` — dual-review blocker, UTBMS-like label counts,
  fixture audit invariants.
- `tests/test_review_ui_crosswalk_ocg_evidence.py` — QA readiness checks for new
  guardrails and UI source assertions.
