# Decision Trace

## Situation

The Fable learning-vs-leakage packet requires a deterministic information-flow control before any qualitative lesson could cross from Intake to DAD. A QRD proof can reduce lesson disclosure risk, but it does not establish that a proposed cross-repo payload has an allowed sensitivity label, contains only structured fields, or is free of prohibited residue.

## Risk tier and options

This is high risk because a cross-repo schema and a `clean` result can become a future-agent default.

- **Chosen:** closed sensitivity labels, max-label joins, structured QRD proof input, deterministic residue classes, hash-bound rebuild, and literal-false DAD/human authority.
- **Rejected:** regex-only filtering over arbitrary mail JSON. It cannot prove label flow, structured-IR use, proof binding, or receiver authority.
- **Bounded comparison:** synthetic fixtures exercise the same structured payload against clean, prohibited-residue, high-label, mixed-label, and relabeling cases. No real-data comparison is allowed.

## Decision

- Add the closed lattice `public < candidate < internal < privileged`; a join always takes the most restrictive input label.
- Permit no proposed DAD candidate crossing above `candidate`.
- Accept only a strict synthetic crossing request whose pinned QRD request/proof pair rebuilds exactly.
- Scan deterministic prohibited classes for currency/rate, specific carrier, PII, privilege/work-product, signal-bearing free text, and raw/long source residue without echoing matched content.
- Produce a deterministic `CrossingProof` and rebuild it inside `reviewed_learning_gate.py`, the existing single promotion chokepoint.
- Label the check only `deterministic_declared_pattern_residue_check` and set formal noninterference guarantee claimed to false. Pattern coverage is not semantic zero-residue proof.
- Keep receiver-schema verification and authenticated human crossing review literal false. No proof authorizes a send or outbox write.

## Non-decision

- No real carrier-name, PII, privilege, work-product, currency, rate, client, matter, or intake-production corpus is created or scanned.
- No classifier, learned DLP model, declassification rule, external connector, DAD call, mail send, outbox write, sibling mutation, or promotion is added.
- No DAD receiver schema is changed from Intake. That change requires a separate clean DAD owner PR.
- No human, counsel, privacy, compliance, DAD, Orchestrator, or Substrate authority decision is inferred.

## Premortem and red team

- **Forged low label:** caller marks privileged material `candidate`. Containment: strict structured input, closed fixture scope, residue scan, and max join; arbitrary payloads are not accepted.
- **Mixed-label downgrade:** one candidate input hides an internal dependency. Containment: every source label participates and the effective label is the maximum.
- **Scanner false confidence:** prohibited semantics evade known patterns. Containment: scanner-clean is only local candidate evidence; QRD, DAD receiver, authenticated human, and owner gates remain mandatory.
- **Forged QRD artifact:** a caller supplies a synthetic-looking proof detached from its source request. Containment: the internal crossing request carries the pinned QRD request and rebuilds the proof exactly before IFC evaluation.
- **Proof replay:** a clean proof is paired with a different request. Containment: canonical request digest, deterministic proof rebuild, and external digest anchor at the reviewed-learning gate.
- **Error-message leak:** a refusal echoes sensitive content. Containment: closed reason codes and count-only scan summaries.
- **Proof-as-send-authority:** a future agent interprets `CrossingProof` as permission. Containment: literal false authority fields, blocked status, no send API, and explicit governance/data-flow discovery.
- **Formal-guarantee overclaim:** declared regex classes are described as semantic noninterference. Containment: exact non-formal guarantee label plus a literal-false formal-claim field and gate check.
- **Receiver drift:** Intake and DAD schemas diverge. Containment: separate DAD owner PR and cross-repo fixture review; Intake cannot silently redefine DAD.
- **False-green discovery:** tests pass while front doors or the governance mirror remain stale. Containment: update AI TOC, README, data-flow map, governance boundary, threat model, mirror, schemas, and decision trace in the same PR.

## Rollback and kill criteria

Rollback is deletion of this unpromoted branch/PR. Kill the candidate path if a proof serializes prohibited source text, a request can carry arbitrary payload fields, labels can downgrade under join, a QRD proof can detach from its rebuilt request, a blocked QRD proof can become crossing-ready, a formal guarantee is claimed, or any function sends/writes outside the local test output surface.

## Evidence

- `docs/fable/codex-learning-leakage-build-packet.opus-draft.md`, IFC component.
- `docs/fable/cross-matter-noninterference-kernel.opus-draft.md`.
- `src/lawfirm_os_intake/outbox/` and `tests/test_outbox_crossing.py`.
- Synthetic-only fixtures under `examples/synthetic/outbox/`.

## Validation

- `python scripts/run_full_pytest.py tests/test_lesson_disclosure.py tests/test_outbox_crossing.py tests/test_outbox_crossing_gate.py tests/test_calibration_reviewed_learning_gate.py tests/test_reviewed_learning_gate.py -q -rA` -> 78 passed.
- `python scripts/export_schemas.py` -> 443 schemas exported.
- `python -m ruff check --no-cache src tests scripts` -> all checks passed.
- `python -m ruff format --check --no-cache src tests scripts` -> 351 files already formatted.
- `python scripts/run_full_pytest.py` -> 921 passed in 718.11s.
- `bash scripts/smoke_demo.sh` -> demo completed; final boundary `blocked_pending_conflicts_and_engagement`.
- `python scripts/validate_repo.py` -> repository validation passed.
- `python scripts/validate_governance_dependency_map_mirror.py --mirror-updated true` -> governance dependency-map mirror validation passed.
- DAD postflight handoff: `dad:handoff:d9405cc4-346c-525f-a0d1-9a88cf1f040b`.
- DAD lesson: `dad:lesson:26756c4f-e884-5e80-b53e-a8916eb356dd`.
- Fresh-eyes explorer review was attempted but unavailable because the agent usage ceiling was reached. The implementer red-team/checklist and adversarial tests found and fixed request-digest oracle, proof-only QRD forgery, scanner coverage, label-set identity, blocker consistency, and formal-guarantee overclaim risks.

## Human gates

- HD-7 continues to block every real-data path.
- DAD owner review must accept the warning-only receiver extension before any payload compatibility claim.
- Substrate/Orchestrator/DAD owners must define shared label/declassification authority and authenticated crossing review before any runtime use.
