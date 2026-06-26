# Decision Trace

## Situation

Carrier guideline projection needs to prove that carrier-specific rules can change
the carrier-compliant view without changing the underlying proposed budget. A
single fake carrier proves the mechanics, but it does not prove counterfactual
discipline.

## Decision

Add a second synthetic carrier profile to `config/synthetic-carrier-guideline.yaml`
and a same-budget counterfactual regression in
`tests/test_carrier_counterfactual.py`.

The test projects one already-built synthetic med-mal budget under Carrier A and
Carrier B. It verifies that proposal lines remain identical while compliant
totals, caps, contingency treatment, staffing deltas, guideline refs, and
preapproval thresholds differ deterministically by carrier.

## Non-decision

This does not add real carrier guidelines, negotiated rates, provider calls,
connectors, budget submission, carrier communication, Lake admission, profile
mutation, or canonical event/schema promotion.

## Authority impact

This is local candidate/eval work in `LawFirm-os-intake`. Semantic Substrate owns
canonical schemas and event labels. Orchestrator owns future runtime guideline
resolution and human pauses. Exception Lake owns append-only persistence.

## Evidence

- `config/synthetic-carrier-guideline.yaml` has two fake carriers and explicitly
  marks the artifact as synthetic-only candidate data.
- `tests/test_carrier_counterfactual.py` proves same-budget/two-carrier
  counterfactual behavior and no proposal-line mutation.
- `docs/carrier-rate-and-guideline-layer-design.md`, `docs/roadmap.md`,
  `README.md`, and `DATA_FLOW_MAP.md` describe the candidate-only boundary.

## Alternatives rejected

- Rerun the whole intake flow with a changed confirmed carrier: rejected because
  that changes rate-card resolution and would not isolate the guideline
  counterfactual.
- Add a real carrier guideline example: rejected because real carrier guideline
  text and negotiated rates are prohibited in this repo.
- Promote the second carrier as canon: rejected because promotion belongs to the
  owning platform repos.

## Risks and rollback

The risk is a reviewer misreading the synthetic Carrier B profile as real
guideline knowledge. The artifact is clearly synthetic, candidate-only, and
prohibited from real-data use. Rollback is limited to removing the Carrier B
fixture entries and the counterfactual test/docs.

## Validation

Run focused counterfactual and carrier guideline tests, then full repo validation
before push.

## Human gates

Human PR review remains required. Any real guideline profile, private rate store,
runtime carrier selection, external submission, or Lake persistence requires
owning-repo approval.
