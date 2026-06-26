# TRACE 2026-06-26: Cross-Repo Owner Adoption Packets

## Decision

Add `build-cross-repo-owner-adoption` as the bridge between the static
cross-repo promotion package and the run-specific readiness/PR review evidence.

The command writes:

- `cross_repo_owner_adoption_report.json`
- `cross_repo_owner_adoption_report.md`
- `cross_repo_owner_adoption_packets.jsonl`
- per-owner JSON/Markdown packets under `owner_adoption_packets/`

## Why

The static promotion package lists candidate proposals, but after PR readiness
review each owning repo needs a concise packet that says what to inspect, what
acceptance checks matter, what the red-team risk is, and which actions still
belong outside intake.

## Red-Team Notes

- A candidate promotion package can be mistaken for actual promotion.
- A local readiness audit can be mistaken for owner adoption.
- Owner work can be skipped if all proposals are left in one broad inventory.
- Creating GitHub issues or PRs from intake would become a sibling-repo write.
- Lake, Orchestrator, and Substrate authority must remain with those owners.

## Boundary

The command does not create issues, open PRs, write sibling repos, promote
canon, admit Lake records, write SQLite, apply learning, implement connectors,
or authorize production use.

## Tests

- Ready PR-review evidence produces one owner packet for each of the five target
  repos with all nine static proposals grouped by owner.
- Blocked PR-review evidence keeps every owner packet blocked.
- CLI writes the report, packet JSONL, per-owner packets, and no-write flags.
