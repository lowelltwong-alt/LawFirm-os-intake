# TRACE: Carrier Rejection Orchestrator Interface Draft

## Context

The carrier rejection workflow now has local capture/reconciliation, human review,
and learning-candidate artifacts. The next risk is future connector work landing
in the intake repo or bypassing human authorization for appeal submission.

## Decision

Add `CarrierRejectionOrchestratorInterfaceDraft` and the
`draft-carrier-rejection-orchestrator-interface` command.

The command writes:

- `carrier_rejection_orchestrator_interface.json`;
- `carrier_rejection_orchestrator_interface.md`.

The draft names future Orchestrator-owned connector channels for portal notices,
email notices, LEDES response files, returned workbooks, appeal correspondence,
and manual human entry. It also names response-state ledger duties, human pause
points, the human-authorized appeal submission gate, and guarded Lake handoff.

## Boundary

This is a candidate interface only. It does not implement connectors, assign
route IDs, create production workflows, submit appeals, write Lake records, or
authorize intake to perform production capture.

The only proposed external-write step is Orchestrator-owned appeal submission
after `human_appeal_submission_authorization` and connector authority checks.
Intake remains reference/eval only.

## Validation

- Unit tests prove all connector channels are Orchestrator-owned.
- Tests prove raw payload storage and intake connector implementation are
  disallowed for every connector channel.
- Tests prove the only external-write workflow step is
  `human_authorized_appeal_submission`.
