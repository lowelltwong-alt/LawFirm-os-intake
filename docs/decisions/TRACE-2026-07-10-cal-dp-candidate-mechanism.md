# Decision Trace

## Situation

The Fable learning-vs-leakage packet requires a homegrown CAL-DP candidate before any reviewed privacy dependency. Packet E2 supplied an aggregate-only proof scaffold, but dominance, small-sample, group-accounting, utility-floor, and exhausted-budget cases still had no executable DP route. Treating that scaffold as a privacy mechanism would create false confidence.

## Decision

- Add a standard-library Gaussian mechanism over per-matter L2-clipped `(sum, count)` sufficient-statistic vectors.
- Use in-memory synthetic replay material and serialize only its SHA-256 replay identifier. This is deterministic test support, not a secrecy or entropy boundary.
- Fsync and read back a local hash-chained synthetic zCDP JSONL entry. This is local consistency evidence, not an authority-owned, transactional, or tamper-resistant privacy ledger.
- Use sequential zCDP composition and the Bun-Steinke group bound `effective_rho = k^2 * rho`. This corrects the draft's linear group shorthand for zCDP accounting.
- Compute a synthetic all-but-one sum-reconstruction smoke check under an explicitly placeholder adversary policy; label it non-security and non-privacy evidence.
- Refuse before ledger write when budget, policy, utility, reconstruction, scope, or evidence binding fails.
- Extend `reviewed_learning_gate.py`; do not create another promotion path. DP review checks rebuilt request and release digests but remains failed until an authority-owned ledger receipt and governed secret-seed service are verified. The `approval:` identifier remains explicitly unauthenticated shape evidence.

## Non-decision

- No epsilon, rho, delta, clipping, K, utility, reset, protected-unit, or adversary value is selected for real work.
- No real client, matter, carrier, intake-production, public-matter, or privileged data is admitted.
- No calibrated value is published, no formal production privacy guarantee is claimed, and no candidate is promoted.
- No OpenDP, Tumult, Google DP, or other privacy dependency is imported.
- No Substrate, Orchestrator, Exception Lake, Skills Registry, DAD, connector, or external system is mutated.

## Authority impact

This is an intake-local candidate implementation under `authority_plane: none`. Semantic Substrate remains canonical for privacy, compliance, promotion, route, event, and schema authority. Orchestrator remains the future execution owner, and Exception Lake remains the future append-only evidence owner. The upstream governance dependency map was checked at LFGD-004, LFGD-005, LFGD-008, LFGD-013, and LFGD-016; this slice does not change their authority.

## Evidence

- `docs/fable/bounded-leakage-calibration-kernel.opus-draft.md`
- `docs/fable/codex-learning-leakage-build-packet.opus-draft.md`
- Bun and Steinke, *Concentrated Differential Privacy: Simplifications, Extensions, and Lower Bounds* (2016): Gaussian zCDP calibration, additive composition, and quadratic group privacy.
- Five synthetic policy-placeholder fixtures under `examples/synthetic/calibration/`.
- Exported local candidate schemas for the preflight request and leakage proof.

## Alternatives rejected

- A linear `k * rho` group debit was rejected because zCDP group privacy scales quadratically.
- Noising an already pooled vector with a clipping API was rejected because sensitivity is bounded only when each protected contribution is clipped before pooling.
- Basic epsilon composition was rejected in favor of zCDP accounting.
- Storing replay material or noised sufficient-stat values in the proof was rejected; the proof carries digests only.
- Auto-routing failed utility or smoke-check results to publication was rejected; they remain synthetic and refused.

## Premortem and red team

- **Governance weakening:** a local proof could be mistaken for canonical privacy approval. Containment: candidate-only literals, local authority statement, no formal production claim, and the existing promotion chokepoint.
- **Child/control-plane drift:** a later caller could skip the upstream map. Containment: update the intake governance mirror and keep Substrate authority explicit.
- **Boundary blur:** proof metadata or a ledger could carry matter facts. Containment: exact synthetic scope guards and digest-only release evidence; real/private flags fail before computation.
- **AI authority laundering:** an `approval:` string could be read as attorney approval. Containment: gate text and tests state shape-only and unauthenticated.
- **Local convenience override:** an intake parameter could become production policy. Containment: every configured value must be labeled a synthetic policy placeholder and the reset policy remains unresolved.
- **False-green CI:** unit tests could pass while group accounting, local readback, or release anchoring is absent. Containment: independent fixtures and negative tests cover `k^2 * rho`, duplicate matter IDs, cap exhaustion before write, hash-chain inconsistency, utility refusal, request binding, and release-digest binding.
- **Red-team P0, fixed closed:** a caller could forge local ledger/release fields and collaborate on a matching digest. The DP promotion gate now cannot pass: the candidate schema pins `authoritative_ledger_receipt_verified=false` and `secret_seed_authority_verified=false`.
- **Red-team P0, owner-blocked:** the local JSONL file can be reset, rewritten with a recomputed unkeyed chain, or raced. It is no longer described or accepted as authoritative. A single transactional authority-owned ledger belongs in the future Orchestrator/Exception Lake design.
- **Red-team P1, fixed:** duplicate `matter_id` values now fail before sensitivity accounting, preserving one clipped contribution per neighboring matter.
- **Red-team P1, fixed by honest labeling:** the all-but-one calculation is a synthetic implementation smoke check only and is not promotion or privacy evidence. A governed adversary and tolerance remain HD-2.
- **Red-team P1, owner-blocked:** caller-provided deterministic replay bytes are not secret randomness. The code and schema now label them synthetic replay material; real use requires a governed fresh-entropy service.
- **Residual limitation:** request/release digest anchors are also unauthenticated. Real use remains blocked until owning repos define and verify the ledger, entropy, and evidence authorities.

Rollback is deletion of this unpromoted candidate branch/PR. No production state or external evidence is changed.

## Validation

- `python scripts/run_full_pytest.py tests/test_dp_mechanism.py tests/test_zcdp_ledger.py tests/test_calibration_leakage.py tests/test_calibration_reviewed_learning_gate.py -q` -> 73 passed.
- `python scripts/export_schemas.py` -> 438 schemas exported.
- `python scripts/validate_repo.py` -> repository validation passed.
- `python scripts/validate_governance_dependency_map_mirror.py` -> governance dependency-map mirror validation passed.
- `python scripts/run_validation_suite.py` -> repository validation passed; 438 schemas exported; Ruff passed; 337 files formatted; 870 tests passed in 451.57s; synthetic smoke demo completed; final boundary `blocked_pending_conflicts_and_engagement`; final repository validation passed.
- DAD postflight handoff: `dad:handoff:fd47e659-f971-5494-bc45-7db03db4d22c`.
- DAD lesson: `dad:lesson:09d93819-ec52-51d1-a07c-098277d890c6`.
- Root cross-repo diagnostic `validate_ai_front_door.py` remains blocked by a pre-existing missing Exception Lake example: `examples/legal_document_integrity_check_event.json`.
- Root cross-repo diagnostic `validate_skill_agent_control_plane.py` remains blocked by the pre-existing unregistered repo `LawFirm-os-talent-intelligence-private`.

## Human gates

- HD-1/HD-2: protected unit, rho/epsilon cap, delta, reset policy, clipping/utility policy, K/dominance policy, and declared adversary model.
- HD-7: whether any real-outcome calibration is allowed; currently blocked.
- HD-8: privacy-library, license, security, and privacy review before any dependency replaces the homegrown candidate.
- Privacy, compliance, counsel, data-owner, Substrate, Orchestrator, and Exception Lake review before any real-data or cross-repo execution path.
