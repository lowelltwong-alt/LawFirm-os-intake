# Endpoints and Commands

There are no network endpoints in the starter.

## CLI

### Intake preflight

```bash
python -m lawfirm_os_intake preflight \
  --input examples/synthetic/inbound/carrier-assignment-medmal.json \
  --practice-profile context/synthetic-profiles/insurance-defense.yaml \
  --out-dir .lawfirm-os-intake/runs
```

### Build budget after human confirmation

```bash
python -m lawfirm_os_intake build-budget \
  --preflight-packet PATH/TO/intake_preflight_packet.json \
  --confirmation PATH/TO/human_confirmation.json \
  --practice-profile context/synthetic-profiles/insurance-defense.yaml \
  --out-dir .lawfirm-os-intake/budget
```

### Complete synthetic demo

```bash
bash scripts/smoke_demo.sh
```

### Record append-only human budget review changes

```bash
python -m lawfirm_os_intake record-budget-review \
  --budget PATH/TO/legal_budget_proposal.json \
  --review examples/synthetic/budget-review/medmal-human-budget-review-change.json \
  --out-dir .lawfirm-os-intake/budget-review
```

This writes `budget_review_change_record.json`,
`budget_revision_history.jsonl`, `budget_revision_report.json`,
`budget_revision_report.md`, and
`budget_revision_exception_lake_candidates.jsonl`. The command records human
budget changes as candidate append-only evidence, calculates phase/code deltas,
and emits a dry-run `budget_human_change_recorded` Lake candidate. It does not
mutate the original budget, write a superseding budget, authorize submission,
write billing, write SQLite, or admit Lake records.

### Compare budget to synthetic actual costs

```bash
python -m lawfirm_os_intake compare-budget-actuals \
  --budget PATH/TO/legal_budget_proposal.json \
  --actuals examples/synthetic/actuals/medmal-phase-code-actuals.json \
  --budget-revision-report .lawfirm-os-intake/budget-review/budget_revision_report.json \
  --out-dir .lawfirm-os-intake/budget-actuals
```

This writes `budget_actual_comparison_report.json`,
`budget_actual_comparison_report.md`, and
`budget_actual_variance_candidates.jsonl`. The command compares original or
human-revised candidate budgets to governed synthetic actuals by phase and UTBMS
code, flags zero-budget/positive-actual rows as over-threshold, and emits dry-run
variance candidates. It performs no billing connector read or write and does not
silently learn from variance.

### Capture synthetic carrier rejection responses

```bash
python -m lawfirm_os_intake capture-carrier-rejections \
  --budget PATH/TO/legal_budget_proposal.json \
  --source-bundle examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json \
  --out-dir .lawfirm-os-intake/carrier-rejections
```

This writes `carrier_rejection_reconciliation_report.json`,
`carrier_rejection_remediation_cases.json`, and
`carrier_rejection_exception_lake_candidates.jsonl`. The command reconciles
synthetic expected responses against captured notices, classifies local candidate
labels deterministically, collapses duplicate notices by idempotency key, and
keeps all Lake records dry-run only.

### Review synthetic carrier rejection remediation cases

```bash
python -m lawfirm_os_intake review-carrier-rejections \
  --reconciliation-report .lawfirm-os-intake/carrier-rejections/carrier_rejection_reconciliation_report.json \
  --out-dir .lawfirm-os-intake/carrier-rejection-review
```

This writes `carrier_rejection_review_packet.json`,
`carrier_rejection_review_notes.md`, and
`carrier_rejection_review_decision_template.json`. The packet gives each
remediation case a recommended human review action, explains why, surfaces
red-team checks, and preserves the no-Lake-write, no-external-submission, and
no-silent-learning boundaries.

### Propose carrier rejection learning candidates

```bash
python -m lawfirm_os_intake propose-carrier-rejection-learning \
  --review-packet .lawfirm-os-intake/carrier-rejection-review/carrier_rejection_review_packet.json \
  --out-dir .lawfirm-os-intake/carrier-rejection-learning
```

This writes `carrier_rejection_learning_report.json` and
`carrier_rejection_learning_report.md`. The report groups reviewed rejection
pressure into candidate learning proposals for guideline, budget-driver,
template, narrative, preapproval, parser, reconciliation, SLA, validation, and
appeal-outcome loops. Every proposal remains blocked until human-reviewed outcome
evidence exists, and the command performs no profile, template, connector, Lake,
or external mutation.

### Review aggregate learning gate candidates

```bash
python -m lawfirm_os_intake review-learning-gate \
  --carrier-learning-report .lawfirm-os-intake/carrier-rejection-learning/carrier_rejection_learning_report.json \
  --budget-revision-report .lawfirm-os-intake/budget-review/budget_revision_report.json \
  --budget-actual-comparison-report .lawfirm-os-intake/budget-actuals/budget_actual_comparison_report.json \
  --out-dir .lawfirm-os-intake/reviewed-learning-gate
```

This writes `reviewed_learning_gate_report.json`,
`reviewed_learning_gate_report.md`, and
`reviewed_learning_gate_candidates.jsonl`. The report aggregates carrier
rejection learning proposals, human budget-revision deltas, and budget actual
variance drivers into one candidate learning gate. Every candidate remains
blocked until human-reviewed outcome evidence, append-only evidence recording,
synthetic fixture updates, shadow evals, and owning-repo review exist. The
command performs no profile, template, connector, budget, guideline, Lake,
SQLite, or external mutation.

### Audit learning promotion readiness

```bash
python -m lawfirm_os_intake audit-learning-promotion-readiness \
  --reviewed-learning-gate-report .lawfirm-os-intake/reviewed-learning-gate/reviewed_learning_gate_report.json \
  --out-dir .lawfirm-os-intake/learning-promotion-readiness
```

This writes `learning_shadow_eval_plan.json`,
`learning_shadow_eval_plan.md`, `learning_promotion_readiness_report.json`, and
`learning_promotion_readiness_report.md`. The audit builds one shadow-eval case
per reviewed-learning candidate and blocks promotion until proposed change
artifacts, synthetic fixture updates, shadow eval results, regression checks, and
owning-repo review exist. It does not apply proposed changes, mutate baselines,
authorize promotion, write Lake/SQLite records, or perform external writes.

### Draft learning proposed-change artifacts

```bash
python -m lawfirm_os_intake draft-learning-proposed-changes \
  --shadow-eval-plan .lawfirm-os-intake/learning-promotion-readiness/learning_shadow_eval_plan.json \
  --promotion-readiness-report .lawfirm-os-intake/learning-promotion-readiness/learning_promotion_readiness_report.json \
  --out-dir .lawfirm-os-intake/learning-proposed-changes
```

This writes `learning_proposed_change_set.json`,
`learning_proposed_change_set.md`, and `learning_proposed_changes.jsonl`. Each
draft change names the target learning loop, owning repo, proposed behavior,
recommendation, recommendation rationale, red-team objections, required fixture
updates, eval suites, regression guardrails, and next gates. These are reviewer
notes and shadow-eval inputs only; the command applies no changes, authorizes no
promotion, writes no Lake/SQLite records, and performs no external writes.

### Run learning shadow eval

```bash
python -m lawfirm_os_intake run-learning-shadow-eval \
  --proposed-change-set .lawfirm-os-intake/learning-proposed-changes/learning_proposed_change_set.json \
  --fixture-result examples/synthetic/learning/shadow-eval-result-budget-driver.json \
  --fixture-result examples/synthetic/learning/shadow-eval-result-capture-completeness.json \
  --out-dir .lawfirm-os-intake/learning-shadow-eval
```

This writes `learning_shadow_eval_result_report.json`,
`learning_shadow_eval_result_report.md`, and
`learning_shadow_eval_results.jsonl`. The harness checks that every proposed
change has synthetic fixture result evidence, required eval suites, regression
guardrails, red-team notes, and no-mutation/no-promotion boundaries. Missing
fixture evidence blocks; failed eval or guardrail evidence fails; passing results
still require human shadow-eval review and owning-repo promotion review. The
command applies no proposed changes, mutates no baselines, writes no Lake/SQLite
records, and performs no external writes.

### Build budget fixture-binding handoff

```bash
python -m lawfirm_os_intake build-budget-fixture-binding-handoff \
  --fixture-binding-candidate-report .lawfirm-os-intake/budget-fixture-bindings/budget_fixture_binding_candidate_report.json \
  --out-dir .lawfirm-os-intake/budget-fixture-binding-handoff
```

This writes `budget_fixture_binding_handoff_report.json`,
`budget_fixture_binding_handoff_report.md`, and
`budget_fixture_binding_handoff_items.jsonl`. The handoff tells the human
reviewer which approved synthetic replay outputs are ready for a separate
fixture-update PR and which candidates remain blocked, with why-notes,
recommended owner actions, and red-team objections. It does not update fixture
files, create a PR, apply learning, mutate profiles/templates/guidelines, write
Lake/SQLite records, or perform external writes.

### Audit budget calibration readiness

```bash
python -m lawfirm_os_intake audit-budget-calibration-readiness \
  --corpus-report .lawfirm-os-intake/budget-corpus/budget_calibration_corpus_report.json \
  --replay-plan .lawfirm-os-intake/budget-replay-plan/budget_corpus_replay_plan.json \
  --replay-execution-report .lawfirm-os-intake/budget-replay-execution/budget_corpus_replay_execution_report.json \
  --replay-review-packet .lawfirm-os-intake/budget-replay-review/budget_corpus_replay_review_packet.json \
  --replay-review-outcome-report .lawfirm-os-intake/budget-replay-review-outcome/budget_corpus_replay_review_outcome_report.json \
  --fixture-binding-candidate-report .lawfirm-os-intake/budget-fixture-bindings/budget_fixture_binding_candidate_report.json \
  --fixture-binding-handoff-report .lawfirm-os-intake/budget-fixture-binding-handoff/budget_fixture_binding_handoff_report.json \
  --out-dir .lawfirm-os-intake/budget-calibration-readiness
```

This writes `budget_calibration_readiness_report.json` and
`budget_calibration_readiness_report.md`. The audit checks that the corpus,
replay plan, replay execution, human replay review packet, append-only review
outcome, fixture-binding candidate report, and fixture-binding handoff all line
up by ID and preserve no-mutation/no-write boundaries. A passing report means
ready for manual fixture-update review only. It does not update fixtures, create
a PR, apply learning, mutate profiles/templates/guidelines, write Lake/SQLite
records, or perform external writes.

### Build learning owner handoffs

```bash
python -m lawfirm_os_intake build-learning-owner-handoffs \
  --shadow-eval-result-report .lawfirm-os-intake/learning-shadow-eval/learning_shadow_eval_result_report.json \
  --out-dir .lawfirm-os-intake/learning-owner-handoffs
```

This writes `learning_owner_handoff_report.json`,
`learning_owner_handoff_report.md`, `learning_owner_handoff_packages.jsonl`, and
one JSON/Markdown package per owning repo under `owner_handoffs/`. The handoff
separates passed, failed, and blocked candidates for each target owner. Passed
candidates are only ready for owner review, failed candidates must be declined or
repaired, and blocked candidates stay blocked pending evidence. The command
performs no promotion, implementation, Lake/SQLite write, sibling-repo write, or
external write.

### Audit intake vertical readiness

```bash
python -m lawfirm_os_intake audit-intake-vertical-readiness \
  --owner-handoff-report .lawfirm-os-intake/learning-owner-handoffs/learning_owner_handoff_report.json \
  --budget-event-lake-bundle-report .lawfirm-os-intake/budget-event-lake-bundle/budget_event_lake_admission_bundle_report.json \
  --repo-root . \
  --out-dir .lawfirm-os-intake/intake-vertical-readiness-audit
```

This writes `intake_vertical_readiness_audit_report.json` and
`intake_vertical_readiness_audit_report.md`. The audit checks the local
intake-to-budget, carrier rejection, budget revision, actual-cost comparison,
reviewed learning, shadow-eval, owner-handoff, promotion-package, and command
surfaces, then validates the generated learning artifact chain back through the
reviewed-learning gate and the generated budget-event Lake bundle. A passing
audit means the branch is ready for human PR review while external adoption
remains required. It does not mark the PR ready,
promote canon, write sibling repos, implement connectors, admit Lake records,
write SQLite, apply proposed changes, or perform silent learning.

### Build PR review checklist

```bash
python -m lawfirm_os_intake build-pr-review-checklist \
  --readiness-audit-report .lawfirm-os-intake/intake-vertical-readiness-audit/intake_vertical_readiness_audit_report.json \
  --out-dir .lawfirm-os-intake/pr-review-checklist
```

This writes `pr_review_checklist.json` and `pr_review_checklist.md`. The
checklist gives the human reviewer explicit recommended checks, why-notes,
red-team notes, blocking readiness items, required human decisions, validation
commands, and no-write boundary flags before any PR state change. It does not
mark a PR ready, call GitHub write APIs, promote canon, write sibling repos,
admit Lake records, write SQLite, apply proposed changes, or authorize
production use.

### Build cross-repo owner adoption packets

```bash
python -m lawfirm_os_intake build-cross-repo-owner-adoption \
  --promotion-package promotion/cross_repo_promotion_package.json \
  --readiness-audit-report .lawfirm-os-intake/intake-vertical-readiness-audit/intake_vertical_readiness_audit_report.json \
  --pr-review-checklist .lawfirm-os-intake/pr-review-checklist/pr_review_checklist.json \
  --out-dir .lawfirm-os-intake/cross-repo-owner-adoption
```

This writes `cross_repo_owner_adoption_report.json`,
`cross_repo_owner_adoption_report.md`,
`cross_repo_owner_adoption_packets.jsonl`, and owner-specific packets under
`owner_adoption_packets/`. The packets group the static promotion proposals by
target owner and bind them to the live readiness audit and PR checklist. They
name owner actions, acceptance checks, and red-team notes for Semantic
Substrate, Orchestrator, Exception Lake, Skills Registry, and Legal Knowledge
Runtime. The command does not create issues, open PRs, write sibling repos,
promote canon, admit Lake records, write SQLite, apply learning, or authorize
production use.

### Build cross-repo owner issue drafts

```bash
python -m lawfirm_os_intake build-cross-repo-owner-issue-drafts \
  --owner-adoption-report .lawfirm-os-intake/cross-repo-owner-adoption/cross_repo_owner_adoption_report.json \
  --out-dir .lawfirm-os-intake/cross-repo-owner-issue-drafts
```

This writes `cross_repo_owner_issue_draft_report.json`,
`cross_repo_owner_issue_draft_report.md`,
`cross_repo_owner_issue_drafts.jsonl`, and per-owner Markdown/JSON drafts under
`owner_issue_drafts/`. The drafts contain suggested issue titles, labels, source
evidence refs, owner actions, acceptance checks, red-team notes, and boundaries
for manual creation in the owning repos. The command does not create issues,
open PRs, write sibling repos, promote canon, admit Lake records, write SQLite,
apply learning, or authorize production use.

### Audit intake local closeout

```bash
python -m lawfirm_os_intake audit-intake-local-closeout \
  --readiness-audit-report .lawfirm-os-intake/intake-vertical-readiness-audit/intake_vertical_readiness_audit_report.json \
  --pr-review-checklist .lawfirm-os-intake/pr-review-checklist/pr_review_checklist.json \
  --owner-adoption-report .lawfirm-os-intake/cross-repo-owner-adoption/cross_repo_owner_adoption_report.json \
  --owner-issue-draft-report .lawfirm-os-intake/cross-repo-owner-issue-drafts/cross_repo_owner_issue_draft_report.json \
  --observed-pr-number 7 \
  --observed-pr-state draft \
  --out-dir .lawfirm-os-intake/intake-local-closeout
```

This writes `intake_local_closeout_report.json` and
`intake_local_closeout_report.md`. The audit aggregates the final local evidence
chain and reports whether intake-local candidate work is ready for manual
external actions. It preserves the remaining human PR decision, manual owner
issue creation, owner triage, owner implementation PR, and cross-repo validation
gates. It does not mark a PR ready, create issues, open PRs, write sibling repos,
promote canon, admit Lake records, write SQLite, apply learning, or authorize
production use.

### Draft carrier rejection Orchestrator interface

```bash
python -m lawfirm_os_intake draft-carrier-rejection-orchestrator-interface \
  --out-dir .lawfirm-os-intake/carrier-rejection-orchestrator-interface
```

This writes `carrier_rejection_orchestrator_interface.json` and
`carrier_rejection_orchestrator_interface.md`. The draft specifies future
Orchestrator-owned connector channels, response-state ledger duties, human pause
points, appeal-submission gate requirements, and guarded Exception Lake handoff.
It does not implement connectors, assign routes, submit appeals, write Lake
records, or authorize intake to perform production capture.

### Draft carrier rejection Exception Lake admission proposal

```bash
python -m lawfirm_os_intake draft-carrier-rejection-lake-admission \
  --out-dir .lawfirm-os-intake/carrier-rejection-lake-admission
```

This writes `carrier_rejection_lake_admission_proposal.json` and
`carrier_rejection_lake_admission_proposal.md`. The proposal defines candidate
append-only Lake record families for carrier rejection notices, reconciliation,
human review outcomes, appeal submissions, appeal results, financial outcomes,
and learning candidates. It requires idempotency fields, support hashes,
record hashes, Orchestrator evidence packets, and correction-by-supersession.
It does not create SQLite tables, write Lake records, assign canonical event
classes, or authorize intake to persist runtime evidence.

### Audit carrier rejection roadmap completion

```bash
python -m lawfirm_os_intake audit-carrier-rejection-roadmap \
  --repo-root . \
  --out-dir .lawfirm-os-intake/carrier-rejection-roadmap-audit
```

This writes `carrier_rejection_roadmap_audit_report.json` and
`carrier_rejection_roadmap_audit_report.md`. The audit checks that carrier
rejection roadmap slices 1-8 have local proof artifacts and command refs, then
keeps Orchestrator, Exception Lake, and Semantic Substrate adoption as required
external work. It performs no connector implementation, SQLite write, Lake
admission, sibling repo write, external write, or canonical mutation.

## Exit posture

- `0`: local workflow step completed and artifacts emitted.
- `2`: blocked by input, data, confirmation, contract, or filesystem validation.

A zero exit code does not mean legal approval or external authorization.
