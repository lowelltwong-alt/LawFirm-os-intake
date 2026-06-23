# LawFirm OS Integration Contract

For current sibling AI front doors, file paths, and validation commands, read `sibling-repo-entry-points.md` first.

## Platform relationship

### Semantic Substrate

Consume read-only:

- canonical repo/authority map;
- intake-source types;
- party-role registry;
- matter-family and posture registry;
- practice-profile and effective-context schemas;
- human confirmation and approval doctrine;
- evidence packet and run-record contracts;
- budget proposal contract and external taxonomy mappings;
- tool/model/prompt authority.

Do not create platform canon here. Local schemas are candidate scaffolds.

### Orchestrator

Move runtime mechanics there when ready:

- workflow state machine;
- data-origin gate;
- context resolution;
- worker selection;
- model/tool budgets;
- human pause/resume;
- authorization/revocation;
- evidence assembly;
- Exception Lake invocation.

The intake repo retains vertical tests and reference fixtures.

### Exception Lake Runtime

Future events:

- intake_preflight_proposed;
- intake_classification_confirmed;
- intake_classification_corrected;
- party_role_corrected;
- practice_context_missing_or_misleading;
- escalation_triggered;
- conflict_seed_prepared;
- budget_proposal_created;
- budget_proposal_corrected;
- profile_change_candidate.

All are runtime evidence or proposals. None mutates canon directly.

### Skills Registry

Promote each reusable worker only after:

- source and license review;
- static and semantic security scan;
- input/output schemas;
- accepted/forbidden contexts;
- tool/data authority;
- task eval suite;
- reviewer and approval state;
- version, provenance, and revocation metadata.

### Legal Knowledge Runtime

Use for bounded evidence retrieval and Legal Context Bundles:

- jurisdiction reference;
- court/public metadata;
- approved practice guidance;
- source currency and authority;
- citation/provenance.

Legal Knowledge Runtime provides evidence and context, not final legal conclusions or authority to act.

## Pin discipline

Before integration, replace `contracts.lock.example.json` with a reviewed lock containing immutable SHAs for all five repos. Adoption of a sibling change is explicit and tested.

## Cross-repo tests

- contract manifest resolves;
- schemas are compatible;
- candidate values map to registered canon;
- worker skill versions are approved;
- Exception Lake accepts only supported evidence envelopes;
- Legal Context Bundle source refs resolve;
- no repo inverts the authority order.
