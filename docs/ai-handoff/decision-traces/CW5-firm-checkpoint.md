# Decision Trace — CW5 Firm Checkpoint Packet

Wave: CW5 of the converged Opus marathon. Branch: `claude/cw5-firm-checkpoint`,
stacked on CW4. Candidate-only, synthetic-only, deterministic.

## Situation

The plan's no-data firm checkpoint runs three synthetic cases end-to-end and asks
the firm to disposition them ("useful / wrong workflow / missing rule"). CW5's
named gate is a **HARD STOP**: a human presents to the firm and nothing proceeds
until real firm dispositions return. Under the owner's overnight autonomy
authorization, CW5 packaging proceeds using **clearly-labeled synthetic PLACEHOLDER
dispositions** so CW6/CW7 can be built; those placeholders are never real firm
validation.

## Decision

An additive `firm_checkpoint` module composing the CW2–CW4 layers into a
`FirmCheckpointPacket` of exactly three cases, each routed → sized → priced →
exported with a disposition sheet:

1. **Small slip-and-fall** (general_liability_defense) — oversized vs a $10k
   exposure ⇒ `blocked_disproportionate_budget` (proportionality trips) and a
   settle-now recommendation; routes to general_liability_defense.
2. **Mid-size EPLI** (discrimination_harassment) — within the proportionality band
   but the firm-Excel export carries an E119 expert-fee task > $25k ⇒ expert
   preapproval trip; routes to discrimination_harassment.
3. **L&E wage-hour** (wage_hour_flsa_state) — within band; routes to
   wage_hour_flsa_state.

Each case carries a `FirmCheckpointCaseDisposition` placeholder
(`pending_firm_review`, `is_synthetic_placeholder=True`). The packet asserts
exactly three cases and that `synthetic_placeholder_dispositions_used` reflects the
cases (fail-closed), and pins `requires_firm_dispositions=True` and
`real_firm_validation_status=open_pending_firm_review`. Each case validator
re-derives its proportionality trip and recommended posture from its sizing report
(fail-closed).

## Non-decision — the hard stop still stands

The synthetic placeholders **do not** satisfy the real firm checkpoint. The packet
is explicit that firm dispositions remain an open human dependency; CW6/CW7 treat
the placeholders as candidate-only, not firm-validated.

## Authority impact

Local candidate work; new candidate schemas composing existing layers. No
canonical/promoted change; no cross-repo write.

## Evidence

- `tests/test_firm_checkpoint.py` — 6 tests (failing-test-first): three cases +
  placeholder dispositions; slip-and-fall proportionality trip + settle; EPLI
  expert-preapproval within band; L&E present + routed; determinism; case
  proportionality validator fail-closed.
- Three exported schemas.

## Alternatives rejected

- **Wait for real firm dispositions before any further wave.** That is the literal
  hard stop; the owner's overnight authorization explicitly relaxes it *only* via
  clearly-labeled synthetic placeholders, so downstream waves are built while the
  real checkpoint stays flagged open.

## Risks and rollback

- Risk: placeholder dispositions are mistaken for firm validation. Contained by the
  explicit `is_synthetic_placeholder`/`real_firm_validation_status` fields, the
  packet banner, and this trace. Rollback is a single-branch revert; additive.

## Validation

ruff check/format clean; `export_schemas.py` idempotent (three new schemas);
`validate_repo.py` passed; `run_full_pytest.py -q` full suite passed; `npm run
build` + `npm run smoke:browser` OK (no UI change this wave).

## Human gates

CW5 human gate: **HARD STOP — human presents to firm; real firm dispositions
return before genuine validation.** The synthetic placeholders unblock downstream
*construction* only. Opened by the agent; it does not merge its own PR and does not
push `main`.

## DAD

Per-wave preflight/lesson/postflight through the canonical `asset-dir` lesson
pipeline.
