# DAD Learning / Digital-Asset Intake Process — Audit

- Status: Fable audit output, candidate-only. Based on first-hand use of the DAD pipeline on 2026-07-05/06 (preflight → midflight ack → outbox-check → compose ×2 → postflight) from `LawFirm-os-intake-seed-clean-20260623`.
- Author: Fable 5, 2026-07-05.
- Verdict up front: **the process is genuinely good — clearly better than most learning pipelines — but it has one silent-corruption bug, one schema gap that undermines its own learning rules, and several lineage/dedupe weaknesses.** All fixes are Codex-sized and listed in §4.

## 1. Step-5 questions, answered with evidence

| Question | Answer | Evidence |
|---|---|---|
| DAD entry point findable? | **Yes, easily** | `04_Digital_Assett_Directory/AI_FRONT_DOOR.md` is a real deterministic front door; required read order; navigation registry |
| Mailbox/outbox clear? | **Yes** | `docs/MAIL_CENTER.md` defines central + repo-local mirror + explicit fallback rule (`dad_cli_unavailable` → append `.digital-asset/mail/outbox.jsonl`) |
| Schema? | **Envelope yes, payload no** | `schemas/mail-message.schema.json` covers the envelope; `payload` is an untyped object; lesson content structure is unspecified |
| Helper CLI? | **Yes, rich** | `asset-dir mail compose/outbox-check/…`, `agent preflight/midflight/postflight`, dedupe check, learning-rule injection at preflight |
| Lesson vs event vs reusable asset distinguishable? | **Partially** | `message_type` separates lesson/asset/workflow/taxonomy/capability suggestions; but no `asset_type` classification *inside* a lesson, and no "this is an event, wrong destination" triage outcome |
| Enough context/evidence attachable? | Yes | `--evidence`, payload keys, provenance object; all worked |
| Implementation handoffs attachable? | Yes (freeform) | carried in payload; nothing validates their presence |
| "What not to do" attachable? | Yes (freeform) | same |
| Owner repo + authority boundary classifiable? | Yes (freeform) | payload keys; suggested_actions carried routing requests; no controlled vocabulary for owner repos |
| candidate_only / no-hidden-CoT markable? | Yes, but **stringly** | in key=value mode flags arrive as `"true"`/`"false"` strings, not booleans; nothing enforces their presence |
| Can DAD dedupe/cluster lessons? | **Weakly** | `outbox-check` exists but reported `sent_count: 0` while the repo-local outbox already held a hand-written record — the check reads a different ledger than the spool it appends to |
| Can DAD detect new digital assets from docs/code? | Not push-side | asset-recognition scans exist DAD-side, but nothing in the compose path lets a repo *declare* newly created assets (the six kernel docs are undiscovered assets until a scan runs) |
| Can DAD link lesson → source refs → future PRs? | **No forward links** | evidence refs work backward; there is no field or follow-up convention for "implemented by PR X", and `--supersedes` was **not persisted** in the composed record |
| What is missing? | §2–3 | |

## 2. Defects found (ranked)

### D1 (P0, silent corruption): `--payload` mangles raw JSON without warning
`mail compose --payload` parses each value as `key=value` (`cli.py::_key_value_payload`, split on first `=`). Passing a JSON document produced a record whose payload key was everything before the first `=` inside the JSON (`"product != 1"` → key ended at `!`), silently corrupting the packet. Composed record `dad:mail:6af6678c-0ecf-5ca7-9c2a-9a09b146ead3` is a live corrupted specimen (superseded by `dad:mail:71b5d421-…`). Nothing failed; the mangled mail was accepted.

### D2 (P1): no lesson payload schema — the learning rules aren't self-enforcing
Preflight injects `learning-rule:context-bound-lessons-need-non-applicability` (lessons must carry applies_when / does_not_apply_when / danger_if_misapplied) — but compose validates none of it. An agent that skips preflight, or forgets, sends structurally weaker lessons that DAD's own doctrine says are dangerous. The rule exists; the schema to enforce it doesn't.

### D3 (P1): dedupe ledger blind spot
`outbox-check` did not see the pre-existing hand-written outbox record (`sent_count: 0`). Hand-appended fallback mail (explicitly allowed by MAIL_CENTER) is invisible to the near-duplicate check, so the fallback path and the CLI path can double-send forever.

### D4 (P1): supersession lineage not persisted
`--supersedes <mail_id>` was accepted, reused the thread, but the stored record has **no supersedes field** (verified by key inspection). Lineage survives only because I also wrote `supersedes_reason` into the payload by hand. The schema's own guidance ("use supersedes for a true upgrade") cannot be honored by consumers that only read records.

### D5 (P2): mixed encodings in one spool
The repo-local `outbox.jsonl` line 1 carries a UTF-8 BOM (hand-written via PowerShell), later CLI lines don't. Naive `utf-8` readers fail on the whole file. `mail doctor` did not flag it.

### D6 (P2): CLI exits non-zero on success
`agent preflight`/`midflight` returned exit 255 with `status: ok` JSON (Windows shim path). Scripted pipelines can't distinguish success from failure without parsing JSON; worse, PowerShell 5.1 stderr-wrapping makes output look like errors.

### D7 (P2): no forward lifecycle links
No mechanism to attach "lesson X was implemented by PR Y / eval Z now proves it" back to a mail_id. Adoption tracking (`mail triage`, `adoption.jsonl`) covers inbox-side decisions, not source-repo follow-through. Lessons can't graduate on evidence.

### D8 (P3): no push-side asset declaration
A repo creating reusable artifacts (the six kernel docs, the parity-corpus convention, tier-table schema) has no compose affordance to declare them as candidate digital assets with kind/path/consumers — DAD must rediscover them by scan.

## 3. What is genuinely good (keep, don't churn)

Deterministic front door with required read order; append-only candidate doctrine with explicit authority boundaries; the learning-rule injection at preflight (context-bound lessons) is *ahead* of most practice; quarantine/public-release gating; dirty-spool runbooks; the fallback convention for CLI-less repos. None of the fixes below should restructure these.

## 4. Proposed fixes (Codex 5.5-ready, DAD-repo PRs)

### PR-DADM1 — compose input safety (fixes D1, D5, D6; low risk)
- `src/digital_asset_directory/cli.py`: add `--payload-json <path or ->` (mutually exclusive with `--payload`): reads file/stdin, `json.loads` (reject non-object), merges as the payload. In `_key_value_payload`, reject values where the parsed KEY contains `{`, `\n`, or exceeds 128 chars with error "payload looks like raw JSON; use --payload-json".
- Spool IO: read spools with `encoding="utf-8-sig"`, always append plain UTF-8; `mail doctor` gains a BOM/mixed-encoding check over `.digital-asset/mail/*.jsonl` (report-only).
- Exit codes: `agent preflight/midflight/postflight` exit 0 on `status: ok`; nonzero only on failure. Audit the shim (`~/.dad/bin/asset-dir.ps1`) to propagate `$LASTEXITCODE`.
- Tests: compose with JSON file payload round-trips; raw-JSON-as-key rejection message; BOM spool read; doctor BOM finding; exit-code assertions.

### PR-DADM2 — lesson payload schema (fixes D2, flags, classification; medium)
- New `schemas/lesson-payload.schema.json`: required — `problem`, `decision_logic`, `applies_when`, `does_not_apply_when`, `danger_if_misapplied`, `owner_repo`, `classification_labels[]`, `asset_type` (enum: `lesson | reusable_digital_asset | workflow_asset | exception_class_proposal`), plus the eight governance flags as **booleans** (`candidate_only`, `raw_private_payload_included`, `hidden_chain_of_thought_included`, `lake_write_performed`, `sqlite_write_performed`, `external_writes_performed`, `silent_learning_performed`, `dad_review_required_before_promotion`). Optional — `formulas[]`, `alternatives_rejected[]`, `implementation_handoff`, `what_not_to_do`, `future_eval_ref`, `new_assets[] {kind, path, description}` (fixes D8 push-side).
- `mail compose --type lesson_suggestion` validates the payload against it (warning-only for one release, then enforce; flag `--no-payload-validation` for escape).
- Template `templates/mail/lesson-suggestion.mail.template.json`.
- Tests: schema validation matrix; midflight learning-rule + schema agreement test (rule fields == schema-required fields, so the two can't drift).

### PR-DADM3 — dedupe + lineage (fixes D3, D4; low)
- `outbox-check`: also read the target repo's `.digital-asset/mail/outbox.jsonl` (utf-8-sig) and include those packets in the comparison set; report `spool_only_count` separately.
- Persist `supersedes` as an envelope field: add to `schemas/mail-message.schema.json` (optional string), write it in `mail_compose`, and have `mail route`/`digest` render supersession chains.
- Migration note: existing records lack the field; consumers treat absent as "no supersession".
- Tests: outbox-check sees hand-appended record; composed record carries supersedes; digest renders the chain.

### PR-DADM4 — forward lifecycle links (fixes D7; medium)
- New message type is unnecessary — reuse `review_decision`-style follow-up: add `mail follow-up --mail-id <id> --outcome implemented|superseded|invalidated --ref <PR url/commit/eval path>` appending a small linked packet in the same thread; `processed/reports/mail_center.md` gains an "awaiting follow-up" section for lessons older than a configurable age with no lifecycle link.
- Tests: follow-up threading; report section.

Routing note: these are DAD-repo changes. Intake's only action is this audit doc + the candidate mail; intake must not patch DAD's CLI itself.

## 5. Residual risks

- Warning-only phase of PR-DADM2 still admits weak lessons for one release; acceptable to avoid breaking existing senders.
- `outbox-check` reading target spools slightly couples central CLI to repo-local file layout — already a documented convention, so acceptable.
- None of this audits DAD's *review* quality (human side); out of scope for a sender-side audit.
