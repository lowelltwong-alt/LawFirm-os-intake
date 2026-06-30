from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    SyntheticFixtureDepthAuditReport,
    SyntheticFixtureExpansionManifest,
)
from lawfirm_os_intake.synthetic_fixture_depth_audit import (
    run_synthetic_fixture_depth_audit,
)
from lawfirm_os_intake.util import load_json, write_json


def _manifest_path(repo_root):
    return repo_root / "examples/synthetic/fixture-expansion/remaining-roadmap-holdouts.json"


def _loaded_manifest(repo_root):
    return SyntheticFixtureExpansionManifest.model_validate(load_json(_manifest_path(repo_root)))


def _depth_ready_manifest(tmp_path):
    repo = tmp_path / "depth-ready-repo"
    fixtures = repo / "examples/synthetic/depth"
    tests = repo / "tests"
    fixtures.mkdir(parents=True)
    tests.mkdir(parents=True)

    write_json(
        fixtures / "ambiguous-role.json",
        {
            "data_origin": "synthetic",
            "contains_real_client_data": False,
            "contains_real_matter_data": False,
            "contains_privileged_data": False,
            "signals": ["carrier payer insured represented-client unknown context source-bound"],
        },
    )
    write_json(
        fixtures / "missing-actuals.json",
        {
            "data_origin": "synthetic",
            "actuals_by_phase": {},
            "actuals_by_code": {},
            "billing_connector_read_performed": False,
            "billing_connector_write_performed": False,
            "external_writes_performed": False,
            "signals": ["missing actual actuals_not_available variance_ledger_no_actuals"],
        },
    )
    write_json(
        fixtures / "carrier-rejections.json",
        {
            "data_origin": "synthetic",
            "contains_real_client_data": False,
            "contains_real_matter_data": False,
            "contains_privileged_data": False,
            "response_type": "partially_accepted",
            "appeal_results": [{"result": "stale"}, {"result": "denied"}],
            "signals": [
                "duplicate missing_response_count unlinked_notice_count parser_failure_count appeal total_disputed_amount"
            ],
        },
    )
    write_json(
        fixtures / "budget-le.json",
        {
            "data_origin": "synthetic",
            "driver_cases": [
                "soft_tissue lower_intensity_projection",
                "catastrophic higher_intensity_projection",
                "unknown profile_default not observed facts",
            ],
            "labor_employment": "labor employment employee employer party claimant class collective budget driver critical fact gap",
            "calibration_approved": False,
            "external_writes_performed": False,
            "silent_learning_performed": False,
        },
    )
    (tests / "test_depth_ready.py").write_text(
        """
def test_ambiguous_role_depth():
    fixture = "examples/synthetic/depth/ambiguous-role.json"
    assert "carrier payer insured represented-client unknown context source-bound"
    assert "human review unknown no learning external lake sqlite submission"


def test_missing_actuals_depth():
    fixture = "examples/synthetic/depth/missing-actuals.json"
    assert "missing actual actuals_not_available variance_ledger_no_actuals"
    assert "billing_connector_read_performed billing_connector_write_performed"


def test_carrier_rejection_depth():
    fixture = "examples/synthetic/depth/carrier-rejections.json"
    assert "duplicate missing_response_count unlinked_notice_count parser_failure_count"
    assert "appeal total_disputed_amount partially_accepted stale denied"
    assert "human review no learning external lake sqlite submission"


def test_budget_labor_employment_depth():
    fixture = "examples/synthetic/depth/budget-le.json"
    assert "soft_tissue lower_intensity_projection catastrophic higher_intensity_projection"
    assert "unknown profile_default not observed facts context"
    assert "labor employment employee employer party claimant class collective budget driver critical fact gap"
""",
        encoding="utf-8",
    )
    manifest = {
        "schema_version": "0.1",
        "manifest_id": "synthetic-fixture-expansion.depth-ready.fixture",
        "source_remaining_roadmap_item_id": "fixture-and-eval-expansion",
        "required_families": [
            "ambiguous_roles",
            "missing_actuals",
            "carrier_rejection_variants",
            "budget_driver_edges",
        ],
        "holdouts": [
            {
                "holdout_id": "holdout-depth-ambiguous-role.fixture",
                "family": "ambiguous_roles",
                "description": "Ambiguous role source context separation.",
                "fixture_refs": ["examples/synthetic/depth/ambiguous-role.json"],
                "test_refs": ["tests/test_depth_ready.py::test_ambiguous_role_depth"],
                "expected_signals": ["role alternatives remain source-bound"],
                "red_team_notes": ["human review keeps unknown available"],
            },
            {
                "holdout_id": "holdout-depth-missing-actuals.fixture",
                "family": "missing_actuals",
                "description": "Missing actuals not zero or connector backfill.",
                "fixture_refs": ["examples/synthetic/depth/missing-actuals.json"],
                "test_refs": ["tests/test_depth_ready.py::test_missing_actuals_depth"],
                "expected_signals": ["actuals_not_available"],
                "red_team_notes": ["no billing connector read or write"],
            },
            {
                "holdout_id": "holdout-depth-carrier-rejections.fixture",
                "family": "carrier_rejection_variants",
                "description": "Carrier rejection completeness plus partial allowance and negative appeals.",
                "fixture_refs": ["examples/synthetic/depth/carrier-rejections.json"],
                "test_refs": ["tests/test_depth_ready.py::test_carrier_rejection_depth"],
                "expected_signals": ["stale and denied appeals stay evidence"],
                "red_team_notes": ["no appeal submission or silent learning"],
            },
            {
                "holdout_id": "holdout-depth-budget-le.fixture",
                "family": "budget_driver_edges",
                "description": "Budget driver unknowns and labor employment fact gaps.",
                "fixture_refs": ["examples/synthetic/depth/budget-le.json"],
                "test_refs": ["tests/test_depth_ready.py::test_budget_labor_employment_depth"],
                "expected_signals": ["labor employment budget critical fact gap"],
                "red_team_notes": ["unknown facts do not narrow budget"],
            },
        ],
        "calibration_approved": False,
        "fixture_files_mutated_by_audit": False,
        "lake_write_performed": False,
        "sqlite_write_performed": False,
        "external_writes_performed": False,
        "silent_learning_performed": False,
    }
    manifest_path = write_json(
        repo / "examples/synthetic/fixture-expansion/depth-ready-manifest.json",
        SyntheticFixtureExpansionManifest.model_validate(manifest).model_dump(mode="json"),
    )
    return repo, manifest_path


def test_synthetic_fixture_depth_audit_identifies_current_depth_gaps(tmp_path, repo_root):
    report, run_dir = run_synthetic_fixture_depth_audit(
        manifest_path=_manifest_path(repo_root),
        repo_root=repo_root,
        out_dir=tmp_path / "fixture-depth",
    )
    persisted = SyntheticFixtureDepthAuditReport.model_validate(
        load_json(run_dir / "synthetic_fixture_depth_audit_report.json")
    )

    assert persisted.fixture_depth_audit_report_id == report.fixture_depth_audit_report_id
    assert persisted.status == "synthetic_fixture_depth_gaps_identified"
    assert persisted.holdout_count == 4
    assert persisted.dimension_count == 7
    assert persisted.boundary_violation_count == 0
    assert persisted.missing_dimension_count == 2
    assert persisted.missing_dimension_ids == [
        "carrier_partial_allowance_and_appeal_outcome_variety",
        "labor_employment_budget_fact_gap_holdout",
    ]
    assert persisted.calibration_approved is False
    assert persisted.fixture_files_mutated_by_audit is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes = (run_dir / "synthetic_fixture_depth_audit_report.md").read_text(encoding="utf-8")
    assert "synthetic_fixture_depth_gaps_identified" in notes
    assert "carrier_partial_allowance_and_appeal_outcome_variety" in notes
    assert "labor_employment_budget_fact_gap_holdout" in notes
    assert "does not approve calibration" in notes


def test_synthetic_fixture_depth_audit_ready_when_depth_dimensions_are_covered(
    tmp_path,
):
    ready_repo, manifest_path = _depth_ready_manifest(tmp_path)

    report, _ = run_synthetic_fixture_depth_audit(
        manifest_path=manifest_path,
        repo_root=ready_repo,
        out_dir=tmp_path / "fixture-depth-ready",
    )

    assert report.status == "synthetic_fixture_depth_ready_for_review"
    assert report.holdout_count == 4
    assert report.dimension_count == 7
    assert report.missing_dimension_count == 0
    assert report.boundary_violation_count == 0
    assert report.missing_dimension_ids == []
    assert report.required_next_actions == [
        "Use this depth report as candidate review evidence only.",
        "Do not approve calibration or learning without reviewed outcomes and owner gates.",
    ]
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_synthetic_fixture_depth_audit_blocks_external_fixture_ref(tmp_path, repo_root):
    manifest = _loaded_manifest(repo_root)
    raw = manifest.model_dump(mode="json")
    raw["manifest_id"] = "synthetic-fixture-expansion.depth-boundary.fixture"
    raw["holdouts"][0]["fixture_refs"] = [str(tmp_path / "outside-repo-fixture.json")]
    manifest_path = write_json(tmp_path / "depth-boundary-manifest.json", raw)

    report, _ = run_synthetic_fixture_depth_audit(
        manifest_path=manifest_path,
        repo_root=repo_root,
        out_dir=tmp_path / "fixture-depth-blocked",
    )

    assert report.status == "blocked_by_depth_audit_boundary_violation"
    assert report.boundary_violation_count == 1
    assert "resolves outside repo root" in report.boundary_violations[0]
    assert report.github_write_performed is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_synthetic_fixture_depth_audit_rejects_prose_only_dimension_matches(tmp_path):
    ready_repo, manifest_path = _depth_ready_manifest(tmp_path)
    budget_fixture = ready_repo / "examples/synthetic/depth/budget-le.json"
    fixture = load_json(budget_fixture)
    fixture["labor_employment"] = "budget driver placeholder without the required role facts"
    write_json(budget_fixture, fixture)
    test_path = ready_repo / "tests/test_depth_ready.py"
    test_path.write_text(
        test_path.read_text(encoding="utf-8").replace(
            '    assert "labor employment employee employer party claimant class collective budget driver critical fact gap"\n',
            '    assert "budget driver placeholder without required role fact details"\n',
        ),
        encoding="utf-8",
    )
    raw_manifest = load_json(manifest_path)
    raw_manifest["holdouts"][3]["description"] = (
        "Manifest-only labor employment employee employer party claimant class "
        "collective budget driver critical fact gap prose."
    )
    write_json(manifest_path, raw_manifest)

    report, _ = run_synthetic_fixture_depth_audit(
        manifest_path=manifest_path,
        repo_root=ready_repo,
        out_dir=tmp_path / "fixture-depth-prose-only",
    )
    dimension = next(
        item
        for item in report.dimensions
        if item.dimension_id == "labor_employment_budget_fact_gap_holdout"
    )

    assert report.status == "synthetic_fixture_depth_gaps_identified"
    assert dimension.status == "missing"
    assert dimension.matched_holdout_ids == []
    assert dimension.prose_only_match_count == 1
    assert dimension.fixture_evidence_refs == []
    assert dimension.test_evidence_refs == []


def test_synthetic_fixture_depth_audit_requires_named_test_ref_to_exist(tmp_path):
    ready_repo, manifest_path = _depth_ready_manifest(tmp_path)
    raw = load_json(manifest_path)
    raw["holdouts"][0]["test_refs"] = ["tests/test_depth_ready.py::test_missing_named_function"]
    broken_path = write_json(
        ready_repo / "examples/synthetic/fixture-expansion/depth-missing-test.json",
        raw,
    )

    report, _ = run_synthetic_fixture_depth_audit(
        manifest_path=broken_path,
        repo_root=ready_repo,
        out_dir=tmp_path / "fixture-depth-missing-test",
    )

    assert report.status == "blocked_by_depth_audit_boundary_violation"
    assert any("named test function is missing" in item for item in report.boundary_violations)


def test_synthetic_fixture_depth_audit_requires_fixture_ref_used_by_referenced_test(tmp_path):
    ready_repo, manifest_path = _depth_ready_manifest(tmp_path)
    write_json(
        ready_repo / "examples/synthetic/depth/unreferenced.json",
        {"data_origin": "synthetic", "signals": ["carrier payer insured unknown context"]},
    )
    raw = load_json(manifest_path)
    raw["holdouts"][0]["fixture_refs"] = ["examples/synthetic/depth/unreferenced.json"]
    broken_path = write_json(
        ready_repo / "examples/synthetic/fixture-expansion/depth-unbound-fixture.json",
        raw,
    )

    report, _ = run_synthetic_fixture_depth_audit(
        manifest_path=broken_path,
        repo_root=ready_repo,
        out_dir=tmp_path / "fixture-depth-unbound",
    )

    assert report.status == "blocked_by_depth_audit_boundary_violation"
    assert any(
        "is not referenced by any named test ref" in item for item in report.boundary_violations
    )


def test_synthetic_fixture_depth_audit_blocks_recursive_forbidden_flags(tmp_path):
    ready_repo, manifest_path = _depth_ready_manifest(tmp_path)
    ambiguous_fixture = ready_repo / "examples/synthetic/depth/ambiguous-role.json"
    fixture = load_json(ambiguous_fixture)
    fixture["nested"] = {"source": {"contains_real_client_data": True}}
    write_json(ambiguous_fixture, fixture)

    report, _ = run_synthetic_fixture_depth_audit(
        manifest_path=manifest_path,
        repo_root=ready_repo,
        out_dir=tmp_path / "fixture-depth-recursive-boundary",
    )

    assert report.status == "blocked_by_depth_audit_boundary_violation"
    assert any(
        "/nested/source/contains_real_client_data" in item for item in report.boundary_violations
    )


def test_synthetic_fixture_depth_audit_cli_reports_depth_gaps(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "audit-synthetic-fixture-depth",
            "--manifest",
            str(_manifest_path(repo_root)),
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "fixture-depth-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "synthetic_fixture_depth_gaps_identified"' in captured.out
    assert '"holdout_count": 4' in captured.out
    assert '"dimension_count": 7' in captured.out
    assert '"missing_dimension_count": 2' in captured.out
    assert '"external_writes_performed": false' in captured.out
    assert (tmp_path / "fixture-depth-cli" / "synthetic_fixture_depth_audit_report.json").is_file()
