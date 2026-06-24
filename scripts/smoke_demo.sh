#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
rm -rf .lawfirm-os-intake/smoke
python -m lawfirm_os_intake demo \
  --input examples/synthetic/inbound/north-star-messy-intake.json \
  --practice-profile context/synthetic-profiles/insurance-defense.yaml \
  --confirmation-template examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json \
  --out-dir .lawfirm-os-intake/smoke

preflight_dir="$(find .lawfirm-os-intake/smoke/preflight -mindepth 1 -maxdepth 1 -type d | head -n 1)"
test -n "$preflight_dir"
test -s "$preflight_dir/contract_state_report.json"
test -s "$preflight_dir/ingestion_result.json"
test -s "$preflight_dir/rust_ingestion_readiness_report.json"
grep -q '"status": "passed"' "$preflight_dir/contract_state_report.json"
grep -q '"parity_contract": "rust_ready_ingestion_v0_1"' "$preflight_dir/ingestion_result.json"
grep -q '"status": "passed"' "$preflight_dir/rust_ingestion_readiness_report.json"
grep -q '"rust_replacement_allowed": false' "$preflight_dir/rust_ingestion_readiness_report.json"
test -s "$preflight_dir/exception_lake_candidates.jsonl"
test -s "$preflight_dir/exception_lake_readiness_report.json"
grep -q "prompt_injection_source_content" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q "source_missing" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q "duplicate_source_detected" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q '"status": "passed"' "$preflight_dir/exception_lake_readiness_report.json"
test -s ".lawfirm-os-intake/smoke/budget/exception_lake_candidates.jsonl"
test -s ".lawfirm-os-intake/smoke/budget/exception_lake_readiness_report.json"
grep -q '"admission_state": "dry_run_not_admitted"' ".lawfirm-os-intake/smoke/budget/exception_lake_readiness_report.json"
test -s ".lawfirm-os-intake/smoke/budget/budget_precondition_report.json"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/budget/budget_precondition_report.json"
test -s ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
test -s ".lawfirm-os-intake/smoke/budget/review_package_manifest.json"
test -s ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
test -s ".lawfirm-os-intake/smoke/budget/safety_gate_report.json"
grep -q "Status: passed" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "review_package_completeness_report.json" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "blocked_pending_conflicts_and_engagement" ".lawfirm-os-intake/smoke/budget/safety_gate_report.json"
