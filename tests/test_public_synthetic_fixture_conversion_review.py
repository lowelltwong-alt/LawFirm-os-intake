from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import PublicSyntheticFixtureConversionReviewPacket
from lawfirm_os_intake.public_source_methodology import run_public_source_methodology_audit
from lawfirm_os_intake.public_synthetic_fixture_conversion import (
    run_public_synthetic_fixture_conversion_plan,
)
from lawfirm_os_intake.public_synthetic_fixture_conversion_review import (
    run_public_synthetic_fixture_conversion_review,
)
from lawfirm_os_intake.util import load_json, write_json


def _conversion_plan_path(tmp_path, repo_root):
    _, methodology_dir = run_public_source_methodology_audit(
        repo_root=repo_root,
        out_dir=tmp_path / "public-source-methodology",
    )
    _, conversion_dir = run_public_synthetic_fixture_conversion_plan(
        methodology_report_path=methodology_dir / "public_source_methodology_report.json",
        out_dir=tmp_path / "public-synthetic-fixture-conversion",
    )
    return conversion_dir / "public_synthetic_fixture_conversion_plan.json"


def test_public_synthetic_fixture_conversion_review_packet_ready(tmp_path, repo_root):
    conversion_plan_path = _conversion_plan_path(tmp_path, repo_root)

    packet, run_dir = run_public_synthetic_fixture_conversion_review(
        conversion_plan_path=conversion_plan_path,
        out_dir=tmp_path / "public-synthetic-fixture-conversion-review",
    )
    persisted = PublicSyntheticFixtureConversionReviewPacket.model_validate(
        load_json(run_dir / "public_synthetic_fixture_conversion_review_packet.json")
    )
    decision_templates = load_json(
        run_dir / "public_synthetic_fixture_conversion_review_decision_template.json"
    )

    assert persisted.review_packet_id == packet.review_packet_id
    assert persisted.status == "ready_for_human_conversion_review"
    assert persisted.spec_count == 6
    assert persisted.recommendation_count == 6
    assert persisted.decision_template_count == len(decision_templates) == 6
    assert persisted.red_team_note_count >= 5
    assert all(rec.why for rec in persisted.recommendations)
    assert all(rec.required_human_decisions for rec in persisted.recommendations)
    assert all(template.required_fields for template in persisted.decision_templates)

    by_source = {rec.source_id: rec for rec in persisted.recommendations}
    assert by_source["cmu-enron-email"].recommended_action == "hold_for_privacy_or_license_review"
    assert (
        by_source["npdb-public-use-data"].recommended_action == "hold_for_privacy_or_license_review"
    )
    assert by_source["courtlistener-recap"].priority == "critical"
    assert any(note.scope == "identity_reconstruction" for note in persisted.red_team_notes)
    assert any(note.scope == "prompt_injection" for note in persisted.red_team_notes)
    assert any(note.scope == "privacy_license_retention" for note in persisted.red_team_notes)

    assert persisted.public_records_ingested is False
    assert persisted.raw_public_payload_committed is False
    assert persisted.synthetic_fixtures_created is False
    assert persisted.fixture_files_mutated is False
    assert persisted.fixture_pr_created is False
    assert persisted.connector_implemented is False
    assert persisted.legal_knowledge_adapter_authorized is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False

    notes = (run_dir / "public_synthetic_fixture_conversion_review_packet.md").read_text(
        encoding="utf-8"
    )
    assert "Recommendations" in notes
    assert "Red-Team Notes" in notes
    assert "Fixture files mutated: False" in notes


def test_public_synthetic_fixture_conversion_review_blocks_unready_plan(tmp_path, repo_root):
    conversion_plan_path = _conversion_plan_path(tmp_path, repo_root)
    payload = load_json(conversion_plan_path)
    payload["status"] = "blocked_public_methodology_not_ready"
    payload["checks"][0]["status"] = "blocked"
    payload["checks"][0]["message"] = "Synthetic blocked conversion plan fixture."
    payload["spec_count"] = 0
    payload["specs"] = []
    blocked_path = write_json(
        tmp_path / "blocked-conversion-plan" / "public_synthetic_fixture_conversion_plan.json",
        payload,
    )

    packet, _ = run_public_synthetic_fixture_conversion_review(
        conversion_plan_path=blocked_path,
        out_dir=tmp_path / "public-synthetic-fixture-conversion-review-blocked",
    )

    assert packet.status == "blocked_by_conversion_plan"
    assert packet.recommendation_count == 0
    assert packet.decision_template_count == 0
    assert packet.red_team_note_count == 1
    assert packet.public_records_ingested is False
    assert packet.synthetic_fixtures_created is False
    assert packet.fixture_files_mutated is False
    assert packet.external_writes_performed is False


def test_public_synthetic_fixture_conversion_review_cli(tmp_path, repo_root, capsys):
    conversion_plan_path = _conversion_plan_path(tmp_path, repo_root)

    exit_code = main(
        [
            "review-public-synthetic-fixture-conversion",
            "--conversion-plan",
            str(conversion_plan_path),
            "--out-dir",
            str(tmp_path / "public-synthetic-fixture-conversion-review-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "ready_for_human_conversion_review"' in captured.out
    assert '"recommendation_count": 6' in captured.out
    assert '"fixture_pr_created": false' in captured.out
    assert (
        tmp_path
        / "public-synthetic-fixture-conversion-review-cli"
        / "public_synthetic_fixture_conversion_review_packet.json"
    ).is_file()
