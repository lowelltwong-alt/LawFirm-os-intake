# Branch Model

This repository's branch list is part of its evidence, not clutter. It records a multi-agent,
gate-checked development process.

| Pattern | Meaning |
|---|---|
| `main` | Default branch. Released, reviewed state. |
| `codex/*` | Background agent work branches. Each corresponds to a bounded task packet; work lands through PRs with squash merges, so tips may look stale after their content has merged. |
| `feat/*` | Human-directed feature lines (e.g. `feat/port-dad-layer-docs`). |
| `chore/*` | Maintenance and publication-hygiene changes. |

## How to read it

- The PR history, not the branch list, is the merge record: squash merges mean a branch whose
  content landed still shows an unmerged tip.
- Decision records for non-trivial changes live in `docs/decisions/` as `TRACE-*.md` files.
- Agent branches are intentionally left visible: reviewing how bounded agent tasks were specified,
  validated, and merged is part of what this repository demonstrates.

## Hygiene policy

Fully merged branches are deleted opportunistically, never under deadline pressure, and only after
`git branch -r --merged` confirmation. Stale unmerged branches that carry decision records or
registry changes require an explicit disposition rather than silent deletion.
