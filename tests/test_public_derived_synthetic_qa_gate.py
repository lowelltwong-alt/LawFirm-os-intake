from hashlib import sha256

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import PublicDerivedSyntheticQAGateReport
from lawfirm_os_intake.public_data_cache import run_public_data_cache_audit
from lawfirm_os_intake.public_derived_synthetic_qa_gate import (
    run_public_derived_synthetic_qa_gate,
)
from lawfirm_os_intake.public_source_methodology import run_public_source_methodology_audit
from lawfirm_os_intake.public_synthetic_fixture_conversion import (
    run_public_synthetic_fixture_conversion_plan,
)
from lawfirm_os_intake.public_synthetic_fixture_conversion_review import (
    run_public_synthetic_fixture_conversion_review,
)
from lawfirm_os_intake.util import load_json, write_json


def _ready_chain(tmp_path, repo_root):
    _, methodology_dir = run_public_source_methodology_audit(
        repo_root=repo_root,
        out_dir=tmp_path / "methodology",
    )
    methodology_path = methodology_dir / "public_source_methodology_report.json"
    _, conversion_dir = run_public_synthetic_fixture_conversion_plan(
        methodology_report_path=methodology_path,
        out_dir=tmp_path / "conversion",
    )
    conversion_path = conversion_dir / "public_synthetic_fixture_conversion_plan.json"
    _, review_dir = run_public_synthetic_fixture_conversion_review(
        conversion_plan_path=conversion_path,
        out_dir=tmp_path / "review",
    )
    review_path = review_dir / "public_synthetic_fixture_conversion_review_packet.json"
    return methodology_path, conversion_path, review_path


def _sample_cache_entry(cache_root):
    sample = b'{"fields":["nature_of_suit","filing_date","disposition"]}\n'
    sample_path = cache_root / "fjc" / "sample-field-shape.json"
    sample_path.parent.mkdir(parents=True)
    sample_path.write_bytes(sample)
    return {
        "source_id": "fjc-idb",
        "source_url": "https://www.fjc.gov/research/idb",
        "source_type": "aggregate_case_metadata",
        "retrieved_at": "2026-07-01T00:00:00Z",
        "sha256": sha256(sample).hexdigest(),
        "byte_count": len(sample),
        "cache_ref": "fjc/sample-field-shape.json",
        "license_terms_note": "Public methodology reference; review terms before use.",
        "allowed_use": "Field-shape and aggregate distribution methodology review only.",
        "prohibited_use": "Runtime intake, identity reconstruction, legal or budget inference.",
        "retention_posture": "Ignored local cache; delete or regenerate after review.",
    }


def test_public_derived_synthetic_qa_gate_ready_for_review_metadata_only_chain(
    tmp_path,
    repo_root,
):
    methodology_path, conversion_path, review_path = _ready_chain(tmp_path, repo_root)

    report, run_dir = run_public_derived_synthetic_qa_gate(
        methodology_report_path=methodology_path,
        conversion_plan_path=conversion_path,
        conversion_review_packet_path=review_path,
        out_dir=tmp_path / "gate",
    )
    persisted = PublicDerivedSyntheticQAGateReport.model_validate(
        load_json(run_dir / "public_derived_synthetic_qa_gate_report.json")
    )

    assert persisted.public_derived_synthetic_qa_gate_report_id == (
        report.public_derived_synthetic_qa_gate_report_id
    )
    assert persisted.status == "public_derived_synthetic_qa_ready_for_review"
    assert persisted.methodology_source_count == 6
    assert persisted.conversion_spec_count == 6
    assert persisted.review_recommendation_count == 6
    assert persisted.review_red_team_note_count >= 4
    assert persisted.failed_check_count == 0
    assert persisted.blocked_check_count == 0
    assert persisted.cache_audit_required is False
    assert persisted.cache_custody_status == "not_required"
    assert persisted.fixture_generation_authorized is False
    assert persisted.fixture_files_mutated is False
    assert persisted.github_pr_created is False
    assert persisted.public_records_ingested is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert "fixture_generation_requires_separate_review" in (
        persisted.candidate_exception_lake_labels
    )

    notes = (run_dir / "public_derived_synthetic_qa_gate_report.md").read_text(encoding="utf-8")
    assert "does not approve fixture generation" in notes


def test_public_derived_synthetic_qa_gate_blocks_failed_cache_custody_when_samples_present(
    tmp_path,
    repo_root,
):
    methodology_path, conversion_path, review_path = _ready_chain(tmp_path, repo_root)
    cache_root = tmp_path / "public-data-cache"
    entry = _sample_cache_entry(cache_root)
    (cache_root / entry["cache_ref"]).write_text("changed after manifest\n", encoding="utf-8")
    write_json(cache_root / "public_data_cache_manifest.json", {"sources": [entry]})
    _, cache_audit_dir = run_public_data_cache_audit(
        repo_root=repo_root,
        cache_root=cache_root,
        out_dir=tmp_path / "cache-audit",
    )

    report, _ = run_public_derived_synthetic_qa_gate(
        methodology_report_path=methodology_path,
        conversion_plan_path=conversion_path,
        conversion_review_packet_path=review_path,
        public_data_cache_audit_report_path=(
            cache_audit_dir / "public_data_cache_audit_report.json"
        ),
        out_dir=tmp_path / "gate-cache-failed",
    )

    assert report.status == "blocked_by_public_derived_synthetic_qa_gate"
    assert report.cache_audit_required is True
    assert report.cache_custody_status == "failed"
    assert report.failed_check_count == 1
    assert any(
        check.check_id == "cache_custody_ready_when_samples_exist" and check.status == "failed"
        for check in report.checks
    )


def test_public_derived_synthetic_qa_gate_blocks_mismatched_conversion_plan_or_spec(
    tmp_path,
    repo_root,
):
    methodology_path, conversion_path, review_path = _ready_chain(tmp_path, repo_root)
    plan_payload = load_json(conversion_path)
    plan_payload["source_methodology_report_id"] = "wrong_methodology_id"
    plan_payload["specs"] = plan_payload["specs"][:-1]
    plan_payload["spec_count"] = len(plan_payload["specs"])
    tampered_plan = write_json(
        tmp_path / "tampered" / "public_synthetic_fixture_conversion_plan.json",
        plan_payload,
    )

    report, _ = run_public_derived_synthetic_qa_gate(
        methodology_report_path=methodology_path,
        conversion_plan_path=tampered_plan,
        conversion_review_packet_path=review_path,
        out_dir=tmp_path / "gate-mismatch",
    )

    assert report.status == "blocked_by_public_derived_synthetic_qa_gate"
    assert report.failed_check_count >= 1
    assert any(
        check.check_id == "conversion_plan_matches_methodology" and check.status == "failed"
        for check in report.checks
    )


def test_public_derived_synthetic_qa_gate_blocks_side_effect_flags(tmp_path, repo_root):
    methodology_path, conversion_path, review_path = _ready_chain(tmp_path, repo_root)
    plan_payload = load_json(conversion_path)
    plan_payload["fixture_files_mutated"] = True
    tampered_plan = write_json(
        tmp_path / "tampered-side-effect" / "public_synthetic_fixture_conversion_plan.json",
        plan_payload,
    )

    report, _ = run_public_derived_synthetic_qa_gate(
        methodology_report_path=methodology_path,
        conversion_plan_path=tampered_plan,
        conversion_review_packet_path=review_path,
        out_dir=tmp_path / "gate-side-effect",
    )

    assert report.status == "blocked_by_public_derived_synthetic_qa_gate"
    assert any(
        check.check_id == "no_public_payload_or_side_effects"
        and check.status == "failed"
        and "conversion_plan.fixture_files_mutated" in check.message
        for check in report.checks
    )


def test_public_derived_synthetic_qa_gate_cli_writes_report_and_markdown(
    tmp_path,
    repo_root,
    capsys,
):
    methodology_path, conversion_path, review_path = _ready_chain(tmp_path, repo_root)
    run_dir = tmp_path / "gate-cli"

    exit_code = main(
        [
            "build-public-derived-synthetic-qa-gate",
            "--methodology-report",
            str(methodology_path),
            "--conversion-plan",
            str(conversion_path),
            "--conversion-review-packet",
            str(review_path),
            "--out-dir",
            str(run_dir),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "public_derived_synthetic_qa_ready_for_review"' in captured.out
    assert '"conversion_spec_count": 6' in captured.out
    assert '"fixture_generation_authorized": false' in captured.out
    assert (run_dir / "public_derived_synthetic_qa_gate_report.json").is_file()
    assert (run_dir / "public_derived_synthetic_qa_gate_report.md").is_file()
