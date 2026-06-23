# Claude Agent SDK Operating Contract

Primary reference: `https://code.claude.com/docs/en/agent-sdk/agent-loop`

Related reference implementation: `https://github.com/anthropics/claude-for-legal`

## Agent loop mapping

| Claude Agent SDK concept | LawFirm OS contract |
|---|---|
| system prompt / `CLAUDE.md` | versioned front-door policy and stop conditions |
| prompt | registered prompt reference/version/hash |
| tool definition | governed ToolSpec from the control plane |
| allowed/disallowed tools | tool authority manifest |
| permission mode | environment/run execution policy |
| max turns / budget | deterministic run budget gate |
| tool request | pre-tool authorization and revocation check |
| tool result | hashed/redacted run event and evidence ref |
| session ID | agent-run ledger correlation |
| result message | terminal state validated against workflow contract |
| refusal / max turns | explicit blocked/failed run event |
| compaction | durable summary and artifact-reference checkpoint |
| subagent | registered bounded worker with typed handoff |

## Required controls

- Set maximum turns, cost/token budget, wall-clock limit, and retry count.
- Use the narrowest permission mode and tool allowlist.
- Recheck revocation and authorization before every tool call.
- Never let a model-selected tool expand the run’s authority.
- Store the durable business state in LawFirm OS artifacts, not only SDK session history.
- Keep source text separate from system instructions.
- Validate every worker result against a schema and evidence rule.
- Treat compaction as a lossy event unless essential state is externalized.
- Preserve session ID and terminal subtype in the run ledger.

## Suggested hooks

### `UserPromptSubmit`

Inject run ID, profile hash, contract pin, data scope, worker ID, allowed intents, and prohibited actions.

### `PreToolUse`

Check worker registration, tool authority, data scope, route scope, approval state, revocation, idempotency, and side-effect class.

### `PostToolUse`

Hash and redact tool result; record latency/status; validate output schema; attach evidence reference.

### `Stop`

Validate terminal state, evidence completeness, unresolved risks, and required human gate. Write packet and ledger.

### `PreCompact`

Persist objective, acceptance criteria, current state, decisions, file/artifact refs, tests, open risks, and prohibited actions.

### Subagent hooks

Require parent run ID, registered worker ID, fixed input/output schemas, bounded tools, and fresh-context justification. A subagent returns a typed result, not a free-form transcript.

## Effort/model routing

Reasoning effort controls harness depth, not authority. Use low/medium effort for routine bounded extraction after evals justify it; high effort for architecture or difficult ambiguity; frontier effort only through escalation. Human gates remain unchanged.

## Data posture

The starter uses synthetic data only. Model/provider retention and confidentiality must be separately approved before real-data use.
