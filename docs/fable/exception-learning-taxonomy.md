# Exception Lake Learning Taxonomy

- Status: Fable design output, candidate-only. Extends (does not replace) `exception_mapping.py` rule definitions, `ExceptionLakeCandidate`, and the carrier-rejection learning loops.
- Author: Fable 5, 2026-07-05.
- Goal: every error, rejection, correction, appeal, appeal result, budget variance, matter-link ambiguity, QA defect, fixture weakness, and workflow discovery becomes a **structured, deduplicated, human-gated** exception candidate — and nothing learns silently.

## 1. Current state (what already exists)

- `ExceptionLakeCandidate` is type-locked to `status="dry_run_candidate"`, `canonical_promotion_required=True`, target repo `LawFirm-os-exceptions-lake-runtime`. Intake never writes the Lake. Good — keep.
- `exception_mapping.py` has versioned mapping rules (`*.v1`) with `issue_family` → `canonical_lake_class` ∈ {`retrieval_miss`, `workflow_escalation`, `authority_conflict_override`}.
- `carrier_rejection_learning.py` has 12 named learning loops with owner repos; `reviewed_learning_gate.py` gates promotion.
- Gap: no lifecycle beyond "candidate emitted"; no dedupe keys; no severity; no explicit DAD-vs-Lake routing rule; matter-link and invariant-audit classes don't exist yet.

## 2. Candidate exception classes (superset taxonomy)

`issue_family` (local, fine-grained) → `canonical_lake_class` (Lake canon, coarse). New families marked ★.

| issue_family | lake class | typical producer |
|---|---|---|
| broken_template_formula | workflow_escalation | budget_form audit |
| missing_budget_code_mapping | retrieval_miss | budget_form |
| unknown_budget_driver | workflow_escalation | budget engine |
| guideline_or_cap_issue | workflow_escalation | guideline flags |
| carrier_preapproval_required | workflow_escalation | preapproval report |
| budget_actual_cost_variance | workflow_escalation | budget_actuals |
| ★ budget_invariant_violation | workflow_escalation | `budget_invariants.py` (PR-BK1) — I1–I17 breaches |
| ★ scenario_policy_invalid | workflow_escalation | D1/D7/D8 blocks |
| ★ rate_resolution_ambiguous | authority_conflict_override | D2–D4 blocks (two authorities claim the rate) |
| carrier_rejection_* (existing channels) | workflow_escalation | rejection capture |
| ★ carrier_appeal_outcome | workflow_escalation | appeal result recording (human-entered) |
| ★ matter_link_ambiguity | workflow_escalation | linking HOLD dispositions |
| ★ matter_link_conflict | authority_conflict_override | R3/R5/B1–B3 blocks |
| ★ human_correction_of_machine_output | workflow_escalation | any confirmation that supersedes with changed values (the diff is the payload) |
| ★ qa_gate_defect | workflow_escalation | QA/replay failures on fixtures previously green |
| ★ fixture_weakness | retrieval_miss | eval ladder: fixture passes but holdout variant fails, or gold marked stale |
| ★ workflow_discovery | workflow_escalation | free-form but structured "we found a missing step/rule" — the only class allowed prose-first |
| prompt_injection / prohibited_transition (existing) | workflow_escalation | safety layer |

Rule: adding an issue_family is a versioned edit to `exception_mapping.py` RULE_DEFINITIONS (a reviewable diff), never a runtime string.

## 3. Lifecycle

Lifecycle state lives **outside** intake (intake artifacts are per-run and immutable); intake only ever emits `dry_run_candidate`. The lifecycle below is the handoff contract for `LawFirm-os-exceptions-lake-runtime`:

```
dry_run_candidate ─► admitted_pending_review ─► triaged ─┬─► lesson_extracted ─► promotion_proposed ─► promoted_to_canon
        │                     │                          ├─► duplicate_of(existing)                (Semantic Substrate gate)
        │                     │                          ├─► wont_fix(reason)
        └─► rejected_at_admission (schema/scope)         └─► expired(ttl)
```

Transitions requiring a human actor: `triaged→lesson_extracted`, `promotion_proposed→promoted_to_canon` (always), and any transition out of `authority_conflict_override` class. Machine-allowed transitions: dedupe (`duplicate_of`) and `expired`. Every transition is append-only with actor + timestamp.

## 4. Dedupe keys

Dedupe must not collapse distinct legal events, and must not let one flaky formula flood the Lake. Two-level key:

```
identity_key  = sha256(issue_family | primary_structured_ref | normalized_subject_ids)
  - primary_structured_ref: the FIRST structured_ref (rule-defined, e.g. the policy path or invariant id)
  - normalized_subject_ids: run-independent ids (template_id, phase_id/task_id, carrier_id,
    driver_id, cluster rule id) — NEVER run_id, packet_id, or generated ids
recurrence_key = identity_key + calendar week
```

- Same `identity_key`, new run ⇒ increment `occurrence_count` on the existing record (recurrence is signal, not noise — count it, don't duplicate it).
- Distinct matters (different confirmed cluster/claim contexts) intentionally produce distinct `normalized_subject_ids` for matter-scoped families (variance, rejection) — those are NOT duplicates.
- `human_correction_of_machine_output` dedupes on (field_path, from_class, to_class), not on values — "reviewers keep flipping matter_family from X to Y" is one lesson with a count.

## 5. Severity rules (deterministic)

| Severity | Rule |
|---|---|
| S0 (block-now) | any `authority_conflict_override`; any prohibited-transition/prompt-injection; any invariant violation in {I1, I4, I6, I14} (arithmetic or scope corruption) |
| S1 (review-before-budget) | budget-blocking states: scenario_policy_invalid, rate_resolution_ambiguous, matter_link_conflict, L&E blocked facts |
| S2 (review-with-budget) | guideline/cap flags, preapproval required, variance over threshold, matter_link_ambiguity holds |
| S3 (queueable) | fixture_weakness, qa_gate_defect on non-shipping paths, workflow_discovery |

Severity is a pure function of (issue_family, lake class, invariant id). No model-judged severity.

## 6. Routing: DAD vs Exception Lake vs local intake artifacts

| Destination | What belongs there | Test |
|---|---|---|
| **Local run artifacts** (jsonl/json in run dir) | every candidate, always, in full — the source of truth for replay | "would deleting this break replay?" |
| **Exception Lake** (via dry-run candidates + admission bundle) | operational events tied to a run/matter context: variances, rejections, ambiguity, invariant violations, QA defects | "is this an *event* that should be counted, triaged, and trended?" |
| **DAD candidate outbox** (`cross_repo_owner_issue_drafts` path) | *reusable lessons and complex issues*: distilled patterns (with occurrence counts), proposed policy/taxonomy changes, cross-repo design gaps, anything requiring an owner decision in another repo | "is this a *lesson or decision request*, not an event?" |

Rule of thumb: Lake gets events; DAD gets lessons. An event stream (10 rejections with the same identity_key) becomes ONE DAD outbox item citing the Lake records. A DAD item must carry: before/after behavior statement, evidence refs, proposed owner repo, and eval that would validate the change — exactly the shape `PROPOSAL_POLICY` in `carrier_rejection_learning.py` already uses; generalize that shape to all families.

## 7. Anti-silent-learning invariants

1. **No emitted candidate changes behavior.** Emitting an exception candidate must have zero effect on math, thresholds, templates, or policies in the same or later runs, until a human-reviewed, versioned policy/config diff lands. (Learning = git diff, never state.)
2. **Every behavior-changing diff cites its candidates.** Policy/template PRs must reference the identity_keys they respond to (PR template field), so learning is auditable in both directions.
3. **Shadow-first.** A proposed change replays against the calibration corpus + holdouts as a shadow eval (`learning_shadow_eval_*` machinery) before merge; the shadow report is attached to the PR.
4. **Holdout hygiene.** Holdout fixtures may gate promotion but never generate `fixture_weakness` lessons that tune the same rule they hold out (no training on the test set). Mark holdout-derived candidates `holdout_origin=true`; the reviewed-learning gate must refuse proposals whose only evidence is holdout-origin.
5. **Feedback-loop damping.** A change that was itself produced by loop L cannot be cited as evidence for a further change in loop L within the same review cycle; require fresh events post-merge. Prevents self-amplifying threshold drift.
6. **Counts, not narratives, trigger review.** Escalation to DAD requires `occurrence_count ≥ N` (per-family N in config) OR severity ≤ S1 — a single S3 anecdote does not open a lesson.

## 8. Codex handoff (ordered)

### PR-EX1 — identity_key + severity on ExceptionLakeCandidate (risk: low)
- Files: `models.py` (additive optional fields: `identity_key`, `severity`, `occurrence_hint`, `holdout_origin`), `exceptions.py`/`exception_mapping.py` (compute keys per §4, severity per §5), tests `test_exception_candidates.py`, `test_exception_lake_mapping_package.py`.
- Do NOT: change existing candidate emission sites' semantics; keys are additive metadata.

### PR-EX2 — new issue families (risk: low)
- Files: `exception_mapping.py` (★ families as `*.v1` rules), producers: `budget_invariants.py` (after PR-BK1), matter-linking (after PR-ML3), human-review outcome diff capture in `budget_human_review_outcomes.py`.
- Tests: one emission test per family; dedupe-key stability tests (same event twice ⇒ same key; different matter ⇒ different key).

### PR-EX3 — DAD outbox generalization (risk: medium)
- Purpose: generalize `PROPOSAL_POLICY` shape into a family-agnostic `LessonDraft` (before/after/eval/owner) built from candidate clusters by identity_key with occurrence counts; route via existing `cross_repo_owner_issue_drafts.py`.
- Tests: threshold behavior (no lesson below N), holdout-origin refusal, S0/S1 immediate-lesson path.
- Do NOT: auto-file issues anywhere external; drafts stay local artifacts.

### PR-EX4 — Lifecycle handoff draft for Exceptions Lake runtime (risk: low, docs+schema only)
- Files: `docs/fable/exception-learning-taxonomy.md` (this doc) referenced from `promotion/`/`cross-repo-promotion-package`; JSON schema export for the lifecycle record so the Lake repo can adopt it; an `exception_lake_handoff` manifest field carrying §3 states.
- The Lake repo (not intake) implements state storage.

## 9. Exception Lake handoff draft (summary for the runtime repo)

- Accept only `dry_run_candidate` with valid `identity_key`, severity, and ≥1 structured_ref; reject otherwise at admission (`rejected_at_admission`).
- Maintain occurrence counters keyed by identity_key; expose per-family weekly trend.
- Enforce §3 transition/actor matrix; expose `duplicate_of` links.
- Emit DAD-bound lesson candidates only when §7.6 thresholds fire; never mutate intake artifacts.
