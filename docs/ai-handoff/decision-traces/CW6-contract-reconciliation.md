# Decision Trace — CW6 Contract Reconciliation

Wave: CW6 of the converged Opus marathon. Branch:
`claude/cw6-contract-reconciliation`, stacked on CW5. Candidate-only,
synthetic-only, deterministic.

## Situation

The vertical needs rule kinds the Substrate-owned OCG rule IR does not yet
express — an aggregate task-hour allowance, a declared ordered attribution, and a
typed applicability envelope. Intake must reconcile with (not fork) that IR: no new
rule language, no canonical rule IDs authored in Intake, and the sibling
billing-guideline-simulator is a read-only challenger.

## Decision

An additive `ocg_contract_reconciliation` module:

1. **Extension proposal** (`OCGRuleKindExtensionProposal`) — a candidate
   executable proposal covering exactly the three needed rule kinds
   (task_hour_allowance, ordered_attribution, applicability_envelope), each with a
   rationale and nearest existing OCG family; `authors_no_canonical_ids=True`,
   `requires_substrate_owner_review=True`, `source_owner_required=Substrate`.
2. **Local adapter** (`build_local_adapter_ir`) — expresses the vertical's CW1
   rules (rate/expense caps) plus the three proposed kinds as candidate
   `OCGSharedRuleIR` rules with **local, non-canonical** IDs (`ocg_ir_candidate:` …),
   `source_owner = Substrate`, and the standard prohibited-actions list. Running the
   existing `build_ocg_rule_ir_adoption_report` against the CW1 budget + projection
   yields **zero** canonical-rule-id / source-owner / rewrite / blocker violations —
   proving the adapter reconciles within bounds and authors no canon.
3. **Sibling conformance** (`run_sibling_conformance`) — read-only conformance of
   the sibling simulator against the CW1 outputs. The sibling is **not present** in
   this workspace, so the report records `blocked_sibling_unavailable` (fail-closed)
   with the frozen CW1 output refs a future diff must run against — never an
   assumed-passing result.

Composed into `OCGContractReconciliationReport`, whose validator rejects any
adapter canonical-id or source-owner violation (fail-closed) and pins
`requires_substrate_owner_review=True`.

## Non-decision

- No new rule language; no canonical rule IDs; no modification of the OCG IR
  enums (extension is Substrate's to make on review).
- No fabricated sibling conformance — absence is a typed blocked status.

## Authority impact

Local candidate work. New candidate schemas + a local adapter. The Substrate owns
the canonical OCG IR; this is a proposal for owner review, not a promotion.

## Evidence

- `tests/test_ocg_contract_reconciliation.py` — 5 tests (failing-test-first):
  proposal covers three kinds + no canonical IDs; adapter has zero canonical-id /
  owner violations; sibling conformance fail-closed when absent; determinism;
  report rejects a canonical-id violation.
- Reuses `build_ocg_rule_ir_adoption_report` against CW1 outputs (epli budget +
  synthetic-carrier-a projection).
- Four exported schemas.

## Alternatives rejected

- **Extend the OCG IR enums directly.** Rejected: authoring canonical rule kinds in
  Intake violates `do_not_author_canonical_ocg_rule_ids_in_intake`; the extension is
  proposed for Substrate-owner review, expressed locally as candidate metadata.
- **Record the absent sibling as passing.** Rejected — fail-closed demands a typed
  `blocked_sibling_unavailable`.

## Risks and rollback

- Risk: the proposal is mistaken for an adopted contract. Contained by
  `requires_substrate_owner_review`, candidate-only status, and the adoption-report
  proof. Rollback is a single-branch revert; the module is additive.

## Validation

ruff check/format clean; `export_schemas.py` idempotent (four new schemas);
`validate_repo.py` passed; `run_full_pytest.py -q` full suite passed; `npm run
build` + `npm run smoke:browser` OK (no UI change this wave).

## Human gates

CW6 human gate: **Substrate owner review** of the extension proposal and the
local-adapter reconciliation. Opened by the agent; it does not merge its own PR and
does not push `main`.

## DAD

Per-wave preflight/lesson/postflight through the canonical `asset-dir` lesson
pipeline.
