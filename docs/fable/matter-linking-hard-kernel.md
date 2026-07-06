# Matter Linking Without Matter Numbers — Hard Kernel

- Status: Fable design output, candidate-only, synthetic-only. No implementation exists yet; this is the oracle spec Codex builds against.
- Author: Fable 5, 2026-07-05.
- Problem: one sender (a carrier claims inbox, a TPA, a broker) sends many documents about many matters, with no official matter number. A perfect budget attached to the wrong matter is a product failure. Linking must be deterministic, evidence-bound, and must **hold** rather than guess.

## 1. Position in the pipeline

Today: one inbound bundle → one `IntakePreflightPacket` → one confirmation → one budget. Matter linking inserts a candidate layer between ingestion and preflight:

```
sources/segments ──► document identity extraction ──► MatterLinkKeySet per document
                                        │
                                        ▼
                     deterministic clustering (tiers, below)
                                        │
                                        ▼
      MatterClusterProposal(s) + MatterLinkDecisionRecord(s)  [candidate, review-only]
                                        │
                     unambiguous ─► per-cluster preflight packets
                     everything else ─► hold / human review packet
```

Hard boundaries preserved: no matter opening, no conflict conclusions, no writes outside run artifacts. A cluster is a *review proposal*, never an identity assertion.

## 2. Candidate schema fields

New models (additive, `StrictModel`, all `status: Literal["candidate"]`):

```
MatterLinkKey:
  key_type: Literal[
    "claim_number", "policy_number", "docket_ref", "adjuster_ref",
    "party_pair",            # normalized (claimant/plaintiff, insured/defendant)
    "employer_employee_pair",# L&E variant of party_pair
    "counsel_ref",           # opposing counsel firm
    "email_thread",          # RFC-2822 References/In-Reply-To chain or subject-normalized
    "attachment_identity",   # content sha256 of an attachment
    "incident_date_party",   # incident/DOL date + one party name
    "subsidiary_alias",      # entity resolved through a declared alias/subsidiary table
  ]
  raw_value: str
  normalized_value: str          # deterministic normalization, recorded
  tier: Literal["strong", "medium", "weak"]
  evidence_refs: list[EvidenceRef]   # offsets into source text — mandatory, ≥1
  extraction_rule_id: str            # which deterministic rule fired

MatterLinkKeySet:
  document_id: str                  # source_id
  bundle_id: str
  sender_identity: str              # normalized from address; sender is NEVER a linking key by itself
  keys: list[MatterLinkKey]
  extraction_gaps: list[str]        # e.g. "attachment unreadable; keys may be incomplete"

MatterClusterProposal:
  cluster_id: str
  document_ids: list[str]
  ambiguity_class: Literal[         # ordinal, NOT probability — see §4
    "corroborated_multi_key",
    "single_strong_key",
    "medium_key_only",
    "weak_key_only",
    "conflicted",
  ]
  supporting_keys: list[MatterLinkKey]
  conflicting_keys: list[MatterLinkKey]      # non-empty ⇒ ambiguity_class == "conflicted"
  disposition: Literal["proposed_link", "hold_for_more_documents", "human_review_required", "blocked_conflict"]
  decision_rule_ids: list[str]               # replayable decision trace
  requires_human_confirmation: Literal[True] = True
  matter_identity_asserted: Literal[False] = False

MatterLinkDecisionRecord:                    # append-only, one per pairwise/cluster decision
  decision_id, cluster_id, rule_id, inputs (key refs), outcome, note
```

Human confirmation extends the existing `HumanConfirmation` pattern: a reviewer confirms/splits/merges clusters; confirmations supersede, never mutate.

## 3. Matching feature matrix

Tier semantics: **strong** keys are near-unique per matter; **medium** keys are unique per matter *within one sender's book* but collide across time or affiliates; **weak** keys corroborate only.

| Feature | Tier | Normalization | Known failure modes (must be fixtures) |
|---|---|---|---|
| Claim number | strong | uppercase, strip `[-. /#]`, strip labels ("Claim No.", "Claim #", "Our ref") | reused claim number for two claimants (carrier error); claim vs. policy number confusion; OCR `O/0`, `I/1` — do NOT fuzzy-correct, extract verbatim and let conflict rules catch it |
| Docket/case number | strong | court-format-aware canonicalization (e.g. `2:26-cv-01234`) | same docket, different carrier claims (multi-insured); removed/refiled actions |
| Policy number + claimant name | strong (composite) | policy alone is **medium** — one policy covers many claims | multiple claims same claimant same policy (two incidents) → needs incident date to split |
| Adjuster reference / file number | medium | per-sender namespace: normalized value is `(sender_domain, ref)` | adjuster handles many matters; ref reused after adjuster reassignment |
| Party pair (claimant × insured) | medium | entity normalization: casefold, strip punctuation & suffixes (LLC/Inc/Ltd), alias table lookup | common names; family members; subsidiaries (see below); same pair, two incidents |
| Employer × employee pair (L&E) | medium | as party pair | serial plaintiffs; class/collective (one employer, many employees ⇒ pair explosion — cap and route to review) |
| Subsidiary/affiliate resolution | medium→weak | ONLY via declared alias/subsidiary table in synthetic profile; never inferred from string similarity | "Valley Medical Center" vs "Valley Medical Center of Henderson LLC" — without a table entry these are DIFFERENT entities and must not merge |
| Opposing counsel | weak | firm-name normalization | one plaintiff firm sends many matters — high collision |
| Email thread (References/In-Reply-To) | medium | header chain; fallback: normalized subject + participant set | **thread drift**: adjuster replies in an old thread about a new claim — thread key must be overridden by conflicting strong keys |
| Attachment identity (sha256) | medium | exact content hash | same blank form attached to many matters (cap: hash that appears in > K clusters becomes weak); re-sent complaint = genuine link |
| Incident date + party | weak | ISO date + normalized name | date typos; multiple incidents same day (mass tort) |
| Sender identity | none | — | **never a linking key**: one claims inbox sends everything. Sender only namespaces medium keys |

Entity normalization is deterministic string algebra + declared alias tables. No embedding similarity, no learned matcher, in v1 — the Python oracle must be replayable and diffable.

## 4. Ambiguity classes (explicitly not probability)

We refuse fake confidence-as-probability. Classes are **ordinal labels defined by which rule tier fired**, so two engineers reading the same evidence must derive the same class:

| Class | Definition (deterministic) | Default disposition |
|---|---|---|
| `corroborated_multi_key` | ≥2 independent keys agree, ≥1 strong, 0 conflicts. "Independent" = different key_types not derived from the same text span | `proposed_link` (still human-confirmed) |
| `single_strong_key` | exactly 1 strong key, 0 conflicts, no medium disagreement | `proposed_link`, flagged single-source |
| `medium_key_only` | ≥1 medium key agrees, 0 strong keys, 0 conflicts | `hold_for_more_documents` (auto-upgrades when corroboration arrives) |
| `weak_key_only` | only weak keys | `hold_for_more_documents`; never auto-link |
| `conflicted` | any two keys of tier ≥ medium disagree across the candidate pair | `blocked_conflict` → human review, mandatory |

Class assignment is a pure function of the key sets; the `decision_rule_ids` trace makes every assignment replayable.

## 5. Split / merge / hold / review decision table

Pairwise document rules, applied in order; first match wins. (Cluster = transitive closure of MERGE decisions, but a BLOCK between any two members poisons the whole cluster to `conflicted` — no "merge through an intermediate document" laundering.)

| # | Condition | Decision |
|---|-----------|----------|
| R1 | Strong keys disagree (different normalized claim numbers, or different dockets) | **SPLIT** (never merge, regardless of other agreement) |
| R2 | Same strong key value, same key_type | **MERGE** (conflicts checked by R1 first) |
| R3 | Same strong key value but different claimant names attached | **BLOCK** `strong_key_reuse_conflict` → human review |
| R4 | Same policy number, different claimant or different incident date | **SPLIT** (policy is shared infrastructure) |
| R5 | Same email thread AND a new strong key appears mid-thread differing from the thread's established strong key | **SPLIT + BLOCK** `thread_drift` (the drifting message reviews separately) |
| R6 | Same email thread, no conflicting keys | MERGE (medium) |
| R7 | Same adjuster ref within same sender namespace, no conflicts | MERGE (medium) |
| R8 | Same party pair + incident date within tolerance 0 days, no conflicts | MERGE (medium) |
| R9 | Same party pair, different/absent incident dates | **HOLD** (could be two incidents) |
| R10 | Attachment sha256 shared, attachment is case-specific (not shared across >K clusters) | MERGE (medium) |
| R11 | Only weak agreement | **HOLD** |
| R12 | Entity match requires an alias-table edge that is `unreviewed` | **HOLD** + review of the alias itself |
| R13 | Employer×employee pair count in candidate cluster > cap (default 5) | **REVIEW** `possible_class_or_collective` (do not fan out) |
| R14 | Document has zero extractable keys (blank/unreadable attachment) | **HOLD** `insufficient_keys`; attach to nothing; surface in extraction_gaps |

Deterministic blocking cases (must never auto-resolve): R3, R5, plus:
- B1: two documents claim the same docket ref but name disjoint insured sets;
- B2: a document matches strong keys in **two existing clusters** (bridge document) — block both clusters' growth until human review;
- B3: confirmed cluster later receives a document that would re-open a SPLIT decision — new review, never silent re-merge;
- B4: any key whose evidence_refs are empty — hard validation error (extraction bug, exception candidate).

Ordering & idempotence requirements: decisions must be **order-invariant** — process documents in any order, same final clusters. This forces: (a) rules operate on the full pairwise matrix, not streaming greedy merge; (b) HOLD documents re-evaluated whenever any cluster changes; (c) replay test = permutation test (same bundle shuffled ⇒ identical clusters). This is the single hardest correctness property; it is what makes the kernel a kernel.

## 6. Interaction with budget truth

- A budget may only be generated for a confirmation whose preflight packet derives from a **human-confirmed** cluster (extend `build_budget_precondition_report` with a `matter_link_confirmed` check when the linking layer is active).
- `conflicted`/`hold` clusters are budget-blocking states, mapped to exception candidates (`matter_link_ambiguity_requires_review`, lake class `workflow_escalation`).
- Cluster confirmation evidence flows into `ConflictSeedPacket` party lists (more documents ⇒ better conflict seeds), still with `no_conflict_conclusion`.

## 7. Synthetic fixture plan

All fixtures follow the existing `examples/synthetic/inbound/*.json` bundle shape (multi-source bundles; sender `claims@harborpoint-insurance.example` reused deliberately).

| Fixture | Contents | Gold expectation |
|---|---|---|
| `linking-two-matters-one-sender` | 4 emails, 2 claim numbers, interleaved | 2 clusters, `corroborated_multi_key` |
| `linking-thread-drift` | 3-message thread; msg 3 introduces new claim number | R5: split + blocked drift message |
| `linking-claim-number-reuse` | same claim number, two claimant names | R3 block |
| `linking-policy-shared` | one policy number, two claimants | R4 split |
| `linking-no-keys-attachment` | email + unreadable attachment | R14 hold, extraction gap surfaced |
| `linking-subsidiary-alias` | "Valley Medical Center" vs "VMC of Henderson LLC", alias table present vs absent | merge with table; hold without |
| `linking-bridge-document` | doc matching strong keys of 2 clusters | B2 double block |
| `linking-le-collective` | 1 employer, 7 employees, same counsel | R13 review, no fan-out |
| `linking-adjuster-ref-only` | 2 emails sharing only adjuster ref | R7 merge as medium; upgrade on later strong key |
| `linking-permutation-holdout` | any fixture above, shuffled source order | identical clusters (holdout: never used to tune rules) |

## 8. Codex handoff (ordered, PR-sized)

### PR-ML1 — Key extraction + schema (risk: low)
- Purpose: `MatterLinkKey(Set)` models + deterministic extraction rules (regex/label-driven, per feature matrix) with evidence offsets.
- Files: new `src/lawfirm_os_intake/matter_link_keys.py`, `models.py` (additive), new `config/matter-link-policy.yaml` (normalization rules, alias tables, tier assignments, caps).
- Tests: new `tests/test_matter_link_keys.py` — extraction on `linking-*` fixtures 1–5 (add fixtures in same PR); every key must carry ≥1 evidence ref (B4).
- Validate: `PYTHONPATH=src pytest tests/test_matter_link_keys.py`, full suite, ruff, `export_schemas`.
- Do NOT: implement clustering yet; no fuzzy matching; no sender-as-key.

### PR-ML2 — Pairwise rules + clustering (risk: medium)
- Purpose: R1–R14, ambiguity classes, `MatterClusterProposal`, decision records, permutation invariance.
- Files: new `src/lawfirm_os_intake/matter_linking.py`; wire an optional stage into `workflow.py` behind an explicit flag (default off).
- Tests: `tests/test_matter_linking.py` — decision-table rows as parametrized cases; permutation test (≥20 shuffles, identical output); bridge/poison cases.
- Artifacts: `matter_cluster_proposals.json`, `matter_link_decisions.jsonl` in run dir.
- Do NOT: auto-generate budgets per cluster yet; do not let clustering mutate preflight packets.

### PR-ML3 — Review packet + budget gate integration (risk: medium)
- Purpose: human confirm/split/merge flow; `matter_link_confirmed` precondition; exception candidates for holds/conflicts.
- Files: `matter_linking.py`, `preconditions.py`, `exception_mapping.py` (new rule ids `matter_link_ambiguity.v1`, `matter_link_conflict.v1`), review rendering.
- Tests: extend `tests/test_exception_candidates.py`, preflight/preconditions tests.
- Do NOT: let a confirmed cluster silently re-merge past a human SPLIT (B3 regression test required).

### PR-ML4 — Holdout + eval wiring (risk: low)
- Purpose: `linking-permutation-holdout` + gold reports through the existing fixture-gold machinery.
- Files: `examples/synthetic/inbound/`, gold JSONs, `tests/test_fixture_gold.py` pattern.

Open hard problems (Fable, not Codex): cross-bundle linking over time (persistent cluster state store conflicts with "no Lake writes from intake" — needs an Orchestrator-owned store; design doc required before ML5); entity resolution beyond declared alias tables; and any learned matcher (prohibited until the deterministic oracle has fixture history).
