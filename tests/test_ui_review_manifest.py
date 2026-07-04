from lawfirm_os_intake.cli import main
from lawfirm_os_intake.ui_review_manifest import ARTIFACT_SPECS, build_ui_review_manifest
from lawfirm_os_intake.util import load_json, write_json


def _write_required_artifacts(run_root, *, exclude: set[str] | None = None):
    excluded = exclude or set()
    budget_dir = run_root / "budget"
    preflight_dir = run_root / "preflight" / "run_001"
    budget_dir.mkdir(parents=True)
    preflight_dir.mkdir(parents=True)
    for spec in ARTIFACT_SPECS:
        if spec.file_name in excluded:
            continue
        target_dir = (
            preflight_dir if spec.file_name == "intake_preflight_packet.json" else budget_dir
        )
        payload = {"status": "passed", "external_writes_performed": False}
        if spec.file_name == "legal_budget_proposal.json":
            payload = {
                "matter_family": "employment_litigation_defense",
                "approval_state": "proposed_for_human_review",
                "not_authorized_for_client_submission": True,
                "external_writes_performed": False,
            }
        write_json(target_dir / spec.file_name, payload)


def _write_quality_evidence(run_root):
    quality_dir = run_root / "quality"
    quality_dir.mkdir()
    for file_name in [
        "budget_coherence_report.json",
        "synthetic_qa_bundle_report.json",
        "synthetic_fixture_depth_audit_report.json",
        "matter_linking_preflight_report.json",
        "budget_calibration_readiness_report.json",
        "budget_calibration_starter_pack_report.json",
        "labor_employment_qa_matrix_report.json",
        "labor_employment_fixture_family_pack_report.json",
        "labor_employment_executable_fixtures_report.json",
        "labor_employment_executable_coverage_report.json",
        "labor_employment_executable_fact_binding_report.json",
        "labor_employment_executable_driver_binding_report.json",
        "labor_employment_executable_driver_impact_report.json",
        "labor_employment_driver_impact_review_report.json",
        "labor_employment_blocked_driver_impact_review_report.json",
        "labor_employment_budget_output_expectations_report.json",
        "labor_employment_budget_qa_gate_report.json",
        "labor_employment_budget_learning_fixtures_report.json",
        "labor_employment_budget_outcome_replay_readiness_report.json",
        "labor_employment_budget_fact_gold_report.json",
        "budget_learning_loop_report.json",
    ]:
        write_json(
            quality_dir / file_name, {"status": "passed", "external_writes_performed": False}
        )
    scripts_dir = run_root / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "run_full_pytest.py").write_text(
        "# synthetic evidence marker\n", encoding="utf-8"
    )
    (scripts_dir / "smoke_demo.sh").write_text("# synthetic evidence marker\n", encoding="utf-8")


def test_build_ui_review_manifest_from_local_artifacts(tmp_path):
    run_root = tmp_path / "demo"
    _write_required_artifacts(run_root)
    _write_quality_evidence(run_root)
    out = tmp_path / "ui_review_manifest.json"

    manifest = build_ui_review_manifest(
        run_root=run_root,
        out_path=out,
        generated_at="2026-07-02T00:00:00Z",
    )

    assert out.is_file()
    assert manifest["overallStatus"] == "passed"
    assert manifest["practiceArea"] == "labor_and_employment"
    assert manifest["matterFamily"] == "employment_litigation_defense"
    assert manifest["boundaryFlags"]["readOnly"] is True
    assert manifest["boundaryFlags"]["networkCallsAllowed"] is False
    assert all(not artifact["externalWritesPerformed"] for artifact in manifest["artifacts"])
    assert {gate["status"] for gate in manifest["qualityGates"]} == {"passed"}


def test_build_ui_review_manifest_blocks_missing_calibration_evidence(tmp_path):
    run_root = tmp_path / "demo"
    _write_required_artifacts(
        run_root,
        exclude={
            "synthetic_fixture_depth_audit_report.json",
            "budget_calibration_readiness_report.json",
        },
    )
    write_json(
        run_root / "budget" / "budget_coherence_report.json",
        {"status": "passed", "external_writes_performed": False},
    )
    out = tmp_path / "ui_review_manifest.json"

    manifest = build_ui_review_manifest(
        run_root=run_root,
        out_path=out,
        generated_at="2026-07-02T00:00:00Z",
    )

    gates = {gate["gateId"]: gate for gate in manifest["qualityGates"]}
    assert manifest["overallStatus"] == "blocked"
    assert gates["budget_coherence"]["status"] == "passed"
    assert gates["budget_calibration_readiness"]["status"] == "blocked"
    assert "Calibration Readiness" in " ".join(manifest["blockerSummary"])


def test_build_ui_review_manifest_cli_writes_local_json(tmp_path):
    run_root = tmp_path / "demo"
    _write_required_artifacts(run_root)
    _write_quality_evidence(run_root)
    out = tmp_path / "ui_review_manifest.json"

    code = main(
        [
            "build-ui-review-manifest",
            "--run-root",
            str(run_root),
            "--out",
            str(out),
            "--generated-at",
            "2026-07-02T00:00:00Z",
        ]
    )

    manifest = load_json(out)
    assert code == 0
    assert manifest["overallStatus"] == "passed"
    assert manifest["boundaryFlags"]["mutationCommandsAllowed"] is False
