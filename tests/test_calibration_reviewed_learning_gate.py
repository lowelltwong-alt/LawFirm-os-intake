from hashlib import sha256

import pytest

from lawfirm_os_intake.calibration import (
    CalibrationLeakageProof,
    build_calibration_leakage_proof,
    build_dp_calibration_leakage_proof,
)
from lawfirm_os_intake.reviewed_learning_gate import (
    CALIBRATION_LEAKAGE_PROOF_REQUIRED_GATES,
    build_reviewed_learning_gate_report,
    check_calibration_leakage_proof_for_promotion,
    validate_calibrated_parameter_gate,
)
from lawfirm_os_intake.util import load_json


def _request(repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json"
    )
    return raw["request"]


def _expected_digest(proof):
    return proof.determinism.aggregate_input_digest


def _dp_request(repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/calibration/calib-dp-epsilon-bound.synthetic-policy-placeholder.json"
    )
    return raw["request"]


def test_calibration_gate_refuses_missing_proof():
    check = validate_calibrated_parameter_gate(
        estimator_id="synthetic_budget_driver_mean",
        parameter="synthetic_phase_hours_mean",
        corpus_version_ref=(
            "examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json"
        ),
        screen_version="synthetic-screen-v0",
        calibration_leakage_proof=None,
        approval_id=None,
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_required"
    assert "require a CalibrationLeakageProof" in check.message


def test_calibration_gate_refuses_valid_proof_without_approval(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    check = check_calibration_leakage_proof_for_promotion(
        proof,
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_preflight_request=_request(repo_root),
        expected_aggregate_input_digest=_expected_digest(proof),
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_promotion_gate"
    assert "missing_approval_id" in check.message
    assert check.candidate_ids == [proof.proof_id]


def test_calibration_gate_refuses_valid_proof_without_preflight_request(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=proof,
        expected_aggregate_input_digest=_expected_digest(proof),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_preflight_request_required"
    assert "rebuilt instead of trusted from the proof" in check.message


def test_calibration_gate_refuses_valid_proof_without_expected_digest(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=proof,
        calibration_preflight_request=_request(repo_root),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_expected_request_digest_required"
    assert "independently of the proof/request pair" in check.message


def test_calibration_gate_refuses_refused_proof_even_with_approval(repo_root):
    raw = _request(repo_root)
    raw["policy"]["dominance_threshold"] = 0.01
    proof = build_calibration_leakage_proof(raw)

    check = check_calibration_leakage_proof_for_promotion(
        proof,
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_preflight_request=raw,
        expected_aggregate_input_digest=_expected_digest(proof),
        approval_id="approval:human-review-record-0001",
    )

    assert proof.status == "refused"
    assert check.status == "failed"
    assert "path=refused" in check.message
    assert "refusal_reasons_present" in check.message


def test_calibration_gate_accepts_valid_proof_plus_unverified_evidence_id(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=proof.model_dump(mode="json"),
        calibration_preflight_request=_request(repo_root),
        expected_aggregate_input_digest=_expected_digest(proof),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "passed"
    assert check.candidate_ids == [proof.proof_id]
    assert "does not mutate" in check.message
    assert "Identifier shape only" in check.message
    assert "no approval registry" in check.message
    assert "attorney role" in check.message
    assert CALIBRATION_LEAKAGE_PROOF_REQUIRED_GATES == [
        "valid_calibration_leakage_proof",
        "external_request_digest_anchor",
        "external_dp_release_digest_anchor_for_dp_path",
        "authoritative_zcdp_ledger_receipt_for_dp_path",
        "governed_secret_seed_authority_for_dp_path",
        "approval_evidence_identifier_shape_only",
        "owning_repo_review",
        "no_calibrated_value_publication_from_intake",
    ]


def test_calibration_gate_refuses_identity_mismatch(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    check = validate_calibrated_parameter_gate(
        estimator_id="different-estimator",
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=proof,
        calibration_preflight_request=_request(repo_root),
        expected_aggregate_input_digest=_expected_digest(proof),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert "estimator_id_mismatch" in check.message


def test_calibration_gate_wrapper_refuses_identity_mismatch(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    check = check_calibration_leakage_proof_for_promotion(
        proof,
        estimator_id="different-estimator",
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_preflight_request=_request(repo_root),
        expected_aggregate_input_digest=_expected_digest(proof),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert "estimator_id_mismatch" in check.message


@pytest.mark.parametrize("approval_id", [" ", "synthetic-approval-placeholder", "reviewed"])
def test_calibration_gate_refuses_unreviewed_approval_ids(repo_root, approval_id):
    proof = build_calibration_leakage_proof(_request(repo_root))

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=proof,
        calibration_preflight_request=_request(repo_root),
        expected_aggregate_input_digest=_expected_digest(proof),
        approval_id=approval_id,
    )

    assert check.status == "failed"
    assert "missing_approval_id" in check.message


def test_calibration_gate_refuses_malformed_proof_dict(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root)).model_dump(mode="json")
    expected_digest = proof["determinism"]["aggregate_input_digest"]
    proof.pop("proof_id")

    check = validate_calibrated_parameter_gate(
        estimator_id="synthetic_budget_driver_mean",
        parameter="synthetic_phase_hours_mean",
        corpus_version_ref=(
            "examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json"
        ),
        screen_version="synthetic-screen-v0",
        calibration_leakage_proof=proof,
        calibration_preflight_request=_request(repo_root),
        expected_aggregate_input_digest=expected_digest,
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_valid"
    assert "invalid" in check.message


def test_calibration_gate_refuses_non_validating_constructed_proof(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))
    forged = proof.model_copy()
    forged.calibrated_value_published = "False"

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=forged,
        calibration_preflight_request=_request(repo_root),
        expected_aggregate_input_digest=_expected_digest(proof),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_valid"


def test_calibration_gate_refuses_forged_proof_id(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root)).model_dump(mode="json")
    expected_digest = proof["determinism"]["aggregate_input_digest"]
    proof["proof_id"] = "calibrationleakageproof_forged"

    check = validate_calibrated_parameter_gate(
        estimator_id=proof["estimator_id"],
        parameter=proof["parameter"],
        corpus_version_ref=proof["corpus_version_ref"],
        screen_version=proof["screen_version"],
        calibration_leakage_proof=proof,
        calibration_preflight_request=_request(repo_root),
        expected_aggregate_input_digest=expected_digest,
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert "proof_id does not match" in check.message


def test_calibration_gate_refuses_self_consistent_forged_proof(repo_root):
    request = _request(repo_root)
    original_proof = build_calibration_leakage_proof(request)
    forged = original_proof.model_dump(mode="json")
    forged_digest = "sha256:" + ("0" * 64)
    forged["determinism"]["aggregate_input_digest"] = forged_digest
    forged["proof_id"] = (
        "calibrationleakageproof_" + sha256(forged_digest.encode("utf-8")).hexdigest()[:20]
    )
    forged["lomo"]["delta_lomo"] = 0.0

    CalibrationLeakageProof.model_validate(forged)
    check = validate_calibrated_parameter_gate(
        estimator_id=forged["estimator_id"],
        parameter=forged["parameter"],
        corpus_version_ref=forged["corpus_version_ref"],
        screen_version=forged["screen_version"],
        calibration_leakage_proof=forged,
        calibration_preflight_request=request,
        expected_aggregate_input_digest=_expected_digest(original_proof),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_request_binding"
    assert "aggregate_input_digest_mismatch" in check.message
    assert "proof_id_mismatch" in check.message
    assert "proof_content_mismatch" in check.message


def test_calibration_gate_refuses_matching_forged_request_and_proof(repo_root):
    original_proof = build_calibration_leakage_proof(_request(repo_root))
    forged_request = _request(repo_root)
    forged_request["matters"][0]["contribution"] = 999.0
    forged_proof = build_calibration_leakage_proof(forged_request)

    check = validate_calibrated_parameter_gate(
        estimator_id=forged_proof.estimator_id,
        parameter=forged_proof.parameter,
        corpus_version_ref=forged_proof.corpus_version_ref,
        screen_version=forged_proof.screen_version,
        calibration_leakage_proof=forged_proof,
        calibration_preflight_request=forged_request,
        expected_aggregate_input_digest=_expected_digest(original_proof),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_request_binding"
    assert "expected_digest_does_not_match_rebuilt_request" in check.message
    assert "proof_digest_does_not_match_expected_digest" in check.message


def test_reviewed_learning_report_includes_calibration_gate_failure(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    report = build_reviewed_learning_gate_report(
        calibrated_parameter_gate_requests=[
            {
                "estimator_id": proof.estimator_id,
                "parameter": proof.parameter,
                "corpus_version_ref": proof.corpus_version_ref,
                "screen_version": proof.screen_version,
                "calibration_leakage_proof": proof.model_dump(mode="json"),
                "calibration_preflight_request": _request(repo_root),
                "expected_aggregate_input_digest": _expected_digest(proof),
                "proof_ref": proof.corpus_version_ref,
            }
        ]
    )

    assert report.status == "failed"
    assert any(
        check.check_id == "calibration_leakage_proof_promotion_gate"
        and check.status == "failed"
        and "missing_approval_id" in check.message
        for check in report.checks
    )


def test_reviewed_learning_report_accepts_calibration_gate_review_inputs(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    report = build_reviewed_learning_gate_report(
        calibrated_parameter_gate_requests=[
            {
                "estimator_id": proof.estimator_id,
                "parameter": proof.parameter,
                "corpus_version_ref": proof.corpus_version_ref,
                "screen_version": proof.screen_version,
                "calibration_leakage_proof": proof.model_dump(mode="json"),
                "calibration_preflight_request": _request(repo_root),
                "expected_aggregate_input_digest": _expected_digest(proof),
                "approval_id": "approval:human-review-record-0001",
                "proof_ref": proof.corpus_version_ref,
            }
        ]
    )

    assert report.status == "candidate_learning_gate_ready"
    assert report.candidate_count == 0
    assert report.candidates == []
    assert proof.corpus_version_ref in report.source_report_refs
    assert any(
        check.check_id == "calibration_gate_review_inputs_visible"
        and check.status == "passed"
        and check.candidate_ids == [proof.proof_id]
        and "not an ordinary learning candidate" in check.message
        for check in report.checks
    )
    assert any(
        check.check_id == "calibration_leakage_proof_promotion_gate" and check.status == "passed"
        for check in report.checks
    )


def test_dp_calibration_gate_requires_independent_release_digest(repo_root, tmp_path):
    request = _dp_request(repo_root)
    proof = build_dp_calibration_leakage_proof(
        request,
        ledger_path=tmp_path / "gate.synthetic-zcdp-ledger.jsonl",
        synthetic_replay_seed=b"synthetic-cal-dp-gate-seed-0001",
        generated_at="2026-07-10T00:00:00+00:00",
    )

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=proof,
        calibration_preflight_request=request,
        expected_aggregate_input_digest=_expected_digest(proof),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_expected_dp_release_digest_required"


def test_dp_calibration_gate_stays_blocked_without_authoritative_ledger_and_seed(
    repo_root, tmp_path
):
    request = _dp_request(repo_root)
    proof = build_dp_calibration_leakage_proof(
        request,
        ledger_path=tmp_path / "gate-pass.synthetic-zcdp-ledger.jsonl",
        synthetic_replay_seed=b"synthetic-cal-dp-gate-seed-0002",
        generated_at="2026-07-10T00:00:00+00:00",
    )
    assert proof.dp is not None

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=proof,
        calibration_preflight_request=request,
        expected_aggregate_input_digest=_expected_digest(proof),
        expected_dp_release_digest=proof.dp.release_digest,
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_promotion_gate"
    assert "authoritative_dp_ledger_receipt_not_verified" in check.message
    assert "governed_secret_seed_authority_not_verified" in check.message


def test_dp_gate_rejects_forged_authority_booleans(repo_root, tmp_path):
    request = _dp_request(repo_root)
    proof = build_dp_calibration_leakage_proof(
        request,
        ledger_path=tmp_path / "gate-forged-authority.synthetic-zcdp-ledger.jsonl",
        synthetic_replay_seed=b"synthetic-cal-dp-gate-seed-0004",
        generated_at="2026-07-10T00:00:00+00:00",
    )
    assert proof.dp is not None
    forged = proof.model_dump(mode="json")
    forged["dp"]["authoritative_ledger_receipt_verified"] = True
    forged["dp"]["secret_seed_authority_verified"] = True

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=forged,
        calibration_preflight_request=request,
        expected_aggregate_input_digest=_expected_digest(proof),
        expected_dp_release_digest=proof.dp.release_digest,
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_valid"


def test_dp_calibration_gate_refuses_wrong_external_release_digest(repo_root, tmp_path):
    request = _dp_request(repo_root)
    proof = build_dp_calibration_leakage_proof(
        request,
        ledger_path=tmp_path / "gate-wrong-anchor.synthetic-zcdp-ledger.jsonl",
        synthetic_replay_seed=b"synthetic-cal-dp-gate-seed-0003",
        generated_at="2026-07-10T00:00:00+00:00",
    )

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=proof,
        calibration_preflight_request=request,
        expected_aggregate_input_digest=_expected_digest(proof),
        expected_dp_release_digest="sha256:" + ("0" * 64),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert "dp_release_digest_does_not_match_expected_digest" in check.message


def test_reviewed_learning_report_carries_dp_gate_without_ordinary_candidate(repo_root, tmp_path):
    request = _dp_request(repo_root)
    proof = build_dp_calibration_leakage_proof(
        request,
        ledger_path=tmp_path / "report.synthetic-zcdp-ledger.jsonl",
        synthetic_replay_seed=b"synthetic-cal-dp-report-seed-001",
        generated_at="2026-07-10T00:00:00+00:00",
    )
    assert proof.dp is not None

    report = build_reviewed_learning_gate_report(
        calibrated_parameter_gate_requests=[
            {
                "estimator_id": proof.estimator_id,
                "parameter": proof.parameter,
                "corpus_version_ref": proof.corpus_version_ref,
                "screen_version": proof.screen_version,
                "calibration_leakage_proof": proof.model_dump(mode="json"),
                "calibration_preflight_request": request,
                "expected_aggregate_input_digest": _expected_digest(proof),
                "expected_dp_release_digest": proof.dp.release_digest,
                "approval_id": "approval:human-review-record-0001",
                "proof_ref": proof.corpus_version_ref,
            }
        ]
    )

    assert report.status == "failed"
    assert report.candidate_count == 0
    assert report.candidates == []
    assert any(
        check.check_id == "calibration_leakage_proof_promotion_gate"
        and check.status == "failed"
        and check.candidate_ids == [proof.proof_id]
        and "authoritative_dp_ledger_receipt_not_verified" in check.message
        for check in report.checks
    )
