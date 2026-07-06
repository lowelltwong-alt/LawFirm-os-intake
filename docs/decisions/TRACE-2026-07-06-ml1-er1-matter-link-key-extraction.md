# TRACE 2026-07-06 ML1/ER1 Matter-Link Key Extraction

## Decision

Add a local candidate-only matter-link key extraction and entity-normalization
slice before any clustering or budget flow. The slice reads synthetic
`SourceBundle` fixtures, emits `MatterLinkKeySet` artifacts with exact
source-span evidence refs, and records deterministic entity comparison outcomes
for review.

## Why

The workflow now has Upfront-like matter-linking preflight/review/QA artifacts,
but it did not yet have the Fable ML1/ER1 oracle that extracts deterministic
keys from raw source bundles. Without this layer, later clustering would have to
mix parsing, identity logic, and decision policy in one step.

## Boundary

- Candidate-only and synthetic-only.
- No clustering, no matter identity assertion, no persistent state.
- Sender identity may namespace medium keys but is never emitted as a key.
- No fuzzy matching, embeddings, acronym inference, or learned identity matcher.
- No conflict conclusion, budget generation, budget submission, matter opening,
  connector call, Lake write, SQLite write, or DAD lesson emission.
- Entity suffix conflicts and possible affiliates hold for human review instead
  of merging identities.

## Files

- `config/matter-link-policy.yaml`
- `src/lawfirm_os_intake/matter_link_keys.py`
- `src/lawfirm_os_intake/models.py`
- `src/lawfirm_os_intake/cli.py`
- `examples/synthetic/inbound/linking-*.source-bundle.json`
- `tests/test_matter_link_keys.py`

## Tests

- Source-bound extraction preserves offsets and hashes.
- Same sender does not become a linking key.
- Empty/unreadable and no-key sources surface extraction gaps.
- Non-synthetic bundles fail closed.
- Entity normalization is deterministic and idempotent.
- Suffix conflicts, acronym negatives, and possible affiliates follow the ER1
  boundary.

## Premortem

The largest risk is that a future clustering PR treats extracted keys as matter
truth. This trace and the schema flags deliberately keep them as candidate
review evidence only. Another risk is over-normalizing entity names; the first
implementation avoids fuzzy matching and routes suffix/residual cases to review.
