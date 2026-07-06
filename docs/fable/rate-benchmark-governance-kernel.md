# Rate Benchmark Governance — Hard Kernel

- Status: Fable design output, candidate-only. Second pass; expands the rate-calibration lesson into the full contract. This doc doubles as the candidate design request to `LawFirm-os-legal-knowledge-runtime` (LKR).
- Author: Fable 5, 2026-07-05.
- Owner boundaries: LKR owns retrieval, grading, snapshot pinning, and the grading rubric's review clock; intake owns snapshot validation, consumption rules, and replay; no real negotiated firm/carrier rates anywhere; public proxies are context, never pricing authority.

## 1. Problem and why it is hard

The product needs *plausible* state/role rate context so demo budgets and guideline flags are not laughably wrong — but (a) real negotiated firm rates are prohibited data; (b) real carrier panel rates are confidential and must not be guessed at; (c) public proxies (fee-award opinions, market surveys, Laffey-style matrices) measure different things than panel rates and skew high; (d) any ungraded number that enters budget math becomes de facto authority and contaminates every later learning loop. The hard part is not finding numbers — it is building a governance shape where numbers carry their own epistemic grade and the math *refuses* to run when the grade is insufficient.

## 2. Division of labor

```
LKR (governed retrieval repo)                    Intake (candidate consumer)
────────────────────────────                     ───────────────────────────
finds public evidence                            validates snapshot hash + schema
grades each source (rubric below)                enforces consumption rules (§5)
normalizes to BenchmarkCells                     annotates budgets/review packets
pins BenchmarkSnapshot (hashed, versioned)       falls back hours-only / blocks
owns rubric + staleness review clock             never fetches, never grades, never blends
```

Intake's only inbound artifact is the pinned snapshot file, referenced like a rate card (`profile.benchmark_snapshot_ref`), loaded read-only with the same real-data refusal guards as existing loaders.

## 3. BenchmarkCell schema (candidate)

```
BenchmarkSnapshot:
  schema_version, snapshot_id, produced_by: "LawFirm-os-legal-knowledge-runtime"
  produced_at, method_version, rubric_version
  content_sha256 (canonical body), status: "candidate"
  contains_real_negotiated_rates: false        # load-time refusal if true
  cells: list[BenchmarkCell]

BenchmarkCell:
  cell_key: {state, market_tier: metro|state_wide|rural, role, year}
  low, median, high: float                     # USD/hour
  unit: "usd_per_hour"
  basis: "public_proxy"                        # the ONLY allowed basis in this program
  proxy_kind: fee_award_opinion | market_survey | judicial_matrix | agency_schedule
  source_grade: A | B | C | D                  # rubric §4
  provenance_refs: list[str]                   # citations/URLs/docket refs, ≥1
  retrieved_at, observation_period: {from, to}
  sample_note: str                             # observable method note, no hidden reasoning
  proxy_bias_note: str                         # REQUIRED: how this proxy relates to panel rates
                                               # e.g. "fee-award rates typically exceed insurance panel rates"
```

`proxy_bias_note` is mandatory by schema: every cell must carry, in words, the reason it cannot be read as a panel rate. This is the anti-laundering field.

## 4. Source grading rubric (owned by LKR; intake enforces mechanically)

| Grade | Definition | Examples |
|---|---|---|
| A | In-state, court-adjudicated, role-differentiated, observation window ends ≤24 months ago | fee-award opinion with lodestar table |
| B | In-state reviewed aggregate with published method, ≤24 months | state-bar economics survey |
| C | Adjacent-state or national aggregate, or in-state but 24–48 months | national litigation rate survey; aged award |
| D | Method unknown, >48 months, or single anecdote | blog tables, uncited matrices |

Staleness downgrade is mechanical: A/B degrade one grade per 24 months past window end; intake recomputes the *effective* grade at consumption time from `observation_period` — a snapshot cannot stay fresh by being re-pinned unchanged.

## 5. Consumption rules in intake (when pricing / hours-only / blocked)

The keystone rule: **benchmark cells never price anything.** Pricing authority remains exclusively the synthetic (later: firm-authorized) rate card. Cells power *annotation and gating*:

| # | Condition | Behavior |
|---|---|---|
| P1 | Rate card resolves normally + cell (effective grade A/B) covers the (state, role) | budget prices from rate card as today; review packet gains a `benchmark_context` block: card rate vs cell low/median/high + `proxy_bias_note`; a `rate_outside_benchmark_band` flag fires when card rate > cell.high or < cell.low (review-only) |
| P2 | Cell effective grade C/D | annotation only, styled "context (low confidence)"; no band flag may fire from C/D cells (a weak proxy must not generate review pressure) |
| P3 | No cell for (state, role) | budgets price from rate card; review packet states "no benchmark context available"; NOT a block (absence of context ≠ absence of authority) |
| P4 | Rate card resolution FAILED (unmapped state/carrier per budget-truth D2–D4) | hours_only — and benchmark cells may NOT be used as a substitute rate source, whatever their grade. This is the laundering front door; it stays welded shut |
| P5 | Snapshot hash/schema invalid, or `contains_real_negotiated_rates: true` | block: `benchmark_snapshot_invalid`, exception candidate |
| P6 | Two snapshots referenced (profile + CLI arg) disagree | block for human selection; never merge |
| P7 | Cell contradicts itself (low > high, median outside [low, high], year mismatch vs window) | cell ignored + exception candidate `benchmark_cell_malformed`; remaining cells still usable |

## 6. First POC state selection logic

Choose POC states by governance value, not market size. Deterministic scoring per state:

```
poc_score = 2×(has_A_grade_public_source) + 1×(existing synthetic fixtures reference the state)
          + 1×(rate card already has a schedule row) + 1×(distinct market tiers available)
```

Applied to the current synthetic universe (NV/CA/TX in the rate card): **NV first** (fixtures + card + a synthetic A-grade fee-award proxy can be authored against the CourtListener-shaped public corpus), **CA second** (exercises metro/state-wide tier split and high-rate band flags where card CA rates will sit *below* public fee-award proxies — the interesting direction for `proxy_bias_note`). TX third (control state, expect sparse cells → P3 path exercised). The POC uses **synthetic stand-in cells shaped like real public data** (per the non-reconstruction rules in `docs/fable/le-synthetic-corpus-roadmap.md` §6) until LKR's real public-retrieval path is reviewed.

## 7. Fixtures

| Fixture | Pins |
|---|---|
| `benchmark-context-clean` | P1 annotation, in-band, no flag |
| `benchmark-band-flag` | card rate above cell.high → flag with proxy_bias_note quoted |
| `benchmark-weak-grade` | C-grade cell → annotation only, flag suppressed (P2) |
| `benchmark-missing-cell` | P3 statement |
| `benchmark-launder-attempt` (holdout) | rate resolution failed + A-grade cells present → hours_only, cells unused (P4) |
| `benchmark-invalid-snapshot` | P5 block |
| `benchmark-stale-degrade` | A-grade cell aged 30 months → effective B; aged 50 → effective C, flag suppressed |

## 8. Codex handoff

1. **PR-RB1 (intake, low):** `BenchmarkSnapshot`/`BenchmarkCell` models + loader with refusal guards + effective-grade computation + schema export. Tests: schema, staleness math, P5/P7.
2. **PR-RB2 (intake, medium):** consumption wiring — `benchmark_context` block in the human-review budget packet, band flags (P1/P2), P3/P4/P6 paths; fixtures above. Depends on rate-resolution guardrails (PR-BK4) so P4 has a real failure state to bind to.
3. **LKR design request (docs only):** this file + exported schemas; LKR implements retrieval/grading/pinning under its own review. Intake must not stub retrieval.

**Must not do:** let any cell price a line (P4 especially); fire review flags from C/D cells; average/blend cells with card rates; fetch anything over the network from intake; commit real fee data — POC cells are synthetic stand-ins with `data_scope: synthetic_only` until LKR's pipeline is reviewed.
