import pytest

from lawfirm_os_intake.calibration import (
    CalibrationLeakageProof,
    CalibrationPreflightRequest,
    build_calibration_leakage_proof,
    build_dp_calibration_leakage_proof,
)
from lawfirm_os_intake.util import load_json


def _request(repo_root):
    raw = load_json(
        repo_root
        / "examples/synthetic/calibration/calib-aggregate-clean.synthetic-policy-placeholder.json"
    )
    return raw["request"]


def _dp_request(repo_root, fixture_id):
    raw = load_json(
        repo_root
        / "examples/synthetic/calibration"
        / f"{fixture_id}.synthetic-policy-placeholder.json"
    )
    return raw["request"]


def _synthetic_seed():
    return b"synthetic-cal-dp-test-seed-0001"


def test_aggregate_lomo_scaffold_emits_candidate_proof_without_values(repo_root):
    proof = build_calibration_leakage_proof(_request(repo_root))

    assert proof.status == "candidate"
    assert proof.path == "aggregate_only"
    assert proof.calibrated_value_published is False
    assert proof.dp is None
    assert proof.candidate_only is True
    assert proof.human_review_required is True
    assert proof.approval_id is None
    assert proof.methodology.version == "calibration-aggregate-preflight-v0.2"
    assert proof.methodology.k_count_basis == "distinct_declared_protected_units"
    assert proof.methodology.lomo_formula == (
        "max_abs(full_matter_mean_minus_leave_one_matter_out_mean)"
    )
    assert proof.methodology.thresholds == ("request_policy_labeled_synthetic_policy_placeholder")
    assert proof.kanon.distinct_matters == 4
    assert proof.kanon.distinct_protected_units == 4
    assert proof.kanon.K == 4
    assert proof.kanon.dominance_ok is True
    assert proof.lomo.dominance_ok is True
    assert proof.lomo.unit == "matter"
    assert proof.lomo.matter_count == 4
    assert proof.lomo.delta_lomo <= proof.lomo.delta_max
    assert proof.reconstruction.adversary_model == "synthetic strong all-but-one-matter placeholder"
    assert proof.reconstruction.recovered_rate == 0.25
    assert proof.reconstruction.chance_rate == 0.25
    assert proof.reconstruction.passed is True
    assert proof.reconstruction.scaffold_only is True
    assert proof.reconstruction.evidence_basis == "supplied_synthetic_scaffold_metrics"
    assert proof.reconstruction.computed_adversary_test_performed is False
    assert proof.reconstruction.formal_privacy_guarantee_claimed is False
    assert proof.determinism.aggregate_byte_identical is True
    assert proof.group_privacy.unit == "matter"
    assert proof.group_privacy.effective_epsilon is None


def test_client_or_affiliate_group_k_counts_protected_units(repo_root):
    matter_level_proof = build_calibration_leakage_proof(_request(repo_root))
    raw = _request(repo_root)
    raw["policy"]["protected_unit"] = "client"
    for matter in raw["matters"]:
        matter["protected_unit_id"] = "same-synthetic-client"

    proof = build_calibration_leakage_proof(raw)

    assert proof.status == "refused"
    assert proof.path == "refused"
    assert proof.kanon.distinct_matters == 4
    assert proof.kanon.distinct_protected_units == 1
    assert proof.lomo.unit == "matter"
    assert proof.lomo.matter_count == 4
    assert proof.lomo.delta_lomo == pytest.approx(matter_level_proof.lomo.delta_lomo)
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


@pytest.mark.parametrize(
    ("field_name", "replacement"),
    [
        ("request_id", "changed-request-id"),
        ("estimator_id", "changed-estimator"),
        ("parameter", "changed-parameter"),
        ("corpus_version_ref", "changed-corpus-version"),
        ("screen_version", "changed-screen-version"),
    ],
)
def test_digest_binds_request_identity(repo_root, field_name, replacement):
    base_proof = build_calibration_leakage_proof(_request(repo_root))
    changed = _request(repo_root)
    changed[field_name] = replacement

    changed_proof = build_calibration_leakage_proof(changed)

    assert changed_proof.proof_id != base_proof.proof_id
    assert changed_proof.determinism.aggregate_input_digest != (
        base_proof.determinism.aggregate_input_digest
    )


@pytest.mark.parametrize(
    ("path", "replacement"),
    [
        (("matters", 0, "matter_id"), "changed-synthetic-matter"),
        (("matters", 0, "contribution"), 10.125),
        (("policy", "reconstruction_recovered_rate"), 0.24),
        (("policy", "reconstruction_chance_rate"), 0.26),
    ],
)
def test_digest_binds_matter_and_reconstruction_inputs(repo_root, path, replacement):
    base_proof = build_calibration_leakage_proof(_request(repo_root))
    changed = _request(repo_root)
    if path[0] == "matters":
        changed[path[0]][path[1]][path[2]] = replacement
    else:
        changed[path[0]][path[1]] = replacement

    changed_proof = build_calibration_leakage_proof(changed)

    assert changed_proof.proof_id != base_proof.proof_id
    assert changed_proof.determinism.aggregate_input_digest != (
        base_proof.determinism.aggregate_input_digest
    )


def test_digest_is_independent_of_input_order(repo_root):
    base = _request(repo_root)
    reordered = _request(repo_root)
    reordered["matters"] = list(reversed(reordered["matters"]))

    base_proof = build_calibration_leakage_proof(base)
    reordered_proof = build_calibration_leakage_proof(reordered)

    assert reordered_proof.proof_id == base_proof.proof_id
    assert reordered_proof.determinism.aggregate_input_digest == (
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


def test_duplicate_matter_ids_fail_before_sensitivity_accounting(repo_root):
    raw = _request(repo_root)
    raw["matters"][1]["matter_id"] = raw["matters"][0]["matter_id"]

    with pytest.raises(ValueError, match="one aggregated contribution per unique matter_id"):
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


def test_dominance_routes_to_synthetic_dp_candidate_with_local_ledger_evidence(repo_root, tmp_path):
    ledger_path = tmp_path / "dominance.synthetic-zcdp-ledger.jsonl"
    proof = build_dp_calibration_leakage_proof(
        _dp_request(repo_root, "calib-dominance-route-dp"),
        ledger_path=ledger_path,
        synthetic_replay_seed=_synthetic_seed(),
        generated_at="2026-07-10T00:00:00+00:00",
    )

    assert proof.status == "candidate"
    assert proof.path == "dp"
    assert proof.dp is not None
    assert proof.dp.accounting == "zCDP"
    assert proof.dp.clipped_matter_count == 1
    assert proof.dp.calibrated_value_included is False
    assert proof.dp.production_privacy_guarantee_claimed is False
    assert proof.dp.local_jsonl_fsync_readback_confirmed is True
    assert proof.dp.authoritative_ledger_receipt_verified is False
    assert proof.dp.seed_is_synthetic_replay_only is True
    assert proof.dp.secret_seed_authority_verified is False
    assert proof.reconstruction.computed_adversary_test_performed is True
    assert proof.reconstruction.formal_privacy_guarantee_claimed is False
    assert proof.reconstruction.security_or_privacy_evidence_claimed is False
    assert proof.utility["utility_floor_ok"] is True
    assert proof.determinism.aggregate_byte_identical is None
    assert proof.determinism.dp_seed_hash == proof.dp.seed_hash
    assert ledger_path.read_text(encoding="utf-8").count("\n") == 1


def test_dp_release_replays_deterministically_from_synthetic_seed(repo_root, tmp_path):
    request = _dp_request(repo_root, "calib-dp-epsilon-bound")
    first = build_dp_calibration_leakage_proof(
        request,
        ledger_path=tmp_path / "first.synthetic-zcdp-ledger.jsonl",
        synthetic_replay_seed=_synthetic_seed(),
        generated_at="2026-07-10T00:00:00+00:00",
    )
    second = build_dp_calibration_leakage_proof(
        request,
        ledger_path=tmp_path / "second.synthetic-zcdp-ledger.jsonl",
        synthetic_replay_seed=_synthetic_seed(),
        generated_at="2026-07-10T00:00:00+00:00",
    )

    assert first.dp is not None and second.dp is not None
    assert first.dp.release_digest == second.dp.release_digest
    assert first.dp.noised_sufficient_stats_digest == second.dp.noised_sufficient_stats_digest
    assert first.proof_id == second.proof_id


def test_group_privacy_uses_k_squared_rho_not_linear_rho(repo_root, tmp_path):
    proof = build_dp_calibration_leakage_proof(
        _dp_request(repo_root, "calib-group-privacy"),
        ledger_path=tmp_path / "group.synthetic-zcdp-ledger.jsonl",
        synthetic_replay_seed=_synthetic_seed(),
        generated_at="2026-07-10T00:00:00+00:00",
    )

    assert proof.status == "candidate"
    assert proof.dp is not None
    assert proof.dp.group_size == 6
    assert proof.dp.base_rho == pytest.approx(0.01)
    assert proof.dp.effective_rho == pytest.approx(0.36)
    assert proof.dp.effective_rho != pytest.approx(0.06)
    assert proof.group_privacy.accounting_rule == "zcdp_group_privacy_k_squared_rho"
    assert proof.group_privacy.effective_rho == pytest.approx(0.36)


def test_dp_proof_rejects_linearized_group_accounting(repo_root, tmp_path):
    proof = build_dp_calibration_leakage_proof(
        _dp_request(repo_root, "calib-group-privacy"),
        ledger_path=tmp_path / "tamper-group.synthetic-zcdp-ledger.jsonl",
        synthetic_replay_seed=_synthetic_seed(),
        generated_at="2026-07-10T00:00:00+00:00",
    ).model_dump(mode="json")
    proof["dp"]["effective_rho"] = proof["dp"]["base_rho"] * proof["dp"]["group_size"]
    proof["group_privacy"]["effective_rho"] = proof["dp"]["effective_rho"]

    with pytest.raises(ValueError, match="k-squared group accounting"):
        CalibrationLeakageProof.model_validate(proof)


@pytest.mark.parametrize(
    ("fixture_id", "reason"),
    [
        ("calib-utility-floor", "noise_exceeds_signal_stay_synthetic"),
        ("calib-budget-exhausted", "privacy_budget_exhausted_before_sampling"),
    ],
)
def test_dp_utility_or_budget_failure_stays_synthetic_without_ledger_write(
    repo_root, tmp_path, fixture_id, reason
):
    ledger_path = tmp_path / f"{fixture_id}.synthetic-zcdp-ledger.jsonl"
    proof = build_dp_calibration_leakage_proof(
        _dp_request(repo_root, fixture_id),
        ledger_path=ledger_path,
        synthetic_replay_seed=_synthetic_seed(),
        generated_at="2026-07-10T00:00:00+00:00",
    )

    assert proof.status == "refused"
    assert proof.path == "refused"
    assert reason in proof.refusal_reasons
    assert proof.dp is None
    assert proof.calibrated_value_published is False
    assert not ledger_path.exists()


def test_dp_builder_refuses_missing_human_policy_fields_before_write(repo_root, tmp_path):
    request = _dp_request(repo_root, "calib-dp-epsilon-bound")
    request["policy"].pop("dp_rho")
    ledger_path = tmp_path / "missing-policy.synthetic-zcdp-ledger.jsonl"

    proof = build_dp_calibration_leakage_proof(
        request,
        ledger_path=ledger_path,
        synthetic_replay_seed=_synthetic_seed(),
    )

    assert proof.status == "refused"
    assert "missing_dp_rho" in proof.refusal_reasons
    assert not ledger_path.exists()
