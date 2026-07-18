# TRACE: Labor/Employment Candidate Profile

## Decision

Add a synthetic-only, ranking-only Labor/Employment candidate profile and
recognize the eight local candidate matter-family labels already present in the
synthetic fixture pack. Replace substring signal matching with token-aware
lexical matching for deterministic candidate evidence.

## Why

The executable L&E fixture manifest used the insurance-defense profile, while
the deterministic matter classifier had no L&E signal set. A retaliation
source could therefore rank medical malpractice from practice context rather
than its observed L&E language.

Independent review also found that a short signal such as `ada` matched inside
unrelated words such as `metadata` and `Canada`. The classifier now requires
non-word boundaries around every declared signal while retaining phrase and
punctuation matching.

## Boundaries

- The profile and manifest explicitly declare `candidate_only: true` and
  `not_promoted_canon: true`; labels remain local to this repository.
- Source terms create observed candidates; profile priors only influence scores.
- `unknown` remains available and human confirmation remains mandatory.
- The new profile intentionally has no rates, carrier rules, or budget templates.
- Shared terms such as `right-to-sue` may support multiple distinct candidates;
  they are not silently collapsed or resolved.
- This change does not create a budget, conflict conclusion, matter opening,
  docketing action, external write, Lake write, or SQLite write.

## Validation Plan

Run representative source bundles for all eight L&E families under the L&E and
insurance-defense profiles. Segment hashes, source inventory, observed evidence
refs, evidence status, and support summaries for every candidate must match; only the disclosed
profile prior may change confidence and context refs. A dedicated synthetic
negative fixture proves that `metadata` and `Canada` do not create ADA support,
and a collision test preserves separate discrimination and exhaustion
candidates when `right-to-sue` supports both.

## Review Resolution

The first independent review requested changes for short-token substring
matching, untested shared-term collisions, incomplete evidence invariance, and
coverage of only three L&E families. This slice addresses all four findings and
requires another independent replay before publication.

## Merge-Gate Repairs

GitHub CI exposed two pre-existing integration defects before the Python suite:
the browser smoke invoked the Python CLI before package installation, and a
long synthetic workbook filename escaped its wrapping flex row at a 390px
viewport. CI now installs only declared runtime dependencies before browser
smoke, exposes local source through `PYTHONPATH`, validates repository
cleanliness, and then performs the editable development install. Direct spans in
the rate-card controls may shrink and wrap. The existing browser smoke remains
the acceptance gate; table wrappers retain intentional horizontal scrolling.

The complete CI replay also caught that the executable-fixture manifest's new
`not_promoted_canon` declaration was not accepted by its strict typed model. The
model now requires that field to remain true, and a parsed-model regression
assertion keeps the manifest and contract synchronized.