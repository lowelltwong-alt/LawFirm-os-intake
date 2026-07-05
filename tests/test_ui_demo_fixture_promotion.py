import json
from pathlib import Path

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.ui_demo_fixture_promotion import (
    UIDemoFixturePromotionSpec,
    promote_ui_demo_run_fixtures,
)
from lawfirm_os_intake.util import load_json


STALE_SHA = "sha256:" + ("1" * 64)


def _write_json(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def _report(status: str, **extra):
    payload = {
        "status": status,
        "candidate_only": True,
        "synthetic_only": True,
        "non_authoritative": True,
        "local_json_only": True,
        "external_writes_performed": False,
        "lake_write_performed": False,
        "sqlite_write_performed": False,
        "budget_submission_authorized": False,
        "matter_opening_authorized": False,
        "silent_learning_performed": False,
    }
    payload.update(extra)
    return payload


def _detail(*, detail_report_id, report_kind, file_name, fixture_name, required=True):
    return {
        "detail_report_id": detail_report_id,
        "label": detail_report_id,
        "report_kind": report_kind,
        "file_name": file_name,
        "required": required,
        "present": True,
        "status": "ready",
        "renderer": "TestPanel",
        "artifact_ref": fixture_name,
        "source_sha256": STALE_SHA,
        "candidate_only": True,
        "synthetic_only": True,
        "external_writes_performed": False,
        "notes": ["seeded detail"],
    }


def _seed_fixture_root(tmp_path):
    fixtures = tmp_path / "fixtures"
    _write_json(fixtures / "demo-run-manifest.json", {"overallStatus": "old"})
    _write_json(
        fixtures / "demo-synthetic-confidence-summary-report.json",
        _report("old_confidence"),
    )
    _write_json(
        fixtures / "demo-rust-fixture-boundary-report.json",
        {
            "schema_version": "0.1",
            "checker": "fixture-boundary-checker",
            "status": "passed",
            "root": str(fixtures),
            "ui_bundle_ref": str(fixtures / "demo-ui-review-data-bundle.json"),
            "checked_json_file_count": 0,
            "checked_object_count": 0,
            "failure_count": 0,
            "failures": [],
            "candidate_only": True,
            "synthetic_only": True,
            "non_authoritative": True,
            "local_json_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )
    _write_json(
        fixtures / "demo-rust-fixture-manifest-report.json",
        {
            "schema_version": "0.1",
            "scanner": "fixture-manifest-scanner",
            "status": "passed",
            "root": str(fixtures),
            "manifest_sha256": "sha256:" + ("0" * 64),
            "checked_json_file_count": 0,
            "parsed_json_file_count": 0,
            "parse_error_count": 0,
            "skipped_file_count": 0,
            "skipped_files": [],
            "total_byte_count": 0,
            "files": [],
            "failure_count": 0,
            "failures": [],
            "candidate_only": True,
            "synthetic_only": True,
            "non_authoritative": True,
            "local_json_only": True,
            "external_writes_performed": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "budget_submission_authorized": False,
            "matter_opening_authorized": False,
            "silent_learning_performed": False,
        },
    )
    details = [
        _detail(
            detail_report_id="ui-review-manifest",
            report_kind="ui_review_manifest",
            file_name="ui_review_manifest.json",
            fixture_name="demo-run-manifest.json",
        ),
        _detail(
            detail_report_id="synthetic-confidence-summary",
            report_kind="synthetic_confidence_summary",
            file_name="synthetic_confidence_summary_report.json",
            fixture_name="demo-synthetic-confidence-summary-report.json",
        ),
        _detail(
            detail_report_id="rust-fixture-boundary",
            report_kind="rust_fixture_boundary",
            file_name="rust_fixture_boundary_report.json",
            fixture_name="demo-rust-fixture-boundary-report.json",
            required=False,
        ),
        _detail(
            detail_report_id="rust-fixture-manifest",
            report_kind="rust_fixture_manifest",
            file_name="rust_fixture_manifest_report.json",
            fixture_name="demo-rust-fixture-manifest-report.json",
            required=False,
        ),
    ]
    _write_json(
        fixtures / "demo-ui-review-data-bundle.json",
        {
            "schema_version": "0.1",
            "ui_review_data_bundle_id": "ui_review_data_bundle_seed",
            "status": "ready_for_review",
            "run_root_ref": "<demo-run-root>",
            "detail_report_count": len(details),
            "required_detail_report_count": 2,
            "present_detail_report_count": len(details),
            "missing_required_detail_report_count": 0,
            "external_write_report_count": 0,
            "detail_reports": details,
            "required_next_actions": ["seeded"],
            "candidate_only": True,
            "synthetic_only": True,
            "non_authoritative": True,
            "local_json_only": True,
            "not_authorized_for_external_write": True,
            "not_authorized_for_lake_write": True,
            "not_authorized_for_sqlite_write": True,
            "not_authorized_for_budget_submission": True,
            "not_authorized_for_matter_opening": True,
            "not_authorized_for_calibration": True,
            "budget_amount_output_authorized": False,
            "budget_submission_authorized": False,
            "conflict_conclusion_emitted": False,
            "matter_opening_authorized": False,
            "training_pipeline_created": False,
            "lake_write_performed": False,
            "sqlite_write_performed": False,
            "external_writes_performed": False,
            "silent_learning_performed": False,
            "generated_at": "2026-07-05T00:00:00Z",
        },
    )
    return fixtures


def _seed_run_root(tmp_path, *, side_effect=False, run_rel="run"):
    run = tmp_path / run_rel
    _write_json(
        run / "ui_review_manifest.json",
        {
            "manifestId": "ui_review_manifest_test",
            "generatedAt": "2026-07-05T00:00:00Z",
            "runLabel": "Test Run",
            "practiceArea": "synthetic_intake",
            "matterFamily": "labor_employment",
            "overallStatus": "blocked",
            "boundaryFlags": {
                "readOnly": True,
                "localJsonOnly": True,
                "networkCallsAllowed": False,
                "mutationCommandsAllowed": False,
                "exceptionLakeWritesAllowed": False,
                "sqliteWritesAllowed": False,
                "publicRuntimeIngestionAllowed": False,
                "budgetSubmissionAllowed": False,
                "matterOpeningAllowed": False,
            },
            "artifacts": [],
            "qualityGates": [],
            "blockerSummary": [str(run / "quality" / "synthetic_confidence_summary_report.json")],
            "redTeamNotes": [],
        },
    )
    _write_json(
        run / "quality" / "synthetic_confidence_summary_report.json",
        _report(
            "synthetic_confidence_summary_ready_for_review",
            source_ui_review_data_bundle_ref=str(run / "ui_review_data_bundle.json"),
            relative_run_ref=(
                ".lawfirm-os-intake/synthetic-qa-review/quality/"
                "synthetic_confidence_summary_report.json"
            ),
            detail_reports=[],
            external_writes_performed=side_effect,
        ),
    )
    return run


def _specs():
    return (
        UIDemoFixturePromotionSpec("ui_review_manifest.json", "demo-run-manifest.json"),
        UIDemoFixturePromotionSpec(
            "quality/synthetic_confidence_summary_report.json",
            "demo-synthetic-confidence-summary-report.json",
        ),
    )


def test_promote_ui_demo_run_fixtures_requires_explicit_write_flag(repo_root, tmp_path):
    fixtures = _seed_fixture_root(tmp_path)
    run = _seed_run_root(tmp_path)
    before = (fixtures / "demo-run-manifest.json").read_text(encoding="utf-8")

    code = main(
        [
            "promote-ui-demo-run-fixtures",
            "--run-root",
            str(run),
            "--fixtures-root",
            str(fixtures),
            "--out-dir",
            str(tmp_path / "out"),
            "--repo-root",
            str(repo_root),
        ]
    )

    report = load_json(tmp_path / "out" / "ui_demo_fixture_promotion_report.json")
    assert code == 2
    assert report["status"] == "ui_demo_fixture_promotion_blocked_write_flag_required"
    assert report["local_fixture_updates_performed"] is False
    assert (fixtures / "demo-run-manifest.json").read_text(encoding="utf-8") == before


def test_promote_ui_demo_run_fixtures_sanitizes_and_verifies(repo_root, tmp_path):
    fixtures = _seed_fixture_root(tmp_path)
    run = _seed_run_root(tmp_path, run_rel=Path(".lawfirm-os-intake") / "synthetic-qa-review")
    _write_json(run / "quality" / "unallowlisted_extra_report.json", _report("extra"))

    report, report_path = promote_ui_demo_run_fixtures(
        run_root=run,
        fixtures_root=fixtures,
        out_dir=tmp_path / "out",
        repo_root=repo_root,
        write_fixtures=True,
        generated_at="2026-07-05T00:00:00Z",
        promotion_specs=_specs(),
    )

    persisted = load_json(report_path)
    manifest = load_json(fixtures / "demo-run-manifest.json")
    confidence = load_json(fixtures / "demo-synthetic-confidence-summary-report.json")
    bundle = load_json(fixtures / "demo-ui-review-data-bundle.json")
    assert report.status == "ui_demo_fixture_promotion_verified"
    assert persisted["status"] == "ui_demo_fixture_promotion_verified"
    assert persisted["rust_boundary_status"] == "passed"
    assert persisted["wrapper_refresh_status"] == "ui_demo_fixture_refresh_verified"
    assert persisted["manifest_status"] == "passed"
    assert persisted["source_hash_gate_status"] == "passed"
    assert persisted["snapshot_gate_status"] == "passed"
    assert persisted["generated_wrapper_count"] == 3
    assert persisted["sanitized_replacement_count"] >= 2
    assert persisted["forbidden_run_root_leak_count"] == 0
    assert persisted["local_fixture_updates_performed"] is True
    assert persisted["rollback_performed"] is False
    assert "<demo-run-root>" in manifest["blockerSummary"][0]
    assert str(run) not in json.dumps(confidence)
    assert ".lawfirm-os-intake" not in json.dumps(confidence)
    assert confidence["source_ui_review_data_bundle_ref"].startswith("<demo-run-root>")
    assert bundle["ui_review_data_bundle_id"].startswith("ui_review_data_bundle_")
    assert all(
        detail["source_sha256"].startswith("sha256:")
        for detail in bundle["detail_reports"]
        if detail["present"] is True
    )
    assert not (fixtures / "demo-unallowlisted-extra-report.json").exists()


def test_promote_ui_demo_run_fixtures_blocks_missing_source_without_mutation(repo_root, tmp_path):
    fixtures = _seed_fixture_root(tmp_path)
    run = _seed_run_root(tmp_path)
    before = (fixtures / "demo-run-manifest.json").read_text(encoding="utf-8")

    report, _ = promote_ui_demo_run_fixtures(
        run_root=run,
        fixtures_root=fixtures,
        out_dir=tmp_path / "out",
        repo_root=repo_root,
        write_fixtures=True,
        promotion_specs=(
            UIDemoFixturePromotionSpec("missing_report.json", "demo-run-manifest.json"),
        ),
    )

    assert report.status == "ui_demo_fixture_promotion_failed"
    assert report.missing_source_count == 1
    assert report.local_fixture_updates_performed is False
    assert (fixtures / "demo-run-manifest.json").read_text(encoding="utf-8") == before


def test_promote_ui_demo_run_fixtures_blocks_ambiguous_source(repo_root, tmp_path):
    fixtures = _seed_fixture_root(tmp_path)
    run = _seed_run_root(tmp_path)
    _write_json(run / "a" / "duplicate_report.json", _report("first"))
    _write_json(run / "b" / "duplicate_report.json", _report("second"))
    before = (fixtures / "demo-run-manifest.json").read_text(encoding="utf-8")

    report, _ = promote_ui_demo_run_fixtures(
        run_root=run,
        fixtures_root=fixtures,
        out_dir=tmp_path / "out",
        repo_root=repo_root,
        write_fixtures=True,
        promotion_specs=(
            UIDemoFixturePromotionSpec(
                "quality/duplicate_report.json",
                "demo-run-manifest.json",
            ),
        ),
    )

    assert report.status == "ui_demo_fixture_promotion_failed"
    assert report.ambiguous_source_count == 1
    assert report.local_fixture_updates_performed is False
    assert (fixtures / "demo-run-manifest.json").read_text(encoding="utf-8") == before


def test_promote_ui_demo_run_fixtures_blocks_out_of_root_source_ref(repo_root, tmp_path):
    fixtures = _seed_fixture_root(tmp_path)
    run = _seed_run_root(tmp_path)
    _write_json(tmp_path / "outside_report.json", _report("outside"))
    before = (fixtures / "demo-run-manifest.json").read_text(encoding="utf-8")

    report, _ = promote_ui_demo_run_fixtures(
        run_root=run,
        fixtures_root=fixtures,
        out_dir=tmp_path / "out",
        repo_root=repo_root,
        write_fixtures=True,
        promotion_specs=(
            UIDemoFixturePromotionSpec(
                "../outside_report.json",
                "demo-run-manifest.json",
            ),
        ),
    )

    assert report.status == "ui_demo_fixture_promotion_failed"
    assert report.missing_source_count == 1
    assert "under run root" in report.items[0].message
    assert report.local_fixture_updates_performed is False
    assert (fixtures / "demo-run-manifest.json").read_text(encoding="utf-8") == before


def test_promote_ui_demo_run_fixtures_blocks_side_effect_source(repo_root, tmp_path):
    fixtures = _seed_fixture_root(tmp_path)
    run = _seed_run_root(tmp_path, side_effect=True)
    before = (fixtures / "demo-synthetic-confidence-summary-report.json").read_text(
        encoding="utf-8"
    )

    report, _ = promote_ui_demo_run_fixtures(
        run_root=run,
        fixtures_root=fixtures,
        out_dir=tmp_path / "out",
        repo_root=repo_root,
        write_fixtures=True,
        promotion_specs=_specs(),
    )

    assert report.status == "ui_demo_fixture_promotion_failed"
    assert report.blocked_side_effect_count == 1
    assert report.local_fixture_updates_performed is False
    assert (fixtures / "demo-synthetic-confidence-summary-report.json").read_text(
        encoding="utf-8"
    ) == before
