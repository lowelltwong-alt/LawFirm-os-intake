import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.dad_review_issue_outbox import record_dad_review_issue_to_outbox
from lawfirm_os_intake.models import DADReviewIssueOutboxMail, DADReviewIssueOutboxReport
from lawfirm_os_intake.util import load_json, load_jsonl, write_json


def _fixture_path(repo_root):
    return (
        repo_root
        / "examples"
        / "synthetic"
        / "dad-review-issues"
        / "fable-le-budget-output-expectations.issue.json"
    )


def test_dad_review_issue_records_candidate_mail_with_classification(tmp_path, repo_root):
    report, outbox = record_dad_review_issue_to_outbox(
        _fixture_path(repo_root),
        repo_root=tmp_path,
        report_out=tmp_path / "dad_review_issue_outbox_report.json",
    )
    persisted = DADReviewIssueOutboxReport.model_validate(
        load_json(tmp_path / "dad_review_issue_outbox_report.json")
    )
    rows = load_jsonl(outbox)
    mail = DADReviewIssueOutboxMail.model_validate(rows[0])

    assert persisted.status == "dad_review_issue_recorded_to_outbox"
    assert persisted.source_issue_id == "fable-le-budget-output-expectations-001"
    assert persisted.severity == "P0"
    assert persisted.outbox_append_performed is True
    assert persisted.outbox_duplicate_suppressed is False
    assert persisted.candidate_only is True
    assert persisted.dad_pickup_required is True
    assert persisted.hidden_chain_of_thought_included is False
    assert persisted.raw_private_payload_included is False
    assert persisted.lake_write_performed is False
    assert persisted.sqlite_write_performed is False
    assert persisted.external_writes_performed is False
    assert persisted.silent_learning_performed is False
    assert outbox == tmp_path / ".digital-asset" / "mail" / "outbox.jsonl"
    assert (tmp_path / ".digital-asset" / "mail" / ".gitignore").is_file()
    assert len(rows) == 1
    assert mail.mail_id == persisted.dad_mail_id
    assert mail.message_type == "governance_notice"
    assert mail.target_repo == "central_only"
    assert mail.payload["issue_classes"] == persisted.issue_classes
    assert "observable_decision_logic" in mail.payload
    assert "hidden chain-of-thought is explicitly excluded" in persisted.checks[2].message
    assert "budget_math_risk" in persisted.issue_classes
    assert "dad_learning_loop_candidate" in persisted.candidate_exception_labels


def test_dad_review_issue_duplicate_is_suppressed(tmp_path, repo_root):
    first_report, outbox = record_dad_review_issue_to_outbox(
        _fixture_path(repo_root),
        repo_root=tmp_path,
    )
    second_report, _ = record_dad_review_issue_to_outbox(
        _fixture_path(repo_root),
        repo_root=tmp_path,
    )

    assert first_report.status == "dad_review_issue_recorded_to_outbox"
    assert second_report.status == "dad_review_issue_duplicate_suppressed"
    assert second_report.outbox_append_performed is False
    assert second_report.outbox_duplicate_suppressed is True
    assert first_report.dad_mail_id == second_report.dad_mail_id
    assert len(load_jsonl(outbox)) == 1


def test_dad_review_issue_rejects_sensitive_text(tmp_path, repo_root):
    data = load_json(_fixture_path(repo_root))
    data["reviewer_notes"].append("Do not mail this fake key sk-proj-secretvalue1234567890")
    issue_path = write_json(tmp_path / "sensitive.issue.json", data)

    with pytest.raises(ValueError, match="sensitive-looking text"):
        record_dad_review_issue_to_outbox(issue_path, repo_root=tmp_path)

    assert not (tmp_path / ".digital-asset" / "mail" / "outbox.jsonl").exists()


def test_dad_review_issue_outbox_path_cannot_escape_mailbox(tmp_path, repo_root):
    with pytest.raises(ValueError, match="must stay under .digital-asset/mail"):
        record_dad_review_issue_to_outbox(
            _fixture_path(repo_root),
            repo_root=tmp_path,
            outbox_path=tmp_path / "not-mail" / "outbox.jsonl",
        )


def test_dad_review_issue_cli(tmp_path, repo_root, capsys):
    exit_code = main(
        [
            "record-dad-review-issue",
            "--issue",
            str(_fixture_path(repo_root)),
            "--repo-root",
            str(tmp_path),
            "--report-out",
            str(tmp_path / "report.json"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 0
    assert '"status": "dad_review_issue_recorded_to_outbox"' in captured.out
    assert '"source_issue_id": "fable-le-budget-output-expectations-001"' in captured.out
    assert '"hidden_chain_of_thought_included": false' in captured.out
    assert '"lake_write_performed": false' in captured.out
    assert (tmp_path / ".digital-asset" / "mail" / "outbox.jsonl").is_file()
    assert (tmp_path / "report.json").is_file()
