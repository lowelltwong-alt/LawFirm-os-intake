# Build Verification

Verified in the artifact build environment on 2026-06-24:

```text
PYTHONPATH=src python scripts/export_schemas.py
# exported 27 schemas

PYTHONPATH=src python scripts/validate_repo.py
# repository validation passed

PYTHONPATH=src python -m pytest -q
# 78 passed

PYTHONPATH=src ruff check src tests scripts
# All checks passed

PYTHONPATH=src ruff format --check src tests scripts
# 55 files already formatted

PYTHONPATH=src bash scripts/smoke_demo.sh
# completed without error and wrote budget/starter_release_audit_report.json
```

The monetary result is a synthetic test calculation, not a fee quote or approved budget.

The smoke demo now also writes `starter_release_audit_report.json` after the north-star demo finishes. That report is a local, non-authoritative starter release audit over generated artifacts; it fails if required outputs, synthetic-only scope, source-bound evidence refs, human gates, carrier/client separation, conflict/budget boundaries, dry-run Exception Lake posture, safety boundary, fixture-gold gates, run ledgers, candidate-registry noncanonical status, or Rust-readiness posture drift.

The current demo also emits local `exception_lake_candidates.jsonl` files in preflight and budget outputs. These are dry-run candidates only; they are not canonical Exception Lake admissions and include no raw legal payload.

The preflight output now includes `contract_state_report.json`, which verifies the reviewed local sibling-repo lock state before source processing. The report is carried forward into the final review manifest and safety gate.

Source-bound evidence references now include segment offsets as well as source ID, segment ID, and hash. Strict evidence validation fails if a ref drifts from the cited segment.

Party-role alternatives now carry their own source-bound evidence refs, render in the intake review form, and appear as supported candidate nodes in the evidence graph.

ADR-004 records the Rust-ready ingestion boundary for future high-volume or constrained-compute document processing. Python remains the reference implementation until any Rust adapter proves golden parity.

Preflight runs now emit `ingestion_result.json` as the Python reference parity oracle for source inventory, coverage summary, segments, and segment-level evidence refs.

Preflight runs now emit `ingestion_volume_profile.json`, a deterministic source/segment scale report that can require profiling before any future Rust adapter proposal while keeping `rust_replacement_allowed=false`.

Preflight runs now also emit `rust_ingestion_readiness_report.json`, proving the Python ingestion artifact is a valid future Rust parity target while keeping `rust_replacement_allowed=false`.

The preflight intake review form now renders detailed source inventory fields and explicit review outcome handling, including the fact that only confirmed outcomes can advance toward the budget precondition gate and that corrections append or supersede rather than silently mutating history.

The budget stage now emits `budget_precondition_report.json`; failed confirmation attempts write this report, a blocked ledger event, and a dry-run Exception Lake candidate before any proposal output is created. The gate requires the human confirmation to be matching, confirmed, and evidence-bound.

The budget output now includes `matter_opening_review_package.md` and `review_package_manifest.json` as the consolidated review surface for the north-star demo.

Budget runs now also emit `review_package_completeness_report.json`, proving the final review package has required artifacts, review sections, human gates, blockers, safety proof, dry-run Exception Lake readiness, run ledgers, and non-authorization boundary flags before the package is accepted.

The completeness report now also verifies that linked intake and budget review forms preserve their required human-review sections, evidence-hash visibility where source-bound evidence exists, and non-authorization boundary text, including source coverage, outcome handling, budget lines, support items, and submission boundary.

Human-facing review Markdown now renders evidence refs inline for confirmation evidence, confirmed parties, deadlines, missing-information candidates, critic findings, conflict-search terms, and budget supports.

Those reviewer-facing evidence refs now include source IDs, segment IDs, offsets, and hashes, so the final package exposes the full source-bound pointer without requiring JSON inspection first.

The final matter-opening review package now includes a candidate-alternatives section for inbound-event, matter-family, representation-posture, and party-role candidates, and package completeness requires that section.

The final matter-opening review package now includes a required-human-gates section for conflicts clearance, engagement authorization, budget review, and matter-opening authorization, and package completeness requires that section.

The final matter-opening review package now includes calculation summary, budget line, and budget support subsections, and package completeness requires those budget detail sections.

The standalone legal budget review form now includes itemized budget lines and a submission-boundary section so budget reviewers can inspect hours, rates, synthetic-rate labels, fees, expenses, assumptions, evidence refs, and non-authorization state without opening JSON first.

The final matter-opening review package now includes source-inventory detail and a run-ledger summary, and package completeness requires those auditability sections.

The final matter-opening review package now includes an evidence-graph summary with node/edge counts, node-type counts, relationship counts, and key provenance edge examples; package completeness requires that section.

The final matter-opening review package now includes authority and precondition subsections for contract-state status, human-review outcome, and budget precondition checks; package completeness requires those sections.

The final matter-opening review package now includes Exception Lake readiness and exception candidate detail subsections showing dry-run posture, raw-payload exclusion, promotion requirement, target runtime repo, and support refs; package completeness requires those sections.

Exception candidate detail evidence refs now render source IDs, segment IDs, offsets, and hashes inline, matching the rest of the reviewer-facing evidence surface.

Budget runs now write `human_review_outcome.<confirmation_id>.json` and append it to `human_confirmation_history.jsonl` before budget preconditions run. Non-confirmed review outcomes remain blocked, and superseding corrections append new history rows instead of mutating prior outcomes.

Budget assumptions, exclusions, and unknowns now emit `budget_support_items` with evidence refs or structured refs for human review.

The budget-stage evidence graph now includes human review outcome, conflict seed packet, conflict-search term, budget line, budget support item, and structured-ref nodes with source-backed or structured-ref support edges.

Budget uncertainty now emits dry-run Exception Lake candidates for proposal unknowns, missing approved synthetic budget templates, and hours-only missing-rate states. These candidates may carry structured refs and still include no raw payload.

Unread sources now count as explicit source coverage gaps, render in review summaries, and emit `source_unread` dry-run `retrieval_miss` candidates.

Exception Lake candidate files now emit `exception_lake_readiness_report.json`, proving dry-run posture, raw-payload exclusion, promotion-required status, target runtime repo, and source/evidence ref integrity before future Lake handoff.

The budget output also includes `safety_gate_report.json`; a failed safety check raises before the final review package is accepted.

The smoke demo runs the messy north-star synthetic fixture, not the clean carrier-only fixture.

Conflict-search seed packets now require every normalized search term to carry source-bound evidence refs from the human confirmation. The packet remains a search seed only and preserves `no_conflict_conclusion`.

The safety gate now independently verifies evidence completeness for conflict-search terms, budget lines, budget support items, and proposal-level assumptions, exclusions, and unknowns before accepting the final review package.

## GitHub seed verification

Verified on 2026-06-23:

```text
origin/main: 4d3d67b0324c59aba90f9a3100dc082f19f8b84a
GitHub Actions ci run: 28054850346
status: success
```
