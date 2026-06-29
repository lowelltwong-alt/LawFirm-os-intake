from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    PublicSyntheticFixtureConversionPlan,
    PublicSyntheticFixtureConversionReviewOutcomeReport,
    PublicSyntheticFixtureConversionReviewRecord,
    PublicSyntheticFixturePRPackageReport,
)
from lawfirm_os_intake.public_source_methodology import run_public_source_methodology_audit
from lawfirm_os_intake.public_synthetic_fixture_conversion import (
    run_public_synthetic_fixture_conversion_plan,
)
from lawfirm_os_intake.public_synthetic_fixture_conversion_review import (
    run_public_synthetic_fixture_conversion_review,
)
from lawfirm_os_intake.public_synthetic_fixture_conversion_review_outcomes import (
    run_public_synthetic_fixture_conversion_review_outcome_record,
)
from lawfirm_os_intake.public_synthetic_fixture_pr_package import (
    build_public_synthetic_fixture_pr_package_report,
    run_public_synthetic_fixture_pr_package,
)
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


REQUIRED_APPROVAL_GATES = [
    "human_public_synthetic_conversion_review",
    "source_license_review",
    "privacy_review",
    "retention_decision",
    "separate_synthetic_fixture_generation_pr_if_approved",
    "synthetic_fixture_gold_review",
    "red_team_identity_reconstruction_review",
]


def _conversion_plan_and_review_packet(tmp_path, repo_root):
    _, methodology_dir = run_public_source_methodology_audit(
        repo_root=repo_root,
        out_dir=tmp_path / "public-source-methodology",
    )
    _, conversion_dir = run_public_synthetic_fixture_conversion_plan(
        methodology_report_path=methodology_dir / "public_source_methodology_report.json",
        out_dir=tmp_path / "public-synthetic-fixture-conversion",
    )
    _, review_dir = run_public_synthetic_fixture_conversion_review(
        conversion_plan_path=conversion_dir / "public_synthetic_fixture_conversion_plan.json",
        out_dir=tmp_path / "public-synthetic-fixture-conversion-review",
    )
    return (
        conversion_dir / "public_synthetic_fixture_conversion_plan.json",
        review_dir / "public_synthetic_fixture_conversion_review_packet.json",
    )


def _review_record(packet, *, source_id, outcome):
    template = next(item for item in packet["decision_templates"] if item["source_id"] == source_id)
    accepted = outcome == "approve_conversion_spec_for_separate_fixture_pr"
    return PublicSyntheticFixtureConversionReviewRecord(
        conversion_review_id=f"public-fixture-pr-package-review-{source_id}-{outcome}",
        review_packet_id=packet["review_packet_id"],
        conversion_plan_id=packet["conversion_plan_id"],
        conversion_spec_id=template["conversion_spec_id"],
        source_id=source_id,
        reviewer_id="synthetic-reviewer",
        reviewed_at="2026-06-26T00:00:00Z",
        outcome=outcome,
        decision_reason="Synthetic public fixture PR package review decision.",
        accepted_required_gates=REQUIRED_APPROVAL_GATES if accepted else [],
        rejected_or_revision_reasons=[],
        required_followups=(
            [] if accepted else ["Resolve privacy and license posture before fixture PR work."]
        ),
        evidence_refs=[packet["review_packet_id"], *template["required_evidence_refs"]],
    )


def _review_outcome_report_path(tmp_path, repo_root, *, source_id, outcome):
    plan_path, packet_path = _conversion_plan_and_review_packet(tmp_path, repo_root)
    packet = load_json(packet_path)
    review_path = write_json(
        tmp_path / f"{source_id}-review-decision.json",
        _review_record(packet, source_id=source_id, outcome=outcome).model_dump(mode="json"),
    )
    _, outcome_dir = run_public_synthetic_fixture_conversion_review_outcome_record(
        review_packet_path=packet_path,
        review_path=review_path,
        out_dir=tmp_path / f"{source_id}-public-conversion-review-outcome",
    )
    return (
        plan_path,
        outcome_dir / "public_synthetic_fixture_conversion_review_outcome_report.json",
    )


def test_public_fixture_pr_package_builds_manual_item_for_approved_outcome(tmp_path, repo_root):
    plan_path, outcome_report_path = _review_outcome_report_path(
        tmp_path,
        repo_root,
        source_id="courtlistener-recap",
        outcome="approve_conversion_spec_for_separate_fixture_pr",
    )

    report, run_dir = run_public_synthetic_fixture_pr_package(
        review_outcome_report_path=outcome_report_path,
        conversion_plan_path=plan_path,
        out_dir=tmp_path / "public-fixture-pr-package",
    )
    persisted = PublicSyntheticFixturePRPackageReport.model_validate(
        load_json(run_dir / "public_synthetic_fixture_pr_package_report.json")
    )
    items = load_jsonl(run_dir / "public_synthetic_fixture_pr_package_items.jsonl")

    assert persisted.fixture_pr_package_report_id == report.fixture_pr_package_report_id
    assert persisted.status == "public_fixture_pr_package_ready_for_manual_pr"
    assert persisted.manual_fixture_generation_pr_required is True
    assert persisted.item_count == persisted.ready_item_count == len(items) == 1
    assert persisted.target_fixture_family == "docket_structure"
    assert persisted.package_items[0].target_fixture_family == "docket_structure"
    assert "raw_public_payloads" in persisted.package_items[0].forbidden_inputs
    assert all(check.status == "passed" for check in persisted.checks)
    assert persisted.fixture_generation_authorized is False
    assert persisted.github_pr_created is False
    assert persisted.fixture_files_mutated is False
    assert persisted.public_records_ingested is False
    assert persisted.raw_public_payload_committed is False
    assert persisted.legal_knowledge_adapter_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes = (run_dir / "public_synthetic_fixture_pr_package_report.md").read_text(encoding="utf-8")
    assert "does not edit fixtures" in notes
    assert "Forbidden inputs" in notes


def test_public_fixture_pr_package_noops_for_needs_more_information(tmp_path, repo_root):
    plan_path, outcome_report_path = _review_outcome_report_path(
        tmp_path,
        repo_root,
        source_id="cmu-enron-email",
        outcome="needs_more_information",
    )

    report, _ = run_public_synthetic_fixture_pr_package(
        review_outcome_report_path=outcome_report_path,
        conversion_plan_path=plan_path,
        out_dir=tmp_path / "public-fixture-pr-package-noop",
    )

    assert report.status == "no_public_fixture_pr_package_needed"
    assert report.manual_fixture_generation_pr_required is False
    assert report.item_count == 0
    assert report.package_items == []
    assert all(check.status == "passed" for check in report.checks)
    assert report.github_pr_created is False
    assert report.fixture_files_mutated is False
    assert report.silent_learning_performed is False


def test_public_fixture_pr_package_blocks_mismatched_conversion_plan(tmp_path, repo_root):
    plan_path, outcome_report_path = _review_outcome_report_path(
        tmp_path,
        repo_root,
        source_id="courtlistener-recap",
        outcome="approve_conversion_spec_for_separate_fixture_pr",
    )
    plan_payload = load_json(plan_path)
    plan_payload["conversion_plan_id"] = "wrong-plan-id"
    mismatched_plan_path = write_json(
        tmp_path / "mismatched-public-conversion-plan.json",
        plan_payload,
    )

    report = build_public_synthetic_fixture_pr_package_report(
        review_outcome_report=PublicSyntheticFixtureConversionReviewOutcomeReport.model_validate(
            load_json(outcome_report_path)
        ),
        review_outcome_report_ref=str(outcome_report_path),
        conversion_plan=PublicSyntheticFixtureConversionPlan.model_validate(
            load_json(mismatched_plan_path)
        ),
        conversion_plan_ref=str(mismatched_plan_path),
    )

    assert report.status == "blocked_by_public_fixture_review_outcome"
    assert report.manual_fixture_generation_pr_required is False
    assert any(
        check.check_id == "conversion_plan_matches_review_outcome" and check.status == "failed"
        for check in report.checks
    )
    assert report.fixture_files_mutated is False
    assert report.public_records_ingested is False
    assert report.silent_learning_performed is False


def test_public_fixture_pr_package_cli_writes_report(tmp_path, repo_root, capsys):
    plan_path, outcome_report_path = _review_outcome_report_path(
        tmp_path,
        repo_root,
        source_id="courtlistener-recap",
        outcome="approve_conversion_spec_for_separate_fixture_pr",
    )

    exit_code = main(
        [
            "build-public-synthetic-fixture-pr-package",
            "--review-outcome-report",
            str(outcome_report_path),
            "--conversion-plan",
            str(plan_path),
            "--out-dir",
            str(tmp_path / "public-fixture-pr-package-cli"),
        ]
    )
    captured = capsys.readouterr()
    report = PublicSyntheticFixturePRPackageReport.model_validate(
        load_json(
            tmp_path
            / "public-fixture-pr-package-cli"
            / "public_synthetic_fixture_pr_package_report.json"
        )
    )

    assert exit_code == 0
    assert report.status == "public_fixture_pr_package_ready_for_manual_pr"
    assert '"manual_fixture_generation_pr_required": true' in captured.out
    assert '"github_pr_created": false' in captured.out
    assert '"fixture_files_mutated": false' in captured.out
    assert '"public_records_ingested": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
