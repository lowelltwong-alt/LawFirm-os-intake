# Decision Trace

## Situation

The Fable learning-vs-leakage packet identifies qualitative lessons as a distinct disclosure surface: a rule can reveal a rare matter context or carry strategy/work product even when no numeric calibration value is released. The research packet proposes a structured LessonIR, reviewed generalization lattice, anonymity/support thresholds, sensitive-outcome diversity, privilege partition, and cross-lesson differencing, while stating that this does not yield a formal privacy guarantee.

## Decision

- Add a closed, synthetic-only LessonIR with coded claims and contexts. Nonempty free text is never consumed as signal and blocks the candidate.
- Pin the only accepted lesson fixtures and the complete synthetic policy/lattice/universe context by SHA-256. A caller cannot relabel a private or real-looking lesson as synthetic and supply a matching universe.
- Generalize operational atoms by deterministic minimum-hop traversal over a reviewed synthetic lattice. Strategy atoms are blocked, never generalized.
- Require population anonymity, support count, and explicit sensitive-outcome diversity. Human values for K and the adversary model remain synthetic placeholders.
- Check the candidate against all declared published lesson projections, including ancestor/descendant lattice predicates. Proof output contains counts and generalized values, not support IDs or the original rare value.
- Bind the proof to a full internal request digest at `reviewed_learning_gate.py`, the existing single chokepoint. The serializable proof deliberately excludes that sensitive request digest.
- Keep every proof blocked because the publication snapshot is not authority-verified and human disclosure review is not authenticated.
- Label the only guarantee `bounded_reident_under_declared_adversary`; set formal privacy guarantee claimed to false.

## Non-decision

- No K_qual, K_support, adversary model, sensitive-outcome policy, strategy class, or real publication universe is selected.
- No real client, prospective-client, matter, carrier, intake-production, public-matter, privileged, or work-product data is admitted.
- No lesson is published or sent to DAD. No DAD schema is mutated from this repo.
- No local proof, approval-shaped string, or AI output becomes legal, privacy, compliance, or promotion authority.

## Authority impact

This is an intake-local candidate under `authority_plane: none`. Semantic Substrate remains canonical for shared governance and schema authority. Orchestrator is the future owner of runtime review and authoritative publication-snapshot evidence. DAD owns receiver-side lesson payload validation under its own promotion review. The upstream governance dependency map was checked; intake cannot override it or mutate a sibling repo.

## Premortem and red team

- **Relabeled private data:** a caller could claim real values are synthetic. Fixed by closed identifiers plus pinned lesson and context manifests.
- **Incomplete publication history:** a caller could omit a prior lesson and evade differencing. Locally detectable snapshot integrity is implemented, but completeness requires an owner authority; the literal-false authority flag keeps every proof blocked.
- **Rare-value leakage:** a generalization path could reveal the value it replaced. Fixed by serializing only dimension and destination; the source value is explicitly absent.
- **Support leakage:** proof atoms, errors, or intersections could reveal support matter IDs. Fixed by count-only summaries, closed reasons, and negative serialization tests.
- **Strategy laundering:** a strategy value could be generalized into an operational value. Fixed by pre/post generalization privilege screens and a prohibition on published strategy projections.
- **False l-diversity:** an unrelated claim-code count could masquerade as sensitive diversity. Fixed by an explicit synthetic sensitive-outcome attribute and threshold.
- **Lattice differencing gap:** ancestor/descendant predicates could be skipped as conflicts. Fixed by a lattice-aware conjunction and a focused regression test.
- **AI authority laundering:** a proof could appear ready because an approval ID has the right shape. Fixed by `authenticated_human_disclosure_review_verified=false` and a gate that cannot pass.
- **False-green discovery:** unit tests could pass while schemas or governance discovery are stale. Containment: schema export, repo validator, mirror validator, AI TOC, README, data-flow map, threat model, governance boundary, and full validation suite are part of this PR.

## Evidence

- `docs/fable/learning-vs-leakage-hard-kernels.opus-draft.md`, P2.
- `docs/fable/codex-learning-leakage-build-packet.opus-draft.md`.
- `src/lawfirm_os_intake/lessons/` and `tests/test_lesson_disclosure.py`.
- `examples/synthetic/lessons/qrd-disclosure-cases.synthetic-policy-placeholder.json`.
- Exported candidate schemas for LessonIR, LessonDisclosureRequest, and LessonDisclosureProof.

## Handoff anchor verification

- `[C]` confirmed: `src/lawfirm_os_intake/reviewed_learning_gate.py`, `src/lawfirm_os_intake/carrier_rejection_learning.py`, `THREAT_MODEL.md`, and `GOVERNANCE_BOUNDARY.md` exist. This PR changes the gate, threat model, and governance boundary; carrier-rejection routing remains a later CHW/IFC integration concern.
- `[V]` verified this session: `src/lawfirm_os_intake/budget_calibration_corpus.py`, `src/lawfirm_os_intake/budget_learning_loop.py`, `src/lawfirm_os_intake/benchmarks.py`, and `src/lawfirm_os_intake/matter_linking.py` all exist. This QRD PR does not change them.
- The handoff's proposed `src/lawfirm_os_intake/lessons/` module family is now implemented locally. Receiver-side DAD schema wiring remains PR-LL3 under DAD owner review.

## Validation

- `python scripts/run_full_pytest.py tests/test_lesson_disclosure.py tests/test_calibration_reviewed_learning_gate.py tests/test_reviewed_learning_gate.py -q` -> 55 passed.
- `python scripts/export_schemas.py` -> 441 schemas exported.
- `python scripts/validate_governance_dependency_map_mirror.py --mirror-updated true` -> governance dependency-map mirror validation passed.
- `python scripts/validate_repo.py` -> repository validation passed.
- `python scripts/run_validation_suite.py` -> repository validation passed; 441 schemas exported; Ruff passed; 345 files formatted; 898 tests passed in 463.17s; synthetic smoke demo completed; final boundary `blocked_pending_conflicts_and_engagement`; final repository validation passed.
- DAD postflight handoff: `dad:handoff:cb4b745f-2ea0-57bc-9ab0-49012c6db967`.
- DAD lesson: `dad:lesson:c272cada-ac1b-58c0-908a-c37fb36776cc`.

## Human gates

- HD-3: privacy and counsel must define the adversary model, K_qual, K_support, sensitive-outcome diversity policy, and strategy classes.
- HD-7: privacy, counsel, data-owner, and Substrate governance must approve any real-data pilot; current posture is blocked.
- Counsel and owners must decide whether any qualitative lesson may cross to DAD before a pilot.
- Orchestrator/DAD owners must define an authenticated, complete, append-only publication snapshot and authenticated human disclosure-review evidence.

Rollback is deletion of this unpromoted branch/PR. No production state, published lesson, or external evidence is changed.
