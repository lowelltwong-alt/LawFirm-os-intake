import pytest

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.models import HumanConfirmation
from lawfirm_os_intake.util import load_json, load_jsonl
from lawfirm_os_intake.workflow import run_budget, run_preflight


def _confirmation(packet, repo_root, *, status: str = "confirmed") -> HumanConfirmation:
    raw = load_json(
        repo_root
        / "examples/synthetic/confirmations/carrier-assignment-medmal.confirmation-template.json"
    )
    raw["preflight_packet_id"] = packet.packet_id
    raw["status"] = status
    confirmation = HumanConfirmation.model_validate(raw)
    return bind_confirmation_to_packet_evidence(packet, confirmation)


def _labels(manifest: dict) -> dict[str, dict]:
    return {item["local_event_label"]: item for item in manifest["label_summaries"]}


def test_preflight_writes_dry_run_exception_lake_handoff_manifest(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-duplicate-missing-attachment.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )

    manifest = load_json(run_dir / "exception_lake_handoff_manifest.json")
    labels = _labels(manifest)

    assert packet.exception_lake_handoff_manifest_ref == str(
        run_dir / "exception_lake_handoff_manifest.json"
    )
    assert manifest["stage"] == "preflight"
    assert manifest["status"] == "dry_run_ready_not_admitted"
    assert manifest["admission_state"] == "dry_run_not_admitted"
    assert manifest["target_runtime_repo"] == "LawFirm-os-exceptions-lake-runtime"
    assert manifest["storage_owner"] == "LawFirm-os-exceptions-lake-runtime"
    assert manifest["sqlite_write_performed"] is False
    assert manifest["external_writes_performed"] is False
    assert manifest["mapping_review_required"] is True
    assert manifest["canonical_promotion_required"] is True
    assert manifest["candidate_count"] == len(
        load_jsonl(run_dir / "exception_lake_candidates.jsonl")
    )
    assert labels["source_missing"]["canonical_lake_class"] == "retrieval_miss"
    assert labels["source_missing"]["support_modes"] == ["source_inventory_ref"]
    assert labels["duplicate_source_detected"]["canonical_lake_class"] == "workflow_escalation"
    assert {check["status"] for check in manifest["checks"]} == {"passed"}


def test_budget_writes_combined_exception_lake_handoff_manifest(tmp_path, repo_root):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")

    _, budget_dir = run_budget(
        preflight_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )

    manifest = load_json(budget_dir / "exception_lake_handoff_manifest.json")
    review_manifest = load_json(budget_dir / "review_package_manifest.json")
    labels = _labels(manifest)

    assert manifest["stage"] == "budget_combined"
    assert manifest["status"] == "dry_run_ready_not_admitted"
    assert manifest["candidate_count"] == len(
        load_jsonl(preflight_dir / "exception_lake_candidates.jsonl")
        + load_jsonl(budget_dir / "exception_lake_candidates.jsonl")
    )
    assert manifest["candidate_file_refs"] == [
        str(preflight_dir / "exception_lake_candidates.jsonl"),
        str(budget_dir / "exception_lake_candidates.jsonl"),
    ]
    assert manifest["sqlite_write_performed"] is False
    assert (
        labels["matter_opening_blocked_pending_conflicts_and_engagement"]["canonical_lake_class"]
        == "workflow_escalation"
    )
    assert "blocked_state" in labels["budget_unknowns_require_review"]["support_modes"]
    assert review_manifest["exception_lake_handoff_manifest_ref"] == str(
        budget_dir / "exception_lake_handoff_manifest.json"
    )
    assert review_manifest["artifact_refs"]["budget_exception_lake_handoff_manifest"] == str(
        budget_dir / "exception_lake_handoff_manifest.json"
    )


def test_blocked_budget_precondition_writes_handoff_manifest_without_budget_outputs(
    tmp_path, repo_root
):
    packet, preflight_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root, status="needs_more_information")
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="budget precondition gate failed"):
        run_budget(
            preflight_dir / "intake_preflight_packet.json",
            confirmation_path,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            tmp_path / "budget",
        )

    manifest = load_json(tmp_path / "budget/exception_lake_handoff_manifest.json")
    labels = _labels(manifest)

    assert manifest["stage"] == "budget_precondition_blocked"
    assert manifest["status"] == "dry_run_ready_not_admitted"
    assert manifest["sqlite_write_performed"] is False
    assert manifest["candidate_count"] == 1
    assert labels["budget_blocked_before_human_confirmation"]["blocked_states"] == [
        "budget_blocked_before_human_confirmation"
    ]
    assert not (tmp_path / "budget/legal_budget_proposal.json").exists()
    assert not (tmp_path / "budget/conflict_search_seed_packet.json").exists()
