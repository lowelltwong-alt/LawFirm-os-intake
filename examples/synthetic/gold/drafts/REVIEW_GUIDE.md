# Holdout Gold Drafts — Owner Review Guide

Status: **five drafts, `reviewed: false` — inert until signed**
Purpose: unlock correctness grading on the holdout partition. Until these are reviewed,
`gold_conformance` on the holdout set is `— (0/5)` and no ranking of implementation
strategies is possible, regardless of how many conditions exist.

## Read this first: the circularity trap

Every draft was dry-run against the current pipeline and **passes all its checks**
(16 / 15 / 22 / 16 / 18 checks respectively, 0 failures). That is *not* evidence the drafts
are correct — it is the hazard. A gold spec consistent with current behavior can never catch
a current error; it only pins today's output. **Your review is the only step that converts
"what the pipeline does" into "what is actually right."** Where you believe the pipeline is
wrong, change the expectation to what *should* happen — a signed gold spec that fails against
the pipeline is a finding, not a mistake.

## Where each field came from

| Field class | Source | Review burden |
|---|---|---|
| `prohibited_party_role_candidates`, `expected_preflight_exception_labels`, `expected_critic_finding_codes` | **Fixture intent** — each holdout's declared purpose (`fixture_hints`, expansion-manifest `expected_signals`) | Confirm the intent is captured; these are the load-bearing expectations |
| `expected_party_role_candidates` | Fixture intent, cross-checked against observation | Confirm names and roles; watch for roles the fixture intends that the pipeline *missed* (a draft built from observation cannot contain those) |
| `expected_top_three_matter_families`, `expected_top_inbound_event`, `expected_top_representation_posture` | **Observation** of the current pipeline | Highest circularity risk — decide independently what the right answer is |
| `expected_missing_information`, `expected_source_states`, `expected_source_coverage` | Observation, aligned with fixture structure | Verify against the fixture's own sources, not the pipeline |
| `expected_preflight_status`, `expected_prohibited_next_steps`, `require_source_bound_evidence` | Governance invariants | Should be uncontroversial; flag if not |

## Per-case notes — what to scrutinize

1. **carrier-client-role-matrix** — the point of the case: carrier, TPA, and affiliate roles
   stay *distinct*, and neither Harbor Point nor ClaimsPro may ever appear as
   prospective/represented client. The `prohibited_*` block is the teeth; check it matches
   your intent for the fixture.
2. **correspondence-dump-message-boundaries** — the embedded prompt-injection content and the
   two prohibited-transition attempts must surface as exception labels. If you believe any
   *additional* injection or boundary signal should fire, add it — the pipeline missing it
   would then be a genuine holdout failure.
3. **duplicate-missing-attachment** — verify the `expected_source_states` rows against the
   fixture's three sources (which one is the duplicate, which attachment is missing). These
   were observation-derived; the fixture is the authority.
4. **misleading-sender-role-ambiguity** — the sharpest judgment call in the set. Observed top
   event is `coverage_inquiry` and posture `defense_of_insured`; decide whether that is the
   *correct* reading of a deliberately misleading sender, or whether `unknown` posture is the
   right answer. Taylor Person must never be a client candidate.
5. **unread-source** — the unread source must appear in `expected_source_states` as unread and
   surface `source_unread`; confirm which of the two sources carries the flag.

## Sign-off procedure (per spec)

1. Edit the draft: correct any expectation that reflects the pipeline rather than your intent.
2. Set `"reviewed": true`, `"reviewer_id": "<you>"`, `"reviewed_at": "<YYYY-MM-DD>"`.
3. Move it out of `drafts/` into `examples/synthetic/gold/`, dropping `.draft` from the name.
4. Add the file to the matching assignment's `gold_refs` in
   `examples/synthetic/evaluation/intake-evaluation-split.json` (fixture digests are unchanged
   by this, so the pinned split remains valid).
5. Re-run, in order:
   ```bash
   python -m lawfirm_os_intake audit-evaluation-split --split-manifest examples/synthetic/evaluation/intake-evaluation-split.json --out-dir .lawfirm-os-intake/split-audit
   python -m lawfirm_os_intake run-condition-comparison --split-manifest examples/synthetic/evaluation/intake-evaluation-split.json --condition-specs examples/synthetic/evaluation/intake-condition-specs.json --out-dir .lawfirm-os-intake/comparison
   python -m lawfirm_os_intake grade-condition-runs --comparison-dir .lawfirm-os-intake/comparison --split-manifest examples/synthetic/evaluation/intake-evaluation-split.json --out-dir .lawfirm-os-intake/grading
   ```
6. A `gold_conformance` failure after signing is a **pipeline finding** — record it, do not
   soften the spec to make it pass.

When all five are signed, `gold_coverage_complete` flips to true and the holdout set can grade
correctness — the last precondition (besides a second condition) for a ranked comparison.
