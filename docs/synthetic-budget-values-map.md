# Synthetic Budget Values Map

This map identifies where the POC's editable synthetic budget values live. These files
are not firm rates, carrier panel rates, billing authority, or a production configuration.

| Value family | Editable source | Runtime use | Guardrail |
| --- | --- | --- | --- |
| Carrier/state/title hourly rates | `config/synthetic-carrier-rate-card.yaml` | Confirmed carrier + jurisdiction rate resolution | Candidate synthetic only; no carrier role or jurisdiction match means hours-only. |
| Flat fallback hourly rates | `context/synthetic-profiles/insurance-defense.yaml` | Legacy/no-card profile fallback | Synthetic fallback, not a substitute for a missing confirmed rate-card match. |
| Budget template hours, task mix, expenses, and contingency | `context/synthetic-profiles/insurance-defense.yaml` | Deterministic proposal construction | Candidate template assumptions; facts and human gates can block amount output. |
| Carrier guideline caps/disallowances | `config/synthetic-carrier-guideline.yaml` | Candidate proposed-vs-compliant projection | Separate from proposed budget; cannot rewrite proposed math. |
| Labor and employment nonlinear structures | `examples/synthetic/labor-employment/labor-employment-nonlinear-budget-templates.json` | Synthetic L&E fixture and replay evaluation | Candidate-only nonlinear modeling, not a production rate authority. |
| Per-fixture scenario values and expected outputs | `examples/synthetic/labor-employment/replay-inputs/` | Reviewed synthetic replay evidence | Generated/replayed evidence; change through fixture and QA review, never silent mutation. |
| Actual vs budget values | `examples/synthetic/actuals/` and L&E replay raw sources | Variance/learning candidates | Synthetic evidence only; review outcome required before any future owner learning. |

## Editing Workflow

1. Change the applicable synthetic source, with no real firm, client, matter, carrier,
   negotiated-rate, or public-record payload.
2. Run its deterministic builder, including
   `build-synthetic-rate-card-workbench` for rate-card changes.
3. Update only generated fixtures produced by the builder.
4. Add or revise gold, counterfactual, and safety tests; run the governed validation
   commands.
5. Record a decision trace. Any future real-data replacement requires a Legal Knowledge
   Runtime reviewed snapshot and owner approval; it is not an Intake edit.
