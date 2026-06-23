# Governance Boundary

This repository must never invert the LawFirm OS authority order.

## Candidate lifecycle

Local schemas, taxonomies, worker manifests, prompts, and templates are experimental candidates. They become platform-authoritative only through the owning sibling repository and its promotion process.

## Promotion targets

| Candidate | Promotion target |
|---|---|
| party/matter/context/budget schema or registry | Semantic Substrate |
| workflow runtime, approval pause, adapter, gate | Orchestrator |
| correction/defect/run event | Exception Lake Runtime |
| reusable worker/prompt | Skills Registry |
| legal/public evidence adapter/context bundle | Legal Knowledge Runtime |

## Prohibited governance behavior

- no direct mutation of sibling repositories from an intake run;
- no local redefinition of a pinned canonical value;
- no model-generated promotion decision;
- no consensus-by-agent-volume;
- no silent profile/template updates from one correction;
- no permission expansion in prompts.
