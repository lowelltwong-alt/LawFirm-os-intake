# CourtListener Early-Case Dataset Strategy

## Purpose

This repo should learn public legal document structure before it learns from any real firm matter. The first public-derived corpus is a CourtListener/RECAP early-case corpus for labor and employment intake-stage documents.

The corpus is for evaluation and fixture design only. It is not a production ingestion pipeline, a training pipeline, a conflicts system, a budget-accuracy proof, or a source of law-firm actuals.

## Default Source Mode

`config/courtlistener-dataset-strategy.yaml` is the local candidate source profile.

Defaults:

- offline fixture mode is on;
- live calls are off;
- PACER purchasing is off;
- RECAP Fetch purchase flow is off;
- uploads are off;
- court writes are off;
- sealed or restricted requests are off;
- real-client and privileged data are off.

The audit command is:

```bash
python -m lawfirm_os_intake.cli audit-courtlistener-dataset-strategy --repo-root . --out-dir .lawfirm-os-intake/courtlistener-dataset-strategy
```

It writes `courtlistener_dataset_strategy_report.json` and a Markdown report. A passing report means the strategy is ready for human review, not that data has been ingested.

The first offline fixture shape lives under `examples/synthetic/courtlistener-derived/`:

- `labor-employment-removal-snapshot.json` is a synthetic CourtListener-style removal docket snapshot;
- `labor-employment-dataset-manifest.json` binds document-stage, conflict-seed, budget-driver, and person-timeline labels to exact synthetic source spans.

Audit it with:

```bash
python -m lawfirm_os_intake audit-courtlistener-fixture --repo-root . --manifest examples/synthetic/courtlistener-derived/labor-employment-dataset-manifest.json --out-dir .lawfirm-os-intake/courtlistener-fixture
```

A passing fixture audit proves only that the local synthetic fixture is source-bound, offline, early-case, and reviewable. It does not approve public-data collection, training, or budget accuracy.

## First Corpus

Start with labor and employment:

- single-plaintiff employment discrimination;
- retaliation;
- FMLA;
- ADA employment;
- single-plaintiff wage-and-hour / FLSA.

Class action, collective action, MDL, mass tort, and high-dollar exposure are Tier 3 escalation flags, not the starter corpus.

## Positive Intake-Stage Examples

Positive document-type examples stay in the first 90-120 days of docket activity and include startup documents such as complaints, summons, notices of removal, civil cover sheets, answers, early motions, early scheduling orders, right-to-sue letters, EEOC charges, and contract/policy attachments when already attached to public filings.

Post-discovery, dispositive, trial, post-judgment, appellate, and fee documents are not positive intake-stage examples. They may be retained only as negative or routing examples in synthetic/public-derived evaluation plans.

## Removal Proxy

The `courtlistener_removal_state_pleadings_proxy` profile uses federal removal dockets to model state-court starter pleadings when those pleadings are already attached to public RECAP material.

This does not authorize direct state-court scraping. Direct state-court work starts later with manual/snapshot profiles and source-terms review.

## Labels

Every future label must preserve:

- source document ID;
- source segment ID;
- source span;
- hash/provenance refs;
- labeler and review state;
- uncertainty.

Labels can train or evaluate document recognition, chronology, party/counsel extraction, conflict-search seed extraction, claims/damages/procedural posture extraction, budget-driver recognition, person timelines, and contradiction candidates.

Labels cannot establish negotiated rates, carrier guidelines, true law-firm costs, budget accuracy, settlement authority, conflict clearance, matter opening, or approved budgets.

The starter fixture intentionally includes one later deposition notice as a negative/routing example. The audit fails if that post-discovery document leaks into the positive intake-stage corpus.

## Rust Posture

Rust can later help with deterministic corpus mechanics: snapshot normalization, manifest indexing, hashing, duplicate detection, source-span indexing, and label-offset indexing.

Rust may not decide legal meaning, admit a training corpus, assign roles, clear conflicts, open matters, docket deadlines, approve or submit budgets, persist Exception Lake records, or promote learning.

The Python reference outputs remain the parity oracle until profiling and golden tests justify a separate Rust adapter.
