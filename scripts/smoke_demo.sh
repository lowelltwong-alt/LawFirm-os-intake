#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"
rm -rf .lawfirm-os-intake/smoke
export PYTHONDONTWRITEBYTECODE=1
PYTHON_BIN="${PYTHON_BIN:-}"
if [[ -z "$PYTHON_BIN" ]]; then
  if command -v python >/dev/null 2>&1; then
    PYTHON_BIN="python"
  elif command -v python.exe >/dev/null 2>&1; then
    PYTHON_BIN="python.exe"
  elif command -v python3 >/dev/null 2>&1; then
    PYTHON_BIN="python3"
  else
    echo "python, python.exe, or python3 is required" >&2
    exit 127
  fi
fi
if [[ "$PYTHON_BIN" == *.exe ]]; then
  if [[ "$ROOT" =~ ^/mnt/([A-Za-z])/(.*)$ ]]; then
    drive="${BASH_REMATCH[1]^^}"
    rest="${BASH_REMATCH[2]}"
    export PYTHONPATH="${drive}:/${rest}/src${PYTHONPATH:+;$PYTHONPATH}"
  elif command -v cygpath >/dev/null 2>&1; then
    export PYTHONPATH="$(cygpath -w "$ROOT/src")${PYTHONPATH:+;$PYTHONPATH}"
  elif command -v wslpath >/dev/null 2>&1; then
    export PYTHONPATH="$(wslpath -w "$ROOT/src")${PYTHONPATH:+;$PYTHONPATH}"
  else
    export PYTHONPATH="$ROOT/src${PYTHONPATH:+;$PYTHONPATH}"
  fi
else
  export PYTHONPATH="$ROOT/src${PYTHONPATH:+:$PYTHONPATH}"
fi
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import runpy
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
sys.argv = [
    "lawfirm_os_intake",
    "demo",
    "--input",
    "examples/synthetic/inbound/north-star-messy-intake.json",
    "--practice-profile",
    "context/synthetic-profiles/insurance-defense.yaml",
    "--confirmation-template",
    "examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json",
    "--fixture-gold",
    "examples/synthetic/gold/north-star-messy-intake.fixture-gold.json",
    "--out-dir",
    ".lawfirm-os-intake/smoke",
]
runpy.run_module("lawfirm_os_intake", run_name="__main__")
PY

preflight_dir="$(find .lawfirm-os-intake/smoke/preflight -mindepth 1 -maxdepth 1 -type d | head -n 1)"
test -n "$preflight_dir"
test -s "$preflight_dir/contract_state_report.json"
test -s "$preflight_dir/data_scope_gate_report.json"
test -s "$preflight_dir/ingestion_result.json"
test -s "$preflight_dir/ingestion_volume_profile.json"
test -s "$preflight_dir/rust_ingestion_readiness_report.json"
test -s "$preflight_dir/intake_review_form.md"
test -s "$preflight_dir/deadline_docketing_guard_report.json"
grep -q '"status": "passed"' "$preflight_dir/contract_state_report.json"
grep -q '"status": "passed"' "$preflight_dir/data_scope_gate_report.json"
grep -q '"runtime_mode": "synthetic_only"' "$preflight_dir/data_scope_gate_report.json"
grep -q '"data_origin": "synthetic"' "$preflight_dir/data_scope_gate_report.json"
grep -q '"raw_payload_written": false' "$preflight_dir/data_scope_gate_report.json"
grep -q '"parity_contract": "rust_ready_ingestion_v0_1"' "$preflight_dir/ingestion_result.json"
grep -q '"decision": "keep_python_reference"' "$preflight_dir/ingestion_volume_profile.json"
grep -q '"rust_transition_policy_ref": "config/rust-ingestion-transition-policy.json"' "$preflight_dir/ingestion_volume_profile.json"
grep -q '"rust_replacement_allowed": false' "$preflight_dir/ingestion_volume_profile.json"
grep -q '"required_performance_profile_dimensions"' "$preflight_dir/ingestion_volume_profile.json"
grep -q '"candidate_rust_hot_path_scope"' "$preflight_dir/ingestion_volume_profile.json"
grep -q '"status": "passed"' "$preflight_dir/rust_ingestion_readiness_report.json"
grep -q '"rust_transition_policy_ref": "config/rust-ingestion-transition-policy.json"' "$preflight_dir/rust_ingestion_readiness_report.json"
grep -q '"rust_replacement_allowed": false' "$preflight_dir/rust_ingestion_readiness_report.json"
grep -q '"status": "passed"' "$preflight_dir/deadline_docketing_guard_report.json"
grep -q '"docketing_action_performed": false' "$preflight_dir/deadline_docketing_guard_report.json"
grep -q '"proposed_next_gate": "human_deadline_review"' "$preflight_dir/deadline_docketing_guard_report.json"
test -s "$preflight_dir/exception_lake_candidates.jsonl"
test -s "$preflight_dir/exception_lake_readiness_report.json"
test -s "$preflight_dir/exception_lake_handoff_manifest.json"
test -s "$preflight_dir/run_ledger_integrity_report.json"
test -s "$preflight_dir/fixture_gold_report.json"
grep -q '"status": "passed"' "$preflight_dir/fixture_gold_report.json"
grep -q '"top_three_matter_family_recall"' "$preflight_dir/fixture_gold_report.json"
grep -q "prompt_injection_source_content" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q "prohibited_transition_attempted_conflicts_cleared" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q "prohibited_transition_attempted_deadline_docketed" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q "prohibited_transition_attempted_matter_opened" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q "critic_role_candidates_ambiguous" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q "source_missing" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q "duplicate_source_detected" "$preflight_dir/exception_lake_candidates.jsonl"
grep -q '"status": "passed"' "$preflight_dir/exception_lake_readiness_report.json"
grep -q '"status": "dry_run_ready_not_admitted"' "$preflight_dir/exception_lake_handoff_manifest.json"
grep -q '"sqlite_write_performed": false' "$preflight_dir/exception_lake_handoff_manifest.json"
grep -q '"status": "passed"' "$preflight_dir/run_ledger_integrity_report.json"
grep -q '"stage": "preflight"' "$preflight_dir/run_ledger_integrity_report.json"
grep -q "duplicate_of=syn-northstar-email-001" "$preflight_dir/intake_review_form.md"
grep -q "attachments=complaint.pdf, medical-chronology.pdf" "$preflight_dir/intake_review_form.md"
grep -q "## Review Outcome Handling" "$preflight_dir/intake_review_form.md"
grep -q "confirmed -> budget_precondition_gate" "$preflight_dir/intake_review_form.md"
grep -q "append_or_supersede_only" "$preflight_dir/intake_review_form.md"
test -s ".lawfirm-os-intake/smoke/budget/exception_lake_candidates.jsonl"
test -s ".lawfirm-os-intake/smoke/budget/exception_lake_readiness_report.json"
test -s ".lawfirm-os-intake/smoke/budget/exception_lake_handoff_manifest.json"
test -s ".lawfirm-os-intake/smoke/budget/run_ledger_integrity_report.json"
grep -q '"admission_state": "dry_run_not_admitted"' ".lawfirm-os-intake/smoke/budget/exception_lake_readiness_report.json"
grep -q '"stage": "budget_combined"' ".lawfirm-os-intake/smoke/budget/exception_lake_handoff_manifest.json"
grep -q '"sqlite_write_performed": false' ".lawfirm-os-intake/smoke/budget/exception_lake_handoff_manifest.json"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/budget/run_ledger_integrity_report.json"
grep -q '"stage": "budget_success"' ".lawfirm-os-intake/smoke/budget/run_ledger_integrity_report.json"
test -s ".lawfirm-os-intake/smoke/budget/budget_precondition_report.json"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/budget/budget_precondition_report.json"
test -s ".lawfirm-os-intake/smoke/budget/legal_budget_review_form.md"
grep -q "## Budget Lines" ".lawfirm-os-intake/smoke/budget/legal_budget_review_form.md"
grep -q "rate source: synthetic_profile" ".lawfirm-os-intake/smoke/budget/legal_budget_review_form.md"
grep -q "## Submission Boundary" ".lawfirm-os-intake/smoke/budget/legal_budget_review_form.md"
grep -q "Client/carrier submission authorized: False" ".lawfirm-os-intake/smoke/budget/legal_budget_review_form.md"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.coherence import validate_budget_artifacts

report = validate_budget_artifacts(
    ".lawfirm-os-intake/smoke/budget/legal_budget_proposal.json",
    report_out=".lawfirm-os-intake/smoke/budget/budget_coherence_report.json",
)
raise SystemExit(0 if report["status"] == "passed" else 1)
PY
test -s ".lawfirm-os-intake/smoke/budget/budget_coherence_report.json"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/budget/budget_coherence_report.json"
test -s ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
test -s ".lawfirm-os-intake/smoke/budget/review_package_manifest.json"
test -s ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
test -s ".lawfirm-os-intake/smoke/budget/fixture_gold_report.json"
test -s ".lawfirm-os-intake/smoke/budget/safety_gate_report.json"
test -s ".lawfirm-os-intake/smoke/budget/budget_submission_guard_report.json"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/budget/fixture_gold_report.json"
grep -q '"final_boundary"' ".lawfirm-os-intake/smoke/budget/fixture_gold_report.json"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/budget/budget_submission_guard_report.json"
grep -q '"client_submission_performed": false' ".lawfirm-os-intake/smoke/budget/budget_submission_guard_report.json"
grep -q '"billing_handoff_performed": false' ".lawfirm-os-intake/smoke/budget/budget_submission_guard_report.json"
grep -q "Status: passed" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "## Authority And Preconditions" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Contract state status: passed" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "### Data Scope Gate" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Data scope gate status: passed" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Runtime mode: synthetic_only" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Raw payload written before gate: False" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Budget precondition status: passed" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "## Source Inventory" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Ingestion volume profile:" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Required performance profile dimensions:" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Candidate Rust hot path scope:" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "syn-northstar-attachment-missing-001" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Human confirmation decision evidence:" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "] sha=sha256:" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "## Candidate Alternatives" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "## Required Human Gates" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
test -s ".lawfirm-os-intake/smoke/budget/human_gate_status_report.json"
grep -q '"status": "pending_human_gates"' ".lawfirm-os-intake/smoke/budget/human_gate_status_report.json"
grep -q '"gate_id": "human_budget_review"' ".lawfirm-os-intake/smoke/budget/human_gate_status_report.json"
grep -q "Human gate status report:" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "human_intake_confirmation: completed" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "human_budget_review: pending" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Deadline docketing guard report:" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Docketing action performed: False" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Deadline proposed next gate: human_deadline_review" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Budget submission guard report:" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Client submission performed: False" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "Billing handoff performed: False" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "### Budget Lines" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "### Exception Lake Readiness" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "### Exception Lake Handoff" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "SQLite write performed: False" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "budget_unknowns_require_review: class=workflow_escalation" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
exception_candidate_details="$(awk '/### Exception Candidate Details/{flag=1;next}/## Safety Gate/{flag=0}flag' \
  ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md")"
grep -q "] sha=sha256:" <<< "$exception_candidate_details"
grep -q "raw_payload_included=False" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "## Evidence Graph Summary" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "supports_conflict_search_term=" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "blocker detail: conflicts_not_cleared" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "blocker detail: budget_review_not_completed" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "structured_ref=workflow/intake-to-budget.workflow.yaml#conflicts_review" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "prohibited action detail: do_not_submit_budget" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "workflow/prohibited-transitions.yaml#budget_proposal_ready->budget_submitted" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "## Run Ledger Summary" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "### Run Ledger Integrity" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "budget_success: status=passed" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "budget step 4: conflict_seed_and_budget_proposal_built" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "linked_review_forms_complete" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "linked_review_forms_preserve_evidence_and_boundaries" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "preflight_ingestion_volume_profile" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "budget_exception_lake_handoff_manifest" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "run_ledger_integrity_reports_passed" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "readiness_blocker_details_rendered" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "human_gate_status_report_complete" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "data_scope_gate_report_complete" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "deadline_docketing_guard_report_complete" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "data_scope_gate_report" ".lawfirm-os-intake/smoke/budget/review_package_manifest.json"
grep -q "preflight_deadline_docketing_guard_report" ".lawfirm-os-intake/smoke/budget/review_package_manifest.json"
grep -q "budget_submission_guard_report_complete" ".lawfirm-os-intake/smoke/budget/review_package_completeness_report.json"
grep -q "budget_submission_guard_report" ".lawfirm-os-intake/smoke/budget/review_package_manifest.json"
grep -q "review_package_completeness_report.json" ".lawfirm-os-intake/smoke/budget/matter_opening_review_package.md"
grep -q "blocked_pending_conflicts_and_engagement" ".lawfirm-os-intake/smoke/budget/safety_gate_report.json"
"$PYTHON_BIN" -B scripts/audit_starter_release.py --demo-dir .lawfirm-os-intake/smoke
test -s ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
grep -q "public_data_catalog_is_metadata_only" ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
grep -q "north_star_source_coverage_exercised" ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
grep -q "north_star_candidate_surface_complete" ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
grep -q "evidence_graph_covers_intake_to_budget_deliverables" ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
grep -q "human_review_package_tells_complete_north_star_story" ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
grep -q "budget_boundary_and_math_hold" ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
grep -q "deadline_and_budget_guard_reports_hold" ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
grep -q "exception_lake_candidates_are_dry_run_and_expected" ".lawfirm-os-intake/smoke/budget/starter_release_audit_report.json"
"$PYTHON_BIN" -B scripts/audit_blocked_budget_attempt.py \
  --preflight-packet "$preflight_dir/intake_preflight_packet.json" \
  --confirmation-template examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json \
  --practice-profile context/synthetic-profiles/insurance-defense.yaml \
  --out-dir .lawfirm-os-intake/smoke/blocked-budget
test -s ".lawfirm-os-intake/smoke/blocked-budget/blocked_budget_attempt_audit_report.json"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/blocked-budget/blocked_budget_attempt_audit_report.json"
grep -q "no_prohibited_budget_outputs_emitted" ".lawfirm-os-intake/smoke/blocked-budget/blocked_budget_attempt_audit_report.json"
grep -q "budget_blocked_before_human_confirmation" ".lawfirm-os-intake/smoke/blocked-budget/blocked_budget_attempt_audit_report.json"
test -s ".lawfirm-os-intake/smoke/blocked-budget/budget/exception_lake_handoff_manifest.json"
test -s ".lawfirm-os-intake/smoke/blocked-budget/budget/run_ledger_integrity_report.json"
grep -q '"stage": "budget_precondition_blocked"' ".lawfirm-os-intake/smoke/blocked-budget/budget/exception_lake_handoff_manifest.json"
grep -q '"sqlite_write_performed": false' ".lawfirm-os-intake/smoke/blocked-budget/budget/exception_lake_handoff_manifest.json"
grep -q '"stage": "budget_precondition_blocked"' ".lawfirm-os-intake/smoke/blocked-budget/budget/run_ledger_integrity_report.json"
grep -q '"terminal_status": "blocked"' ".lawfirm-os-intake/smoke/blocked-budget/budget/run_ledger_integrity_report.json"
test ! -e ".lawfirm-os-intake/smoke/blocked-budget/budget/legal_budget_proposal.json"
test ! -e ".lawfirm-os-intake/smoke/blocked-budget/budget/conflict_search_seed_packet.json"
"$PYTHON_BIN" -B scripts/audit_context_counterfactual.py \
  --input examples/synthetic/inbound/help-email.json \
  --baseline-profile context/synthetic-profiles/insurance-defense.yaml \
  --comparison-profile context/synthetic-profiles/plaintiff-personal-injury.yaml \
  --out-dir .lawfirm-os-intake/smoke/context-counterfactual
test -s ".lawfirm-os-intake/smoke/context-counterfactual/context_counterfactual_audit_report.json"
grep -q '"status": "passed"' ".lawfirm-os-intake/smoke/context-counterfactual/context_counterfactual_audit_report.json"
grep -q "observed_evidence_refs_stable" ".lawfirm-os-intake/smoke/context-counterfactual/context_counterfactual_audit_report.json"
grep -q "context_only_candidate_not_observed_fact" ".lawfirm-os-intake/smoke/context-counterfactual/context_counterfactual_audit_report.json"
grep -q "practice_context_changes_ranking" ".lawfirm-os-intake/smoke/context-counterfactual/context_counterfactual_audit_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.budget_calibration_starter_pack import (
    run_budget_calibration_starter_pack,
)

report, _ = run_budget_calibration_starter_pack(
    corpus_root="examples/synthetic",
    repo_root=".",
    out_dir=".lawfirm-os-intake/smoke/quality/calibration-starter",
    reviewed_at="2026-07-02T00:00:00Z",
)
raise SystemExit(
    0
    if report.status == "starter_pack_ready_for_manual_fixture_update_review"
    else 1
)
PY
test -s ".lawfirm-os-intake/smoke/quality/calibration-starter/budget_calibration_starter_pack_report.json"
test -s ".lawfirm-os-intake/smoke/quality/calibration-starter/budget-calibration-readiness/budget_calibration_readiness_report.json"
grep -q '"status": "starter_pack_ready_for_manual_fixture_update_review"' \
  ".lawfirm-os-intake/smoke/quality/calibration-starter/budget_calibration_starter_pack_report.json"
grep -q '"budget_calibration_readiness_status": "ready_for_manual_fixture_update_review"' \
  ".lawfirm-os-intake/smoke/quality/calibration-starter/budget_calibration_starter_pack_report.json"
grep -q '"status": "ready_for_manual_fixture_update_review"' \
  ".lawfirm-os-intake/smoke/quality/calibration-starter/budget-calibration-readiness/budget_calibration_readiness_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.labor_employment_qa_matrix import (
    run_labor_employment_qa_matrix,
)

report, _ = run_labor_employment_qa_matrix(
    repo_root=".",
    out_dir=".lawfirm-os-intake/smoke/quality/le-qa-matrix",
)
raise SystemExit(
    0 if report.status == "labor_employment_qa_matrix_ready_for_review" else 1
)
PY
test -s ".lawfirm-os-intake/smoke/quality/le-qa-matrix/labor_employment_qa_matrix_report.json"
grep -q '"status": "labor_employment_qa_matrix_ready_for_review"' \
  ".lawfirm-os-intake/smoke/quality/le-qa-matrix/labor_employment_qa_matrix_report.json"
grep -q '"case_id": "critical_fact_gaps_block_amount_budget"' \
  ".lawfirm-os-intake/smoke/quality/le-qa-matrix/labor_employment_qa_matrix_report.json"
grep -q '"case_id": "ready_critical_facts_still_range_only"' \
  ".lawfirm-os-intake/smoke/quality/le-qa-matrix/labor_employment_qa_matrix_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.labor_employment_fixture_family_pack import (
    run_labor_employment_fixture_family_pack_audit,
)

report, _ = run_labor_employment_fixture_family_pack_audit(
    pack_path=(
        "examples/synthetic/labor-employment/"
        "labor-employment-budget-fixture-family-pack.json"
    ),
    fact_needs_path="config/labor-employment-budget-fact-needs.yaml",
    out_dir=".lawfirm-os-intake/smoke/quality/le-fixture-family-pack",
)
raise SystemExit(
    0
    if report.status == "labor_employment_fixture_family_pack_ready_for_review"
    else 1
)
PY
test -s ".lawfirm-os-intake/smoke/quality/le-fixture-family-pack/labor_employment_fixture_family_pack_report.json"
grep -q '"status": "labor_employment_fixture_family_pack_ready_for_review"' \
  ".lawfirm-os-intake/smoke/quality/le-fixture-family-pack/labor_employment_fixture_family_pack_report.json"
grep -q '"case_count": 32' \
  ".lawfirm-os-intake/smoke/quality/le-fixture-family-pack/labor_employment_fixture_family_pack_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.labor_employment_executable_fixtures import (
    run_labor_employment_executable_fixture_audit,
)

report, _ = run_labor_employment_executable_fixture_audit(
    manifest_path=(
        "examples/synthetic/labor-employment/"
        "labor-employment-executable-fixtures-manifest.json"
    ),
    repo_root=".",
    out_dir=".lawfirm-os-intake/smoke/quality/le-executable-fixtures",
)
raise SystemExit(
    0
    if report.status == "labor_employment_executable_fixtures_ready_for_review"
    else 1
)
PY
test -s ".lawfirm-os-intake/smoke/quality/le-executable-fixtures/labor_employment_executable_fixtures_report.json"
grep -q '"status": "labor_employment_executable_fixtures_ready_for_review"' \
  ".lawfirm-os-intake/smoke/quality/le-executable-fixtures/labor_employment_executable_fixtures_report.json"
grep -q '"preflight_executed_count": 8' \
  ".lawfirm-os-intake/smoke/quality/le-executable-fixtures/labor_employment_executable_fixtures_report.json"
grep -q '"budget_fact_audit_required": true' \
  ".lawfirm-os-intake/smoke/quality/le-executable-fixtures/labor_employment_executable_fixtures_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.labor_employment_executable_coverage import (
    run_labor_employment_executable_coverage_audit,
)

report, _ = run_labor_employment_executable_coverage_audit(
    manifest_path=(
        "examples/synthetic/labor-employment/"
        "labor-employment-executable-fixtures-manifest.json"
    ),
    repo_root=".",
    out_dir=".lawfirm-os-intake/smoke/quality/le-executable-coverage",
)
raise SystemExit(
    0
    if report.status == "labor_employment_executable_coverage_ready_for_review"
    else 1
)
PY
test -s ".lawfirm-os-intake/smoke/quality/le-executable-coverage/labor_employment_executable_coverage_report.json"
grep -q '"coverage_state": "partial_executable_coverage"' \
  ".lawfirm-os-intake/smoke/quality/le-executable-coverage/labor_employment_executable_coverage_report.json"
grep -q '"pack_case_count": 32' \
  ".lawfirm-os-intake/smoke/quality/le-executable-coverage/labor_employment_executable_coverage_report.json"
grep -q '"covered_pack_case_count": 9' \
  ".lawfirm-os-intake/smoke/quality/le-executable-coverage/labor_employment_executable_coverage_report.json"
grep -q '"missing_executable_pack_case_count": 23' \
  ".lawfirm-os-intake/smoke/quality/le-executable-coverage/labor_employment_executable_coverage_report.json"
grep -q '"missing_family_count": 0' \
  ".lawfirm-os-intake/smoke/quality/le-executable-coverage/labor_employment_executable_coverage_report.json"
grep -q '"fixture_generation_authorized": false' \
  ".lawfirm-os-intake/smoke/quality/le-executable-coverage/labor_employment_executable_coverage_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.labor_employment_executable_fact_binding import (
    run_labor_employment_executable_fact_binding_audit,
)

report, _ = run_labor_employment_executable_fact_binding_audit(
    binding_manifest_path=(
        "examples/synthetic/labor-employment/"
        "labor-employment-executable-budget-fact-bindings.json"
    ),
    executable_fixture_report_path=(
        ".lawfirm-os-intake/smoke/quality/le-executable-fixtures/"
        "labor_employment_executable_fixtures_report.json"
    ),
    repo_root=".",
    out_dir=".lawfirm-os-intake/smoke/quality/le-executable-fact-binding",
)
raise SystemExit(
    0
    if report.status
    == "labor_employment_executable_budget_fact_bindings_ready_for_review"
    else 1
)
PY
test -s ".lawfirm-os-intake/smoke/quality/le-executable-fact-binding/labor_employment_executable_fact_binding_report.json"
grep -q '"status": "labor_employment_executable_budget_fact_bindings_ready_for_review"' \
  ".lawfirm-os-intake/smoke/quality/le-executable-fact-binding/labor_employment_executable_fact_binding_report.json"
grep -q '"fact_binding_count": 19' \
  ".lawfirm-os-intake/smoke/quality/le-executable-fact-binding/labor_employment_executable_fact_binding_report.json"
grep -q '"budget_amount_output_authorized": false' \
  ".lawfirm-os-intake/smoke/quality/le-executable-fact-binding/labor_employment_executable_fact_binding_report.json"
grep -q '"sqlite_write_performed": false' \
  ".lawfirm-os-intake/smoke/quality/le-executable-fact-binding/labor_employment_executable_fact_binding_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.labor_employment_executable_driver_binding import (
    run_labor_employment_executable_driver_binding_audit,
)

report, _ = run_labor_employment_executable_driver_binding_audit(
    executable_fixture_report_path=(
        ".lawfirm-os-intake/smoke/quality/le-executable-fixtures/"
        "labor_employment_executable_fixtures_report.json"
    ),
    executable_fact_binding_report_path=(
        ".lawfirm-os-intake/smoke/quality/le-executable-fact-binding/"
        "labor_employment_executable_fact_binding_report.json"
    ),
    repo_root=".",
    out_dir=".lawfirm-os-intake/smoke/quality/le-executable-driver-binding",
)
raise SystemExit(
    0
    if report.status == "labor_employment_executable_driver_bindings_ready_for_review"
    else 1
)
PY
test -s ".lawfirm-os-intake/smoke/quality/le-executable-driver-binding/labor_employment_executable_driver_binding_report.json"
grep -q '"status": "labor_employment_executable_driver_bindings_ready_for_review"' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-binding/labor_employment_executable_driver_binding_report.json"
grep -q '"missing_driver_dimensions": \[\]' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-binding/labor_employment_executable_driver_binding_report.json"
grep -q '"budget_amount_output_authorized": false' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-binding/labor_employment_executable_driver_binding_report.json"
grep -q '"sqlite_write_performed": false' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-binding/labor_employment_executable_driver_binding_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.labor_employment_executable_driver_impact import (
    run_labor_employment_executable_driver_impact_audit,
)

report, _ = run_labor_employment_executable_driver_impact_audit(
    executable_driver_binding_report_path=(
        ".lawfirm-os-intake/smoke/quality/le-executable-driver-binding/"
        "labor_employment_executable_driver_binding_report.json"
    ),
    out_dir=".lawfirm-os-intake/smoke/quality/le-executable-driver-impact",
)
raise SystemExit(
    0
    if report.status == "labor_employment_executable_driver_impacts_ready_for_review"
    else 1
)
PY
test -s ".lawfirm-os-intake/smoke/quality/le-executable-driver-impact/labor_employment_executable_driver_impact_report.json"
grep -q '"status": "labor_employment_executable_driver_impacts_ready_for_review"' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-impact/labor_employment_executable_driver_impact_report.json"
grep -q '"impact_item_count": 30' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-impact/labor_employment_executable_driver_impact_report.json"
grep -q '"block_amount_budget_impact_count": 12' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-impact/labor_employment_executable_driver_impact_report.json"
grep -q '"missing_impact_policy_dimensions": \[\]' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-impact/labor_employment_executable_driver_impact_report.json"
grep -q '"budget_amount_output_authorized": false' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-impact/labor_employment_executable_driver_impact_report.json"
grep -q '"sqlite_write_performed": false' \
  ".lawfirm-os-intake/smoke/quality/le-executable-driver-impact/labor_employment_executable_driver_impact_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.labor_employment_driver_impact_review import (
    run_labor_employment_driver_impact_review,
)

report, _ = run_labor_employment_driver_impact_review(
    review_spec_path=(
        "examples/synthetic/gold/labor-employment-driver-impact-review.json"
    ),
    driver_impact_report_path=(
        ".lawfirm-os-intake/smoke/quality/le-executable-driver-impact/"
        "labor_employment_executable_driver_impact_report.json"
    ),
    out_dir=".lawfirm-os-intake/smoke/quality/le-driver-impact-review",
)
raise SystemExit(
    0
    if report.status
    == "labor_employment_driver_impact_review_ready_for_budget_gate_replay"
    else 1
)
PY
test -s ".lawfirm-os-intake/smoke/quality/le-driver-impact-review/labor_employment_driver_impact_review_report.json"
test -s ".lawfirm-os-intake/smoke/quality/le-driver-impact-review/labor_employment_driver_impact_reviewed_slice_report.json"
grep -q '"status": "labor_employment_driver_impact_review_ready_for_budget_gate_replay"' \
  ".lawfirm-os-intake/smoke/quality/le-driver-impact-review/labor_employment_driver_impact_review_report.json"
grep -q '"selected_case_count": 2' \
  ".lawfirm-os-intake/smoke/quality/le-driver-impact-review/labor_employment_driver_impact_review_report.json"
grep -q '"block_amount_budget_impact_count": 0' \
  ".lawfirm-os-intake/smoke/quality/le-driver-impact-review/labor_employment_driver_impact_review_report.json"
grep -q '"budget_amount_output_authorized": false' \
  ".lawfirm-os-intake/smoke/quality/le-driver-impact-review/labor_employment_driver_impact_review_report.json"
grep -q '"sqlite_write_performed": false' \
  ".lawfirm-os-intake/smoke/quality/le-driver-impact-review/labor_employment_driver_impact_review_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.labor_employment_budget_fact_gold import (
    run_labor_employment_budget_fact_gold_validation,
)

report, _ = run_labor_employment_budget_fact_gold_validation(
    gold_path="examples/synthetic/gold/labor-employment-budget-fact-gold.json",
    repo_root=".",
    out_dir=".lawfirm-os-intake/smoke/quality/le-budget-fact-gold",
)
raise SystemExit(0 if report.status == "passed" else 1)
PY
test -s ".lawfirm-os-intake/smoke/quality/le-budget-fact-gold/labor_employment_budget_fact_gold_report.json"
grep -q '"status": "passed"' \
  ".lawfirm-os-intake/smoke/quality/le-budget-fact-gold/labor_employment_budget_fact_gold_report.json"
grep -q '"reviewed_gold": true' \
  ".lawfirm-os-intake/smoke/quality/le-budget-fact-gold/labor_employment_budget_fact_gold_report.json"
grep -q '"case_count": 2' \
  ".lawfirm-os-intake/smoke/quality/le-budget-fact-gold/labor_employment_budget_fact_gold_report.json"
grep -q '"budget_amount_output_authorized": false' \
  ".lawfirm-os-intake/smoke/quality/le-budget-fact-gold/labor_employment_budget_fact_gold_report.json"
"$PYTHON_BIN" -B - <<'PY'
from pathlib import Path
import sys

sys.path.insert(0, str(Path.cwd() / "src"))
from lawfirm_os_intake.synthetic_qa_bundle import run_synthetic_qa_bundle

report, _, manifest = run_synthetic_qa_bundle(
    run_root=".lawfirm-os-intake/smoke",
    out_dir=".lawfirm-os-intake/smoke/quality",
    fixture_depth_manifest_path=(
        "examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json"
    ),
    repo_root=".",
    ui_manifest_out=".lawfirm-os-intake/smoke/ui_review_manifest.json",
)
if report.status not in {"blocked", "pending_review", "passed"}:
    raise SystemExit(1)
if manifest is None or manifest["overallStatus"] not in {"blocked", "pending", "passed"}:
    raise SystemExit(1)
PY
test -s ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"status": "pending_review"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"synthetic_fixture_depth"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"budget_calibration_readiness"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"labor_employment_qa_matrix"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"labor_employment_fixture_family_pack"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"labor_employment_executable_fixtures"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"labor_employment_executable_coverage"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"labor_employment_executable_fact_binding"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"labor_employment_executable_driver_binding"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"labor_employment_executable_driver_impact"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"labor_employment_driver_impact_review"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
grep -q '"labor_employment_budget_fact_gold"' ".lawfirm-os-intake/smoke/quality/synthetic_qa_bundle_report.json"
test -s ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"synthetic_qa_bundle"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"budget_coherence"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"budget_calibration_readiness"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"labor_employment_qa_matrix"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"labor_employment_fixture_family_pack"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"labor_employment_executable_fixtures"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"labor_employment_executable_coverage"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"labor_employment_executable_fact_binding"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"labor_employment_executable_driver_binding"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"labor_employment_executable_driver_impact"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"labor_employment_driver_impact_review"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"labor_employment_budget_fact_gold"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"status": "pending_review"' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
grep -q '"networkCallsAllowed": false' ".lawfirm-os-intake/smoke/ui_review_manifest.json"
