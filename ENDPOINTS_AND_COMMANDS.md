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
