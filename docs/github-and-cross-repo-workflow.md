# GitHub and Cross-Repo Workflow

The intended remote is `https://github.com/lowelltwong-alt/LawFirm-os-intake`.

## GitHub-connected coding agent posture

A GitHub-connected AI may read sibling repositories and prepare branches/PRs. It must not treat repository access as legal or semantic authority.

## Required sequence

1. Read this repo's AI front door.
2. Read the pinned sibling entry points at their reviewed commits.
3. Create a decision trace and PR-sized plan.
4. Work on a branch; do not write directly to protected `main`.
5. Keep changes in the correct owning repo.
6. Run repo-local and cross-repo contract tests.
7. Open a PR with authority impact, tests, fixtures, and rollback.
8. Update pins here only after the sibling PR is reviewed and merged.

## Cross-repo change rule

Do not bundle independent high-risk changes across all repos into one opaque task. Use coordinated PRs with explicit dependency order:

```text
Semantic Substrate contract PR
→ Skills/Legal Knowledge/Exception Lake adoption PRs as needed
→ Orchestrator runtime adoption PR
→ Intake vertical pin and end-to-end regression PR
```

## Claude for Legal lessons applied

- shared organization context, practice context, and matter context are separate;
- cold-start/customization workflows create profiles rather than burying context in prompts;
- current matter state and append-only history are distinct;
- connectors declare capabilities and fallbacks;
- reader/analyzer/writer authority is separated;
- every output remains attorney-reviewable.
