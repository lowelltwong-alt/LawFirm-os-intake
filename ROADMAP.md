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
- FJC Integrated Database field mapping;
- Enron email structural parser stress tests;
- source/license/privacy/retention review templates;
- planning-only public-source methodology audit;
- planning-only conversion specs for public structures to non-identifying synthetic fixtures;
- human review packet with recommendations, why-notes, red-team checks, and decision templates;
- approved process for creating those fixtures in a separate reviewed PR.

Exit criteria:

- public source catalog is complete and reviewed;
- methodology audit passes with direct runtime ingestion and adapter authorization still disabled;
- synthetic fixture conversion plan is ready for human review with red-team checks and no fixture mutation;
- conversion review packet is ready for human decision with no fixture PR creation or silent learning;
- human conversion review outcome is recorded append-only before any fixture PR is prepared;
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

## Deferred enterprise capabilities

- durable multi-day workflow runtime;
- approved iManage read adapter;
- approved conflicts-system integration;
- approved budget-system/carrier portal connector;
- event-driven execution;
- rich multi-user review UI;
- graph database/GraphRAG only after measured need.
