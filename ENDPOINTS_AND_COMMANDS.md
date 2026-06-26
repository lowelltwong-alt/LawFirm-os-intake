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

## Exit posture

- `0`: local workflow step completed and artifacts emitted.
- `2`: blocked by input, data, confirmation, contract, or filesystem validation.

A zero exit code does not mean legal approval or external authorization.
