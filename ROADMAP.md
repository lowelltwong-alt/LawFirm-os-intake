# Roadmap

Roadmap items are organized by bottleneck and governance maturity, not by feature count.

## Phase 0 — Starter and architecture lock

**Goal:** another AI can understand the repository, run the demo, and identify authority boundaries without prior conversation context.

Deliverables:

- AI front doors and builder brief;
- executable synthetic demo;
- practice profiles;
- candidate schemas;
- worker manifests;
- premortem and threat model;
- tests and CI;
- five-repo integration map.

Exit evidence:

- all tests pass;
- demo produces preflight, confirmation, conflict seed, budget, readiness, evidence graph, and ledger;
- no external connector or real data path exists.

## Phase 1 — Intake preflight quality

**Bottleneck:** reviewer time spent reconstructing sources and correcting party/matter candidates.

Build:

- stronger email and correspondence segmentation;
- duplicate and quoted-message handling;
- attachment inventory states;
- deterministic source coverage report;
- improved party alias normalization;
- human review form/TUI prototype;
- hidden synthetic holdout set.

Exit criteria:

- every candidate has a valid evidence ref;
- top-three matter-family recall meets attorney-reviewed threshold on synthetic holdout;
- reviewer can select `unknown` and alternatives;
- no carrier/client role collapse.

## Phase 2 — Public-source methodology, still no live case ingestion

**Bottleneck:** synthetic fixtures may not represent real document structures.

Build:

- CourtListener/RECAP metadata mapping;
- CourtListener early-case dataset strategy with offline fixture mode, live calls disabled, no PACER/RECAP Fetch purchase path, and labor/employment as the first corpus;
- removal-packet state-court starter-pleading proxy profile for already-available RECAP material;
- dataset label strategy for document type, case stage, conflict seed roles, budget drivers, person timelines, contradictions, and risk tier;
- offline synthetic CourtListener-style snapshot and dataset manifest with source-bound document, conflict, budget-driver, and timeline labels;
- Rust shadow-acceleration boundary for deterministic corpus mechanics only, with no Rust runtime until profiling and parity justify it;
- FJC Integrated Database field mapping;
- Enron email structural parser stress tests;
- source/license/privacy/retention review templates;
- planning-only public-source methodology audit;
- planning-only conversion specs for public structures to non-identifying synthetic fixtures;
- human review packet with recommendations, why-notes, red-team checks, and decision templates;
- approved process for creating those fixtures in a separate reviewed PR.

Exit criteria:

- public source catalog is complete and reviewed;
- `audit-courtlistener-dataset-strategy` passes with offline fixture mode, purchase/upload/write paths disabled, and Rust replacement unauthorized;
- `audit-courtlistener-fixture` passes on the synthetic labor/employment removal snapshot while blocking hash drift and post-discovery positive-corpus leaks;
- `audit-labor-employment-budget-facts` produces a source-bound fact-gap report and blocks precise budget posture when critical L&E facts such as party/entity relationships, claims, damages, ESI, depositions, experts, or carrier/rate context are missing;
- methodology audit passes with direct runtime ingestion and adapter authorization still disabled;
- synthetic fixture conversion plan is ready for human review with red-team checks and no fixture mutation;
- conversion review packet is ready for human decision with no fixture PR creation or silent learning;
- human conversion review outcome is recorded append-only before any fixture PR is prepared;
- manual fixture PR package preserves allowed inputs, forbidden inputs, identity rules, gold checks, and red-team checks without editing fixtures;
- no copyrighted bulk corpus is committed;
- no real public party data enters runtime fixtures;
- provenance and transformation method are documented.

## Phase 3 — Practice Context Foundation promotion

**Bottleneck:** profiles and taxonomies remain local candidates.

Promote through Semantic Substrate:

- firm/practice/source/matter context schemas;
- context precedence;
- party-role registry;
- matter-family registry;
- intake-source registry;
- human-confirmation contract;
- intake boundary doctrine.

Update this repo to consume pinned promoted contracts and remove shadow copies.

## Phase 4 — Orchestrator and Skills integration

**Bottleneck:** reference workers are local mocks rather than governed runtime skills.

Promote:

- intake workflow runner and approval pause to Orchestrator;
- source reader, party extractor, router, deadline/gap extractor, evidence critic, and budget planner to Skills Registry;
- model-class routing and tool permissions;
- Claude Agent SDK adapter with hooks and budgets;
- local-small-model adapters and evals.

Exit criteria:

- one outer Orchestrator owns execution;
- workers are predeclared and revocable;
- no dynamic agent creation;
- typed handoffs and run ledger are enforced.

## Phase 5 — Exception Lake and Legal Knowledge integration

**Bottleneck:** corrections and legal/public context are not yet platform-native.

Build:

- intake proposal/correction/escalation event contracts;
- context-defect and profile-change candidates;
- Legal Context Bundle for intake;
- bounded public-source lookup adapter;
- evidence packet validation and append-only persistence.

## Phase 6 — Budget hardening

**Bottleneck:** budget templates may create false precision or miss client/carrier requirements.

Build:

- promoted budget proposal schema;
- authorized private profile store for rates/guidelines;
- hours-only and priced modes;
- phase/task template review workflow;
- UTBMS/LEDES mapping as optional reference adapter;
- budget variance and assumption tracking;
- pricing professional/partner approval workflow.

Exit criteria:

- no rate invention;
- deterministic calculations;
- guideline source and version recorded;
- budget submission remains a separate approved tool/action.

## Phase 7 — Approved real-data pilot

This phase requires a separate governance decision. Preconditions include confidentiality and vendor review, retention controls, matter isolation, access authorization, secure transcript/artifact storage, human oversight, incident response, and a reviewed pilot protocol.

Initial real-data mode should be read-only, narrow, and shadow-mode. No external writes.

## Phase 8 — Governed predictive budget challenger

**Bottleneck:** deterministic templates remain reproducible but may not capture
empirical cost, duration, variance, and carrier-response patterns present in
reviewed historical outcomes.

XGBoost is a candidate challenger model for phase/task hours and cost ranges,
budget-overrun risk, and carrier rejection or appeal-outcome risk. It does not
own budget arithmetic, invent rates or facts, approve a budget, or silently
change a profile or template.

Do not begin model training until Phase 7 governance approves the exact data use
and a sufficiently representative set of reviewed budget, actual, rejection,
appeal, jurisdiction, and matter-outcome records exists. Synthetic fixtures may
validate feature shapes, pipeline behavior, safety gates, and evaluation code;
they may not establish predictive accuracy or calibration.

Required activation evidence:

- a versioned feature/target contract with provenance and post-outcome leakage
  exclusions;
- immutable training/evaluation snapshot manifests, hashes, retention terms,
  and authorized-use records;
- matter-grouped temporal splits and untouched holdouts;
- comparison against the deterministic budget baseline and simple statistical
  baselines using predeclared error, interval-coverage, calibration, subgroup,
  and stability thresholds;
- model card, hyperparameter and seed record, feature-importance/SHAP review,
  drift plan, reproducible build, and rollback artifact;
- human approval for shadow use, followed by a separately approved advisory
  pilot with the deterministic engine retained as fallback.

Intake may own candidate feature contracts, offline evaluation fixtures, and
comparison reports. Orchestrator owns runtime invocation and human pauses;
Exception Lake owns reviewed outcome evidence; Legal Knowledge Runtime owns
governed external benchmark evidence; Semantic Substrate and Skills Registry
own promoted meaning and model/skill trust state.

Exit criteria:

- the challenger materially improves predeclared holdout metrics without
  unacceptable subgroup or temporal degradation;
- every prediction records model/data versions, feature provenance, range or
  risk calibration, limitations, and deterministic-baseline comparison;
- incomplete or out-of-distribution matters widen, abstain, or fall back rather
  than receive false precision;
- no model output can rewrite deterministic line math, clear conflicts, open a
  matter, submit a budget, or trigger external writes;
- continued use is conditional on monitored drift and periodic reviewed
  revalidation.

## Deferred enterprise capabilities

- durable multi-day workflow runtime;
- approved iManage read adapter;
- approved conflicts-system integration;
- approved budget-system/carrier portal connector;
- event-driven execution;
- rich multi-user review UI;
- graph database/GraphRAG only after measured need.
