# Decision Trace — CW4 Routing Eval Harness

Wave: CW4 of the converged Opus marathon. Branch: `claude/cw4-routing-eval`,
stacked on the CW3 branch. Candidate-only, synthetic-only, deterministic. **No ML
router.**

## Situation

The design calls for evaluating the existing deterministic
`matter_family_candidates -> confirmation` router before any ML challenger: does
it recover known-truth families on a held-out synthetic set, and does it abstain
correctly on ambiguous / adversarial input (including prompt-injection-as-text)?
The World Builder stays deferred; this is ordinary versioned fixtures.

## Decision

An additive `routing_eval` module:

1. **Synthetic intake fixture factory** — `build_synthetic_intake_case(spec)`
   builds a `SourceBundle` + segments from a labeled `RouterEvalCaseSpec` (ground
   truth family known by construction), embedding the family's real
   `MATTER_SIGNALS` terms and variant-specific adversarial content.
2. **Frozen holdout + adversarial set** —
   `examples/synthetic/routing-eval/router-eval-cases.json`: clean cases across 7
   families plus adversarial variants: `mixed_signals` (two families' terms →
   abstain), `quoted_thread_noise` (dominant family survives quoted noise → route),
   `missing_attachment` (no readable content → abstain), and `injection_as_text`
   (a `SYSTEM OVERRIDE` instruction carrying no genuine signal terms, on a segment
   flagged `source_instruction_risk`).
3. **Deterministic route/abstain decision** — `route_decision` routes the top real
   family only if it clears `ROUTE_MIN_CONFIDENCE` (≥ one observed signal) and beats
   the next real family by `ROUTE_MARGIN`; otherwise it abstains (unknown-top,
   low-evidence, or ambiguous). The deterministic rules + human confirmation remain
   the authority.
4. **Router evaluation report** — `RouterEvaluationReport` with per-family accuracy
   and abstention correctness (recall, over-abstention), all recomputed from the
   case results in the model validator (fail-closed).

## Result

On the frozen set the deterministic router recovers **every** known-truth label
(overall accuracy 1.0, per-family accuracy 1.0), abstains on **every** ambiguous /
missing case (abstention recall 1.0), never over-abstains on clean cases, and
**prompt-injection-as-text is inert** — the router follows the genuine signal
terms and ignores the injected instruction.

## Non-decision

- No ML router; no scoring of the injection instruction as an authority signal.
- No change to `classify_matter` or the intake workflow — the harness evaluates
  the existing router.

## Authority impact

Local candidate work; new candidate schemas + a frozen synthetic fixture set. No
canonical/promoted contract change; no cross-repo write.

## Evidence

- `tests/test_routing_eval.py` — 8 tests (failing-test-first): factory
  determinism; clean routing; mixed/missing abstention; **injection inertness** +
  instruction-risk flag; report reconciliation (fail-closed) + label recovery;
  frozen-set coverage.
- Four exported schemas; frozen cases under `examples/synthetic/routing-eval/`.

## Alternatives rejected

- **Abstain on any second-place family (including `unknown`).** Rejected: it would
  over-abstain on clean single-signal cases; the margin is measured against the
  next *real* family, with a minimum-confidence floor for evidence.
- **Score the injected instruction.** Rejected on purpose — the whole point is that
  the deterministic router cannot be steered by instruction text.

## Risks and rollback

- Risk: the thresholds are synthetic and not firm-tuned. Contained by candidate
  status and the routing-eval review gate; the ML challenger (later) runs only as a
  shadow. Rollback is a single-branch revert; the module is additive.

## Validation

ruff check/format clean; `export_schemas.py` idempotent (four new schemas);
`validate_repo.py` passed; `run_full_pytest.py -q` full suite passed; `npm run
build` + `npm run smoke:browser` OK (no UI change this wave).

## Human gates

CW4 human gate: **routing-eval review**. Opened by the agent; it does not merge its
own PR and does not push `main`.

## DAD

Per-wave preflight/lesson/postflight through the canonical `asset-dir` lesson
pipeline.
