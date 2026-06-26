# TRACE: Carrier Preapproval Thresholds

Date: 2026-06-26

## Decision

Implement Slice D from the carrier rate and guideline layer: synthetic
preapproval thresholds emit candidate review artifacts, pending human gates, and
dry-run Exception Lake candidates.

## Why

Carrier guideline compliance is not only a math projection. Some work should not
be submitted without human-reviewed preapproval evidence. The budget run needs to
surface that condition deterministically before any future carrier-facing
workflow can proceed.

## Implemented Surface

- `config/synthetic-carrier-guideline.yaml` now includes
  `pre_approval_thresholds`.
- `CarrierPreapprovalRequirement` and `CarrierPreapprovalReport` candidate
  schemas.
- `legal_budget_proposal.json` embeds the preapproval report and budget runs
  also write `carrier_preapproval_report.json`.
- Triggered thresholds add a pending `human_carrier_preapproval` gate.
- Triggered thresholds emit dry-run `carrier_preapproval_required`
  `ExceptionLakeCandidate` rows and a mapping-package rule.
- Review surfaces render threshold status, required gate, no-preapproval state,
  and no carrier-submission authority.

## Boundary

This slice does not obtain preapproval, submit a budget, send a carrier message,
write Lake/SQLite records, implement connectors, mutate a carrier guideline, or
promote any event label to canon. It records review pressure only.

## Red-Team Notes

- A threshold crossing is not evidence that the carrier would reject the work; it
  is a deterministic human-review gate.
- Synthetic thresholds are not real carrier guidelines and must not be copied
  into production policy without owner review.
- The preapproval gate must block carrier-facing submission but must not mutate
  proposed budget math or compliant projection math.
- Future Orchestrator work must own any actual preapproval request, response
  capture, and appeal/submission workflow.

## Validation Plan

- Export schemas.
- Run focused carrier guideline, review package, and north-star tests.
- Run full repo tests, lint, formatting, smoke demo, and front-door validators.
