# Rust Fixture Boundary Checker

`rust/fixture-boundary-checker` is a local QA leaf tool for read-only JSON fixtures. It is not an ingestion adapter, not a legal classifier, not a budget engine, and not an Exception Lake writer.

The checker validates local candidate fixture/report JSON for the boundaries the UI depends on:

- candidate-only, synthetic-only, non-authoritative, and local-JSON-only flags stay true when present;
- connector, Lake, SQLite, matter-opening, budget-submission, appeal-submission, runtime-artifact, and silent-learning flags stay false when present;
- the UI review data bundle counts match its `detail_reports`;
- required UI detail reports are present;
- present UI detail reports carry `sha256:` source hashes.

Run it locally:

```powershell
python -m lawfirm_os_intake build-rust-fixture-boundary-report `
  --root apps/legal-intake-budget/src/fixtures `
  --ui-bundle apps/legal-intake-budget/src/fixtures/demo-ui-review-data-bundle.json `
  --out-dir .lawfirm-os-intake/rust-fixture-boundary `
  --repo-root .
```

Stage a prebuilt report into the synthetic QA review run:

```powershell
python -m lawfirm_os_intake build-synthetic-qa-review-run `
  --run-root .lawfirm-os-intake/synthetic-qa-review `
  --repo-root . `
  --fixture-boundary-report .lawfirm-os-intake/rust-fixture-boundary/rust_fixture_boundary_report.json
```

The emitted report is candidate-only and read-only evidence. A failed report blocks confidence claims about the UI fixture bundle, but it does not mutate fixtures, submit budgets, open matters, write SQLite/Lake records, or promote any canonical LawFirm OS contract.

This tool deliberately does not change `rust_replacement_allowed=false` for ingestion. Python remains the reference oracle for intake preflight, source offsets, evidence refs, budget math, and legal workflow decisions.
