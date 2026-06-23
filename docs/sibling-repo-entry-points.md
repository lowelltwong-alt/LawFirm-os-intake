# Sibling Repo Entry Points

Last reviewed: 2026-06-23.

This file records the sibling repo front doors that `LawFirm-os-intake` must read before treating a platform surface as available. It is an orientation map, not a source of canonical authority.

## Authority Rule

Semantic Substrate owns canonical schemas, registries, governance, route IDs, event classes, lifecycle policy, AI front door, validation contracts, and skill-agent control-plane membership.

Runtime repos consume those contracts read-only. Intake composes and evaluates a vertical workflow under those contracts.

## Sibling Front Doors

| Repo | Plane | GitHub repo | Required entry points |
|---|---|---|---|
| `LawFirm-os-semantic-substrate` | control | `lowelltwong-alt/LawFirm-os-semantic-substrate` | `AI_START_HERE.md`, `AI_WORK_START_HERE.md`, `AGENTS.md`, `AI_TABLE_OF_CONTENTS.md`, `registry/ai-front-door-registry.json`, `registry/lawfirm-os-repo-registry.json`, `governance/CROSS_REPO_MAP.md`, `manifests/contract_manifest.v1.json` |
| `LawFirm-os-orchestrator` | execution | `lowelltwong-alt/LawFirm-os-orchestrator` | `AI_WORK_START_HERE.md`, `AGENTS.md`, `AI_TABLE_OF_CONTENTS.md`, `DATA_FLOW_MAP.md`, `docs/CANONICAL_ROUTE_MAPPING.md`, `contracts.lock.json` |
| `LawFirm-os-exceptions-lake-runtime-main` | evidence | `lowelltwong-alt/LawFirm-os-exceptions-lake-runtime` | `AI_WORK_START_HERE.md`, `AGENTS.md`, `AI_TABLE_OF_CONTENTS.md`, `DATA_FLOW_MAP.md`, `docs/RUNTIME_BOUNDARY.md`, `docs/CANONICAL_ROUTE_MAPPING.md`, `contracts.lock.json` |
| `LawFirm-os-legal-knowledge-runtime` | legal knowledge runtime | `lowelltwong-alt/LawFirm-os-legal-knowledge-runtime` | `AI_WORK_START_HERE.md`, `AGENTS.md`, `README.md`, `skill-agent-manifest.json`, `contracts.lock.json` |
| `LawFirm-os-skills-registry` | skill supply chain | `lowelltwong-alt/LawFirm-os-skills-registry` | `AI_WORK_START_HERE.md`, `AGENTS.md`, `README.md`, `skill-agent-manifest.json`, `registry/approved-skills.json`, `registry/skill-agent-local-registry.json` |

## Intake Consumption Posture

| Need | Owning repo | Intake behavior |
|---|---|---|
| Canonical party roles, matter families, event classes, route IDs, schema promotion | Semantic Substrate | Consume pinned contracts; keep local copies candidate-only |
| Workflow execution, gates, model/tool routing, human pauses, evidence packet assembly | Orchestrator | Keep local CLI as reference until runtime mechanics are promoted |
| Exception/admission/audit persistence | Exception Lake Runtime | Emit evidence packets or dry-run candidates; do not own storage |
| Legal source integrity, passage refs, claim refs, context bundles | Legal Knowledge Runtime | Use refs, hashes, and bundles instead of raw payload fanout |
| Reusable specialist skills and trust records | Skills Registry | Use approved/predeclared specialists or draft candidate proposals only |

## Current Lock Sources

The initial seed lock uses the live public `main` SHAs captured on 2026-06-23. These pins are a bootstrap guardrail, not proof that a full cross-repo promotion review has occurred.

Use `contracts.lock.json` and `repo_topology.lock.yaml` for the current values.

## Stop Conditions

Stop before integration work if:

- a sibling repo pin is missing or floating;
- a local candidate conflicts with pinned canon;
- a requested event class or route ID is not registered by Semantic Substrate;
- a run would ingest real client, matter, privileged, or confidential data;
- an intake output would clear conflicts, accept a client, docket a deadline, open a matter, or submit a budget.
