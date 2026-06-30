# TRACE-2026-06-30 - Post-Merge Remaining Roadmap

## Context

The remaining-roadmap planner was built while the intake PR was still awaiting
human review. After a PR is observed as merged, the planner should not keep
recommending "human PR state decision" as the first next action.

## Decision

Add `merged` as an allowed observed PR state for local closeout and PR readiness
decision evidence. When supplied closeout or PR decision evidence records
`observed_pr_state=merged`, `plan-remaining-roadmap`:

- keeps the human PR review item in the item list as completed observed evidence;
- replaces the pending PR gate with
  `human_pr_state_decision_completed_by_observed_merge`;
- moves next recommendations to manual owner issue creation, owner triage, and
  Semantic Substrate contract review;
- preserves all no-write flags.

## Red-Team Notes

- Observing `merged` is not an intake-side GitHub write and does not authorize
  owner repo implementation, canonical promotion, Lake admission, or production
  use.
- A merged intake PR is still only local candidate evidence for downstream
  owner adoption.
- The validation-runtime policy remains mandatory: full and focused pytest runs
  must use `python scripts/run_full_pytest.py` with an outer timeout at or above
  the configured policy ceiling.

## Validation

Validation is recorded on the implementing PR.
