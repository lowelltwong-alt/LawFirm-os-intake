# TRACE: Synthetic Budget Input Catalog

## Decision

Document a single navigation map for editable synthetic budget inputs. The map
separates source-controlled values from browser-memory drafts and defines the
future read-only replacement boundary for reviewed benchmark or negotiated-rate
data.

## Why

The workbench now exposes charts, editable what-if tables, candidate JSON/CSV,
and local XLSX outputs. Without an explicit catalog, a later contributor could
mistake a downloaded draft for a source of truth or change a chart input without
knowing which policy, fixture, and safety boundary it affects.

## Boundary

All current values remain synthetic. The catalog does not ingest, estimate,
claim, or authorize real firm, carrier, panel, or negotiated rates. Public
material may inform a separately governed Legal Knowledge Runtime benchmark
snapshot; it does not flow directly into this repository or its browser UI.

## Verification

The catalog points to existing source files and existing deterministic
workbench/export validation. It does not change calculations, schemas, browser
behavior, or any external-write boundary.

The catalog review also corrected a misleading synthetic-rate-card comment. The
complete candidate rate-card package received the resulting new source hash;
that deliberately proves that source-language changes cannot bypass pinned
package lineage.
