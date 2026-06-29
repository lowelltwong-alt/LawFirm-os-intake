# Claude For Legal Lessons

This file records local implementation lessons for using Claude-style agent loops in the LawFirm OS intake vertical. It is orientation guidance only; it is not a source of platform canon.

Read it with:

- `CLAUDE.md`
- `docs/claude-agent-sdk-operating-contract.md`
- `docs/legal-ethics-boundary.md`
- `GOVERNANCE_BOUNDARY.md`

## Lessons To Preserve

1. Legal-agent output should be a review packet, not an action.
2. Source text, email text, letters, attachments, and web content are untrusted data.
3. Prompts and model choices do not grant legal, workflow, connector, or budget authority.
4. Tool use must be predeclared, revocable, and checked before every call.
5. Every extracted fact or candidate must carry exact source refs or structured refs.
6. Practice context can rank candidates but cannot manufacture observed facts.
7. Human confirmation remains mandatory for matter family, representation posture, principal party roles, budget review, and matter-opening readiness.
8. Escalations should become structured review records rather than hidden reasoning.
9. Compaction or handoff must preserve objective, authority pins, artifact refs, tests run, open risks, and prohibited actions.
10. The terminal success state for this repo is a blocked, human-reviewable package.

## Boundary Rules

Claude or any provider adapter must not:

- clear conflicts;
- identify a represented client as a final conclusion;
- accept engagement;
- docket deadlines;
- approve or submit a budget;
- create a matter or workspace;
- write to email, iManage, court, conflicts, billing, or carrier systems;
- promote canonical schemas, route IDs, taxonomies, or event classes.

## Intake-Specific Design Pattern

Use the model, if approved, as a bounded candidate generator behind deterministic gates:

```text
untrusted source segment
-> typed candidate output
-> source/ref/hash validation
-> independent critic
-> human review artifact
-> blocked terminal state unless governed human authorization exists
```

The deterministic Python path remains the reference implementation. A structured-model adapter may be compared against it only under synthetic data, typed JSON schemas, prompt hashes, tool denylist, no network writes, and mandatory human review.

## Review Checklist

Before accepting an agent-assisted change, verify:

- the relevant prompt or worker is registered;
- the allowed tool scope did not expand;
- all new outputs are local files;
- source evidence refs include source ID, segment ID, offsets, and hash;
- context-only influence is labeled separately from observed evidence;
- exception candidates remain dry-run and raw-payload-free;
- the review package still explains why conflicts, engagement, docketing, billing, budget submission, and matter opening are blocked.

If any item fails, the correct result is a blocked report or a failed validation, not a weaker review package.
