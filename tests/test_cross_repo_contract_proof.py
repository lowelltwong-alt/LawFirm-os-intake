import json
from pathlib import Path
import subprocess

import pytest

from lawfirm_os_intake.cross_repo_contract_proof import (
    CROSS_REPO_CONTRACT_PROOF_REPORT_FILENAME,
    run_cross_repo_contract_proof,
)
from lawfirm_os_intake.models import OrchestratorOwnerReviewRequest
from lawfirm_os_intake.util import load_json, write_json


def _request_payload() -> dict:
    return {
        "schema_version": "intake_owner_review_request.v0_1",
        "request_id": "synthetic-contract-proof-request",
        "generated_at": "2026-07-12T00:00:00Z",
        "workflow_label": "orchestrator.local.intake_to_budget_owner_review",
        "synthetic": True,
        "contains_real_firm_data": False,
        "contains_real_client_data": False,
        "contains_real_matter_data": False,
        "contains_privileged_data": False,
        "source_refs": [
            {
                "source_ref_id": "source-001",
                "sha256": "a" * 64,
                "segment_refs": ["segment-001"],
                "coverage": "full",
            }
        ],
        "human_confirmations": {
            "confirm_matter_family": {
                "status": "confirmed",
                "human_review_ref": "review://matter",
                "evidence_refs": ["source-001#segment-001"],
            },
            "confirm_representation_posture": {
                "status": "confirmed",
                "human_review_ref": "review://posture",
                "evidence_refs": ["source-001#segment-001"],
            },
            "confirm_principal_party_roles": {
                "status": "confirmed",
                "human_review_ref": "review://parties",
                "evidence_refs": ["source-001#segment-001"],
            },
            "approve_budget_proposal_before_external_submission": {
                "status": "pending",
                "human_review_ref": "review://budget",
                "evidence_refs": [],
            },
            "approve_exception_lake_handoff_before_admission": {
                "status": "pending",
                "human_review_ref": "review://lake",
                "evidence_refs": [],
            },
        },
        "budget_preconditions": {
            "party_count_known": True,
            "complexity_known": False,
            "matter_family_confirmed": True,
            "representation_posture_confirmed": True,
            "principal_roles_confirmed": True,
        },
        "budget_actual_lines": [],
        "carrier_rejection_notices": [],
        "lake_handoff_mode": "validate_only",
    }


def _completed(command: list[str], *, cwd: Path, **_kwargs) -> subprocess.CompletedProcess[str]:
    if "prepare-owner-packet" in command:
        root = Path(command[command.index("--out-dir") + 1])
        packet = root / "owner" / "intake_owner_review_packet.json"
        packet.parent.mkdir(parents=True)
        write_json(packet, {"packet": "owner"})
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "status": "blocked_pending_owner_review",
                    "lake_handoff_allowed": False,
                    "not_authorized_for_client_submission": True,
                    "packet_path": str(packet),
                }
            ),
            "",
        )
    if "build-lake-admission-review-packet" in command:
        root = Path(command[command.index("--out-dir") + 1])
        packet = root / "lake" / "intake_lake_admission_review_packet.json"
        packet.parent.mkdir(parents=True)
        write_json(packet, {"packet": "lake"})
        return subprocess.CompletedProcess(
            command,
            0,
            json.dumps(
                {
                    "status": "blocked_pending_exception_lake_owner_review",
                    "lake_handoff_allowed": False,
                    "sqlite_write_authorized_now": False,
                    "packet_path": str(packet),
                }
            ),
            "",
        )
    report = Path(command[command.index("--report-out") + 1])
    write_json(
        report,
        {
            "status": "passed_candidate_packet_validation",
            "admission_allowed_now": False,
            "lake_write_authority_now": False,
            "sqlite_write_authorized_now": False,
            "raw_payload_storage_allowed": False,
        },
    )
    return subprocess.CompletedProcess(command, 0, "passed", "")


def _owner_repo(root: Path, required_relative_path: str) -> Path:
    (root / required_relative_path).parent.mkdir(parents=True)
    (root / required_relative_path).write_text("placeholder", encoding="utf-8")
    (root / ".git").mkdir()
    return root


def test_cross_repo_contract_proof_records_hashed_no_write_chain(tmp_path, monkeypatch):
    import lawfirm_os_intake.cross_repo_contract_proof as proof

    expected = load_json(
        Path(__file__).parents[1]
        / "examples/synthetic/cross-repo-contract-proof/expected-contract-proof.json"
    )
    request_path = write_json(tmp_path / "request.json", _request_payload())
    orchestrator_root = _owner_repo(tmp_path / "orchestrator", "src/lawfirm_os_orchestrator/cli.py")
    lake_root = _owner_repo(
        tmp_path / "lake", "scripts/validate_intake_lake_admission_review_packet.py"
    )
    monkeypatch.setattr(proof, "_repo_commit", lambda root, required_path: f"{root.name}-commit")
    monkeypatch.setattr(proof, "_run", _completed)

    report, out_dir = run_cross_repo_contract_proof(
        request_path=request_path,
        orchestrator_root=orchestrator_root,
        exception_lake_root=lake_root,
        out_dir=tmp_path / "proof",
    )

    assert report.status == "passed_candidate_contract_proof"
    assert report.owner_packet_status == expected["expected_owner_packet_status"]
    assert report.lake_review_packet_status == expected["expected_lake_review_packet_status"]
    assert report.lake_validation_status == expected["expected_lake_validation_status"]
    assert all(getattr(report, flag) is False for flag in expected["required_false_flags"])
    assert (out_dir / CROSS_REPO_CONTRACT_PROOF_REPORT_FILENAME).is_file()
    assert len(report.owner_packet_sha256) == 64
    assert len(report.lake_validation_report_sha256) == 64


def test_cross_repo_contract_proof_rejects_real_data_before_owner_invocation(tmp_path):
    payload = _request_payload()
    payload["contains_real_matter_data"] = True
    request_path = write_json(tmp_path / "real-request.json", payload)

    with pytest.raises(ValueError, match="synthetic no-real-data"):
        run_cross_repo_contract_proof(
            request_path=request_path,
            orchestrator_root=tmp_path / "missing-orchestrator",
            exception_lake_root=tmp_path / "missing-lake",
            out_dir=tmp_path / "proof",
        )


def test_cross_repo_contract_proof_fixture_is_a_valid_owner_request_shape():
    request = OrchestratorOwnerReviewRequest.model_validate(_request_payload())
    assert request.synthetic is True
