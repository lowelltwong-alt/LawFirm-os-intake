# TRACE-2026-06-30 - PR Merge Order Readiness

## Context

The intake repo has multiple green, mergeable draft PRs that touch shared
fixture, roadmap, governance, and test surfaces. Humans need a compact answer to
"what should merge first?" without giving intake authority to merge, mark ready,
create issues, or treat draft PR evidence as production readiness.

## Decision

Add `plan-pr-merge-order`, a local candidate-only command that consumes an
explicit PR snapshot JSON and writes:

- `pr_merge_order_readiness_packet.json`;
- `pr_merge_order_readiness_packet.md`.

The packet recommends `gap_first_then_depth_audit`: land direct fixture gap
closers first, then adjacent role-expansion coverage, then rebase the depth audit
onto the expanded holdout set. It also records shared changed-file surfaces so
reviewers can anticipate rebase and validation work after each accepted merge.

## Boundaries

- No GitHub ready-for-review state change.
- No GitHub merge.
- No GitHub issue or PR creation.
- No sibling repo write.
- No Semantic Substrate promotion.
- No Exception Lake or SQLite write.
- No external write.
- No silent learning.

## Rationale

The depth audit is most useful after the fixture gap PRs land, because it should
verify the updated holdout set instead of preserving the current-main gap report
as apparent roadmap truth. A typed packet makes that ordering reviewable while
keeping all GitHub actions manual and human-gated.

## Red-Team Notes

- GitHub `MERGEABLE` does not prove semantic merge safety on shared manifests,
  docs, schemas, CLI, models, or tests.
- Merging the audit before gap-closing fixtures can make known gaps look like
  settled acceptance criteria.
- A local queue recommendation can be mistaken for merge authorization unless
  no-write flags and required manual gates are explicit.

## Acceptance

- A green open-draft snapshot produces
  `pr_merge_order_ready_manual_queue_required`.
- The default queue orders PRs `#16`, `#18`, `#17`, then `#19` for the current
  synthetic snapshot.
- Red or stale PR evidence produces `blocked_by_pr_merge_order_evidence`.
- Shared surfaces are recorded with high-risk warnings when multiple drafts
  touch governance, roadmap, manifest, schema, CLI, model, or test files.
- The CLI writes local JSON and Markdown outputs without any GitHub write,
  merge, ready-state change, sibling repo write, Lake/SQLite write, promotion,
  external write, or learning side effect.
