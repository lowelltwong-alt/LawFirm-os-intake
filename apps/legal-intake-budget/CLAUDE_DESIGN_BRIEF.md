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
- reviewed gold and synthetic fixture status.
- QA gate strip for budget coherence, fixture depth, calibration readiness, smoke, and full pytest evidence.
