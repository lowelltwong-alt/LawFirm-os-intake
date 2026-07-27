# Case Study: A Governed Deterministic Baseline for Intake-to-Budget

Status: **baseline case study — no comparative claim**
Date: 2026-07-27 · Data: synthetic only · Model spend: **$0.00** (zero provider calls, verified per run)

This is the first public case study for this repository. It covers what exists and is
reproducible today: a governed deterministic workflow, a contamination-controlled evaluation
set, and scored baseline results. It deliberately does **not** compare implementation
strategies, because only one strategy has been built. Every limitation that follows from that
is stated in [Limitations](#limitations).

---

## Problem

Insurance-defense matter intake turns messy inbound material — correspondence dumps, carrier
assignment letters, demand letters — into three consequential outputs: a structured
understanding of the matter, a conflict-search seed, and a proposed litigation budget on
carrier-mandated UTBMS codes. Errors are expensive in both directions: a missed deadline or
party is a liability event, and an inflated budget is rejected by the carrier.

The interesting engineering question is not "can an LLM read a demand letter" but: **what does
this workflow require of *any* implementation — deterministic, retrieval-assisted, or agentic —
before its output can be trusted enough to put in front of an accountable human?**

## Existing workflow (the reference)

The manual process this models: an intake coordinator reads the inbound package, identifies
parties and roles, flags missing information, calendars candidate deadlines for attorney
review, runs a conflict search, and drafts a phase/task budget against the carrier's
guidelines. An attorney reviews everything before a matter is opened. Nothing is filed,
docketed, or submitted by the coordinator alone.

## Architecture decision

The baseline is **deterministic on purpose**, not as a placeholder:

- Where rules are known and enumerable — evidence binding, data-scope gating, deadline-candidate
  extraction patterns, UTBMS mapping, guideline caps — deterministic automation is *better* than
  a model: same input, same output, auditable, free.
- Where judgment is required — confirming the matter family, clearing conflicts, approving a
  budget — **no implementation gets authority**. The run terminates at
  `blocked_pending_conflicts_and_engagement` by construction, and model output (when a model
  condition exists) is proposal-only.
- AI is appropriate in the middle band: reading messy unstructured material, proposing
  candidates, surfacing ambiguity. That band is exactly what the evaluation harness is built to
  measure — *when a second implementation exists to measure*.

## Synthetic dataset

19 synthetic inbound cases (`examples/synthetic/inbound/`), partitioned by a reviewed,
digest-pinned split (`examples/synthetic/evaluation/intake-evaluation-split.json`):

| Partition | Cases | Purpose |
|---|---|---|
| development | 14 | building and debugging; results here are not evidence of generalisation |
| holdout | 5 | reserved for evaluation; adversarial and boundary cases; never developed against |

Contamination is detectable, not assumed: every fixture's content digest is pinned in the
split manifest, and `audit-evaluation-split` fails if a held-out case changes after review.
No real client, matter, carrier, or firm data appears anywhere; contact identifiers use
reserved non-resolvable domains.

## Runnable implementation

One command produces the full artifact chain (see the README quickstart for setup):

```bash
python -m lawfirm_os_intake demo \
  --input examples/synthetic/inbound/north-star-messy-intake.json \
  --practice-profile context/synthetic-profiles/insurance-defense.yaml \
  --confirmation-template examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json \
  --out-dir .lawfirm-os-intake/demo
```

The run ends `blocked_pending_conflicts_and_engagement` with a driver-scaled UTBMS budget
proposal (total 148,406.00 on this fixture) that is priced but neither approved nor submitted.

## Evaluation method

Three commands, all deterministic, all free:

```bash
# 1. Verify the partition is intact (digest-pinned contamination control)
python -m lawfirm_os_intake audit-evaluation-split \
  --split-manifest examples/synthetic/evaluation/intake-evaluation-split.json \
  --out-dir .lawfirm-os-intake/split-audit

# 2. Run every declared condition over the holdout cases
python -m lawfirm_os_intake run-condition-comparison \
  --split-manifest examples/synthetic/evaluation/intake-evaluation-split.json \
  --condition-specs examples/synthetic/evaluation/intake-condition-specs.json \
  --out-dir .lawfirm-os-intake/comparison

# 3. Grade the runs into decomposable per-dimension scores
python -m lawfirm_os_intake grade-condition-runs \
  --comparison-dir .lawfirm-os-intake/comparison \
  --split-manifest examples/synthetic/evaluation/intake-evaluation-split.json \
  --out-dir .lawfirm-os-intake/grading
```

Design properties that make the numbers trustworthy:

- **Records are keyed on (case × condition)** — the unit a comparative claim requires.
- **The spend ceiling is enforced in code, twice**: declared model-call permissions are summed
  and refused before any case executes, and each run's own adapter artifact is re-read
  afterward to corroborate that no provider call occurred.
- **Every score decomposes**: a score must equal its numerator/denominator or the record is
  rejected at validation. Aggregates can always be traced back to individual checks.
- **Honesty is a model invariant, not a convention**: `comparative_claim_supported` and
  `ranking_supported` cannot be hand-edited into a report whose evidence does not support them
  — the validators reject the edit.

## Results

C0 (deterministic baseline), 5 holdout cases, zero provider calls:

| Dimension | Basis | Mean | Computable |
|---|---|---|---|
| evidence_completeness | run artifacts | 1.000 | 5/5 |
| run_integrity | run artifacts | 1.000 | 5/5 |
| adapter_boundary | run artifacts | 1.000 | 5/5 |
| gold_conformance | reviewed gold | **—** | **0/5** |

On the development partition (14 cases, shown for the gold-graded pair only —
development results are not evidence of generalisation):

| Case | gold_conformance |
|---|---|
| carrier-assignment-medmal | 23/23 = 1.000 |
| north-star-messy-intake | 30/30 = 1.000 |

**Read the dash in the holdout table carefully.** It is the most important number on this page:
no holdout case has a reviewed gold specification yet, so *correctness on the held-out set is
unmeasured*. The discipline dimensions say the baseline keeps its rules — evidence stays
source-bound, ledgers stay coherent, boundaries hold. They do not say it is right.

## A failure found and fixed during this work

The first grading run scored `gold_conformance` at 22/23 and 29/30 on the two gold-mapped
cases. Decomposing the scores located a single failing check on each:
`preflight_exception_label_recall`, expected labels compared against an empty list.

The defect was in the **grader**, not the pipeline: the gold builder takes the run's dry-run
exception candidates as a separate argument, and the grading module omitted it. In the failure
taxonomy this is a `grader_defect` — the evaluation instrument itself was wrong, and had it
inflated rather than deflated the score, it would have been dangerous rather than merely
embarrassing. The fix passes the run's `exception_lake_candidates.jsonl` through; a regression
test now pins the behaviour.

This is the exception-to-improvement loop in miniature — score, decompose, diagnose, classify,
fix, re-score — and it worked *because* scores decompose into named checks. An opaque 0.957
would have been shrugged at.

## Cost

Zero. All conditions to date are deterministic. When a model-backed condition is added, its
per-run token and dollar cost becomes part of the condition-comparison record; those fields are
absent today rather than estimated.

## Limitations

Stated as facts, not caveats:

1. **No comparison exists.** One condition ran. The harness refuses the comparative claim on its
   own (`comparative_claim_supported=false`), and this document repeats it.
2. **Holdout correctness is unmeasured** until the 5 holdout gold specs are authored and
   human-reviewed (`reviewed: true` with a named reviewer is required by the schema).
3. **Discipline is not correctness.** The 1.000 rows measure rule-keeping from run artifacts.
4. **Reviewer time and rework are unmeasured.** No human-effort figures appear anywhere in this
   evaluation; they will be measured, not simulated, when they appear.
5. **Development-partition gold results (1.000) are expected**, since the pipeline was built
   against those cases. They demonstrate the gold path works, nothing more.
6. **Synthetic data throughout.** Nothing here is validated against real matters.

## Privacy posture

Synthetic-only, enforced by gates rather than promised: data-scope gating before any raw
payload write, a CI guard against local absolute paths, reserved non-resolvable contact
domains, and a released boundary record (`VISIBILITY_AND_RELEASE.md`) listing what publication
does not authorize.

## Reproduction

Windows: clone with `git clone -c core.longpaths=true`. Then the README quickstart
(install → validation suite → demo) followed by the three evaluation commands above.
Reports embed `--generated-at` timestamps for byte-comparable re-runs.

- Tests run: full suite, 1,357 passed (includes 25 evaluation-harness tests, negative-heavy).
- Tests not run: none skipped in the suite; no load, concurrency, or real-data tests exist.

## Remaining risks

- The holdout set is small (5 cases) and hand-authored; findings on it will be directional,
  not statistically strong. Growing it is cheap and should precede any strong claim.
- Single-machine, single-OS verification (Windows; CI covers Ubuntu).
- The grader defect found above was caught because it *deflated* scores. An inflating
  instrument defect remains the most dangerous failure class in this design; independent
  review of graders is the mitigation.

## Cross-industry portability

Nothing in the evaluation design is legal-specific. The portable pattern: a reviewed,
digest-pinned holdout split · conditions as declared specs with spend ceilings enforced in
code · (case × condition) run records · decomposable scores with explicit bases · honesty
invariants that make overclaiming a validation error. Any document-intensive,
policy-constrained workflow — claims adjudication, underwriting, regulatory submission,
procurement review — could adopt the harness unchanged and swap the fixtures and gold.
See the profile-level [portability map](https://github.com/lowelltwong-alt/lowelltwong-alt/blob/main/PORTABILITY_MAP.md).
