# AI Table of Contents

| Need | Read |
|---|---|
| Understand the repo | `README.md`, `REPO_ROLE.md`, `NON_GOALS.md` |
| Understand authority | `skill-agent-manifest.json`, `repo_topology.yaml`, `contracts.lock.json`, `docs/sibling-repo-entry-points.md`, `docs/lawfirm-os-integration.md` |
| Understand governance-map mirror | `.ai/control/governance-dependency-map-mirror.json`, `scripts/validate_governance_dependency_map_mirror.py`, upstream governance dependency map |
| Understand real-work shadow gate | `docs/real-work-shadow-mode-readiness.md`, upstream Substrate real-work shadow-mode gate |
| Build code | `AGENTS.md`, `docs/ai-handoff/BUILDER_BRIEF.md`, `docs/ai-handoff/FIRST_10_PRS.md` |
| Use Claude | `CLAUDE.md`, `docs/claude-agent-sdk-operating-contract.md`, `docs/claude-for-legal-lessons.md` |
| Understand workflow | `docs/workflow/intake-to-budget.md`, `workflow/intake-to-budget.workflow.yaml` |
| Understand practice context | `docs/practice-context.md`, `config/context_precedence.yaml` |
| Understand specialists | `docs/agent-architecture.md`, `agents/`, `prompts/`, `harnesses/` |
| Understand chunking/graph | `docs/chunking-and-evidence-graph.md` |
| Understand budgets | `docs/legal-budget-design.md`, `templates/legal-budget-review-form.md`, `docs/carrier-rejection-learning-loop-roadmap.md` |
| Understand owner handoffs | `DATA_FLOW_MAP.md`, `ENDPOINTS_AND_COMMANDS.md`, `promotion/cross_repo_promotion_package.json` |
| Understand human gates | `docs/human-review.md`, `config/human_gates.yaml` |
| Understand testing and public data | `docs/evaluation-plan.md`, `docs/public-data-test-plan.md`, `docs/synthetic-data-plan.md`, `docs/data/courtlistener-early-case-dataset-strategy.md` |
| Understand review UI drop-in | `apps/legal-intake-budget/README.md`, `apps/legal-intake-budget/CLAUDE_DESIGN_BRIEF.md`, `apps/legal-intake-budget/src/data-contract.ts` |
| Understand Rust readiness | `docs/rust-ingestion-transition-plan.md`, `config/rust-tool-ladder.json`, `docs/decisions/ADR-004-rust-ready-ingestion-boundary.md` |
| Understand failure risk | `PREMORTEM.md`, `THREAT_MODEL.md` |
| Know completion criteria | `DEFINITION_OF_DONE.md`, `ROADMAP.md`, `BUILD_VERIFICATION.md` |

<!-- BEGIN DIGITAL_ASSET_DIRECTORY_TOC_ROWS -->
| Path | What It Is | Tags | Use When |
| --- | --- | --- | --- |
| `.digital-asset/dad-integration.json` | Versioned DAD enrollment contract and approved write boundary. | dad, enrollment, governance | Confirm DAD cadence, control planes, approval IDs, and managed paths. |
| `.digital-asset/context-map.json` | Repo context to DAD asset/control-plane route map. | dad, context, assets | Choose relevant DAD assets, skills, templates, or architecture references for a task. |
| `.digital-asset/governance-map.yaml` | Repo-local governance dependency mirror. | governance, authority, dependencies | Check local authority boundaries and DAD-managed surfaces. |
| `.digital-asset/data-map.yaml` | Repo-local sensitive-boundary and data-movement map. | data-map, privacy, release | Check what data can move through DAD mail or public-facing release paths. |
| `.digital-asset/mail/` | Candidate-only DAD inbox/outbox/archive. | mail, suggestions, daily | Read or send cross-repo suggestions without mutating source authority. |
| `.digital-asset/assets/index.jsonl` | Repo-local metadata-only digital asset cards using compact DAD address layers. | assets, address-model, learning | Record source-owned asset pointers, workflow refs, validation refs, and learning deltas without copying private content. |
<!-- END DIGITAL_ASSET_DIRECTORY_TOC_ROWS -->
