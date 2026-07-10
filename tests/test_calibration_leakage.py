import pytest

from lawfirm_os_intake.calibration import (
    CalibrationPreflightRequest,
    build_calibration_leakage_proof,
)
from lawfirm_os_intake.util import load_json


def _request(repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json"
    )
    return raw["request"]


def test_aggregate_lomo_scaffold_emits_candidate_proof_without_values(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    assert proof.status == "candidate"
    assert proof.path == "aggregate_only"
    assert proof.calibrated_value_published is False
    assert proof.dp is None
    assert proof.candidate_only is True
    assert proof.human_review_required is True
    assert proof.approval_id is None
    assert proof.kanon.distinct_matters == 4
    assert proof.kanon.distinct_protected_units == 4
    assert proof.kanon.K == 4
    assert proof.kanon.dominance_ok is True
    assert proof.lomo.dominance_ok is True
    assert proof.lomo.delta_lomo <= proof.lomo.delta_max
    assert proof.reconstruction.adversary_model == "synthetic strong all-but-one-matter placeholder"
    assert proof.reconstruction.recovered_rate == 0.25
    assert proof.reconstruction.chance_rate == 0.25
    assert proof.reconstruction.passed is True
    assert proof.reconstruction.scaffold_only is True
    assert proof.determinism.aggregate_byte_identical is True
    assert proof.group_privacy.unit == "matter"
    assert proof.group_privacy.effective_epsilon is None


def test_client_or_affiliate_group_k_counts_protected_units(repo_root):
    raw = _request(repo_root)
    raw["policy"]["protected_unit"] = "client"
    for matter in raw["matters"]:
        matter["protected_unit_id"] = "same-synthetic-client"

    proof = build_calibration_leakage_proof(raw)

    assert proof.status == "refused"
    assert proof.path == "refused"
    assert proof.kanon.distinct_matters == 4
    assert proof.kanon.distinct_protected_units == 1
    assert "insufficient_distinct_protected_units_for_aggregate_only" in proof.refusal_reasons


def test_missing_policy_inputs_fail_closed(repo_root):
    raw = _request(repo_root)
    raw["policy"] = {
        "policy_label": "Synthetic policy placeholder for Packet E tests only",
    }

    proof = build_calibration_leakage_proof(raw)

    assert proof.status == "refused"
    assert proof.path == "refused"
    assert set(proof.refusal_reasons) >= {
        "missing_protected_unit",
        "missing_minimum_distinct_matters_K",
        "missing_dominance_threshold",
        "missing_lomo_delta_limit",
        "missing_adversary_model",
        "missing_reconstruction_test_metrics",
    }
    assert proof.kanon.dominance_ok is False
    assert proof.reconstruction.passed is False


def test_dominance_or_lomo_routes_to_refused_until_dp_exists(repo_root):
    raw = _request(repo_root)
    raw["matters"][0]["contribution"] = 100.0

    proof = build_calibration_leakage_proof(raw)

    assert proof.status == "refused"
    assert proof.path == "refused"
    assert "dominance_threshold_exceeded_dp_path_not_implemented" in proof.refusal_reasons
    assert "lomo_delta_limit_exceeded_dp_path_not_implemented" in proof.refusal_reasons
    assert proof.dp is None
    assert proof.calibrated_value_published is False


def test_digest_binds_policy_and_protected_unit_membership(repo_root):
    base = _request(repo_root)
    policy_changed = _request(repo_root)
    policy_changed["policy"]["dominance_threshold"] = 0.99
    grouping_changed = _request(repo_root)
    grouping_changed["matters"][0]["protected_unit_id"] = "changed-synthetic-unit"

    base_proof = build_calibration_leakage_proof(base)
    policy_proof = build_calibration_leakage_proof(policy_changed)
    grouping_proof = build_calibration_leakage_proof(grouping_changed)

    assert policy_proof.proof_id != base_proof.proof_id
    assert policy_proof.determinism.aggregate_input_digest != (
        base_proof.determinism.aggregate_input_digest
    )
    assert grouping_proof.proof_id != base_proof.proof_id
    assert grouping_proof.determinism.aggregate_input_digest != (
        base_proof.determinism.aggregate_input_digest
    )


def test_reconstruction_metrics_fail_closed(repo_root):
    raw = _request(repo_root)
    raw["policy"]["reconstruction_recovered_rate"] = 0.5
    raw["policy"]["reconstruction_chance_rate"] = 0.25

    proof = build_calibration_leakage_proof(raw)

    assert proof.status == "refused"
    assert proof.path == "refused"
    assert "reconstruction_test_failed" in proof.refusal_reasons
    assert proof.reconstruction.passed is False


@pytest.mark.parametrize(
    "flag",
    [
        "contains_real_client_data",
        "contains_real_matter_data",
        "contains_carrier_private_data",
        "contains_privileged_data",
    ],
)
def test_real_or_protected_data_path_fails_before_proof(repo_root, flag):
    raw = _request(repo_root)
    raw["matters"][0][flag] = True

    with pytest.raises(ValueError, match="prohibited data"):
        CalibrationPreflightRequest.model_validate(raw)


@pytest.mark.parametrize("field_name", ["matter_id", "protected_unit_id"])
def test_empty_protected_unit_identifiers_fail_closed(repo_root, field_name):
    raw = _request(repo_root)
    raw["matters"][0][field_name] = ""

    with pytest.raises(ValueError):
        CalibrationPreflightRequest.model_validate(raw)


def test_non_candidate_or_publishing_path_fails_closed(repo_root):
    raw = _request(repo_root)
    raw["publish_calibrated_value"] = True

    with pytest.raises(ValueError, match="must not publish calibrated values"):
        CalibrationPreflightRequest.model_validate(raw)


def test_policy_values_must_be_labeled_synthetic_placeholders(repo_root):
    raw = _request(repo_root)
    raw["policy"]["policy_label"] = "production calibration policy"

    with pytest.raises(ValueError, match="synthetic policy placeholders"):
        CalibrationPreflightRequest.model_validate(raw)
