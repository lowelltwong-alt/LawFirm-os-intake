#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
rm -rf .lawfirm-os-intake/smoke
python -m lawfirm_os_intake demo \
  --input examples/synthetic/inbound/carrier-assignment-medmal.json \
  --practice-profile context/synthetic-profiles/insurance-defense.yaml \
  --confirmation-template examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json \
  --out-dir .lawfirm-os-intake/smoke

preflight_dir="$(find .lawfirm-os-intake/smoke/preflight -mindepth 1 -maxdepth 1 -type d | head -n 1)"
test -n "$preflight_dir"
test -s "$preflight_dir/exception_lake_candidates.jsonl"
test -s ".lawfirm-os-intake/smoke/budget/exception_lake_candidates.jsonl"
test -s ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
test -s ".lawfirm-os-intake/smoke/budget/review_package_manifest.json"
test -s ".lawfirm-os-intake/smoke/budget/safety_gate_report.json"
