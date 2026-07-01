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
  --labor-employment-budget-fact-report PATH/TO/labor_employment_budget_fact_audit_report.json \
  --out-dir .lawfirm-os-intake/budget
```

`--labor-employment-budget-fact-report` is optional. When supplied, critical
L&E fact gaps fail the budget precondition gate before conflict seed or budget
proposal output. Non-critical L&E review gaps pass through as supported budget
unknowns for human review.

### Complete synthetic demo

```bash
bash scripts/smoke_demo.sh
```

### Validation runtime policy

```bash
python scripts/run_full_pytest.py
python scripts/run_validation_suite.py
```

`config/validation-runtime-policy.yaml` declares the minimum local ceilings for
heavy validation commands. Full and focused pytest runs use the wrapper above
and require a 3600 second ceiling. Direct pytest invocation is blocked so a run
cannot silently inherit a shorter ceiling. Smoke runs also require a 3600 second
ceiling. Schema export, repo validation, and ruff checks require at least 180
seconds. The full validation-suite runner applies those policy ceilings to repo
validation, schema export, lint, full pytest, smoke, and final repo validation.

### Audit labor/employment budget fact gaps

```bash
python -m lawfirm_os_intake audit-labor-employment-budget-facts \
  --repo-root . \
  --manifest examples/synthetic/courtlistener-derived/labor-employment-dataset-manifest.json \
  --out-dir .lawfirm-os-intake/le-budget-facts
```

This writes `labor_employment_budget_fact_audit_report.json` and
`labor_employment_budget_fact_audit_report.md`. The command checks candidate
source-bound coverage for labor/employment budget facts: employee/employer
identity, payer/client posture, supervisors or individual defendants,
joint-employer or affiliate structure, claims, class/collective posture,
timeline, damages, ESI/custodians, depositions, experts/vendors, policy
documents, and carrier/rate guideline context. Critical missing or
human-review-only facts keep the budget readiness state at
`blocked_missing_critical_facts`. It does not output a budget amount, approve or
submit a budget, clear conflicts, open a matter, write Lake/SQLite records,
perform external writes, or learn from corrections.

### Audit ignored public-data cache

```bash
python -m lawfirm_os_intake audit-public-data-cache \
  --repo-root . \
  --cache-root .lawfirm-os-intake/public-data-cache \
  --out-dir .lawfirm-os-intake/public-data-cache-audit
```

This writes `public_data_cache_audit_report.json` and
`public_data_cache_audit_report.md`. The command validates
`public_data_cache_manifest.json`, checks that each source is cataloged in
`examples/public/catalog.yaml`, verifies each cached file's SHA-256 digest and
byte count, and blocks samples that resolve into tracked repo payload paths. A
passing report is only ready for human public-data cache review. It does not
ingest public records into runtime, create fixtures, authorize adapters, write
Lake/SQLite records, perform external writes, or permit public data as intake
input.

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

### Build budget actual variance owner adoption packets

```bash
python -m lawfirm_os_intake build-budget-actual-variance-owner-adoption \
  --budget-actual-comparison-report .lawfirm-os-intake/budget-actuals/budget_actual_comparison_report.json \
  --budget-actual-variance-ledger-report .lawfirm-os-intake/budget-actuals/budget_actual_variance_ledger_report.json \
  --out-dir .lawfirm-os-intake/budget-actual-variance-owner-adoption
```

This writes `budget_actual_variance_owner_adoption_report.json`,
`budget_actual_variance_owner_adoption_report.md`,
`budget_actual_variance_owner_adoption_packets.jsonl`, and owner-specific
JSON/Markdown packets under `budget_actual_variance_owner_packets/`. The packets
route candidate actual-variance labels to Semantic Substrate, governed
billing-actuals workflow work to Orchestrator, and append-only admission,
idempotency, hash, and SQLite-owner work to Exception Lake. Intake does not
read or write billing systems, create issues or PRs, write sibling repos, promote
canon, admit Lake/SQLite records, mutate budgets, profiles, templates, or
guidelines, or apply learning.

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

### Record learning shadow-eval fixture evidence

```bash
python -m lawfirm_os_intake record-learning-shadow-eval-fixture-results \
  --proposed-change-set .lawfirm-os-intake/learning-proposed-changes/learning_proposed_change_set.json \
  --review .lawfirm-os-intake/learning-shadow-eval-fixture-review/review.json \
  --out-dir .lawfirm-os-intake/learning-shadow-eval-fixture-evidence
```

This writes `learning_shadow_eval_fixture_evidence_report.json`,
`learning_shadow_eval_fixture_evidence_report.md`, a normalized
`learning_shadow_eval_fixture_review_record.json`, per-fixture JSON files under
`learning_shadow_eval_fixture_results/`, and
`learning_shadow_eval_fixture_results.jsonl`. The command binds reviewer
decisions to the live proposed-change IDs, fails closed on ID/candidate
mismatches, records partial evidence when some proposed changes are missing, and
keeps all no-mutation/no-promotion/no-Lake-write boundaries intact.

### Run learning shadow eval

```bash
python -m lawfirm_os_intake run-learning-shadow-eval \
  --proposed-change-set .lawfirm-os-intake/learning-proposed-changes/learning_proposed_change_set.json \
  --fixture-result-report .lawfirm-os-intake/learning-shadow-eval-fixture-evidence/learning_shadow_eval_fixture_evidence_report.json \
  --out-dir .lawfirm-os-intake/learning-shadow-eval
```

This writes `learning_shadow_eval_result_report.json`,
`learning_shadow_eval_result_report.md`, and
`learning_shadow_eval_results.jsonl`. The harness checks that every proposed
change has synthetic fixture result evidence, required eval suites, regression
guardrails, red-team notes, and no-mutation/no-promotion boundaries. Fixture
evidence may come from individual `--fixture-result` files or reviewed
`--fixture-result-report` artifacts. Missing fixture evidence blocks; failed eval
or guardrail evidence fails; passing results still require human shadow-eval
review and owning-repo promotion review. The command applies no proposed changes,
mutates no baselines, writes no Lake/SQLite records, and performs no external
writes.

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

### Record budget fixture update review

```bash
python -m lawfirm_os_intake record-budget-fixture-update-review \
  --calibration-readiness-report .lawfirm-os-intake/budget-calibration-readiness/budget_calibration_readiness_report.json \
  --review .lawfirm-os-intake/budget-fixture-update-review/fixture_update_review_decision.json \
  --out-dir .lawfirm-os-intake/budget-fixture-update-review
```

This writes `budget_fixture_update_review_record.json`,
`budget_fixture_update_review_history.jsonl`,
`budget_fixture_update_review_report.json`, and
`budget_fixture_update_review_report.md`. The review input must be a
human-authored decision JSON bound to the supplied readiness report; see
`examples/synthetic/fixture-update-review/medmal-fixture-update-review-accept.json`
for a synthetic shape example. Accepted decisions mean only that a separate
human-reviewed fixture-update PR is required if humans choose to update fixtures.
The command does not update fixtures, create a PR, apply calibration or learning,
mutate budgets/profiles/templates/guidelines, write Lake/SQLite records, or
perform external writes.

### Build budget fixture update PR package

```bash
python -m lawfirm_os_intake build-budget-fixture-update-pr-package \
  --fixture-update-review-report .lawfirm-os-intake/budget-fixture-update-review/budget_fixture_update_review_report.json \
  --out-dir .lawfirm-os-intake/budget-fixture-update-pr-package
```

This writes `budget_fixture_update_pr_package_report.json`,
`budget_fixture_update_pr_package_report.md`, and
`budget_fixture_update_pr_package_items.jsonl` when accepted review decisions
require manual package items. The package is a reviewer-ready instruction set
for a separate fixture-update PR; it does not edit fixtures, create a GitHub PR,
apply calibration or learning, mutate budgets/profiles/templates/guidelines,
write Lake/SQLite records, or perform external writes.

### Audit public source methodology

```bash
python -m lawfirm_os_intake audit-public-source-methodology \
  --repo-root . \
  --out-dir .lawfirm-os-intake/public-source-methodology
```

This writes `public_source_methodology_report.json` and
`public_source_methodology_report.md`. The audit checks that the planning-only
public source catalog covers the Phase 2 structural sources, every source has
methodology role, safe/prohibited uses, review gates, synthetic-conversion
rules, retention/privacy posture, and `adapter_status=not_authorized`, and that
the existing metadata-only public-data boundary still passes. A passing report
means ready for human public-source methodology review only; it does not ingest
public records, authorize adapters, write Lake/SQLite records, or permit runtime
public-data use.

### Plan public synthetic fixture conversion

```bash
python -m lawfirm_os_intake plan-public-synthetic-fixture-conversion \
  --methodology-report .lawfirm-os-intake/public-source-methodology/public_source_methodology_report.json \
  --out-dir .lawfirm-os-intake/public-synthetic-fixture-conversion
```

This writes `public_synthetic_fixture_conversion_plan.json`,
`public_synthetic_fixture_conversion_plan.md`, and
`public_synthetic_fixture_conversion_specs.jsonl`. The plan maps each reviewed
public methodology source to a target synthetic fixture family, allowed
structure-only inputs, forbidden real identity/payload inputs,
identity-replacement rules, synthetic gold checks, and red-team checks. It
blocks if the methodology report is not ready and never creates fixtures,
ingests public records, authorizes adapters, mutates fixture files, writes
Lake/SQLite records, or permits runtime public-data use.

### Review public synthetic fixture conversion

```bash
python -m lawfirm_os_intake review-public-synthetic-fixture-conversion \
  --conversion-plan .lawfirm-os-intake/public-synthetic-fixture-conversion/public_synthetic_fixture_conversion_plan.json \
  --out-dir .lawfirm-os-intake/public-synthetic-fixture-conversion-review
```

This writes `public_synthetic_fixture_conversion_review_packet.json`,
`public_synthetic_fixture_conversion_review_packet.md`, and
`public_synthetic_fixture_conversion_review_decision_template.json`. The packet
adds source-by-source recommendations, why-notes, required human decisions,
red-team notes, and append-only decision templates. It blocks if the conversion
plan is not ready and never approves fixture generation, creates fixture PRs,
ingests public records, authorizes adapters, mutates fixture files, writes
Lake/SQLite records, or applies learning.

### Record public synthetic fixture conversion review

```bash
python -m lawfirm_os_intake record-public-synthetic-fixture-conversion-review \
  --review-packet .lawfirm-os-intake/public-synthetic-fixture-conversion-review/public_synthetic_fixture_conversion_review_packet.json \
  --review .lawfirm-os-intake/public-synthetic-fixture-conversion-review/public_conversion_review_decision.json \
  --out-dir .lawfirm-os-intake/public-synthetic-fixture-conversion-review-outcome
```

This writes `public_synthetic_fixture_conversion_review_record.json`,
`public_synthetic_fixture_conversion_review_history.jsonl`,
`public_synthetic_fixture_conversion_review_outcome_report.json`, and
`public_synthetic_fixture_conversion_review_outcome_report.md`. The review input
must be a human-authored decision JSON bound to the supplied review packet,
source, conversion spec, and decision template. Approved decisions mean only
that a separate fixture-generation PR is required if humans choose to proceed.
The command does not create fixtures, create a PR, ingest public records,
authorize adapters, mutate fixture files, write Lake/SQLite records, or apply
learning.

### Build public synthetic fixture PR package

```bash
python -m lawfirm_os_intake build-public-synthetic-fixture-pr-package \
  --review-outcome-report .lawfirm-os-intake/public-synthetic-fixture-conversion-review-outcome/public_synthetic_fixture_conversion_review_outcome_report.json \
  --conversion-plan .lawfirm-os-intake/public-synthetic-fixture-conversion/public_synthetic_fixture_conversion_plan.json \
  --out-dir .lawfirm-os-intake/public-synthetic-fixture-pr-package
```

This writes `public_synthetic_fixture_pr_package_report.json`,
`public_synthetic_fixture_pr_package_report.md`, and
`public_synthetic_fixture_pr_package_items.jsonl` when an approved conversion
review outcome requires manual package items. The package is a reviewer-ready
instruction set for a separate fixture-generation PR. It preserves the
conversion spec's allowed structure inputs, forbidden inputs, identity
replacement rules, synthetic gold checks, red-team checks, and manual steps. It
does not edit fixtures, create a GitHub PR, ingest public records, authorize
adapters, write Lake/SQLite records, or apply learning.

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

### Audit budget lifecycle

```bash
python -m lawfirm_os_intake audit-budget-lifecycle \
  --budget-change-ledger-report .lawfirm-os-intake/budget-review/budget_change_ledger_report.json \
  --budget-actual-variance-ledger-report .lawfirm-os-intake/actuals/budget_actual_variance_ledger_report.json \
  --carrier-rejection-decision-ledger-report .lawfirm-os-intake/carrier-rejections/carrier_rejection_decision_ledger_report.json \
  --budget-event-lake-bundle-report .lawfirm-os-intake/budget-event-lake-bundle/budget_event_lake_admission_bundle_report.json \
  --out-dir .lawfirm-os-intake/budget-lifecycle-audit
```

This writes `budget_lifecycle_audit_report.json` and
`budget_lifecycle_audit_report.md`. The audit checks that the human budget
change, actual-variance, carrier-rejection, and Lake-bundle evidence streams
refer to the same budget and preflight chain, summarizes financial deltas,
lists pending human decisions and next actions, and preserves no connector,
Lake/SQLite, submission, mutation, sibling-repo write, or silent-learning
authority.

### Build budget human review packet

```bash
python -m lawfirm_os_intake build-budget-human-review-packet \
  --budget-lifecycle-audit-report .lawfirm-os-intake/budget-lifecycle-audit/budget_lifecycle_audit_report.json \
  --budget-revision-report .lawfirm-os-intake/budget-review/budget_revision_report.json \
  --budget-actual-comparison-report .lawfirm-os-intake/actuals/budget_actual_comparison_report.json \
  --carrier-rejection-review-packet .lawfirm-os-intake/carrier-rejection-review/carrier_rejection_review_packet.json \
  --carrier-rejection-learning-report .lawfirm-os-intake/carrier-rejection-learning/carrier_rejection_learning_report.json \
  --out-dir .lawfirm-os-intake/budget-human-review
```

This writes `budget_human_review_packet.json`,
`budget_human_review_packet.md`, and
`budget_human_review_decision_templates.json`. The packet consolidates budget
revision, actual variance, carrier rejection, appeal-result, Lake-handoff, and
learning-loop review pressure into recommendations with why-notes, red-team
notes, and append-only decision templates. It does not submit budgets or
appeals, write billing, admit Lake/SQLite records, mutate budgets, profiles,
templates, or guidelines, write sibling repos, promote canon, or apply learning.

### Record budget human review outcome

```bash
python -m lawfirm_os_intake record-budget-human-review-outcome \
  --budget-human-review-packet .lawfirm-os-intake/budget-human-review/budget_human_review_packet.json \
  --outcome .lawfirm-os-intake/budget-human-review-outcome/budget_human_review_outcome.json \
  --out-dir .lawfirm-os-intake/budget-human-review-outcome
```

This writes `budget_human_review_outcome_record.json`,
`budget_human_review_outcome_history.jsonl`,
`budget_human_review_outcome_report.json`, and Markdown notes. The outcome
record binds human decisions to packet templates, counts appeal/write-off/
correction/owner-routing/no-learning decisions, records required followups, and
emits candidate Lake event labels for owner review. It does not submit budgets
or appeals, write billing, admit Lake/SQLite records, mutate budgets, profiles,
templates, or guidelines, write sibling repos, promote canon, or apply learning.

### Build budget human review outcome owner adoption packets

```bash
python -m lawfirm_os_intake build-budget-human-review-outcome-owner-adoption \
  --budget-human-review-outcome-report .lawfirm-os-intake/budget-human-review-outcome/budget_human_review_outcome_report.json \
  --budget-human-review-outcome-record .lawfirm-os-intake/budget-human-review-outcome/budget_human_review_outcome_record.json \
  --out-dir .lawfirm-os-intake/budget-human-review-outcome-owner-adoption
```

This writes `budget_human_review_outcome_owner_adoption_report.json`,
`budget_human_review_outcome_owner_adoption_report.md`,
`budget_human_review_outcome_owner_adoption_packets.jsonl`, and owner-specific
JSON/Markdown packets under `budget_human_review_outcome_owner_packets/`. The
packets route human outcome labels to Semantic Substrate review, runtime
followups to Orchestrator review, and append-only admission/idempotency/hash
work to Exception Lake review. Intake does not create issues or PRs, write
sibling repos, promote canon, admit Lake/SQLite records, submit budgets or
appeals, mutate budgets, profiles, templates, or guidelines, or apply learning.

### Build budget lifecycle owner adoption packets

```bash
python -m lawfirm_os_intake build-budget-lifecycle-owner-adoption \
  --budget-lifecycle-audit-report .lawfirm-os-intake/budget-lifecycle-audit/budget_lifecycle_audit_report.json \
  --out-dir .lawfirm-os-intake/budget-lifecycle-owner-adoption
```

This writes `budget_lifecycle_owner_adoption_report.json`,
`budget_lifecycle_owner_adoption_report.md`,
`budget_lifecycle_owner_adoption_packets.jsonl`, and owner-specific
JSON/Markdown packets under `budget_lifecycle_owner_packets/`. The packets route
the lifecycle evidence to Semantic Substrate, Orchestrator, and Exception Lake
with owner actions, acceptance checks, candidate contract refs, and red-team
notes. Intake does not create issues, open PRs, write sibling repos, promote
canon, implement connectors, admit Lake records, write SQLite, submit budgets or
appeals, mutate budgets, or apply learning.

### Build Orchestrator owner-review request

```bash
python -m lawfirm_os_intake build-orchestrator-owner-review-request \
  --preflight-packet PATH/TO/intake_preflight_packet.json \
  --confirmation PATH/TO/human_confirmation.json \
  --budget PATH/TO/legal_budget_proposal.json \
  --budget-precondition-report PATH/TO/budget_precondition_report.json \
  --budget-actual-comparison-report PATH/TO/budget_actual_comparison_report.json \
  --carrier-rejection-decision-ledger-report PATH/TO/carrier_rejection_decision_ledger_report.json \
  --carrier-rejection-source-bundle examples/synthetic/carrier-rejections/duplicate-missing-unlinked-appeal.json \
  --lake-handoff-mode validate_only \
  --out-dir .lawfirm-os-intake/orchestrator-owner-review-request
```

This writes `orchestrator_owner_review_request.json` and
`orchestrator_owner_review_request.md` in the Orchestrator
`intake_owner_review_request.v0_1` input shape. The request preserves
source/segment refs, bare SHA-256 source hashes, human pause statuses, budget
preconditions, budget-to-actual rows, carrier rejection notices, appeal results,
and local Lake handoff mode for Orchestrator owner review. It does not call
Orchestrator, write sibling repos, submit budgets or appeals, admit
Lake/SQLite records, create route IDs, create event classes, or authorize
production connector use.

### Audit intake vertical readiness

```bash
python -m lawfirm_os_intake audit-intake-vertical-readiness \
  --owner-handoff-report .lawfirm-os-intake/learning-owner-handoffs/learning_owner_handoff_report.json \
  --budget-event-lake-bundle-report .lawfirm-os-intake/budget-event-lake-bundle/budget_event_lake_admission_bundle_report.json \
  --budget-calibration-readiness-report .lawfirm-os-intake/budget-calibration-readiness/budget_calibration_readiness_report.json \
  --budget-fixture-update-review-report .lawfirm-os-intake/budget-fixture-update-review/budget_fixture_update_review_report.json \
  --budget-fixture-update-pr-package-report .lawfirm-os-intake/budget-fixture-update-pr-package/budget_fixture_update_pr_package_report.json \
  --repo-root . \
  --out-dir .lawfirm-os-intake/intake-vertical-readiness-audit
```

This writes `intake_vertical_readiness_audit_report.json` and
`intake_vertical_readiness_audit_report.md`. The audit checks the local
intake-to-budget, carrier rejection, budget revision, actual-cost comparison,
actual-variance owner-adoption, budget lifecycle audit, budget lifecycle
owner-adoption, labor/employment budget fact-gap audit, reviewed learning,
shadow-eval, owner-handoff, promotion-package, and command surfaces, then
validates the generated learning artifact chain back through the
reviewed-learning gate, the generated budget-event Lake bundle, and the
calibration-readiness chain plus fixture-update review record and PR package. A
passing audit means the branch is ready for human PR review while external
adoption remains required. It does not mark the PR ready,
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

### Record PR readiness decision

```bash
python -m lawfirm_os_intake record-pr-readiness-decision \
  --pr-review-checklist .lawfirm-os-intake/pr-review-checklist/pr_review_checklist.json \
  --intake-local-closeout-report .lawfirm-os-intake/intake-local-closeout/intake_local_closeout_report.json \
  --decision .lawfirm-os-intake/pr-readiness-decision/pr_readiness_decision.json \
  --out-dir .lawfirm-os-intake/pr-readiness-decision
```

This writes `pr_readiness_decision_record.json`,
`pr_readiness_decision_history.jsonl`, `pr_readiness_decision_report.json`, and
`pr_readiness_decision_report.md`. The decision input must be human-authored and
bound to the supplied PR checklist and local closeout report. A
`mark_ready_for_review` decision records that a manual GitHub state change is
required if the human chooses to proceed. The command does not mark the PR
ready, call GitHub write APIs, create issues, open PRs, write sibling repos,
promote canon, admit Lake records, write SQLite, apply proposed changes, or
perform silent learning.

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

### Audit owner issue draft quality

```bash
python -m lawfirm_os_intake audit-owner-issue-draft-quality \
  --issue-draft-report .lawfirm-os-intake/cross-repo-owner-issue-drafts/cross_repo_owner_issue_draft_report.json \
  --out-dir .lawfirm-os-intake/owner-issue-draft-quality
```

This writes `owner_issue_draft_quality_report.json` and
`owner_issue_draft_quality_report.md`. The report checks every generated owner
issue draft for required sections, source evidence labels, matching markdown
output, red-team notes, acceptance checks, next gates, and explicit no-write /
no-promotion / no-learning boundary text. Blocked source drafts stay blocked.
The command does not create issues, open PRs, write sibling repos, promote canon,
admit Lake records, write SQLite, apply learning, or authorize production use.

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
external actions. `--observed-pr-state` accepts `draft`, `ready_for_review`,
`merged`, or `not_supplied` as observed evidence only. It preserves the remaining
human PR decision unless the PR is observed as already merged, manual owner issue
creation, owner triage, owner implementation PR, and cross-repo validation gates.
It does not mark a PR ready, create issues, open PRs, write sibling repos,
promote canon, admit Lake records, write SQLite, apply learning, or authorize
production use.

### Plan remaining roadmap

```bash
python -m lawfirm_os_intake plan-remaining-roadmap \
  --readiness-audit-report .lawfirm-os-intake/intake-vertical-readiness-audit/intake_vertical_readiness_audit_report.json \
  --intake-local-closeout-report .lawfirm-os-intake/intake-local-closeout/intake_local_closeout_report.json \
  --pr-readiness-decision-report .lawfirm-os-intake/pr-readiness-decision/pr_readiness_decision_report.json \
  --out-dir .lawfirm-os-intake/remaining-roadmap
```

This writes `remaining_roadmap_report.json`,
`remaining_roadmap_items.jsonl`, and `remaining_roadmap_report.md`. The report
turns the final readiness, closeout, and optional PR decision evidence into a
typed list of remaining work, including effort, risk, owner, gate, next actions,
acceptance evidence, red-team notes, and next recommended items. It preserves
manual human review, owner repo review, governance approval, production pilot
approval, and cross-repo validation gates. When a supplied closeout or PR
decision report records `observed_pr_state=merged`, the human PR state item is
kept as completed evidence and the next recommendations move to owner follow-up
work. It does not mark a PR ready, create issues, open PRs, write sibling repos,
promote canon, admit Lake records, write SQLite, apply learning, or authorize
production use.

### Audit synthetic fixture expansion

```bash
python -m lawfirm_os_intake audit-synthetic-fixture-expansion \
  --remaining-roadmap-report .lawfirm-os-intake/remaining-roadmap/remaining_roadmap_report.json \
  --manifest examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json \
  --repo-root . \
  --out-dir .lawfirm-os-intake/synthetic-fixture-expansion
```

This writes `synthetic_fixture_expansion_report.json` and
`synthetic_fixture_expansion_report.md`. The report proves the local holdout
manifest covers ambiguous roles, missing actuals, carrier rejection variants,
and budget driver edge cases, and that referenced fixture/test files exist under
the repo root. It records expected signals and red-team notes while keeping the
holdouts candidate-only and not calibration-approved. It does not mutate
fixtures during audit, create issues, open PRs, write sibling repos, promote
canon, admit Lake records, write SQLite, apply learning, or authorize production
use.

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
