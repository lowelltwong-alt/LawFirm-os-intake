from pathlib import Path

from lawfirm_os_intake.crosswalks import run_crosswalk_audit_report
from lawfirm_os_intake.ocg_rule_ir import run_ocg_rule_ir_adoption_report
from lawfirm_os_intake.review_ui_crosswalk_ocg_evidence import (
    build_qa_product_confidence_report,
    build_qa_readiness_report,
)
from lawfirm_os_intake.ui_review_data_bundle import build_ui_review_data_bundle
from lawfirm_os_intake.util import write_json
from tests.test_ocg_rule_ir_adoption import _budget_projection_and_rule_ir
from tests.test_ui_review_data_bundle import _write_ui_detail_reports

CROSSWALK_FIXTURES = [
    "fixtures/synthetic/crosswalks/l-and-e-matter-families-to-sali-lmss.json",
    "fixtures/synthetic/crosswalks/party-roles-to-sali-lmss.json",
    "fixtures/synthetic/crosswalks/budget-phase-task-expense-to-utbms-ledes.json",
    "fixtures/synthetic/crosswalks/rejection-families-to-ledes-error-dimensions.json",
]


def _write_crosswalk_and_ocg_reports(repo_root: Path, tmp_path: Path):
    crosswalk_paths = [repo_root / fixture for fixture in CROSSWALK_FIXTURES]
    _crosswalks, crosswalk_report, crosswalk_dir = run_crosswalk_audit_report(
        crosswalk_paths,
        tmp_path / "crosswalk",
        repo_root=repo_root,
    )
    budget, projection, rule_ir = _budget_projection_and_rule_ir(repo_root, tmp_path)
    budget_path = tmp_path / "budget" / "legal_budget_proposal.json"
    budget_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(budget_path, budget.model_dump(mode="json"))
    projection_path = tmp_path / "projection" / "carrier_compliant_projection.json"
    projection_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(projection_path, projection.model_dump(mode="json"))
    _rule_ir, ocg_report, ocg_dir = run_ocg_rule_ir_adoption_report(
        budget_path,
        projection_path,
        repo_root / "fixtures/synthetic/ocg/shared-rule-ir/harbor-point-alpha.ocg-rule-ir.json",
        tmp_path / "ocg",
    )
    return (
        crosswalk_dir / "crosswalk_audit_report.json",
        ocg_dir / "ocg_rule_ir_adoption_report.json",
    )


def test_ui_bundle_includes_crosswalk_and_ocg_summaries_when_provided(repo_root, tmp_path):
    run_root = tmp_path / "run"
    _write_ui_detail_reports(run_root)
    crosswalk_path, ocg_path = _write_crosswalk_and_ocg_reports(repo_root, tmp_path)
    bundle_path = tmp_path / "ui_review_data_bundle.json"
    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=bundle_path,
        generated_at="2026-07-09T00:00:00Z",
        crosswalk_audit_path=crosswalk_path,
        ocg_rule_ir_adoption_path=ocg_path,
    )
    assert bundle.crosswalk_audit_summary is not None
    assert bundle.ocg_rule_ir_adoption_summary is not None
    assert bundle.crosswalk_audit_summary.status == "passed"
    assert bundle.ocg_rule_ir_adoption_summary.status == "accepted_as_read_only_candidate"
    crosswalk_detail = next(
        detail for detail in bundle.detail_reports if detail.detail_report_id == "crosswalk-audit"
    )
    ocg_detail = next(
        detail
        for detail in bundle.detail_reports
        if detail.detail_report_id == "ocg-rule-ir-adoption"
    )
    assert crosswalk_detail.present is True
    assert ocg_detail.present is True


def test_ui_bundle_backward_compatible_without_crosswalk_or_ocg(repo_root, tmp_path):
    run_root = tmp_path / "run"
    _write_ui_detail_reports(run_root)
    bundle = build_ui_review_data_bundle(
        run_root=run_root,
        out_path=tmp_path / "ui_review_data_bundle.json",
        generated_at="2026-07-09T00:00:00Z",
    )
    assert bundle.crosswalk_audit_summary is None
    assert bundle.ocg_rule_ir_adoption_summary is None
    crosswalk_detail = next(
        detail for detail in bundle.detail_reports if detail.detail_report_id == "crosswalk-audit"
    )
    assert crosswalk_detail.present is False
    assert crosswalk_detail.required is False


def test_qa_readiness_blocks_missing_crosswalk_when_required(repo_root, tmp_path):
    run_root = tmp_path / "run"
    _write_ui_detail_reports(run_root)
    bundle_path = tmp_path / "ui_review_data_bundle.json"
    build_ui_review_data_bundle(run_root=run_root, out_path=bundle_path)
    report = build_qa_readiness_report(
        ui_review_data_bundle_path=bundle_path,
        require_crosswalk_ocg=True,
        generated_at="2026-07-09T00:00:00Z",
    )
    assert report.status == "blocked"
    assert any(check.check_id == "crosswalk_audit_present" for check in report.checks)


def test_qa_readiness_passes_with_crosswalk_and_ocg_reports(repo_root, tmp_path):
    run_root = tmp_path / "run"
    _write_ui_detail_reports(run_root)
    crosswalk_path, ocg_path = _write_crosswalk_and_ocg_reports(repo_root, tmp_path)
    bundle_path = tmp_path / "ui_review_data_bundle.json"
    build_ui_review_data_bundle(
        run_root=run_root,
        out_path=bundle_path,
        crosswalk_audit_path=crosswalk_path,
        ocg_rule_ir_adoption_path=ocg_path,
    )
    report = build_qa_readiness_report(
        ui_review_data_bundle_path=bundle_path,
        crosswalk_audit_path=crosswalk_path,
        ocg_rule_ir_adoption_path=ocg_path,
        require_crosswalk_ocg=True,
        generated_at="2026-07-09T00:00:00Z",
    )
    assert report.status == "ready_for_review"
    assert report.blocker_count == 0
    check_ids = {check.check_id for check in report.checks}
    assert "crosswalk_exact_standard_code_unverified" in check_ids
    assert "crosswalk_zero_high_confidence_dual_review_violations" in check_ids


def test_qa_product_confidence_includes_crosswalk_and_ocg_gates(repo_root, tmp_path):
    run_root = tmp_path / "run"
    _write_ui_detail_reports(run_root)
    crosswalk_path, ocg_path = _write_crosswalk_and_ocg_reports(repo_root, tmp_path)
    bundle_path = tmp_path / "ui_review_data_bundle.json"
    build_ui_review_data_bundle(
        run_root=run_root,
        out_path=bundle_path,
        crosswalk_audit_path=crosswalk_path,
        ocg_rule_ir_adoption_path=ocg_path,
    )
    readiness = build_qa_readiness_report(
        ui_review_data_bundle_path=bundle_path,
        crosswalk_audit_path=crosswalk_path,
        ocg_rule_ir_adoption_path=ocg_path,
        require_crosswalk_ocg=True,
        generated_at="2026-07-09T00:00:00Z",
    )
    readiness_path = tmp_path / "qa_readiness_report.json"
    write_json(readiness_path, readiness.model_dump(mode="json"))
    confidence = build_qa_product_confidence_report(
        ui_review_data_bundle_path=bundle_path,
        qa_readiness_report_path=readiness_path,
        crosswalk_audit_path=crosswalk_path,
        ocg_rule_ir_adoption_path=ocg_path,
        generated_at="2026-07-09T00:00:00Z",
    )
    gate_ids = {gate.gate_id for gate in confidence.gates}
    assert "crosswalk_evidence_gate" in gate_ids
    assert "ocg_adoption_evidence_gate" in gate_ids
    assert confidence.status == "ready_for_poc_review"


def test_review_ui_source_contains_crosswalk_and_ocg_sections(repo_root):
    app_source = (repo_root / "apps/legal-intake-budget/src/App.tsx").read_text(encoding="utf-8")
    assert "Standard Crosswalk Evidence" in app_source
    assert "OCG Rule IR Adoption Evidence" in app_source
    assert "CrosswalkAuditEvidencePanel" in app_source
    assert "OCGRuleIRAdoptionEvidencePanel" in app_source
    assert "exact_standard_code_verified" in app_source
    assert "UTBMS-like Family Labels" in app_source


def test_blocked_actions_preserved_in_crosswalk_report(repo_root, tmp_path):
    crosswalk_paths = [repo_root / fixture for fixture in CROSSWALK_FIXTURES]
    _crosswalks, report, _run_dir = run_crosswalk_audit_report(
        crosswalk_paths,
        tmp_path / "crosswalk",
        repo_root=repo_root,
    )
    assert report.prohibited_actions
    assert "do_not_treat_local_crosswalk_as_canonical" in report.prohibited_actions
