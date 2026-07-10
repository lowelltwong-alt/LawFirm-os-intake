# Decision Trace

## Situation

Fable's PR-LL4 requires a Brewer-Nash-style lesson-firing wall so a lesson derived
from one synthetic conflict class cannot be reused across a declared adverse
class. Counsel has not made HD-4: no real adversity classes, affiliate scope, or
firm-wide imputation policy is authorized.

## Risk tier and options

This is high risk because a local same-side result could be mistaken for a legal
conflict conclusion.

- **Chosen:** digest-pinned synthetic graph, case manifest, and firm-wide
  provenance snapshots; exact declared relationships; unreviewed/unknown holds;
  sanitized blocked proof; and literal-false authoritative imputation plus
  counsel/human/owner authority.
- **Rejected:** similarity or model inference over client, matter, issue, or
  position text. It could manufacture conflict policy and leak source meaning.
- **Rejected:** an optional per-user wall. Fable's handoff requires firm-wide
  imputation, and treating it as optional could launder prior firm knowledge.
- **Bounded comparison:** five synthetic cases cover same-side, reviewed
  adversity, synthetic firm-wide imputation, unreviewed edge, and unknown relationship.
  No real-data comparison is allowed.

## Decision

- SyntheticAdversityGraph accepts only closed synthetic identifiers and exact
  declared edges. The graph, allowed request/lesson/class combinations, and
  synthetic firm-wide provenance snapshots are digest-pinned.
- A fixture-reviewed edge can produce cross_wall_block; an unreviewed edge or
  absent relation produces a hold. No relationship is inferred and no result
  auto-clears a conflict.
- ChineseWallRequest requires an exact pinned case, explicit synthetic scope,
  literal-false real/private/client/matter/carrier/privilege/work-product flags,
  and a pinned synthetic firm-wide provenance snapshot. Authoritative firm-wide
  provenance/imputation remains literal false.
- ChineseWallProof exposes graph/class-set digests and pair counts, not class IDs
  or source facts. Its status is always blocked.
- A reviewed synthetic cross-wall result can produce a local
  ChineseWallViolationCandidate, but no Exception Lake write occurs.
- reviewed_learning_gate.py rebuilds and binds the request/proof at the single
  promotion chokepoint. Carrier-rejection learning now fails unless every
  proposal has source-record-bound QRD and CHW gate requests; repeatable CLI
  proof-request files expose the same checks.

## Non-decisions

- No real adversity or conflict-of-interest class is defined.
- No affiliate, former-client, prospective-client, issue-conflict, positional
  conflict, or legal imputation rule is decided.
- No conflict search, conclusion, clearance, waiver, consent, engagement, or
  representation decision is made.
- No lesson is fired, promoted, published, or sent.
- No Exception Lake, sibling repo, connector, network, or external write occurs.
- No real client, matter, carrier, private, privileged, or work-product data is
  admitted.

## Premortem and red team

- **Synthetic-label laundering:** real classes, request IDs, or lesson IDs are
  renamed with a synthetic prefix. Containment: the request accepts only the
  exact pinned graph and case manifest combinations.
- **Test false positive:** strict Python-list validation fails before an unsafe
  field is reached. Containment: negative tests use the same JSON parser as the
  runtime path.
- **Unreviewed edge treated as safe:** an uncertain relationship silently
  permits reuse. Containment: unreviewed and unknown both hold.
- **Local same-side becomes clearance:** a caller treats the algorithm as legal
  authority. Containment: proof status and counsel/human/owner authority remain
  literal false, and conflict clearance is explicitly false.
- **Imputation overclaim:** a true flag claims complete firm-wide provenance
  without a membership manifest. Containment: synthetic fixture provenance is
  separately digest-pinned, while authoritative firm-wide imputation is false
  and remains a gate blocker.
- **Executable gate bypass:** carrier candidates list CHW as metadata but no
  request is supplied to the runnable chokepoint. Containment: carrier-specific
  QRD/CHW coverage checks fail the report, the run function and CLI load proof
  request files, and failed reports return nonzero.
- **Proof leaks class identity:** class IDs appear in the portable artifact.
  Containment: proof carries only digests and counts; tests scan serialization.
- **Forged proof or replay:** proof is paired with another request. Containment:
  deterministic rebuild plus an independently supplied request digest.
- **Approval ID becomes clearance:** a syntactically valid ID bypasses counsel.
  Containment: it is evidence shape only; literal-false policy and review fields
  keep the gate failed.
- **Violation event becomes a write:** candidate creation mutates the Lake.
  Containment: the builder returns a local sanitized object with a literal-false
  write field and exposes no Lake adapter.
- **False-green discovery:** code passes while governance routes drift.
  Containment: README, AI TOC, data-flow map, governance boundary, threat model,
  mirror, schemas, fixture, tests, and this trace change together.
- **Expected block breaks QA:** a synthetic QA harness treats the newly blocked
  learning loop as a product failure or manufactures authority to recover a green
  result. Containment: the raw learning-loop artifact remains blocked; the QA
  harness accepts only the exact synthetic, no-write, failed-gate state as a
  successful fail-closed test outcome. Arbitrary or side-effecting blocked states
  still fail.

## Rollback and kill criteria

Rollback is deletion of this unpromoted branch/PR. Kill the candidate path if it
accepts an unpinned graph/case/provenance snapshot, infers adversity, permits an
unreviewed or unknown relationship, asserts authoritative firm-wide imputation,
lets a carrier learning report pass without QRD/CHW coverage, serializes class IDs
or source facts into a proof, clears a conflict, fires a lesson, writes the Lake,
or admits non-synthetic data.

## Evidence

- docs/fable/codex-learning-leakage-build-packet.opus-draft.md, CHW component.
- .ai-work/fable/CODEX_CROSS_REPO_HANDOFF.md, PR-LL4 and HD-4.
- Brewer-Nash 1989 is the structural research anchor named by Fable; legal
  conflict policy remains counsel-owned and was not independently verified in
  this implementation session.
- examples/synthetic/conflicts/chinese-wall-cases.synthetic-policy-placeholder.json.

## Validation

- Independent fresh-eyes review agent
  `019f4c91-2033-7eb1-9470-eb0a7b84e2ed` found three issues: executable carrier
  gate bypass, unpinned synthetic identifiers/case combinations, and overstated
  firm-wide imputation. All three were fixed and regression-tested before the
  final baseline.
- `python scripts/run_full_pytest.py tests/test_chinese_wall.py tests/test_chinese_wall_gate.py tests/test_reviewed_learning_gate.py tests/test_carrier_rejection_learning.py -q -rA` -> 34 passed.
- `python scripts/run_full_pytest.py tests/test_labor_employment_budget_outcome_replay_input_pack.py tests/test_budget_learning_loop.py -q` -> 28 passed.
- Combined CHW, reviewed-gate, budget-consumer, and synthetic QA/UI regression
  set -> 72 passed.
- `python scripts/export_schemas.py` -> 447 schemas exported.
- `python -m ruff check --no-cache src tests scripts` -> all checks passed.
- `python -m ruff format --check --no-cache src tests scripts` -> 357 files already formatted.
- `python scripts/run_full_pytest.py` -> 948 passed in 706.76s.
- `bash scripts/smoke_demo.sh` -> passed in 125.2s; final boundary
  `blocked_pending_conflicts_and_engagement`. An initial post-gate run exposed and
  corrected the smoke wrapper's stale ready-status assertion.
- `python -B scripts/validate_repo.py` -> repository validation passed.
- `python -B scripts/validate_governance_dependency_map_mirror.py --mirror-updated true` -> governance dependency-map mirror validation passed.
- DAD preflight: `dad:session:564b6b0f-84af-4960-a595-c02076691bd4`.
- DAD postflight: `dad:handoff:7ba8967b-5c7a-5880-b731-32a835fb3cea`.
- DAD lesson: `dad:lesson:d6566097-2530-5380-ab55-ecfdec74b7e1`.

## Human gates

- HD-4 blocks authoritative adversity/CoI classes and firm-wide legal imputation
  policy.
- HD-7 blocks every real-data path.
- Semantic Substrate must own any shared class vocabulary or proof contract.
- Orchestrator must own any runtime lesson-firing gate.
- Exception Lake must own violation-event admission.
- Authenticated human and owning-repo review remain required.
- Carrier source-record association is candidate wrapper evidence, not a
  production-grade cryptographic source/proof binding. Semantic Substrate and
  Orchestrator owners must define that binding before any authority field can
  become passable.
