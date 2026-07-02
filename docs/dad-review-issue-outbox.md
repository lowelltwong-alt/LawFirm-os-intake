# DAD Review Issue Outbox

`LawFirm-os-intake` can now record complex Fable/Codex/Claude/human review
findings as candidate DAD mail. The recorder is deterministic and local-only:

```powershell
lawfirm-os-intake record-dad-review-issue `
  --issue examples/synthetic/dad-review-issues/fable-le-budget-output-expectations.issue.json `
  --repo-root . `
  --report-out .lawfirm-os-intake/dad-review-issues/dad_review_issue_outbox_report.json
```

The command writes to `.digital-asset/mail/outbox.jsonl` for DAD pickup and
creates mailbox README/.gitignore files if the mailbox does not exist. Outbox
JSONL is operational state and is ignored by git.

## What Gets Captured

Each issue record must include:

- severity: `P0`, `P1`, `P2`, or `P3`;
- issue classes such as `budget_math_risk`, `authority_boundary_risk`,
  `matter_linking_ambiguity`, `budget_driver_gap`, `synthetic_data_gap`,
  `ui_authority_risk`, `exception_lake_mapping_gap`, `learning_loop_gap`, or
  `test_gap`;
- candidate exception labels for DAD pattern analysis;
- observable context, observable decision logic, and solution path;
- fix status, fix refs, test refs, and artifact refs;
- applies-when, does-not-apply-when, and danger-if-misapplied limits.

The mail ID, thread ID, and dedupe key are stable from the issue ID/version and
payload hash. Re-running the command suppresses duplicates instead of appending
another row.

## What Stays Out

This is not a Lake write, learning promotion, or cross-repo mutation. The
recorder rejects sensitive-looking text such as private-key blocks, API-key
patterns, GitHub token patterns, email addresses, and SSN-like identifiers. It
also rejects oversized payloads so raw documents are not smuggled into mail.

The `observable_decision_logic` field is for reviewable rationale and repair
logic. It must not contain hidden chain-of-thought, real client facts, raw case
documents, credentials, or private firm rates.

## DAD Processing Intent

DAD can later consume these outbox rows to build:

- exception event classes;
- issue pattern dashboards;
- fix-outcome ledgers;
- candidate lessons;
- resurfacing rules for recurring hard problems.

Promotion remains DAD/human-reviewed. Intake only creates candidate mail.
