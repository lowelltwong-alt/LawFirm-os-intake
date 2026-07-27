# Decision Trace — DT3 Canonical Pricing in the Case Pipeline (Side-by-Side)

Slice: post-marathon workstream, successor to DT2 (PR #124, squash-merged).
Branch: `claude/dt3-pipeline-canonical-stage`, off `main`. Candidate-only,
synthetic-only, deterministic; no ML, no promotion.

## Situation

DT2's canonical pricing engine existed but nothing consumed it — reviewers never
saw its output. The smallest visible step is surfacing the canonical plan in the
canonical pipeline composition (`case_pipeline`, the P7 seam) **alongside** legacy
sizing, without touching authority.

## Decision

A new INFORMATIONAL pipeline stage, `PipelineCanonicalPricingStage`:

- For med-mal cases (the only CLCM-mapped line so far), the runner builds the
  canonical driver profile from the spec's sizing drivers, prices it with the DT2
  engine, writes `canonical/canonical_priced_work_plan.json` to the run dir, and
  embeds a summary (profile/plan ids, contract digest, canonical total, a copy of
  the legacy sized total, neutral-assumed count, required-missing driver ids).
- **Authority unchanged:** the stage carries `authoritative=False` as a literal;
  the runner never adds it to `blocking_reasons`; legacy sizing remains the
  pipeline's authoritative sizing path.
- **Typed, never silent:** an unpriceable case is `not_priced` with a reason —
  `line_not_yet_clcm_mapped:<case_type>` for non-med-mal lines,
  `sizing_blocked`, or a captured `canonical_pricing_unavailable:<error>`. A
  failure in the candidate stage cannot crash or block the authoritative chain,
  but it is always recorded for review.
- **Fail-closed reconciliation:** the result model requires the stage's copied
  legacy total to equal the sizing stage's total exactly; a priced stage without
  a sized sizing stage is rejected; tampering the side-by-side totals fails
  validation. The stage feeds the pipeline `content_digest`.
- `canonical` is optional on `SyntheticCasePipelineResult` solely so pre-DT3
  artifacts still validate; the runner always populates it.

## Non-decision

- No change to legacy sizing, budget, export, routing, or any stage's authority.
- No swap-over: retiring legacy sizing behind the canonical engine remains a
  future, separately-reviewed decision.
- EPLI/GL/auto lines are typed `not_priced` until they get CLCM baselines and
  elicitation (the next slices).

## Evidence

`tests/test_pipeline_canonical_stage.py` — 7 tests (failing-test-first): stage
present and priced for med-mal; side-by-side total reconciles with sizing; stage
never blocks; plan artifact written and revalidates; unmapped line typed
`not_priced` without blocking; tampered side-by-side rejected; deterministic
across runs. Existing `tests/test_case_pipeline.py` (9) unchanged and green.

## Alternatives rejected

- **Replace legacy sizing now.** Rejected: authority changes deserve their own
  reviewed slice with regression comparison data collected first — which this
  stage now produces on every run.
- **Let canonical-stage errors propagate.** Rejected: a candidate stage must not
  take down the authoritative chain; errors are typed reasons instead.
- **Standalone schema export for the stage.** Rejected for consistency: pipeline
  stages are embedded in the pipeline-result schema via `$defs`, like every other
  stage.

## Validation

DT3 + pipeline tests 16/16; ruff check + format clean; `export_schemas`
idempotent (pipeline-result schema embeds the new stage); full local CI
reproduction green before merge. No UI change.

## Human gate

Owner pre-authorized squash-merge on green local CI for this slice sequence; the
PR description remains the review surface. Swap-over stays gated.

## DAD

Preflight/lesson/asset-use/midflight-acks/postflight recorded.
