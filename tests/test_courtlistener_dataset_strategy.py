import yaml

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.courtlistener_dataset_strategy import (
    build_courtlistener_dataset_strategy_report,
    run_courtlistener_dataset_strategy_audit,
)
from lawfirm_os_intake.models import CourtListenerDatasetStrategyReport
from lawfirm_os_intake.rust_transition_policy import load_rust_transition_policy
from lawfirm_os_intake.util import load_json


def test_courtlistener_dataset_strategy_ready_for_review(tmp_path, repo_root):
    report, run_dir = run_courtlistener_dataset_strategy_audit(
        repo_root=repo_root,
        out_dir=tmp_path / "courtlistener-dataset-strategy",
    )
    persisted = CourtListenerDatasetStrategyReport.model_validate(
        load_json(run_dir / "courtlistener_dataset_strategy_report.json")
    )

    assert persisted.courtlistener_dataset_strategy_report_id == (
        report.courtlistener_dataset_strategy_report_id
    )
    assert persisted.status == "ready_for_human_dataset_strategy_review"
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.offline_fixture_mode is True
    assert persisted.allow_live_calls is False
    assert persisted.pacer_purchase_allowed is False
    assert persisted.recap_fetch_purchase_allowed is False
    assert persisted.uploads_allowed is False
    assert persisted.court_writes_allowed is False
    assert persisted.sealed_or_restricted_requests_allowed is False
    assert persisted.real_client_data_allowed is False
    assert persisted.privileged_data_allowed is False
    assert persisted.public_records_ingested is False
    assert persisted.connector_implemented is False
    assert persisted.rust_runtime_added is False
    assert persisted.rust_replacement_allowed is False
    assert persisted.training_pipeline_created is False
    assert persisted.external_writes_performed is False
    assert persisted.primary_practice_area == "labor_employment"
    assert "single_plaintiff_employment_discrimination" in persisted.starter_matter_families
    assert "courtlistener_removal_state_pleadings_proxy" in persisted.source_profile_ids
    assert "/dockets/" in persisted.endpoint_paths
    assert "courtlistener_snapshot_normalization" in persisted.rust_shadow_scope

    notes = (run_dir / "courtlistener_dataset_strategy_report.md").read_text(encoding="utf-8")
    assert "Live calls allowed: False" in notes
    assert "Rust runtime added: False" in notes


def test_courtlistener_dataset_strategy_blocks_live_calls_and_purchases(
    tmp_path,
    repo_root,
):
    config = yaml.safe_load(
        (repo_root / "config/courtlistener-dataset-strategy.yaml").read_text(encoding="utf-8")
    )
    config["source_modes"]["allow_live_calls"] = True
    config["permissions"]["allow_pacer_purchase"] = True
    config["permissions"]["allow_recap_fetch_purchase"] = True
    config_path = tmp_path / "unsafe-courtlistener-strategy.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    report = build_courtlistener_dataset_strategy_report(
        repo_root=repo_root,
        strategy_config_path=config_path,
    )

    assert report.status == "blocked_courtlistener_dataset_strategy"
    assert report.allow_live_calls is True
    assert report.pacer_purchase_allowed is True
    assert report.recap_fetch_purchase_allowed is True
    failed = {check.check_id for check in report.checks if check.status == "failed"}
    assert "source_modes_default_offline" in failed
    assert "purchasing_uploads_and_court_writes_disabled" in failed
    assert report.public_records_ingested is False
    assert report.external_writes_performed is False


def test_courtlistener_dataset_strategy_blocks_post_discovery_positive_leak(
    tmp_path,
    repo_root,
):
    config = yaml.safe_load(
        (repo_root / "config/courtlistener-dataset-strategy.yaml").read_text(encoding="utf-8")
    )
    config["positive_document_types"].append("deposition_transcripts")
    config_path = tmp_path / "positive-leak-courtlistener-strategy.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    report = build_courtlistener_dataset_strategy_report(
        repo_root=repo_root,
        strategy_config_path=config_path,
    )

    assert report.status == "blocked_courtlistener_dataset_strategy"
    early_case_check = next(
        check
        for check in report.checks
        if check.check_id == "early_case_window_and_negative_routing_declared"
    )
    assert early_case_check.status == "failed"
    assert (
        "deposition_transcripts"
        in early_case_check.details["prohibited_positive_document_types_present"]
    )


def test_courtlistener_dataset_strategy_cli(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "audit-courtlistener-dataset-strategy",
            "--repo-root",
            str(repo_root),
            "--out-dir",
            str(tmp_path / "courtlistener-dataset-strategy-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_human_dataset_strategy_review"' in captured.out
    assert '"allow_live_calls": false' in captured.out
    assert '"rust_runtime_added": false' in captured.out
    assert (
        tmp_path
        / "courtlistener-dataset-strategy-cli"
        / "courtlistener_dataset_strategy_report.json"
    ).is_file()


def test_rust_transition_policy_includes_dataset_shadow_scope(repo_root):
    policy = load_rust_transition_policy()

    assert "courtlistener_snapshot_normalization" in policy.candidate_rust_hot_path_scope
    assert "offline_corpus_manifest_indexing" in policy.candidate_rust_hot_path_scope
    assert "document_label_offset_indexing" in policy.candidate_rust_hot_path_scope
    assert "public_record_download_or_purchase" in policy.forbidden_rust_scope
    assert "legal_training_corpus_admission" in policy.forbidden_rust_scope
    assert "courtlistener_snapshot_normalization" not in policy.eligible_hot_path_scope
    assert policy.no_rust_runtime_added is True
    assert policy.rust_replacement_allowed is False
