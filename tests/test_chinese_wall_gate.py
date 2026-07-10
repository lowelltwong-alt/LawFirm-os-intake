from __future__ import annotations

from copy import deepcopy

from lawfirm_os_intake.conflicts import (
    build_chinese_wall_proof,
    chinese_wall_request_digest,
)
from lawfirm_os_intake.cli import main
from lawfirm_os_intake.reviewed_learning_gate import (
    CHINESE_WALL_PROOF_REQUIRED_GATES,
    build_reviewed_learning_gate_report,
    validate_chinese_wall_gate,
)
from lawfirm_os_intake.util import load_json, write_json


def _request(repo_root, case_id: str = "chw-same-side-ok") -> dict:
    fixture = load_json(
        repo_root
        / "examples/synthetic/conflicts/chinese-wall-cases.synthetic-policy-placeholder.json"
    )
    case = next(item for item in fixture["cases"] if item["case_id"] == case_id)
    return {
        **deepcopy(case["request"]),
        "data_class": "synthetic_fixture",
        "runtime_scope": "synthetic_candidate",
        "candidate_only": True,
        "lesson_status": "candidate",
        "adversity_graph": deepcopy(fixture["adversity_graph"]),
        "synthetic_adversity_graph_digest": fixture["trusted_synthetic_adversity_graph_digest"],
        "synthetic_case_manifest_digest": fixture["trusted_synthetic_case_manifest_digest"],
        "provenance_scope": "synthetic_firm_wide_fixture",
        "trusted_synthetic_firm_wide_provenance_snapshot_pinned": True,
        "synthetic_firm_wide_imputation_required": True,
        "authoritative_firm_wide_provenance_manifest_verified": False,
        "consuming_context_scope_known": True,
        "contains_real_data": False,
        "contains_private_data": False,
        "contains_client_data": False,
        "contains_matter_data": False,
        "contains_real_carrier_data": False,
        "contains_privileged_content": False,
        "contains_work_product": False,
    }


def test_chinese_wall_gate_refuses_missing_proof():
    check = validate_chinese_wall_gate(
        lesson_id="synthetic-lesson-missing-wall-proof",
        chinese_wall_proof=None,
    )

    assert check.status == "failed"
    assert check.check_id == "chinese_wall_proof_required"


def test_same_side_gate_remains_blocked_pending_hd4_and_owner_review(repo_root):
    request = _request(repo_root)
    proof = build_chinese_wall_proof(request)
    check = validate_chinese_wall_gate(
        lesson_id=proof.lesson_id,
        chinese_wall_proof=proof,
        chinese_wall_request=request,
        expected_chinese_wall_request_digest=chinese_wall_request_digest(request),
        approval_id="approval:synthetic-chw-review-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "chinese_wall_proof_promotion_gate"
    assert "status=blocked" in check.message
    assert "authoritative_firm_wide_imputation_not_verified" in check.message
    assert "counsel_adversity_classes_not_authoritative" in check.message
    assert "authenticated_human_conflicts_review_not_verified" in check.message
    assert "owning_repo_review_not_verified" in check.message
    assert CHINESE_WALL_PROOF_REQUIRED_GATES == [
        "valid_chinese_wall_proof",
        "external_chinese_wall_request_digest_anchor",
        "reviewed_adversity_edges_only_no_inference",
        "pinned_synthetic_firm_wide_provenance_snapshot",
        "authoritative_firm_wide_imputation",
        "counsel_adversity_class_authority",
        "authenticated_human_conflicts_review",
        "owning_repo_review",
        "no_lesson_fire_conflict_clearance_or_lake_write_from_intake",
    ]


def test_cross_wall_gate_blocks_and_does_not_treat_approval_id_as_clearance(repo_root):
    request = _request(repo_root, "chw-cross-wall-block")
    proof = build_chinese_wall_proof(request)
    check = validate_chinese_wall_gate(
        lesson_id=proof.lesson_id,
        chinese_wall_proof=proof,
        chinese_wall_request=request,
        expected_chinese_wall_request_digest=chinese_wall_request_digest(request),
        approval_id="approval:synthetic-chw-review-0001",
    )

    assert check.status == "failed"
    assert "cross_wall_detected" in check.message
    assert proof.lesson_fire_performed is False
    assert proof.exception_lake_write_performed is False


def test_chinese_wall_gate_rejects_external_digest_mismatch(repo_root):
    request = _request(repo_root)
    proof = build_chinese_wall_proof(request)
    check = validate_chinese_wall_gate(
        lesson_id=proof.lesson_id,
        chinese_wall_proof=proof,
        chinese_wall_request=request,
        expected_chinese_wall_request_digest="sha256:" + ("0" * 64),
        approval_id="approval:synthetic-chw-review-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "chinese_wall_proof_request_binding"
    assert "expected_digest_does_not_match_rebuilt_request" in check.message


def test_chinese_wall_gate_rejects_forged_proof(repo_root):
    request = _request(repo_root)
    proof = build_chinese_wall_proof(request).model_dump(mode="json")
    proof["local_evaluation"]["local_wall_candidate"] = False

    check = validate_chinese_wall_gate(
        lesson_id=request["lesson_id"],
        chinese_wall_proof=proof,
        chinese_wall_request=request,
        expected_chinese_wall_request_digest=chinese_wall_request_digest(request),
        approval_id="approval:synthetic-chw-review-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "chinese_wall_proof_valid"


def test_reviewed_learning_report_exposes_wall_gate_without_promoting_candidate(repo_root):
    request = _request(repo_root)
    proof = build_chinese_wall_proof(request)
    report = build_reviewed_learning_gate_report(
        chinese_wall_gate_requests=[
            {
                "lesson_id": proof.lesson_id,
                "chinese_wall_proof": proof.model_dump(mode="json"),
                "chinese_wall_request": request,
                "expected_chinese_wall_request_digest": chinese_wall_request_digest(request),
                "approval_id": "approval:synthetic-chw-review-0001",
                "proof_ref": "synthetic-chinese-wall-proof",
            }
        ]
    )

    assert report.status == "failed"
    assert report.candidate_count == 0
    assert report.candidates == []
    assert any(
        check.check_id == "chinese_wall_gate_review_inputs_visible"
        and check.status == "passed"
        and check.candidate_ids == [proof.proof_id]
        for check in report.checks
    )
    assert any(
        check.check_id == "chinese_wall_proof_promotion_gate" and check.status == "failed"
        for check in report.checks
    )


def test_reviewed_learning_cli_loads_wall_request_file_and_fails_closed(
    tmp_path,
    repo_root,
    capsys,
):
    request = _request(repo_root)
    proof = build_chinese_wall_proof(request)
    gate_request_path = write_json(
        tmp_path / "chinese-wall-gate-request.json",
        {
            "lesson_id": proof.lesson_id,
            "chinese_wall_proof": proof.model_dump(mode="json"),
            "chinese_wall_request": request,
            "expected_chinese_wall_request_digest": chinese_wall_request_digest(request),
            "approval_id": "approval:synthetic-chw-review-0001",
        },
    )

    exit_code = main(
        [
            "review-learning-gate",
            "--chinese-wall-gate-request",
            str(gate_request_path),
            "--out-dir",
            str(tmp_path / "chinese-wall-gate-cli"),
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 2
    assert '"status": "failed"' in captured.out
