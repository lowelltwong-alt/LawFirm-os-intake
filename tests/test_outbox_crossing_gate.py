from __future__ import annotations

from copy import deepcopy

from lawfirm_os_intake.lessons import (
    TRUSTED_SYNTHETIC_CONTEXT_DIGEST,
    build_lesson_disclosure_proof,
    published_projection_snapshot_digest,
    synthetic_lesson_fixture_digest,
)
from lawfirm_os_intake.outbox import build_crossing_proof, crossing_request_digest
from lawfirm_os_intake.reviewed_learning_gate import (
    CROSSING_PROOF_REQUIRED_GATES,
    build_reviewed_learning_gate_report,
    validate_crossing_gate,
)
from lawfirm_os_intake.util import load_json


def _crossing_request(repo_root):
    lesson_fixture = load_json(
        repo_root
        / "examples/synthetic/lessons/qrd-disclosure-cases.synthetic-policy-placeholder.json"
    )
    case = next(
        item for item in lesson_fixture["cases"] if item["case_id"] == "lesson-kanon-generalize"
    )
    published_lessons = deepcopy(case["published_lessons"])
    lesson_request = {
        "request_id": "synthetic-ifc-gate-qrd-request",
        "lesson": deepcopy(case["lesson"]),
        "policy": deepcopy(lesson_fixture["policy"]),
        "lattice": deepcopy(lesson_fixture["lattice"]),
        "universe": deepcopy(lesson_fixture["universe"]),
        "synthetic_lesson_fixture_digest": synthetic_lesson_fixture_digest(case["lesson"]),
        "synthetic_context_digest": TRUSTED_SYNTHETIC_CONTEXT_DIGEST,
        "publication_snapshot_id": "synthetic-qrd-publication-snapshot-v1",
        "publication_snapshot_digest": published_projection_snapshot_digest(published_lessons),
        "authoritative_publication_snapshot_verified": False,
        "published_lessons": published_lessons,
    }
    crossing_fixture = load_json(
        repo_root / "examples/synthetic/outbox/ifc-crossing-cases.synthetic.json"
    )
    request = deepcopy(crossing_fixture["request"])
    request["lesson_disclosure_request"] = lesson_request
    request["lesson_disclosure_proof"] = build_lesson_disclosure_proof(
        lesson_request,
        generated_at="2026-07-10T00:00:00+00:00",
    ).model_dump(mode="json")
    return request


def test_crossing_gate_refuses_missing_proof():
    check = validate_crossing_gate(
        request_id="synthetic-ifc-missing-proof",
        crossing_proof=None,
    )

    assert check.status == "failed"
    assert check.check_id == "crossing_proof_required"


def test_crossing_gate_stays_blocked_without_receiver_and_human_authority(repo_root):
    request = _crossing_request(repo_root)
    proof = build_crossing_proof(request)

    check = validate_crossing_gate(
        request_id=proof.request_id,
        crossing_proof=proof,
        crossing_request=request,
        expected_crossing_request_digest=crossing_request_digest(request),
        approval_id="approval:synthetic-ifc-review-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "crossing_proof_promotion_gate"
    assert "status=blocked" in check.message
    assert "qrd_disclosure_not_candidate" in check.message
    assert "dad_receiver_schema_not_authoritative" in check.message
    assert "authenticated_human_crossing_review_not_verified" in check.message
    assert "owning_repo_review_not_verified" in check.message
    assert CROSSING_PROOF_REQUIRED_GATES == [
        "valid_crossing_proof",
        "external_crossing_request_digest_anchor",
        "valid_bound_lesson_disclosure_proof",
        "deterministic_declared_pattern_check_not_formal_noninterference",
        "scanner_clean_and_label_at_most_candidate",
        "dad_receiver_schema_authority",
        "authenticated_human_crossing_review",
        "owning_repo_review",
        "no_send_outbox_write_or_dad_contact_from_intake",
    ]


def test_crossing_gate_rejects_external_digest_mismatch(repo_root):
    request = _crossing_request(repo_root)
    proof = build_crossing_proof(request)

    check = validate_crossing_gate(
        request_id=proof.request_id,
        crossing_proof=proof,
        crossing_request=request,
        expected_crossing_request_digest="sha256:" + ("0" * 64),
        approval_id="approval:synthetic-ifc-review-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "crossing_proof_request_binding"
    assert "expected_digest_does_not_match_rebuilt_request" in check.message


def test_crossing_gate_rejects_forged_proof_content(repo_root):
    request = _crossing_request(repo_root)
    proof = build_crossing_proof(request).model_dump(mode="json")
    proof["local_scanner_and_lattice_candidate"] = False

    check = validate_crossing_gate(
        request_id=request["request_id"],
        crossing_proof=proof,
        crossing_request=request,
        expected_crossing_request_digest=crossing_request_digest(request),
        approval_id="approval:synthetic-ifc-review-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "crossing_proof_valid"


def test_reviewed_learning_report_exposes_crossing_gate_without_candidate(repo_root):
    request = _crossing_request(repo_root)
    proof = build_crossing_proof(request)

    report = build_reviewed_learning_gate_report(
        crossing_gate_requests=[
            {
                "request_id": proof.request_id,
                "crossing_proof": proof.model_dump(mode="json"),
                "crossing_request": request,
                "expected_crossing_request_digest": crossing_request_digest(request),
                "approval_id": "approval:synthetic-ifc-review-0001",
                "proof_ref": "synthetic-ifc-crossing-proof",
            }
        ]
    )

    assert report.status == "failed"
    assert report.candidate_count == 0
    assert report.candidates == []
    assert any(
        check.check_id == "crossing_gate_review_inputs_visible"
        and check.status == "passed"
        and check.candidate_ids == [proof.proof_id]
        for check in report.checks
    )
    assert any(
        check.check_id == "crossing_proof_promotion_gate" and check.status == "failed"
        for check in report.checks
    )
