from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import PublicSyntheticFixtureConversionPlan
from lawfirm_os_intake.public_source_methodology import run_public_source_methodology_audit
from lawfirm_os_intake.public_synthetic_fixture_conversion import (
    run_public_synthetic_fixture_conversion_plan,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


def _methodology_report_path(tmp_path, repo_root):
    _, run_dir = run_public_source_methodology_audit(
        repo_root=repo_root,
        out_dir=tmp_path / "public-source-methodology",
    )
    return run_dir / "public_source_methodology_report.json"


def test_public_synthetic_fixture_conversion_plan_ready(tmp_path, repo_root):
    methodology_report_path = _methodology_report_path(tmp_path, repo_root)

    plan, run_dir = run_public_synthetic_fixture_conversion_plan(
        methodology_report_path=methodology_report_path,
        out_dir=tmp_path / "public-synthetic-fixture-conversion",
    )
    persisted = PublicSyntheticFixtureConversionPlan.model_validate(
        load_json(run_dir / "public_synthetic_fixture_conversion_plan.json")
    )
    specs = load_jsonl(run_dir / "public_synthetic_fixture_conversion_specs.jsonl")

    assert persisted.conversion_plan_id == plan.conversion_plan_id
    assert persisted.status == "ready_for_human_conversion_review"
    assert persisted.spec_count == len(specs) == 6
    assert all(check.status == "passed" for check in persisted.checks)
    assert all(
        spec.review_status == "planned_for_human_conversion_review" for spec in persisted.specs
    )
    assert persisted.public_records_ingested is False
    assert persisted.raw_public_payload_committed is False
    assert persisted.synthetic_fixtures_created is False
    assert persisted.fixture_files_mutated is False
    assert persisted.connector_implemented is False
    assert persisted.legal_knowledge_adapter_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False

    by_source = {spec.source_id: spec for spec in persisted.specs}
    assert by_source["courtlistener-recap"].target_fixture_family == "docket_structure"
    assert by_source["cmu-enron-email"].target_fixture_family == "messy_email_structure"
    assert "prompt_injection_treated_as_data" in (
        by_source["cmu-enron-email"].required_synthetic_gold_checks
    )
    for spec in persisted.specs:
        assert "real_party_names" in spec.forbidden_inputs
        assert "raw_public_payloads" in spec.forbidden_inputs
        assert "does_plan_create_or_mutate_fixture_files" in spec.required_red_team_checks

    notes = (run_dir / "public_synthetic_fixture_conversion_plan.md").read_text(encoding="utf-8")
    assert "Public records ingested: False" in notes
    assert "Red-team checks" in notes


def test_public_synthetic_fixture_conversion_blocks_unready_methodology(tmp_path, repo_root):
    methodology_report_path = _methodology_report_path(tmp_path, repo_root)
    payload = load_json(methodology_report_path)
    payload["status"] = "blocked_public_source_methodology"
    payload["checks"][0]["status"] = "blocked"
    payload["checks"][0]["message"] = "Synthetic blocked methodology fixture."
    blocked_path = write_json(
        tmp_path / "blocked-methodology" / "public_source_methodology_report.json",
        payload,
    )

    plan, run_dir = run_public_synthetic_fixture_conversion_plan(
        methodology_report_path=blocked_path,
        out_dir=tmp_path / "public-synthetic-fixture-conversion-blocked",
    )

    assert plan.status == "blocked_public_methodology_not_ready"
    assert plan.spec_count == 0
    assert load_jsonl(run_dir / "public_synthetic_fixture_conversion_specs.jsonl") == []
    assert any(
        check.check_id == "source_methodology_report_ready" and check.status == "blocked"
        for check in plan.checks
    )
    assert plan.public_records_ingested is False
    assert plan.synthetic_fixtures_created is False
    assert plan.fixture_files_mutated is False
    assert plan.external_writes_performed is False


def test_public_synthetic_fixture_conversion_cli(tmp_path, repo_root, capsys):
    methodology_report_path = _methodology_report_path(tmp_path, repo_root)
    exit_code = main(
        [
            "plan-public-synthetic-fixture-conversion",
            "--methodology-report",
            str(methodology_report_path),
            "--out-dir",
            str(tmp_path / "public-synthetic-fixture-conversion-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_human_conversion_review"' in captured.out
    assert '"spec_count": 6' in captured.out
    assert '"synthetic_fixtures_created": false' in captured.out
    assert (
        tmp_path
        / "public-synthetic-fixture-conversion-cli"
        / "public_synthetic_fixture_conversion_plan.json"
    ).is_file()
