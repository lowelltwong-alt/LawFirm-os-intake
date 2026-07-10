# Replay Input UI Fixture Hash Repair

Date: 2026-07-10
Status: candidate-only implementation trace
Risk classification: low; this repairs deterministic hash lineage for checked synthetic UI fixtures and changes no workflow authority.

## Context

The reconciled Fable snapshot stack changed the checked synthetic labor/employment replay-confidence fixture. The full repository suite correctly failed because demo-ui-review-data-bundle.json still carried the prior source digest.

## Decision

Run the repository-owned refresh-ui-demo-fixtures command with the explicit write flag and a fixed timestamp. The command:

- refreshed the confidence-status source digest;
- refreshed the Rust fixture-manifest digest and byte counts;
- regenerated the deterministic UI bundle identity;
- passed both the Rust source-hash and snapshot-coherence gates;
- performed no external, Lake, SQLite, budget-submission, or matter-opening write.

No raw public, client, matter, carrier, or privileged data was introduced. The checked fixtures remain synthetic-only and candidate-only.

## Validation

    $env:PYTHONPATH='src'
    python -m lawfirm_os_intake refresh-ui-demo-fixtures --fixtures-root apps/legal-intake-budget/src/fixtures --out-dir <local-temp> --repo-root . --write-fixtures --generated-at 2026-07-10T00:00:00Z --timeout-seconds 240
    # ui_demo_fixture_refresh_verified
    # source_hash_gate_status=passed
    # snapshot_gate_status=passed

    python scripts\run_full_pytest.py tests\test_rust_fixture_manifest_scanner.py tests\test_rust_ui_bundle_source_hash.py tests\test_ui_demo_fixture_refresh.py tests\test_ui_foundation_contract.py -q
    # 45 passed

The complete validation suite must pass before this repair is reported as complete.
