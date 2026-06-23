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
