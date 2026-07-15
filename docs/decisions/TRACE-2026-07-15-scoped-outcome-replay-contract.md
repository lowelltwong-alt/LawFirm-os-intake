# TRACE: Scoped Outcome Replay Cannot Claim Aggregate Learning

## Decision

Labor/Employment outcome-replay seeds declare one of three scopes:

- `complete_aggregate`: actuals and carrier lanes are present and the seed may
  claim the aggregate budget learning-loop report.
- `scoped_partial`: the seed exercises only the lanes its synthetic facts support
  and may claim a reviewed-learning gate, but not the aggregate report.
- `blocked_guard`: an adversarial or insufficient-information case exercises only
  the blocked-budget guard.

## Why

The aggregate learning-loop builder requires actuals and carrier artifacts. Some
synthetic cases intentionally cover only actuals or only carrier-rejection
handling. Requiring those cases to claim an aggregate output either leaves an
unresolvable false gap or encourages fabricated carrier/appeal evidence.

## Guardrails

- A scoped partial seed is rejected if it lists `budget_learning_loop_report.json`.
- A complete aggregate seed is rejected unless it includes actuals and carrier
  loops and declares the aggregate report.
- Readiness, execution, and builder-binding artifacts preserve replay scope.
- All artifacts remain synthetic, candidate-only, human-review-bound, and no-write.

## Verification

Focused replay tests verify the scope rules, reduced truthful slot count, and
absence of aggregate slots for scoped partial cases. The full repository suite,
schema export, validation, lint/format, and smoke demo pass.
