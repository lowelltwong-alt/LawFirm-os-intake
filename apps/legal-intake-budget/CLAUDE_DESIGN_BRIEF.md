# Claude Design Brief

Design against `apps/legal-intake-budget/src/data-contract.ts`. Keep the app dense, quiet, and operational. The first screen should be a review workbench, not a landing page.

Required boundaries:

- read local JSON manifests only;
- no network calls;
- no mutation buttons;
- no connector, portal, billing, GitHub, court, SQLite, or Exception Lake writes;
- show blocked gates, missing information, evidence refs, red-team notes, and candidate Lake labels;
- preserve the separation between observed evidence, human-confirmed facts, practice-context priors, public methodology, and synthetic fixtures.

Useful views:

- run summary and gate status;
- source coverage and evidence refs;
- human intake review packet;
- budget proposal, scenario ranges, guideline/compliant projection, and actual variance;
- carrier rejection, appeal outcome, and learning-loop blockers;
- public-data cache and public-source methodology reports;
- Rust public-data cache custody status with metadata-only counts, hashes, failed checks, required review gates, and blocked actions;
- reviewed gold and synthetic fixture status.
- QA gate strip for budget coherence, the synthetic QA bundle, fixture depth, calibration readiness, the labor/employment QA matrix, the L&E fixture family pack, the calibration starter pack, smoke, and full pytest evidence.
- UI review data bundle panel from `src/fixtures/demo-ui-review-data-bundle.json`, showing which local JSON detail reports are renderable and hash-bound.
- Public-data cache audit panel from `src/fixtures/demo-public-data-cache-audit-report.json` and Rust custody panel from `src/fixtures/demo-rust-public-data-cache-custody-report.json`, showing methodology-gate status without public payload text, real party facts, fixture generation, Lake/SQLite writes, ingestion, matter opening, or budget submission.
- Synthetic QA blocker drilldown from `src/fixtures/demo-synthetic-qa-blocker-report.json`, showing `action_state`, `recommended_next_action`, evidence refs, and candidate Lake labels from the backend report without deriving a new authority surface in the UI.
- L&E QA matrix detail panel from `src/fixtures/demo-labor-employment-qa-matrix-report.json`, showing the blocked critical-fact case and the range-only pending-review case without adding mutation controls.
- L&E blocked driver review panel from `src/fixtures/demo-labor-employment-blocked-driver-impact-review-report.json`, showing why amount-budget output is blocked and what deterministic follow-up actions would unblock rerun.
