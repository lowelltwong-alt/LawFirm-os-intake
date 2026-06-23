# Claude Operating Contract

This file adapts the Claude Agent SDK loop to LawFirm OS boundaries.

## The loop

Claude may evaluate state, request a permitted tool call, receive a result, and continue until it emits a terminal result. LawFirm OS—not the model—owns the workflow contract, permissions, budgets, stop conditions, and legal authority.

Read `docs/claude-agent-sdk-operating-contract.md` before using Claude Code or the Agent SDK.

## Preserve during compaction

Always preserve:

- current task objective;
- acceptance criteria;
- authority and contract pins;
- files read or modified;
- source/evidence references;
- tests run and exact results;
- decisions made and alternatives rejected;
- open risks and unresolved questions;
- human-review requirements;
- prohibited actions;
- current PR boundary.

## Default tool posture

For architecture and planning:

```text
permission mode: plan
allowed tools: Read, Glob, Grep
network: off unless research was explicitly authorized
writes: none
```

For an approved implementation PR:

```text
allowed tools: Read, Glob, Grep, Edit, narrowly scoped Bash
writes: repository sandbox only
protected branches: no direct push
external systems: none
```

## Hooks expected in future Orchestrator adapter

- `UserPromptSubmit`: inject run ID, contract pin, practice-profile hash, route scope, and data policy.
- `PreToolUse`: enforce revocation, tool authority, route authority, data scope, and side-effect class.
- `PostToolUse`: hash/redact output and append audit event.
- `Stop`: validate structured output, evidence completeness, and terminal state.
- `PreCompact`: save durable task summary and artifact references.
- `SubagentStart`: require registered worker ID, schema, budget, tools, and parent run.
- `SubagentStop`: accept only typed outputs and artifact references.

## Stop conditions

Stop when real or privileged data appears, a requested tool is not registered, a contract pin is unavailable, source evidence is incomplete, a prompt hash fails, a prohibited action is proposed, or the task attempts to redefine platform canon.

## Result rule

A successful coding session returns tested repository changes. A successful intake workflow returns a review packet. Neither success state authorizes legal or external action.
