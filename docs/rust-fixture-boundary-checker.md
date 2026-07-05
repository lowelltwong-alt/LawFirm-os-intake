# Rust Fixture Boundary And Manifest Tools

`rust/fixture-boundary-checker` is a local QA leaf tool for read-only JSON fixtures. It is not an ingestion adapter, not a legal classifier, not a budget engine, and not an Exception Lake writer.

It currently exposes five explicit Rust binaries through Python CLI wrappers:

- `fixture-boundary-checker` validates local candidate fixture/report JSON for the boundaries the UI depends on.
- `fixture_manifest_scanner` emits a deterministic hash manifest for local JSON fixture/report files.
- `fixture_snapshot_coherence` compares a checked fixture manifest against the current fixture tree and fails closed on drift.
- `ui_bundle_source_hash_checker` verifies that a UI review data bundle's `source_sha256` values match the resolved local detail-report JSON files.
- `public_data_cache_custody_checker` verifies ignored/external public-data cache custody, path containment, file presence, SHA-256 digests, and byte counts.

The boundary checker validates:

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

Build a deterministic fixture manifest locally:

```powershell
python -m lawfirm_os_intake build-rust-fixture-manifest-report `
  --root apps/legal-intake-budget/src/fixtures `
  --out-dir .lawfirm-os-intake/rust-fixture-manifest `
  --repo-root .
```

Check whether the current fixture tree still matches a checked manifest:

```powershell
python -m lawfirm_os_intake build-rust-fixture-snapshot-coherence-report `
  --root apps/legal-intake-budget/src/fixtures `
  --expected-manifest apps/legal-intake-budget/src/fixtures/demo-rust-fixture-manifest-report.json `
  --out-dir .lawfirm-os-intake/rust-fixture-snapshot-coherence `
  --repo-root .
```

The snapshot coherence report is a detector only. It does not repair or
regenerate fixture manifests. Changed, missing, or unexpected fixture JSON files
produce a failed candidate report so stale demo evidence cannot silently become
roadmap truth.

Check whether the UI data bundle still points at the current local detail-report
files:

```powershell
python -m lawfirm_os_intake build-rust-ui-bundle-source-hash-report `
  --root apps/legal-intake-budget/src/fixtures `
  --bundle apps/legal-intake-budget/src/fixtures/demo-ui-review-data-bundle.json `
  --out-dir .lawfirm-os-intake/rust-ui-bundle-source-hash `
  --repo-root .
```

The UI bundle source-hash report resolves both generated run-root paths and the
checked frontend `demo-...` fixture naming convention. It fails closed on invalid
`source_sha256` values, missing source files, and hash mismatches.

Check a local public-data cache custody manifest directly:

```powershell
python -m lawfirm_os_intake build-rust-public-data-cache-custody-report `
  --cache-root .lawfirm-os-intake/public-data-cache `
  --out-dir .lawfirm-os-intake/rust-public-data-cache-custody `
  --repo-root .
```

The public-data cache custody report is byte/path evidence only. The governed
entry point remains `audit-public-data-cache`, which consumes the Rust report
and still requires human cache review before any methodology or synthetic
fixture conversion work. A passing Rust custody report does not authorize public
record ingestion, public payload commits, adapters, Lake/SQLite writes, or
fixture generation.

Refresh the checked frontend wrapper fixtures and verify both Rust gates:

```powershell
python -m lawfirm_os_intake refresh-ui-demo-fixtures `
  --fixtures-root apps/legal-intake-budget/src/fixtures `
  --out-dir .lawfirm-os-intake/ui-demo-fixture-refresh `
  --repo-root . `
  --generated-at 2026-07-05T00:00:00Z `
  --write-fixtures
```

This refresh updates only `demo-ui-review-data-bundle.json` and
`demo-rust-fixture-manifest-report.json`. It intentionally does not regenerate
semantic QA detail reports or copy generated run-root artifacts; use the
promotion command below when an approved generated run root should become the
checked UI demo fixture set.

Promote an approved generated run root into the checked frontend fixtures with:

```powershell
python -m lawfirm_os_intake promote-ui-demo-run-fixtures `
  --run-root .lawfirm-os-intake/synthetic-qa-review `
  --fixtures-root apps/legal-intake-budget/src/fixtures `
  --out-dir .lawfirm-os-intake/ui-demo-fixture-promotion `
  --repo-root . `
  --generated-at 2026-07-05T00:00:00Z `
  --write-fixtures
```

The promotion command is the sanitizer flow. It copies only the static
allowlist of UI-imported JSON reports, parses and rewrites JSON recursively,
replaces generated run-root strings with `<demo-run-root>`, fails closed on
missing, ambiguous, out-of-root, leaking, or side-effecting source artifacts,
regenerates the checked Rust boundary and manifest wrapper reports, then runs
the Rust boundary, UI bundle source-hash, and snapshot-coherence gates. It does
not copy arbitrary run-root JSON, regenerate semantic reports from prompts,
submit budgets, open matters, write SQLite/Lake records, or promote canonical
contracts.

Stage a prebuilt report into the synthetic QA review run:

```powershell
python -m lawfirm_os_intake build-synthetic-qa-review-run `
  --run-root .lawfirm-os-intake/synthetic-qa-review `
  --repo-root . `
  --fixture-boundary-report .lawfirm-os-intake/rust-fixture-boundary/rust_fixture_boundary_report.json `
  --fixture-manifest-report .lawfirm-os-intake/rust-fixture-manifest/rust_fixture_manifest_report.json
```

The emitted reports are candidate-only and read-only evidence. A failed boundary
report blocks confidence claims about the UI fixture bundle. A failed manifest
report blocks claims that the reviewed fixture set is hash-bound. A failed
snapshot coherence report blocks claims that the checked manifest still matches
the current local JSON fixture tree. A failed UI bundle source-hash report blocks
claims that the read-only UI bundle is hash-bound to the detail reports it
displays. None of these reports mutate fixtures, submit budgets, open matters,
write SQLite/Lake records, or promote any canonical LawFirm OS contract.

This tool deliberately does not change `rust_replacement_allowed=false` for ingestion. Python remains the reference oracle for intake preflight, source offsets, evidence refs, budget math, and legal workflow decisions.
