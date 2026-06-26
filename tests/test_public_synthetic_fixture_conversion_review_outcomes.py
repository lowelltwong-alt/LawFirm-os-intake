import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    PublicSyntheticFixtureConversionReviewOutcomeReport,
    PublicSyntheticFixtureConversionReviewPacket,
    PublicSyntheticFixtureConversionReviewRecord,
)
from lawfirm_os_intake.public_source_methodology import run_public_source_methodology_audit
from lawfirm_os_intake.public_synthetic_fixture_conversion import (
    run_public_synthetic_fixture_conversion_plan,
)
from lawfirm_os_intake.public_synthetic_fixture_conversion_review import (
    run_public_synthetic_fixture_conversion_review,
)
from lawfirm_os_intake.public_synthetic_fixture_conversion_review_outcomes import (
    build_public_synthetic_fixture_conversion_review_outcome_report,
    run_public_synthetic_fixture_conversion_review_outcome_record,
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


def _review_packet(tmp_path, repo_root):
    _, methodology_dir = run_public_source_methodology_audit(
        repo_root=repo_root,
        out_dir=tmp_path / "public-source-methodology",
    )
    _, conversion_dir = run_public_synthetic_fixture_conversion_plan(
        methodology_report_path=methodology_dir / "public_source_methodology_report.json",
        out_dir=tmp_path / "public-synthetic-fixture-conversion",
    )
    packet, run_dir = run_public_synthetic_fixture_conversion_review(
        conversion_plan_path=conversion_dir / "public_synthetic_fixture_conversion_plan.json",
        out_dir=tmp_path / "public-synthetic-fixture-conversion-review",
    )
    persisted = PublicSyntheticFixtureConversionReviewPacket.model_validate(
        load_json(run_dir / "public_synthetic_fixture_conversion_review_packet.json")
    )
    assert persisted.review_packet_id == packet.review_packet_id
    return persisted, run_dir / "public_synthetic_fixture_conversion_review_packet.json"


def _record_from_packet(
    packet,
    *,
    source_id="courtlistener-recap",
    outcome="approve_conversion_spec_for_separate_fixture_pr",
    accepted_required_gates=None,
    rejected_or_revision_reasons=None,
    required_followups=None,
):
    template = next(item for item in packet.decision_templates if item.source_id == source_id)
    accepted = outcome == "approve_conversion_spec_for_separate_fixture_pr"
    return PublicSyntheticFixtureConversionReviewRecord(
        conversion_review_id=f"public-conversion-review-{source_id}-{outcome}",
        review_packet_id=packet.review_packet_id,
        conversion_plan_id=packet.conversion_plan_id,
        conversion_spec_id=template.conversion_spec_id,
        source_id=source_id,
        reviewer_id="synthetic-reviewer",
        reviewed_at="2026-06-26T00:00:00Z",
        outcome=outcome,
        decision_reason="Synthetic human conversion review decision.",
        accepted_required_gates=(
            accepted_required_gates
            if accepted_required_gates is not None
            else (REQUIRED_APPROVAL_GATES if accepted else [])
        ),
        rejected_or_revision_reasons=rejected_or_revision_reasons or [],
        required_followups=required_followups or [],
        evidence_refs=[packet.review_packet_id, *template.required_evidence_refs],
    )


def test_public_conversion_review_outcome_records_approval_without_mutation(tmp_path, repo_root):
    packet, packet_path = _review_packet(tmp_path, repo_root)
    record = _record_from_packet(packet)

    report = build_public_synthetic_fixture_conversion_review_outcome_report(
        review_packet=packet,
        review_packet_ref=str(packet_path),
        review_record=record,
        history_ref="public_synthetic_fixture_conversion_review_history.jsonl",
    )

    assert report.status == "conversion_review_recorded_separate_fixture_pr_required"
    assert report.accepted_for_separate_fixture_pr is True
    assert report.separate_fixture_generation_pr_required is True
    assert all(check.status == "passed" for check in report.checks)
    assert report.fixture_generation_authorized is False
    assert report.fixture_pr_created is False
    assert report.fixture_files_mutated is False
    assert report.public_records_ingested is False
    assert report.raw_public_payload_committed is False
    assert report.connector_implemented is False
    assert report.legal_knowledge_adapter_authorized is False
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.silent_learning_performed is False


def test_public_conversion_review_outcome_cli_writes_record_history_and_report(
    tmp_path, repo_root, capsys
):
    packet, packet_path = _review_packet(tmp_path, repo_root)
    review_path = write_json(
        tmp_path / "public_conversion_review_decision.json",
        _record_from_packet(packet).model_dump(mode="json"),
    )

    exit_code = main(
        [
            "record-public-synthetic-fixture-conversion-review",
            "--review-packet",
            str(packet_path),
            "--review",
            str(review_path),
            "--out-dir",
            str(tmp_path / "public-synthetic-fixture-conversion-review-outcome"),
        ]
    )
    captured = capsys.readouterr()
    report_path = (
        tmp_path
        / "public-synthetic-fixture-conversion-review-outcome"
        / "public_synthetic_fixture_conversion_review_outcome_report.json"
    )
    history_path = (
        tmp_path
        / "public-synthetic-fixture-conversion-review-outcome"
        / "public_synthetic_fixture_conversion_review_history.jsonl"
    )
    notes_path = (
        tmp_path
        / "public-synthetic-fixture-conversion-review-outcome"
        / "public_synthetic_fixture_conversion_review_outcome_report.md"
    )
    report = PublicSyntheticFixtureConversionReviewOutcomeReport.model_validate(
        load_json(report_path)
    )
    history = load_jsonl(history_path)

    assert exit_code == 0
    assert report.status == "conversion_review_recorded_separate_fixture_pr_required"
    assert report.append_only_history_ref == str(history_path)
    assert len(history) == 1
    assert history[0]["conversion_review_id"].startswith(
        "public-conversion-review-courtlistener-recap"
    )
    assert '"fixture_pr_created": false' in captured.out
    assert '"public_records_ingested": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert '"silent_learning_performed": false' in captured.out
    assert notes_path.is_file()
    assert "does not create fixtures" in notes_path.read_text(encoding="utf-8")


def test_public_conversion_review_outcome_records_needs_more_information(tmp_path, repo_root):
    packet, packet_path = _review_packet(tmp_path, repo_root)
    record = _record_from_packet(
        packet,
        source_id="cmu-enron-email",
        outcome="needs_more_information",
        required_followups=["Resolve privacy/license posture before any fixture PR."],
    )

    report = build_public_synthetic_fixture_conversion_review_outcome_report(
        review_packet=packet,
        review_packet_ref=str(packet_path),
        review_record=record,
        history_ref="public_synthetic_fixture_conversion_review_history.jsonl",
    )

    assert report.status == "conversion_review_recorded_more_information_required"
    assert report.accepted_for_separate_fixture_pr is False
    assert report.separate_fixture_generation_pr_required is False
    assert report.required_followups == ["Resolve privacy/license posture before any fixture PR."]
    assert all(check.status == "passed" for check in report.checks)


def test_public_conversion_review_outcome_requires_approval_gates(tmp_path, repo_root):
    packet, _ = _review_packet(tmp_path, repo_root)

    with pytest.raises(ValueError, match="approved conversion reviews require all approval gates"):
        _record_from_packet(packet, accepted_required_gates=["privacy_review"])


def test_public_conversion_review_outcome_cli_rejects_unbound_source(tmp_path, repo_root, capsys):
    packet, packet_path = _review_packet(tmp_path, repo_root)
    record_payload = _record_from_packet(packet).model_dump(mode="json")
    record_payload["source_id"] = "missing-source"
    review_path = write_json(
        tmp_path / "public_conversion_review_unbound_decision.json",
        record_payload,
    )

    exit_code = main(
        [
            "record-public-synthetic-fixture-conversion-review",
            "--review-packet",
            str(packet_path),
            "--review",
            str(review_path),
            "--out-dir",
            str(tmp_path / "public-synthetic-fixture-conversion-review-outcome"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "source/spec is not present in review packet" in captured.err


def test_public_conversion_review_outcome_runner_persists_record_history(tmp_path, repo_root):
    packet, packet_path = _review_packet(tmp_path, repo_root)
    review_path = write_json(
        tmp_path / "public_conversion_review_decision.json",
        _record_from_packet(packet).model_dump(mode="json"),
    )

    report, run_dir = run_public_synthetic_fixture_conversion_review_outcome_record(
        review_packet_path=packet_path,
        review_path=review_path,
        out_dir=tmp_path / "public-synthetic-fixture-conversion-review-outcome-runner",
    )

    assert report.status == "conversion_review_recorded_separate_fixture_pr_required"
    assert (run_dir / "public_synthetic_fixture_conversion_review_record.json").is_file()
    assert (run_dir / "public_synthetic_fixture_conversion_review_history.jsonl").is_file()
