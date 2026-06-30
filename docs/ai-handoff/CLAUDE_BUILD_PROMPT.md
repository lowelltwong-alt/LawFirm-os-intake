# Claude Build Prompt

Use this with Claude Code in plan mode.

```text
You are working in lowelltwong-alt/LawFirm-os-intake.

Read, in order:
- AI_WORK_START_HERE.md
- REPO_ROLE.md
- NON_GOALS.md
- AGENTS.md
- CLAUDE.md
- docs/architecture.md
- docs/workflow/intake-to-budget.md
- docs/lawfirm-os-integration.md
- PREMORTEM.md
- DEFINITION_OF_DONE.md
- docs/ai-handoff/FIRST_10_PRS.md

First run:
- python -m pip install -e ".[dev]"
- python scripts/export_schemas.py
- python scripts/run_full_pytest.py
- bash scripts/smoke_demo.sh

Use config/validation-runtime-policy.yaml for local command ceilings. Full and focused pytest and smoke runs require a 1800 second ceiling.

Task:
Assess the current repository against the starter definition of done. Produce a PR-sized plan for the smallest next improvement to source inventory and provenance-preserving email segmentation.

Hard constraints:
- synthetic data only;
- no network or external connector;
- no Semantic Substrate canon invention;
- no conflict clearance, engagement, deadline docketing, matter opening, iManage write, email send, or budget submission;
- practice context is a prior, not evidence;
- carrier/payer/instructing source is not automatically the represented client;
- human confirmation remains mandatory before budget generation;
- no dynamic agents;
- structured typed outputs and exact evidence refs required.

Return:
1. current-state findings;
2. proposed files to change;
3. exact acceptance tests;
4. risks and non-goals;
5. decision trace;
6. cross-repo promotion implications.

Use permission mode plan and read-only tools. Do not edit until the plan is reviewed.
```
