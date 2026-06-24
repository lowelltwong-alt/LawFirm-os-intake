# TRACE: Context Boundary Report

## Situation

The intake workflow already had counterfactual practice-context tests, but an individual preflight run did not produce a durable artifact proving that practice context stayed separate from observed source evidence.

That gap mattered because matter-family, posture, and party-role rankings may be influenced by practice profiles. Reviewers need to see that context influenced ranking only as a transparent prior, not as observed fact.

## Decision

Add `context_boundary_report.json` to every successful preflight run.

The report is local evaluation evidence. It proves:

- observed source evidence has precedence over practice context;
- practice context is not treated as observed evidence;
- context refs remain structured profile refs;
- context-influenced candidates stay packet-anchored;
- explicit unknown options remain available;
- human confirmation is still required for context-ranked candidates;
- no external write or authoritative promotion occurred.

The final review package and review-package completeness report now require this proof before accepting the intake-to-budget package.

## Safety Boundary

This change does not promote canonical doctrine, create route IDs, clear conflicts, approve engagement, docket deadlines, open matters, mutate practice profiles, or write to the Exception Lake.

Semantic Substrate remains the owner of promoted context/evidence doctrine. Orchestrator remains the future owner of execution-plane workflows and evidence-packet assembly.

## Validation

Validation coverage includes:

- preflight writes and passes the context boundary report;
- report enforcement fails if context influence is treated as observed fact;
- review-package completeness fails if the context-boundary artifact drifts;
- starter release audit fails if the context-boundary artifact drifts;
- schema export includes `context-boundary-report.schema.json`.
