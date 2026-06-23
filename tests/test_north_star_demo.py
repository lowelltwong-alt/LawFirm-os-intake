import json

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.util import load_json, load_jsonl


def test_north_star_demo_outputs_complete_messy_review_package(tmp_path, repo_root):
    code = main(
        [
            "demo",
            "--input",
            str(repo_root / "examples/synthetic/inbound/north-star-messy-intake.json"),
            "--practice-profile",
            str(repo_root / "context/synthetic-profiles/insurance-defense.yaml"),
            "--confirmation-template",
            str(
                repo_root
                / "examples/synthetic/confirmations/north-star-messy-intake.confirmation-template.json"
            ),
            "--out-dir",
            str(tmp_path / "north-star"),
        ]
    )

    assert code == 0
    preflight_dir = next((tmp_path / "north-star/preflight").iterdir())
    packet = load_json(preflight_dir / "intake_preflight_packet.json")
    preflight_exceptions = load_jsonl(preflight_dir / "exception_lake_candidates.jsonl")
    budget_dir = tmp_path / "north-star/budget"
    budget_exceptions = load_jsonl(budget_dir / "exception_lake_candidates.jsonl")
    safety = load_json(budget_dir / "safety_gate_report.json")
    manifest = load_json(budget_dir / "review_package_manifest.json")
    review_text = (budget_dir / "matter_opening_review_package.md").read_text(encoding="utf-8")

    labels = {item["local_event_label"] for item in preflight_exceptions}
    assert packet["source_coverage_summary"]["missing_sources"] == 1
    assert packet["source_coverage_summary"]["duplicate_sources"] == 1
    assert packet["source_coverage_summary"]["coverage_complete"] is False
    assert "incident_date" in packet["missing_information"]
    assert "jurisdiction" in packet["missing_information"]
    assert "duplicate_source_detected" in labels
    assert "source_missing" in labels
    assert "prompt_injection_source_content" in labels
    assert {
        ref["source_id"]
        for item in preflight_exceptions
        if item["local_event_label"] == "prompt_injection_source_content"
        for ref in item["evidence_refs"]
    } == {"syn-northstar-injection-001"}
    assert any(
        item["local_event_label"] == "matter_opening_blocked_pending_conflicts_and_engagement"
        for item in budget_exceptions
    )
    assert safety["status"] == "passed"
    assert safety["final_boundary"] == "blocked_pending_conflicts_and_engagement"
    assert manifest["status"] == "blocked_pending_conflicts_and_engagement"
    assert manifest["artifact_refs"]["safety_gate_report"].endswith("safety_gate_report.json")

    for phrase in [
        "Source coverage complete: False",
        "Missing sources: 1",
        "Duplicate sources: 1",
        "missing information: incident_date",
        "missing information: jurisdiction",
        "prompt_injection_source_content",
        "no_conflict_conclusion",
        "Scenario: baseline",
        "Status: passed",
        "blocker: conflicts_not_cleared",
        "blocker: engagement_not_authorized",
        "blocker: matter_opening_not_approved",
        "This package does not clear conflicts",
    ]:
        assert phrase in review_text

    json.dumps(manifest)
