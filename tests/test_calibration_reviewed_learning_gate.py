import pytest

from lawfirm_os_intake.calibration import build_calibration_leakage_proof
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
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_promotion_gate"
    assert "missing_approval_id" in check.message
    assert check.candidate_ids == [proof.proof_id]


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
        approval_id="approval:human-review-record-0001",
    )

    assert proof.status == "refused"
    assert check.status == "failed"
    assert "path=refused" in check.message
    assert "refusal_reasons_present" in check.message


def test_calibration_gate_accepts_valid_proof_plus_explicit_approval_id(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    check = validate_calibrated_parameter_gate(
        estimator_id=proof.estimator_id,
        parameter=proof.parameter,
        corpus_version_ref=proof.corpus_version_ref,
        screen_version=proof.screen_version,
        calibration_leakage_proof=proof.model_dump(mode="json"),
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "passed"
    assert check.candidate_ids == [proof.proof_id]
    assert "does not mutate" in check.message
    assert CALIBRATION_LEAKAGE_PROOF_REQUIRED_GATES == [
        "valid_calibration_leakage_proof",
        "human_calibration_approval_id",
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
        approval_id=approval_id,
    )

    assert check.status == "failed"
    assert "missing_approval_id" in check.message


def test_calibration_gate_refuses_malformed_proof_dict(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root)).model_dump(mode="json")
    proof.pop("proof_id")

    check = validate_calibrated_parameter_gate(
        estimator_id="synthetic_budget_driver_mean",
        parameter="synthetic_phase_hours_mean",
        corpus_version_ref=(
            "examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json"
        ),
        screen_version="synthetic-screen-v0",
        calibration_leakage_proof=proof,
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
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "calibration_leakage_proof_valid"


def test_calibration_gate_refuses_forged_proof_id(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root)).model_dump(mode="json")
    proof["proof_id"] = "calibrationleakageproof_forged"

    check = validate_calibrated_parameter_gate(
        estimator_id=proof["estimator_id"],
        parameter=proof["parameter"],
        corpus_version_ref=proof["corpus_version_ref"],
        screen_version=proof["screen_version"],
        calibration_leakage_proof=proof,
        approval_id="approval:human-review-record-0001",
    )

    assert check.status == "failed"
    assert "proof_id does not match" in check.message


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
                "approval_id": "approval:human-review-record-0001",
                "proof_ref": proof.corpus_version_ref,
            }
        ]
    )

    assert report.status == "no_learning_candidates"
    assert any(
        check.check_id == "calibration_leakage_proof_promotion_gate" and check.status == "passed"
        for check in report.checks
    )
