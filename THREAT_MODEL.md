# Threat Model

## Protected assets

- client and prospective-client confidentiality;
- privilege and work-product boundaries;
- matter isolation;
- firm practice context and client/carrier guidelines;
- negotiated rates and budgeting assumptions;
- canonical schemas, registries, and governance;
- reviewer decisions and audit trail;
- source integrity and provenance;
- tool and connector authority;
- model prompts and worker manifests.

## Trust boundaries

1. Raw inbound source → source reader.
2. Structured source segments → specialist workers.
3. Candidate outputs → independent critic.
4. AI preflight → human intake reviewer.
5. Human confirmation → conflict seed and budget planner.
6. Vertical repo → Orchestrator, Skills Registry, Legal Knowledge Runtime, and Exception Lake.
7. Any future external connector → system of record.

## Principal threats and controls

| Threat | Control in starter |
|---|---|
| Prompt injection in email/document | Treat source as data; no source-directed tools; typed worker outputs |
| Data exfiltration | No network and no external connector |
| Cross-matter leakage | One bundle per run; no shared matter memory |
| Calibration leakage through fitted parameters | Synthetic-only CAL-DP candidate; clipped sufficient statistics, bounded candidate accounting, no publication, and owner authority still required |
| Learned-rule re-identification or work-product leakage | Closed synthetic LessonIR, pinned universe/lattice/fixture manifest, strategy/free-text block, k/diversity and differencing checks, sanitized proof, no DAD crossing, and fail-closed human/owner gates |
| Prohibited residue crossing into DAD | Closed structured crossing request, max-label join, deterministic residue classes, QRD proof binding, literal-false receiver/human authority, reviewed-learning gate rebuild, and no send/outbox capability |
| Positional or issue-conflict laundering through learned lessons | Pinned synthetic adversity graph and case/provenance snapshots, exact declared-edge checks only, source-record-bound QRD/CHW gate coverage for carrier lessons, unreviewed/unknown holds, synthetic-only imputation with authoritative firm-wide imputation false, digest-only proof, literal-false counsel/human/owner authority, no lesson-fire capability, and HD-4/HD-7 real-use block |
| Role hallucination | Candidate status, exact evidence refs, human confirmation |
| Practice-context overreach | Context/evidence separation and counterfactual tests |
| Deadline mischaracterization | Candidate only; human verification; no docket write |
| Conflict-clearance overclaim | Conflict seed schema has no clearance state |
| Budget fabrication | Synthetic templates; no rate invention; deterministic calculations |
| Unauthorized external action | No send/write/open/submit capability |
| Shadow canon | Local candidates must graduate through owning repo |
| Dynamic agent escalation | Predeclared worker registry; no spawning |
| Compaction/context loss | Durable packet, ledger, hashes, and Claude compaction contract |
| Malicious or stale prompt | Future prompt registry and hash gate in Orchestrator |
| Model/provider retention risk | Synthetic-only until provider/data policy is separately approved |
| Public-data privacy or licensing issue | Catalog/planning only; no bulk data committed or directly ingested |

## Threat response

On detection of prohibited data or authority expansion:

1. stop the run;
2. write a redacted local blocker event if safe;
3. do not forward content to another model or tool;
4. preserve only permitted hashes/metadata;
5. escalate to the appropriate human authority;
6. create an Exception Lake candidate only after its contract exists.
