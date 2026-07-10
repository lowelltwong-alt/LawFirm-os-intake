# Governance Boundary

This repository must never invert the LawFirm OS authority order.

## Governance dependency-map mirror

This repo carries `.ai/control/governance-dependency-map-mirror.json` as a local mirror of the upstream governance dependency map in `LawFirm-os-semantic-substrate/registry/governance-dependency-map.json`.

If governance-facing intake files change, check the upstream governance dependency map and update the local mirror, AI work router, AI table of contents, README, validator, and tests when affected. The mirror is downstream enforcement only; it cannot override Semantic Substrate governance or convert intake workflow convenience into platform authority.

## Real-work shadow-mode gate

`docs/real-work-shadow-mode-readiness.md` mirrors the Substrate real-work
shadow-mode gate for Intake. It does not authorize a pilot. Intake remains
synthetic-only until the owner, attorney reviewer, privacy reviewer, compliance
reviewer, and Substrate governance record an explicit decision.

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
| qualitative lesson payload shape | DAD receiver review, then Semantic Substrate review if proposed as shared canon |
| lesson disclosure runtime gate or publication-snapshot authority | Orchestrator |

## Prohibited governance behavior

- no direct mutation of sibling repositories from an intake run;
- no local redefinition of a pinned canonical value;
- no model-generated promotion decision;
- no consensus-by-agent-volume;
- no silent profile/template updates from one correction;
- no permission expansion in prompts.
