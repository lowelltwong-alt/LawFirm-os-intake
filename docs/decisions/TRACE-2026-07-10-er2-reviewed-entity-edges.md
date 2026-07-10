# TRACE: ER2 Reviewed Entity Edges

## Decision

The intake candidate matcher may consume only explicitly declared local candidate
entity edges. A reviewed alias edge may produce a candidate match. A reviewed
structural edge may produce `related_distinct`, never a merged identity. A
proposed edge holds for review and cannot influence a match.

## Why

Employers, insureds, affiliates, staffing agencies, and PEOs can be related
without being interchangeable for conflict, coverage, or budget purposes.
Fuzzy matching, acronym expansion, and embedding similarity are prohibited
because they can silently collapse distinct parties.

## Fail-Closed Rules

- Alias-edge IDs must be unique and endpoints cannot self-reference.
- Only `reviewed_local_candidate` and `proposed` edge states are accepted.
- Reviewed structural cycles fail validation.
- Unreviewed aliases and structural edges hold for human review.
- This local table does not create Semantic Substrate identity canon.

## Premortem

| Failure mode | Early signal | Containment |
| --- | --- | --- |
| A structural relationship is treated as identity | A conflict seed loses one related name | Preserve `related_distinct`; emit both names for later review. |
| An unreviewed edge affects a budget or link | A proposed table row produces `match` | Hold the comparison and require review. |
| A bad table cycle spreads through linking | Two reviewed edges point back to each other | Reject policy loading before extraction. |

## Boundary

This is synthetic-only candidate matching. It does not finalize a matter link,
clear conflicts, open a matter, write to the Lake, or call a connector.
