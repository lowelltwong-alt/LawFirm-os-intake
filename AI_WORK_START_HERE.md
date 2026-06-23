# AI Work Start Here

This file is the required front door for any AI assistant, coding agent, or human builder.

## Mission

Build a governed prospective-matter intake vertical that can transform heterogeneous inbound material into a source-bound intake preflight packet, obtain human confirmation, prepare a conflict-search seed, and produce a reviewable legal budget proposal.

The workflow must remain subordinate to LawFirm OS authority boundaries.

## Required reading order

1. `README.md`
2. `REPO_ROLE.md`
3. `NON_GOALS.md`
4. `skill-agent-manifest.json`
5. `repo_topology.yaml`
6. `contracts.lock.json`
7. `docs/sibling-repo-entry-points.md`
8. `docs/lawfirm-os-integration.md`
9. `docs/architecture.md`
10. `docs/workflow/intake-to-budget.md`
11. `docs/practice-context.md`
12. `docs/agent-architecture.md`
13. `docs/chunking-and-evidence-graph.md`
14. `docs/legal-budget-design.md`
15. `docs/human-review.md`
16. `docs/claude-for-legal-lessons.md`
17. `PREMORTEM.md`
18. `THREAT_MODEL.md`
19. `DEFINITION_OF_DONE.md`
20. `docs/ai-handoff/BUILDER_BRIEF.md`

## Authority rules

- Semantic Substrate owns canonical meaning.
- Orchestrator owns execution mechanics.
- Exception Lake owns append-only runtime evidence.
- Skills Registry owns governed skill promotion and trust state.
- Legal Knowledge Runtime owns bounded legal evidence retrieval.
- This repo owns the vertical specification, fixtures, evaluations, and reference composition only.

When files disagree, stop and resolve the conflict against the pinned Semantic Substrate contract and its cross-repo authority map.

## Work modes

### Explore

Read-only analysis. Do not edit. Produce questions, risks, and file references.

### Plan

Produce a PR-sized implementation plan with acceptance tests and authority impact. Do not edit unless authorized.

### Build

Implement one approved slice. Keep changes bounded. Do not add connectors, new authority planes, or dynamic agents.

### Validate

Run deterministic tests, inspect evidence packets, and compare end states. Do not claim improvement from changed evaluators or changed corpora.

### Review

Check semantic authority, evidence completeness, human gates, data scope, prompt/tool permissions, and prohibited transitions.

## Immediate stop conditions

Stop the task when:

- real client, matter, or privileged data appears;
- a task asks this repo to create platform canon;
- a model is asked to clear conflicts, accept a client, docket a deadline, open a matter, or submit a budget;
- a party or classification lacks an exact source reference;
- practice context is being used as evidence;
- a connector or external write is introduced without an approved platform contract;
- a prompt or agent manifest expands authority;
- sibling repo pins are missing or floating;
- evaluation data contains answer leakage or real confidential information;
- the requested PR mixes documentation/evaluation changes with high-risk output changes without separate review.

## First builder objective

Preserve and harden the existing local demo before adding model providers:

```bash
python -m pip install -e ".[dev]"
python scripts/validate_repo.py
python scripts/export_schemas.py
python -m pytest
bash scripts/smoke_demo.sh
```

A successful run ends in `blocked_pending_conflicts_and_engagement`. That is expected and correct.
