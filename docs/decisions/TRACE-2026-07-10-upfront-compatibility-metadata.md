# TRACE 2026-07-10: Upfront Compatibility Metadata

## Decision

Expose and validate synthetic Upfront-like request identity, request channel, and
external-reference counts in the matter-linking preflight report. Observed
external references must be typed and bound to an inventoried source. An explicit
missing reference, such as an unavailable official matter number, remains an
unknown fact rather than a failed or invented match.

## Boundary

This is a synthetic compatibility contract, not a verified Upfront export or API
schema. It adds no connector, vendor call, screen, matter opening, budget output,
Lake/SQLite write, or identity assertion.

## Red-Team Notes

- An adjuster reference or request ID may be useful correlation evidence but is
  never unique matter identity by itself.
- A source reference that does not resolve to the inventory cannot support an
  observed external identifier.
- A null official-matter-number reference is acceptable only as explicit missing
  information; it cannot become a link key or authorization.
