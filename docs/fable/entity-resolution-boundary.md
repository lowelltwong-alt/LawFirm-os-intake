# Entity Resolution Boundary — Hard Kernel

- Status: Fable design output, candidate-only, synthetic-only. Second pass; expands the entity rules embedded in `docs/fable/matter-linking-hard-kernel.md` (§3) into a standalone boundary spec.
- Author: Fable 5, 2026-07-05.
- Owner boundaries: Semantic Substrate owns canonical entity identity; intake owns deterministic normalization and candidate alias proposals; DAD receives mistake lessons, never identity canon.

## 1. Problem

Declared alias tables are safe but cover only what someone already wrote down. Real intake text contains "Valley Medical Center of Henderson, LLC", "VMC Henderson", "Valley Med. Ctr."; employers appear as parents, subsidiaries, staffing agencies, PEOs, franchises; insureds appear under policy-holder names that differ from operating names. Fuzzy matching "solves" coverage by guessing — and one wrong merge simultaneously corrupts conflict seeds, matter linking, budget drivers, and carrier/client separation. The kernel: expand deterministic reach *without* creating an inference engine.

## 2. The v1 identity ladder (deterministic expansion beyond exact aliases)

Every comparison between two raw names resolves to exactly one rung; rungs are pure functions, so two engineers derive the same answer.

| Rung | Test (in order) | Result |
|---|---|---|
| E1 exact | raw strings equal | MATCH (trivial) |
| E2 normalized-exact | `normalize(a) == normalize(b)` (normalizer set below) | MATCH, label `normalized_exact` |
| E3 declared alias | edge exists in a reviewed alias/subsidiary table (status `reviewed`) | MATCH, label `declared_alias`, table+entry ref recorded |
| E4 declared-structure | both names resolve via E2/E3 to entities linked by a reviewed structural edge (`subsidiary_of`, `staffing_agency_for`, `peo_of`, `franchise_of`, `insured_dba`) | **RELATED, never merged**: entities stay distinct; the edge feeds matter-linking as a *medium* signal and conflict seeds as *both names listed* |
| E5 suffix-residual | normalized forms equal after additionally stripping a **declared residual vocabulary** (geographic qualifiers, "of <place>", department words) — vocabulary is itself a reviewed table | HOLD, label `possible_affiliate`; emits an alias-table proposal |
| E6 anything else | token overlap, abbreviations, acronyms, initialisms, typos | NO MATCH; if a human asserts sameness during review, that becomes a table entry, not a matcher change |

Key structural insight (E4): **affiliate relationships are edges, not merges.** A subsidiary is not its parent — conflicts, coverage, and budgets can differ — so the system must be able to say "related, distinct" as a first-class answer. Collapsing E4 into E3 was considered and rejected: it destroys exactly the distinction L&E (joint employer) and coverage (named insured vs operating entity) cases turn on.

## 3. Allowed normalizers (closed list, versioned in `config/matter-link-policy.yaml`)

1. Unicode NFC normalization, then casefold.
2. Collapse whitespace; strip punctuation `.,'"()&/-` → single spaces (record `&`→`and` as a rewrite, applied before stripping).
3. Strip legal-form suffix tokens from the END only, from a declared list: `llc, l.l.c., inc, incorporated, ltd, llp, lp, pc, pllc, corp, corporation, co, company, pa, sc`. Stripping is *recorded* (`suffix_stripped: "llc"`), because "Acme LLC" vs "Acme Inc" equal-after-strip is an E5 HOLD, not an E2 MATCH — the suffix disagreement is evidence of possible distinctness.
4. Declared token rewrites (reviewed table): `ctr→center, med→medical, hosp→hospital, dept→department, assn→association, natl→national`. Only whole-token, only from the table.
5. Nothing else. Explicitly prohibited: edit distance, Jaro/Winkler, token-set ratios, embeddings, phonetic codes (Soundex/Metaphone), acronym generation ("VMC" from "Valley Medical Center"), word dropping, stemming beyond the rewrite table.

Rule 3's asymmetry deserves emphasis because it is the subtle bug generator: **equal-after-strip with UNEQUAL stripped suffixes is a HOLD, not a match.** Same-suffix or one-sided-suffix cases are E2 matches.

## 4. Hold/review rules

| # | Condition | Disposition |
|---|---|---|
| H1 | E5 fires | HOLD `possible_affiliate` + auto-draft alias-table proposal (below) |
| H2 | Equal-after-strip, unequal suffixes | HOLD `suffix_conflict` |
| H3 | One name is a prefix of the other after normalization with ≥2 residual tokens ("Valley Medical Center" vs "Valley Medical Center of Henderson") | HOLD `possible_affiliate` |
| H4 | E4 edge exists but is status `proposed`/`unreviewed` | HOLD; the edge itself goes to review before it can carry weight (R12 in base kernel) |
| H5 | Same normalized name, conflicting roles across documents (claimant in one, insured in another) | BLOCK `role_identity_conflict` — never resolved by string logic |
| H6 | Alias-table cycle or contradictory edges (A subsidiary_of B, B subsidiary_of A) | BLOCK table itself; table validation failure is an exception candidate |

Alias-table proposal artifact (candidate, run-local): `{proposed_edge, rung_that_fired, evidence_refs (both source spans), proposer: "system_E5", status: proposed}`. Humans review proposals; accepted entries land as **versioned table diffs** (git-reviewable), which is the entire learning loop — the matcher never changes, the tables grow.

## 5. Fixtures (synthetic, per L&E corpus roadmap conventions)

| Fixture | Exercises | Gold |
|---|---|---|
| `entity-suffix-conflict` | "Sierra Staffing LLC" vs "Sierra Staffing Inc" | H2 hold, no merge |
| `entity-residual-geo` | "Valley Medical Center" vs "Valley Medical Center of Henderson LLC" | H3/E5 hold + proposal drafted |
| `entity-declared-subsidiary` | reviewed `subsidiary_of` edge present | E4 related-not-merged; both names in conflict seed; medium link signal |
| `entity-joint-employer-le` | staffing agency + operating employer, reviewed `staffing_agency_for` | E4; L&E fact report shows joint-employer bucket populated |
| `entity-insured-dba` | policyholder name vs storefront name, `insured_dba` edge | E4; carrier-role rate resolution keys on the policyholder side only |
| `entity-rewrite-table` | "Valley Med. Ctr." vs "Valley Medical Center" | E2 via rewrites 4 |
| `entity-acronym-negative` | "VMC" vs "Valley Medical Center", no table entry | E6 no-match (pins the prohibition) |
| `entity-table-cycle` (holdout) | contradictory edges | H6 block |

## 6. How DAD learns entity-resolution mistakes without creating canon

- **Events → Exception Lake:** every H1–H6 occurrence and every human correction (human merged what the system held, or split what a table merged) with identity_key = (rule id | normalized-pair signature). Corrections of *table entries* are their own family — a wrong reviewed edge is more dangerous than a wrong hold.
- **Lessons → DAD:** clustered corrections become one lesson per pattern: "residual vocabulary missing geographic qualifier X (n=…)", "suffix-strip list missing form Y", "E4 edge type needed: Z". Each lesson proposes a **table/vocabulary diff + fixture**, never a matcher behavior change. DAD classification: `identity-vs-normalization-boundary`, asset type: the tables themselves are the reusable digital assets (versioned, reviewed, portable to other repos); the matcher is deliberately boring.
- **Canon boundary:** if a pattern justifies canonical entity identity (not just intake linking), the lesson's owner routing is Semantic Substrate; intake tables remain local candidates even after review.

## 7. Codex handoff

1. **PR-ER1 (with PR-ML1, low risk):** normalizer set (rules 1–4) with recorded rewrites/strips, rungs E1/E2/E5/E6 + H1–H3, tables in `config/matter-link-policy.yaml` (`legal_suffixes`, `token_rewrites`, `residual_vocabulary`, `alias_edges` — all with `status` per entry). Tests: every fixture above except E4/H4/H6; property test: normalize is idempotent and order-independent.
2. **PR-ER2 (medium):** structural edges (E4), edge-status handling (H4), table validation (H6), role-conflict block (H5), alias-proposal artifact emission; conflict-seed integration (both names of an E4 pair listed). Tests: remaining fixtures + holdout.
3. **PR-ER3 (low):** correction-event exception families + DAD lesson drafting from clustered corrections (after PR-EX2/EX3 machinery exists).

**Must not do:** any similarity scoring (including "just for ranking review queues" — that is how scores leak into decisions); acronym inference; merging E4 relatives; letting an `unreviewed` edge carry linking weight; changing matcher behavior in response to corrections (only tables change).
