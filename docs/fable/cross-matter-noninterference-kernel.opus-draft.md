# Cross-Matter Non-Interference — Hard Kernel (Opus first-pass draft)

## 1. Status

- **status:** candidate; **author:** Opus (first-pass architect); **date:** 2026-07-07.
- **synthetic-only, not canon until human-approved.** Parallel draft to any Fable 5 pass (`cross-matter-noninterference-kernel.md`); does not supersede it.
- Extends, does not replace: `reviewed_learning_gate.py`, `carrier_rejection_learning.py`, `exception_mapping.py`, the entity-resolution and rate-benchmark kernels. No learned components introduced. No existing boundary weakened.

## 2. Executive position

Cross-matter non-interference is a deterministic **information-flow property enforced at the aggregation layer, never the evidence layer.** Raw evidence stays append-only and immutable; walls are **versioned exclusion sets**; walled inputs are **purged before** any aggregation function runs; every unwalled output ships a proof that (NI-1) removing walled inputs changes nothing, and (NI-2) no aggregate is attributable to a single matter/person. The existing `reviewed_learning_gate` becomes the chokepoint: no candidate promotes without a valid `NonInterferenceProof` + human approval id. Retroaction is achieved by bumping a screen version and recomputing, not by deleting history. Everything below is schema + predicate + suppression + proof — no new matcher, no new intelligence.

## 3. Formal non-interference property

Let `I` = full input corpus (append-only events/records). Let `S` = active screen set at output-build time. Let `W(S) ⊆ I` = events matching any active screen (§6). Let `purge(I,S) = I \ (W(S) ∪ derived(W(S)))` where `derived` is the transitive closure over cited-source lineage.

For every unwalled aggregate output `O = f(I)` (benchmark cell, proposed rule/threshold, DAD lesson, calibration parameter, taxonomy count, link candidate) and every consumer outside the wall:

- **NI-1 (wall non-interference):** `canon(f(I)) == canon(f(purge(I,S)))`. Walled inputs must not observably change any unwalled output. "Observably" = byte-identical after canonicalization. If purging would change `O`, `O` is **suppressed/blocked, not published**.
- **NI-2 (cohort non-identifiability):** no unwalled `O` permits attributing an aggregate to one matter, person, client, or firm (small-cell + dominance, §8). Protects the sensitive-but-not-yet-walled individual matter.

Both are **fail-closed**: unknown wall status ⇒ treat as walled; missing proof ⇒ output unusable.

## 4. Aggregate loop inventory

Real loops that read across matters (grain = the key they aggregate on):

| # | Loop / producer | Aggregation grain | Cross-matter? | Class (§5) |
|---|---|---|---|---|
| L1 | `budget_calibration_corpus` / `budget_learning_loop` (`budget_model`, `timekeeper_rate`, `validation_rule`) | phase/task/role driver & threshold distributions | yes | with-suppression |
| L2 | `carrier_rejection_learning` (15 `PROPOSAL_POLICY` loops) | carrier × issue pattern, occurrence counts | yes (carrier+matter) | with-suppression |
| L3 | `benchmarks.py` BenchmarkCells | (state, tier, role, year) | public-proxy only today | may-aggregate\* |
| L4 | Exception Lake taxonomy (`identity_key.occurrence_count`, weekly trend) | issue_family × normalized_subject_ids | yes | with-suppression |
| L5 | DAD lesson drafting (`LessonDraft`, `cross_repo_owner_issue_drafts`) | clustered patterns w/ counts, cross-repo | yes | with-suppression |
| L6 | Entity-resolution tables (alias/residual/rewrite growth) | correction clusters | yes | with-suppression |
| L7 | Matter linking (`matter_linking.py`, cross-bundle) | matter↔matter link candidates | yes | must-wall on any screened side |
| — | `reviewed_learning_gate` | promotion chokepoint | — | enforcement point |

\*L3 is `may-aggregate` **only while** `basis == public_proxy` and `contains_real_negotiated_rates == false`; if any cell ever becomes matter-derived it moves to `with-suppression`.

## 5. Signal taxonomy

- **may-aggregate** (no suppression): synthetic fixtures; public-proxy benchmark cells; method/rubric/version metadata; structural taxonomy *definitions* (issue_family enums, edge-type vocab). No per-matter private signal.
- **may-aggregate-with-suppression:** cross-matter statistics where a matter/person could be re-identified — L1/L2/L4/L5/L6 outputs, matter-derived counts, variance/rejection distributions. Require purge (NI-1) **and** k-anon + dominance (NI-2).
- **must-wall:** any signal from a screened matter/person/client/firm/jurisdiction/time-period — rejection events, corrections, variances, appeal outcomes, link edges, rate observations, narrative-derived booleans tied to the screened subject. Contributes **zero** to unwalled outputs.
- **prohibited** (never aggregated, walled or not): privileged narrative text, real negotiated firm rates, real carrier panel rates, raw PII, hidden chain-of-thought, AI inferences presented as fact. Refused at admission; never becomes "signal."

## 6. Wall predicate (deterministic)

Candidate schemas (structured ids only; no free text carries wall weight):

```
Screen:        {screen_id, screen_version, status: active|lifted,
                subjects: [ScreenSubject], include_affiliates: bool,
                scope_note, authorized_by (human id), effective_from}
ScreenSubject: {dim: matter|person|client|firm|jurisdiction|matter_type|time_period,
                canonical_id}          # canonical_id from the reviewed ER ladder, never a raw string
WallScope:     {dims: [dim...]}        # which dims a given aggregate is sensitive to
ExclusionSetRecord: {screen_version, corpus_snapshot_hash,
                     excluded_event_ids_hash, size, built_at}
```

```python
def extract_subjects(event) -> dict[dim, set[canonical_id]]:
    # structured refs only: matter_id, party/timekeeper/adjuster person_id, client_id,
    # firm_id, jurisdiction, matter_type, period bucket. Resolve ids via the deterministic
    # entity ladder (E1–E3). NEVER parse narrative. Missing/ambiguous dim -> UNKNOWN sentinel.

def is_walled(event, screens, at_version) -> WallVerdict:
    subj = extract_subjects(event)
    for scr in active_screens(screens, at_version):          # status==active, sorted by screen_id
        for s in scr.subjects:
            ids = subject_ids(scr, s)                          # s.canonical_id, plus reviewed
                                                               # E4 affiliate ids iff include_affiliates
            if s.dim in subj and subj[s.dim] & ids:
                return WALLED(scr.screen_id, s.dim)
        if scr_cares_about_unknown_dim(scr, subj):             # scr keys a dim we could not extract
            return WALLED(scr.screen_id, "unknown_dim")        # FAIL CLOSED
    if any_unknown(subj) and near_any_screen(subj, screens):   # ambiguous entity next to a screen
        return EXCLUDED_PENDING                                # held out of aggregation until ER resolves
    return UNWALLED
```

Rules: exact structured-id set membership only — **no fuzzy match, no similarity score.** E4 affiliates (`subsidiary_of`, `staffing_agency_for`, `peo_of`, `insured_dba`) expand a wall **only** via `include_affiliates=true` **and** a `reviewed` edge; an `unreviewed`/`possible_affiliate` edge never expands a wall and its events go `EXCLUDED_PENDING` (fail closed without over-walling the whole graph). `EXCLUDED_PENDING` and `WALLED` are both purged from unwalled aggregation.

## 7. Retroactive screen vs append-only evidence

Raw evidence is immutable; **retroaction lives in the exclusion + recompute layer.**

1. Screens are versioned. `exclusion_set(screen_version) = { event_id | is_walled(event, screens, screen_version) }`, persisted as `ExclusionSetRecord`.
2. Every unwalled output pins a `CorpusVersionRecord {corpus_snapshot_hash, screen_version, exclusion_set_hash}`. An aggregate is computed against `corpus_snapshot ∖ exclusion_set` — never raw directly.
3. **New screen at T2 over data admitted at T1:** raw untouched. Bump `screen_version`. Any published output whose `screen_version <` current active version for its `WallScope` is marked **stale + quarantined**; consumers **fail closed** (refuse stale aggregates). Recompute path re-derives against the new exclusion set.
4. **Poisoned promoted rule:** because learning = versioned git diff citing its source `identity_keys` (anti-silent-learning invariant), a promoted rule whose cited sources now intersect `exclusion_set` is flagged `screen_tainted`, auto-opens re-derivation on the purged corpus, and is **reverted-by-superseding-diff** (not deleted) until re-approved via shadow eval. History is appended, never rewritten.

Deletion of raw walled evidence is a **[COUNSEL/HUMAN POLICY]** retention question and is *not required* for non-interference — non-influence ≠ erasure.

## 8. Small-cell & dominance suppression (NI-2)

Applies to `with-suppression` cells after walled purge. Thresholds are **[COUNSEL/PRIVACY POLICY]** inputs; defaults fail closed.

- **k-anonymity:** publish a cell only if it draws on `≥ K_matters` distinct matters AND `≥ K_actors` distinct persons/clients as applicable. Default `K = 5`.
- **(n,k) dominance / p%-rule:** suppress if `top1_share > p1` (default 0.5) or `top2_share > p2` (default 0.7) of the cell's weight — one matter must not dominate an "aggregate."
- **Complementary suppression:** if a suppressed cell is recoverable by differencing published margins/totals, deterministically suppress the complementary cells too (stable order over the table).
- **Counts-not-percentages:** below `min_reviewed_for_percentages`, emit counts only, and only counts `≥ K`.
- Every suppression writes `SuppressionDecisionRecord {cell_key, rule_fired, distinct_matters, distinct_actors, top1_share, top2_share, contribution_profile_hash}` — shares as ratios/hashes, **never raw values**.

## 9. Audit proof artifact

One `NonInterferenceProof` per published unwalled aggregate; it is the object the gate checks.

```
AggregationAdmissionRecord: {output_id, loop_id, corpus_version_ref, inputs_after_purge_hash,
                             walled_excluded_count, pending_excluded_count}
NonInterferenceProof:
  output_id, output_kind, corpus_version_ref, screen_version, exclusion_set_hash
  ni1: {method: construction|recompute, f_full_hash?, f_purged_hash, equal: true}
  ni2: {distinct_matters, distinct_actors, top1_share, top2_share, K, dominance_ok: true}
  suppressions: [SuppressionDecisionRecord.id...]
  determinism: {engine_version, config_hash, rebuilt_identical: true}
  integration_mode: mcp | file_fallback
  status: candidate; human_review_required: true; approval_id: null
```

- `method: construction` = aggregator provably never read walled events (purge-before-f) — production default.
- `method: recompute` = ran `f` on full and purged corpus, hashes matched — CI/fixture verification (stronger; catches lineage leaks).
- No proof ⇒ output is not consumable and cannot reach promotion.

## 10. MCP-first authority implications

- Screen/aggregate/proof services are **MCP servers exposing read-only tools** (`get_corpus_version`, `is_walled`, `build_aggregate`, `emit_proof`). The **host/orchestrator holds authority**; server tools never write canon and never act externally.
- **Tool-chaining risk:** a client could chain `build_aggregate` (read) → a write/submit tool to launder walled signal into action. Defenses: (a) aggregate tools return candidates tagged `requires_reviewed_learning_gate` + attached proof; promotion/write tools **refuse inputs lacking a valid `NonInterferenceProof` + `approval_id`** (extend `reviewed_learning_gate` accordingly — it already blocks auto-promotion). (b) **Side-effect-class separation:** the server declares each tool's class; a host `PreToolUse` hook denies read→write cross-class chaining in one authority context. (c) intake's "no external action ever" is enforced by the intake server **exposing zero write/network tools**, not by client goodwill.
- **API/file fallback (declared):** if MCP is unavailable, the direct loader path is allowed **only** with the same guards compiled in (real-data refusal, `screen_version` required, proof emitted) and must stamp `integration_mode: file_fallback` so audits see the degraded path.

## 11. Required synthetic fixtures

| Fixture | Pins |
|---|---|
| `ni-wall-basic` | screened matter's events in raw; cell identical with/without them (NI-1, construction) |
| `ni-wall-leak-negative` (holdout) | naive aggregator includes walled events → `recompute` hashes differ → **blocked** |
| `ni-retroactive-screen` | build at `screen_v1`; add `screen_v2` over an included matter → prior output stale, recompute differs, citing rule flagged `screen_tainted` |
| `ni-smallcell` | 3 matters → suppressed (K=5); 6 → published; counts-only under % threshold |
| `ni-dominance` | 6 matters, one 80% → dominance suppression; complementary suppression blocks differencing recovery |
| `ni-affiliate` | parent screen + E4 subsidiary event: `include_affiliates=false`→unwalled; `true`+reviewed→walled; unreviewed edge→`EXCLUDED_PENDING` |
| `ni-prohibited` | privileged narrative / real rate → refused at admission, never aggregated |
| `ni-mcp-chain` (holdout) | aggregate-read → external-write without proof/approval → host denies |
| `ni-determinism` | two builds byte-identical |

## 12. Codex PR-sized handoff

- **PR-NI1 — schemas + wall predicate (low).** `Screen/ScreenSubject/WallScope/ExclusionSetRecord/CorpusVersionRecord` models; `wall.py::is_walled` + `extract_subjects` (structured ids only, unknown⇒walled/pending). Tests: `ni-wall-basic`, `ni-affiliate`, `ni-determinism`. **DO NOT:** fuzzy match; expand walls via unreviewed edges; parse narrative.
- **PR-NI2 — purge-by-construction admission (medium).** Shared `aggregate_guard` wrapping L1/L2/L3/L4 producers: purge `WALLED ∪ EXCLUDED_PENDING` before `f`; emit `AggregationAdmissionRecord`. **DO NOT:** change any loop's math; alter `reviewed_learning_gate` semantics yet.
- **PR-NI3 — small-cell/dominance suppression (medium).** `suppression.py` (k-anon, p%-dominance, complementary suppression, counts-only) + `SuppressionDecisionRecord`. Tests: `ni-smallcell`, `ni-dominance`. **DO NOT:** publish cells failing K/dominance; emit sub-threshold percentages.
- **PR-NI4 — proof + gate integration (medium).** Emit `NonInterferenceProof`; extend `reviewed_learning_gate` to require a valid proof + `approval_id` before candidate→promotion; `screen_tainted` detection on promoted rules citing excluded sources. Tests: `ni-wall-leak-negative`. **DO NOT:** auto-promote; auto-revert without a superseding diff.
- **PR-NI5 — retroactive recompute + staleness (medium).** `screen_version` bump → stale/quarantine dependents; recompute; `ni-retroactive-screen`. **DO NOT:** mutate/delete raw evidence; rewrite history.
- **PR-NI6 — MCP surface (medium).** Read-only tools + side-effect-class declarations + host `PreToolUse` cross-class-chaining denial + `file_fallback` mode. Tests: `ni-mcp-chain`. **DO NOT:** expose write/network tools from intake; allow aggregate→write chaining without proof.

## Counsel/human policy inputs (not architect decisions)

- `K`, `p1`, `p2` suppression thresholds (privacy).
- Whether/how far an ethical screen includes E4 affiliates (conflicts/legal judgment).
- Which subject dims constitute the wall for a given screen (matter vs person vs firm/jurisdiction/period).
- Retention/deletion of raw walled evidence (separate from non-interference, which needs non-influence only).
- Sign-off that byte-equality (NI-1) + SDC (NI-2) is a sufficient definition of "not observably influence" for privileged inference.
