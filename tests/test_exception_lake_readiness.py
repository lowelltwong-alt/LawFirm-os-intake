import pytest

from lawfirm_os_intake.confirmation import bind_confirmation_to_packet_evidence
from lawfirm_os_intake.exception_readiness import (
    build_exception_lake_readiness_report,
    enforce_exception_lake_readiness,
)
from lawfirm_os_intake.models import ExceptionLakeCandidate, HumanConfirmation
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
    if status == "confirmed":
        return bind_confirmation_to_packet_evidence(packet, confirmation)
    return confirmation


def _candidate_models(path) -> list[ExceptionLakeCandidate]:
    return [ExceptionLakeCandidate.model_validate(candidate) for candidate in load_jsonl(path)]


def test_preflight_writes_passing_exception_lake_readiness_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-duplicate-missing-attachment.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    report = load_json(run_dir / "exception_lake_readiness_report.json")

    assert packet.exception_lake_readiness_report_ref == str(
        run_dir / "exception_lake_readiness_report.json"
    )
    assert report["status"] == "passed"
    assert report["admission_state"] == "dry_run_not_admitted"
    assert report["candidate_count"] == len(load_jsonl(run_dir / "exception_lake_candidates.jsonl"))
    assert {check["check_id"] for check in report["checks"]} >= {
        "dry_run_only",
        "raw_payload_excluded",
        "canonical_promotion_required",
        "evidence_refs_match_packet_segments",
        "source_inventory_refs_known",
    }


def test_budget_writes_combined_exception_lake_readiness_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root)
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")

    _, budget_dir = run_budget(
        run_dir / "intake_preflight_packet.json",
        confirmation_path,
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "budget",
    )

    report = load_json(budget_dir / "exception_lake_readiness_report.json")
    manifest = load_json(budget_dir / "review_package_manifest.json")

    assert report["status"] == "passed"
    assert report["candidate_count"] == len(
        load_jsonl(run_dir / "exception_lake_candidates.jsonl")
        + load_jsonl(budget_dir / "exception_lake_candidates.jsonl")
    )
    assert manifest["exception_lake_readiness_report_ref"] == str(
        budget_dir / "exception_lake_readiness_report.json"
    )
    assert manifest["artifact_refs"]["budget_exception_lake_readiness_report"].endswith(
        "exception_lake_readiness_report.json"
    )
    assert manifest["artifact_refs"]["preflight_exception_lake_readiness_report"].endswith(
        "exception_lake_readiness_report.json"
    )


def test_failed_budget_precondition_writes_exception_lake_readiness_report(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/carrier-assignment-medmal.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path / "preflight",
    )
    confirmation = _confirmation(packet, repo_root, status="unknown")
    confirmation_path = tmp_path / "human_confirmation.json"
    confirmation_path.write_text(confirmation.model_dump_json(), encoding="utf-8")

    with pytest.raises(ValueError, match="budget precondition gate failed"):
        run_budget(
            run_dir / "intake_preflight_packet.json",
            confirmation_path,
            repo_root / "context/synthetic-profiles/insurance-defense.yaml",
            tmp_path / "budget",
        )

    report = load_json(tmp_path / "budget/exception_lake_readiness_report.json")
    assert report["status"] == "passed"
    assert report["candidate_count"] == 1
    assert report["admission_state"] == "dry_run_not_admitted"


def test_exception_lake_readiness_fails_closed_on_raw_payload_candidate(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/holdout-duplicate-missing-attachment.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    candidates = _candidate_models(run_dir / "exception_lake_candidates.jsonl")
    unsafe = candidates[0].model_copy(update={"raw_payload_included": True})
    report = build_exception_lake_readiness_report(
        packet,
        [unsafe] + candidates[1:],
        [str(run_dir / "exception_lake_candidates.jsonl")],
    )

    assert report.status == "failed"
    assert any(check.check_id == "raw_payload_excluded" for check in report.checks)
    with pytest.raises(ValueError, match="exception lake readiness failed"):
        enforce_exception_lake_readiness(report)


def test_exception_lake_readiness_fails_closed_on_evidence_ref_drift(tmp_path, repo_root):
    packet, run_dir = run_preflight(
        repo_root / "examples/synthetic/inbound/prompt-injection-email.json",
        repo_root / "context/synthetic-profiles/insurance-defense.yaml",
        tmp_path,
    )
    candidates = _candidate_models(run_dir / "exception_lake_candidates.jsonl")
    unsafe = candidates[0].model_copy(deep=True)
    unsafe.evidence_refs[0].start_offset += 1
    report = build_exception_lake_readiness_report(
        packet,
        [unsafe] + candidates[1:],
        [str(run_dir / "exception_lake_candidates.jsonl")],
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "evidence_refs_match_packet_segments" and check.status == "failed"
        for check in report.checks
    )
    with pytest.raises(ValueError, match="exception lake readiness failed"):
        enforce_exception_lake_readiness(report)
