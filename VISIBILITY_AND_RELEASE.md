# Visibility And Release

Status: `PUBLIC_SOURCE_VISIBLE_RELEASE_APPROVED`

Approval identifier: `USER-2026-07-27-INTAKE-PUBLIC-RELEASE`
Approved by: **Lowell T. Wong**
Date: **2026-07-27**
Basis: owner decision recorded 2026-07-26 that this repository becomes public, and explicit
authorization on 2026-07-27 to execute the publication sequence.

## Scope of this approval

Public, source-visible release of the synthetic-only intake-to-budget reference workflow: source,
schemas, synthetic fixtures, tests, decision records (`docs/decisions/`), agent handoff records
(`docs/ai-handoff/`), governance documents, and branch history.

## What this approval does NOT authorize

- Real client, matter, party, claim, employee, carrier, or firm-confidential data of any kind.
- External legal-data ingestion, production connectors, or live adapters.
- Budget submission, client or carrier delivery, billing handoff, or deadline docketing.
- Matter opening, conflicts conclusions, or engagement decisions.
- Autonomous or unattended execution.
- Any claim of production readiness, production validation, or measured business value.
- Reuse beyond the terms in `LICENSE.md` (source-available; all rights reserved).

## Pre-release checklist

| # | Item | State |
|---|---|---|
| 1 | Tracked-file privacy scan, 0 ERROR | **Pass** |
| 2 | Full-history scan across all refs, 0 unadjudicated ERROR | **Pass** — 4,967 objects, all refs |
| 3 | No real workbook, document, or archive artifact in history | **Pass** — no `.xlsx/.xls/.pdf/.docx/.msg/.pst` object exists in any ref |
| 4 | Local absolute paths removed at HEAD on the default branch | **Pass** — `scripts/check_no_local_paths.py` |
| 5 | Private repository names removed from tracked docs | **Pass** |
| 6 | Hub path replaced with `DAD_HUB` indirection | **Pass** — generators emit indirection upstream, so managed blocks cannot regenerate absolute paths |
| 7 | History disclosure decision recorded | **Pass** — accept-and-fix-forward; historical blobs retain machine paths, CI guard prevents regression |
| 8 | Branch exposure decision recorded | **Pass** — all branches public by decision; see `docs/BRANCH_MODEL.md` |
| 9 | `SECURITY.md` present | **Pass** |
| 10 | License reviewed for public release | **Pass** — `LICENSE.md`, source-available, all rights reserved |
| 11 | Synthetic-only assertion verified | **Pass** |
| 12 | Test suite green from a clean checkout | **Pass** — 1,333 passed; README-verbatim quickstart verified on a fresh clone |
| 13 | Registered in `lawfirm-os-repo-registry.json` | **Pass** — `owning_plane: vertical_workflow_composition` |
| 14 | Named owner approval | **Pass** — see identifier above |

## Standing boundaries after release

Publication does not change this repository's authority. It composes and evaluates a vertical
workflow; it defines no platform canon, and Semantic Substrate remains the control plane. Model
output is proposal-only and requires accountable human review. Unknown routes and event classes
fail closed.

## If a defect is found in published content

Report it as a security issue per `SECURITY.md`. Note that deleting published content in a later
commit does not remove it from history or from existing clones; a history-affecting response
requires a separate owner decision.
