from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from math import isclose, isfinite, sqrt
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from ..privacy import (
    GaussianMechanism,
    SyntheticPrivacyScope,
    SyntheticReplaySeed,
    ZCDPLedger,
    zcdp_to_epsilon_delta,
)
from .estimators import l2_norm, mean_sufficient_stat_contributions
from .leakage_proof import calibration_release_digest
from .lomo import max_leave_one_matter_out_mean_delta, top1_protected_unit_leverage
from .reconstruction_test import run_all_but_one_sum_reconstruction_smoke_check


class CalibrationStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ProtectedUnit = Literal["matter", "client", "affiliate_group"]
CalibrationPath = Literal["aggregate_only", "dp", "refused"]
ProofStatus = Literal["candidate", "refused"]
CALIBRATION_METHODOLOGY_VERSION = "calibration-aggregate-preflight-v0.2"


class CalibrationInputMatter(CalibrationStrictModel):
    matter_id: str = Field(min_length=1)
    data_origin: Literal["synthetic"] = "synthetic"
    data_class: Literal["synthetic_fixture"] = "synthetic_fixture"
    protected_unit_id: str = Field(min_length=1)
    contribution: float
    contains_real_client_data: bool = False
    contains_real_matter_data: bool = False
    contains_carrier_private_data: bool = False
    contains_privileged_data: bool = False

    @model_validator(mode="after")
    def synthetic_only(self) -> "CalibrationInputMatter":
        prohibited = [
            self.contains_real_client_data,
            self.contains_real_matter_data,
            self.contains_carrier_private_data,
            self.contains_privileged_data,
        ]
        if self.data_origin != "synthetic" or self.data_class != "synthetic_fixture":
            raise ValueError("calibration input matter must be synthetic_fixture only")
        if any(prohibited):
            raise ValueError("calibration input matter contains prohibited data")
        if not isfinite(self.contribution):
            raise ValueError("calibration contribution must be finite")
        return self


class CalibrationPreflightPolicy(CalibrationStrictModel):
    policy_label: str
    protected_unit: ProtectedUnit | None = None
    minimum_distinct_matters: int | None = Field(default=None, ge=1)
    dominance_threshold: float | None = Field(default=None, gt=0, le=1)
    lomo_delta_limit: float | None = Field(default=None, ge=0)
    adversary_model: str | None = None
    reconstruction_recovered_rate: float | None = Field(default=None, ge=0, le=1)
    reconstruction_chance_rate: float | None = Field(default=None, ge=0, le=1)
    reconstruction_margin: float = Field(default=0.0, ge=0)
    reconstruction_tolerance: float | None = Field(default=None, ge=0)
    dp_route_required: bool = False
    dp_rho: float | None = Field(default=None, gt=0)
    dp_report_delta: float | None = Field(default=None, gt=0, lt=1)
    dp_clip_norm: float | None = Field(default=None, gt=0)
    dp_rho_cap: float | None = Field(default=None, gt=0)
    dp_max_noise_to_signal_ratio: float | None = Field(default=None, gt=0)

    @model_validator(mode="after")
    def synthetic_placeholder_label_required(self) -> "CalibrationPreflightPolicy":
        if "synthetic policy placeholder" not in self.policy_label.lower():
            raise ValueError(
                "calibration policy values must be labeled synthetic policy placeholders"
            )
        if (
            self.reconstruction_chance_rate is not None
            and self.reconstruction_chance_rate + self.reconstruction_margin >= 1
        ):
            raise ValueError("reconstruction chance plus margin must remain below one")
        return self


class CalibrationPreflightRequest(CalibrationStrictModel):
    request_id: str
    estimator_id: str
    parameter: str
    corpus_version_ref: str
    screen_version: str
    runtime_scope: Literal["synthetic_candidate"] = "synthetic_candidate"
    candidate_only: bool = True
    publish_calibrated_value: bool = False
    policy: CalibrationPreflightPolicy
    matters: list[CalibrationInputMatter]

    @model_validator(mode="after")
    def candidate_synthetic_scope_required(self) -> "CalibrationPreflightRequest":
        if self.runtime_scope != "synthetic_candidate" or not self.candidate_only:
            raise ValueError("calibration preflight is synthetic_candidate and candidate_only only")
        if self.publish_calibrated_value:
            raise ValueError("calibration preflight must not publish calibrated values")
        if not self.matters:
            raise ValueError("calibration preflight requires synthetic matters")
        matter_ids = [matter.matter_id for matter in self.matters]
        if len(matter_ids) != len(set(matter_ids)):
            raise ValueError(
                "calibration preflight requires one aggregated contribution per unique matter_id"
            )
        return self


class CalibrationKAnonRecord(CalibrationStrictModel):
    distinct_matters: int
    distinct_protected_units: int
    top1_leverage: float
    K: int | None
    dominance_ok: bool


class CalibrationMethodologyRecord(CalibrationStrictModel):
    version: Literal["calibration-aggregate-preflight-v0.2"] = CALIBRATION_METHODOLOGY_VERSION
    inputs: Literal[
        "synthetic_request_metadata_policy_matter_ids_protected_unit_ids_data_flags_contributions"
    ] = "synthetic_request_metadata_policy_matter_ids_protected_unit_ids_data_flags_contributions"
    aggregation: Literal["arithmetic_mean_of_matter_contributions"] = (
        "arithmetic_mean_of_matter_contributions"
    )
    lomo_formula: Literal["max_abs(full_matter_mean_minus_leave_one_matter_out_mean)"] = (
        "max_abs(full_matter_mean_minus_leave_one_matter_out_mean)"
    )
    top1_leverage_formula: Literal[
        "max_abs(protected_unit_sum)_div_sum_abs(protected_unit_sums)"
    ] = "max_abs(protected_unit_sum)_div_sum_abs(protected_unit_sums)"
    k_count_basis: Literal["distinct_declared_protected_units"] = (
        "distinct_declared_protected_units"
    )
    thresholds: Literal["request_policy_labeled_synthetic_policy_placeholder"] = (
        "request_policy_labeled_synthetic_policy_placeholder"
    )
    normalization: Literal["none"] = "none"
    tie_breaking: Literal["canonical_json_lexicographic_order"] = (
        "canonical_json_lexicographic_order"
    )
    uncertainty_handling: Literal["refuse_missing_nonfinite_or_threshold_breach"] = (
        "refuse_missing_nonfinite_or_threshold_breach"
    )
    output_range: Literal["aggregate_only_dp_or_refused_candidate_proof"] = (
        "aggregate_only_dp_or_refused_candidate_proof"
    )


class CalibrationLomoRecord(CalibrationStrictModel):
    estimator_id: str
    unit: Literal["matter"] = "matter"
    matter_count: int = Field(ge=0)
    delta_lomo: float | None
    delta_max: float | None
    top1_leverage: float
    p_dominance: float | None
    dominance_ok: bool


class CalibrationReconstructionRecord(CalibrationStrictModel):
    adversary_model: str | None
    aux: Literal["all-but-one-matter"] = "all-but-one-matter"
    target_metric: Literal[
        "aggregate_mean_membership_proxy",
        "synthetic_all_but_one_sum_smoke_check",
    ] = "aggregate_mean_membership_proxy"
    recovered_rate: float | None = None
    chance_rate: float | None = None
    margin: float
    tolerance: float | None = None
    target_count: int | None = Field(default=None, ge=1)
    passed: bool
    scaffold_only: bool = True
    evidence_basis: Literal[
        "supplied_synthetic_scaffold_metrics",
        "computed_synthetic_all_but_one_sum_smoke_check",
    ] = "supplied_synthetic_scaffold_metrics"
    computed_adversary_test_performed: bool = False
    formal_privacy_guarantee_claimed: Literal[False] = False
    security_or_privacy_evidence_claimed: Literal[False] = False


class CalibrationGroupPrivacyRecord(CalibrationStrictModel):
    unit: ProtectedUnit | None
    max_group_size: int | None
    effective_rho: float | None = None
    effective_epsilon: float | None = None
    accounting_rule: Literal["zcdp_group_privacy_k_squared_rho"] | None = None


class CalibrationDpRecord(CalibrationStrictModel):
    mechanism: Literal["gaussian_zcdp_homegrown"] = "gaussian_zcdp_homegrown"
    accounting: Literal["zCDP"] = "zCDP"
    base_rho: float = Field(gt=0)
    effective_rho: float = Field(gt=0)
    rho_cap: float = Field(gt=0)
    cumulative_effective_rho_after: float = Field(gt=0)
    report_delta: float = Field(gt=0, lt=1)
    epsilon_at_delta_after: float = Field(gt=0)
    sensitivity: float = Field(gt=0)
    clip_norm: float = Field(gt=0)
    noise_standard_deviation: float = Field(gt=0)
    pre_clip_max_norm: float = Field(ge=0)
    clipped_matter_count: int = Field(ge=0)
    group_size: int = Field(ge=1)
    release_id: str
    seed_hash: str
    ledger_id: str
    ledger_policy_digest: str
    ledger_entry_hash: str
    clipped_sufficient_stats_digest: str
    noised_sufficient_stats_digest: str
    local_jsonl_fsync_readback_confirmed: Literal[True] = True
    authoritative_ledger_receipt_verified: Literal[False] = False
    release_digest: str
    parameters_are_synthetic_policy_placeholders: Literal[True] = True
    seed_is_synthetic_replay_only: Literal[True] = True
    secret_seed_authority_verified: Literal[False] = False
    production_privacy_guarantee_claimed: Literal[False] = False
    calibrated_value_included: Literal[False] = False

    @model_validator(mode="after")
    def accounting_is_self_consistent(self) -> "CalibrationDpRecord":
        if not isclose(
            self.effective_rho,
            self.base_rho * self.group_size**2,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("DP effective_rho must use zCDP k-squared group accounting")
        if self.cumulative_effective_rho_after > self.rho_cap:
            raise ValueError("DP cumulative rho exceeds the candidate ledger cap")
        expected_stddev = self.sensitivity / sqrt(2.0 * self.base_rho)
        if not isclose(
            self.noise_standard_deviation,
            expected_stddev,
            rel_tol=1e-12,
            abs_tol=1e-12,
        ):
            raise ValueError("DP Gaussian noise scale does not match sensitivity and rho")
        if not isclose(self.sensitivity, self.clip_norm, rel_tol=0.0, abs_tol=0.0):
            raise ValueError("DP sensitivity must be established by the clip norm")
        if not self.release_id:
            raise ValueError("DP release_id must be non-empty")
        return self


class CalibrationDeterminismRecord(CalibrationStrictModel):
    aggregate_byte_identical: bool | None
    rebuilt: bool
    aggregate_input_digest: str
    dp_seed_hash: str | None = None


class CalibrationLeakageProof(CalibrationStrictModel):
    proof_id: str
    request_id: str
    estimator_id: str
    parameter: str
    corpus_version_ref: str
    screen_version: str
    path: CalibrationPath
    status: ProofStatus
    refusal_reasons: list[str] = Field(default_factory=list)
    methodology: CalibrationMethodologyRecord
    kanon: CalibrationKAnonRecord
    lomo: CalibrationLomoRecord
    dp: CalibrationDpRecord | None = None
    reconstruction: CalibrationReconstructionRecord
    utility: dict[str, bool | float | None | str]
    determinism: CalibrationDeterminismRecord
    group_privacy: CalibrationGroupPrivacyRecord
    calibrated_value_published: Literal[False] = False
    candidate_only: Literal[True] = True
    human_review_required: Literal[True] = True
    approval_id: None = None
    generated_at: str

    @model_validator(mode="after")
    def proof_fields_consistent(self) -> "CalibrationLeakageProof":
        identity_digest = (
            self.dp.release_digest
            if self.path == "dp" and self.dp
            else (self.determinism.aggregate_input_digest)
        )
        expected_id = _proof_id_for_digest(identity_digest)
        if self.proof_id != expected_id:
            raise ValueError("calibration leakage proof_id does not match aggregate digest")
        if self.path == "dp" and self.dp is not None:
            expected_release_digest = _dp_release_digest(
                self.determinism.aggregate_input_digest,
                self.dp,
            )
            if self.dp.release_digest != expected_release_digest:
                raise ValueError("DP release digest does not match bound release evidence")
            if self.dp.release_id != _dp_release_id(
                self.determinism.aggregate_input_digest,
                self.dp.seed_hash,
            ):
                raise ValueError("DP release_id does not bind request and replay-seed hashes")
        if self.kanon.dominance_ok != self.lomo.dominance_ok:
            raise ValueError("calibration leakage dominance flags disagree")
        if self.lomo.unit != "matter":
            raise ValueError("calibration LOMO must remain matter-level")
        if self.reconstruction.recovered_rate is None or self.reconstruction.chance_rate is None:
            if self.reconstruction.passed:
                raise ValueError("reconstruction cannot pass without recovered/chance rates")
        else:
            reconstruction_ok = self.reconstruction.recovered_rate <= (
                self.reconstruction.chance_rate + self.reconstruction.margin
            )
            if self.reconstruction.passed and not reconstruction_ok:
                raise ValueError("reconstruction passed flag does not match metrics")
        if self.status == "candidate":
            if self.path not in {"aggregate_only", "dp"}:
                raise ValueError("candidate calibration proof must use an implemented path")
            if self.refusal_reasons:
                raise ValueError("candidate calibration proof cannot carry refusal reasons")
            if self.path == "aggregate_only" and (
                not self.kanon.dominance_ok or not self.lomo.dominance_ok
            ):
                raise ValueError("candidate calibration proof requires dominance screens to pass")
            if not self.reconstruction.passed:
                raise ValueError("candidate calibration proof requires reconstruction to pass")
            if self.reconstruction.formal_privacy_guarantee_claimed:
                raise ValueError(
                    "candidate reconstruction evidence cannot claim a formal guarantee"
                )
            if self.path == "aggregate_only" and (
                not self.reconstruction.scaffold_only
                or self.reconstruction.computed_adversary_test_performed
            ):
                raise ValueError("aggregate reconstruction must remain supplied scaffold evidence")
            if self.path == "dp" and (
                self.dp is None
                or self.reconstruction.scaffold_only
                or not self.reconstruction.computed_adversary_test_performed
                or self.determinism.dp_seed_hash != self.dp.seed_hash
                or self.group_privacy.effective_rho != self.dp.effective_rho
                or self.group_privacy.max_group_size != self.dp.group_size
                or self.group_privacy.accounting_rule != "zcdp_group_privacy_k_squared_rho"
            ):
                raise ValueError("DP candidate proof is missing bound release evidence")
            if not self.determinism.rebuilt:
                raise ValueError(
                    "candidate calibration proof requires deterministic rebuild evidence"
                )
            if self.path == "aggregate_only" and not self.determinism.aggregate_byte_identical:
                raise ValueError(
                    "candidate calibration proof requires deterministic aggregate rebuild"
                )
            if self.path == "dp" and self.determinism.aggregate_byte_identical is not None:
                raise ValueError("DP determinism must be represented by the replay-seed hash")
        if self.path != "dp" and self.dp is not None:
            raise ValueError("non-DP calibration proof cannot carry DP release evidence")
        if self.status == "refused" and not self.refusal_reasons:
            raise ValueError("refused calibration proof requires refusal reasons")
        return self


def build_calibration_leakage_proof(
    request: CalibrationPreflightRequest | dict,
) -> CalibrationLeakageProof:
    parsed = (
        request
        if isinstance(request, CalibrationPreflightRequest)
        else CalibrationPreflightRequest.model_validate(request)
    )
    protected_unit_contributions = _protected_unit_contributions(parsed)
    protected_unit_values = list(protected_unit_contributions.values())
    matter_contributions = _matter_contributions(parsed)
    matter_values = list(matter_contributions.values())
    top1_leverage = top1_protected_unit_leverage(protected_unit_values)
    lomo_delta = max_leave_one_matter_out_mean_delta(matter_values)
    distinct_matters = len(matter_contributions)
    distinct_protected_units = len(protected_unit_contributions)
    max_group_size = _max_group_size(parsed.matters)
    refusal_reasons = _refusal_reasons(
        parsed,
        distinct_matters=distinct_matters,
        distinct_protected_units=distinct_protected_units,
        top1_leverage=top1_leverage,
        lomo_delta=lomo_delta,
    )
    path: CalibrationPath = "refused" if refusal_reasons else "aggregate_only"
    status: ProofStatus = "refused" if refusal_reasons else "candidate"
    dominance_ok = _dominance_ok(parsed.policy, top1_leverage, lomo_delta)
    reconstruction_passed = _reconstruction_passed(parsed.policy)
    aggregate_digest = _aggregate_digest(parsed)

    return CalibrationLeakageProof(
        proof_id=_proof_id_for_digest(aggregate_digest),
        request_id=parsed.request_id,
        estimator_id=parsed.estimator_id,
        parameter=parsed.parameter,
        corpus_version_ref=parsed.corpus_version_ref,
        screen_version=parsed.screen_version,
        path=path,
        status=status,
        refusal_reasons=refusal_reasons,
        methodology=CalibrationMethodologyRecord(),
        kanon=CalibrationKAnonRecord(
            distinct_matters=distinct_matters,
            distinct_protected_units=distinct_protected_units,
            top1_leverage=top1_leverage,
            K=parsed.policy.minimum_distinct_matters,
            dominance_ok=dominance_ok,
        ),
        lomo=CalibrationLomoRecord(
            estimator_id=parsed.estimator_id,
            matter_count=distinct_matters,
            delta_lomo=lomo_delta,
            delta_max=parsed.policy.lomo_delta_limit,
            top1_leverage=top1_leverage,
            p_dominance=parsed.policy.dominance_threshold,
            dominance_ok=dominance_ok,
        ),
        reconstruction=CalibrationReconstructionRecord(
            adversary_model=parsed.policy.adversary_model,
            recovered_rate=parsed.policy.reconstruction_recovered_rate,
            chance_rate=parsed.policy.reconstruction_chance_rate,
            margin=parsed.policy.reconstruction_margin,
            passed=reconstruction_passed and path == "aggregate_only",
        ),
        utility={"band_width": None, "utility_floor_ok": None},
        determinism=CalibrationDeterminismRecord(
            aggregate_byte_identical=True,
            rebuilt=True,
            aggregate_input_digest=aggregate_digest,
        ),
        group_privacy=CalibrationGroupPrivacyRecord(
            unit=parsed.policy.protected_unit,
            max_group_size=max_group_size,
        ),
        generated_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
    )


def build_dp_calibration_leakage_proof(
    request: CalibrationPreflightRequest | dict,
    *,
    ledger_path: str | Path,
    synthetic_replay_seed: bytes,
    generated_at: str | None = None,
) -> CalibrationLeakageProof:
    """Build a synthetic-only DP release proof and durably debit its zCDP ledger."""
    parsed = (
        request
        if isinstance(request, CalibrationPreflightRequest)
        else CalibrationPreflightRequest.model_validate(request)
    )
    base = build_calibration_leakage_proof(parsed)
    missing = _missing_dp_policy_fields(parsed.policy)
    if missing:
        return _refused_dp_proof(base, [f"missing_{field}" for field in missing])
    if not parsed.policy.dp_route_required and base.path == "aggregate_only":
        return _refused_dp_proof(base, ["dp_route_not_required_by_synthetic_policy"])

    policy = parsed.policy
    assert policy.protected_unit is not None
    assert policy.dp_rho is not None
    assert policy.dp_report_delta is not None
    assert policy.dp_clip_norm is not None
    assert policy.dp_rho_cap is not None
    assert policy.dp_max_noise_to_signal_ratio is not None
    assert policy.reconstruction_tolerance is not None
    assert policy.reconstruction_chance_rate is not None
    assert policy.adversary_model is not None

    request_digest = base.determinism.aggregate_input_digest
    ledger_id = (
        "calibration-zcdp-"
        + sha256(f"{parsed.estimator_id}|{policy.protected_unit}".encode("utf-8")).hexdigest()[:20]
    )
    scope = SyntheticPrivacyScope()
    ledger = ZCDPLedger(
        ledger_path,
        rho_cap=policy.dp_rho_cap,
        scope=scope,
        ledger_id=ledger_id,
        policy_label=policy.policy_label,
    )
    group_size = _max_group_size(parsed.matters)
    effective_rho = policy.dp_rho * group_size**2
    if ledger.consumed_rho + effective_rho > ledger.rho_cap:
        return _refused_dp_proof(base, ["privacy_budget_exhausted_before_sampling"])

    contributions = mean_sufficient_stat_contributions(parsed.matters)
    replay_seed = SyntheticReplaySeed(synthetic_replay_seed)
    mechanism = GaussianMechanism(
        clip_norm=policy.dp_clip_norm,
        rho=policy.dp_rho,
        replay_seed=replay_seed,
    )
    release_id = _dp_release_id(request_digest, replay_seed.seed_hash)
    contribution_vectors = [contribution.values for contribution in contributions]
    release = mechanism.release_sum(
        contribution_vectors,
        release_id=release_id,
        scope=scope,
    )
    rebuilt_release = mechanism.release_sum(
        contribution_vectors,
        release_id=release_id,
        scope=scope,
    )
    deterministic_rebuild = release == rebuilt_release

    signal_norm = l2_norm(release.clipped_values)
    noise_to_signal_ratio = release.noise_stddev / signal_norm if signal_norm else None
    utility_floor_ok = (
        noise_to_signal_ratio is not None
        and noise_to_signal_ratio <= policy.dp_max_noise_to_signal_ratio
    )
    utility = {
        "band_width": None,
        "sufficient_stat_noise_width": 2.0 * release.noise_stddev,
        "noise_standard_deviation": release.noise_stddev,
        "noise_to_signal_ratio": noise_to_signal_ratio,
        "max_noise_to_signal_ratio": policy.dp_max_noise_to_signal_ratio,
        "utility_floor_ok": utility_floor_ok,
        "calibrated_value_included": False,
    }
    if not utility_floor_ok:
        return _refused_dp_proof(
            base,
            ["noise_exceeds_signal_stay_synthetic"],
            utility=utility,
        )

    reconstruction_result = run_all_but_one_sum_reconstruction_smoke_check(
        matter_values={matter.matter_id: matter.contribution for matter in parsed.matters},
        released_sum=release.values[0],
        tolerance=policy.reconstruction_tolerance,
        chance_rate=policy.reconstruction_chance_rate,
        margin=policy.reconstruction_margin,
        adversary_model=policy.adversary_model,
    )
    reconstruction = CalibrationReconstructionRecord(
        adversary_model=reconstruction_result.adversary_model,
        target_metric="synthetic_all_but_one_sum_smoke_check",
        recovered_rate=reconstruction_result.recovered_rate,
        chance_rate=reconstruction_result.chance_rate,
        margin=reconstruction_result.margin,
        tolerance=reconstruction_result.tolerance,
        target_count=reconstruction_result.target_count,
        passed=reconstruction_result.passed,
        scaffold_only=False,
        evidence_basis="computed_synthetic_all_but_one_sum_smoke_check",
        computed_adversary_test_performed=True,
    )
    if not reconstruction.passed:
        return _refused_dp_proof(
            base,
            ["computed_reconstruction_test_failed"],
            utility=utility,
            reconstruction=reconstruction,
        )

    ledger_entry = ledger.append(
        release_id=release_id,
        rho=policy.dp_rho,
        group_size=group_size,
        created_at=generated_at,
    )
    ledger = ZCDPLedger(
        ledger_path,
        rho_cap=policy.dp_rho_cap,
        scope=scope,
        ledger_id=ledger_id,
        policy_label=policy.policy_label,
    )
    if not ledger.entries or ledger.entries[-1]["entry_hash"] != ledger_entry["entry_hash"]:
        raise ValueError("local zCDP ledger readback did not confirm the appended entry")
    cumulative_report = ledger.report(policy.dp_report_delta)
    group_report = zcdp_to_epsilon_delta(effective_rho, policy.dp_report_delta)
    dp_payload = {
        "mechanism": "gaussian_zcdp_homegrown",
        "accounting": "zCDP",
        "base_rho": policy.dp_rho,
        "effective_rho": effective_rho,
        "rho_cap": policy.dp_rho_cap,
        "cumulative_effective_rho_after": ledger.consumed_rho,
        "report_delta": policy.dp_report_delta,
        "epsilon_at_delta_after": cumulative_report.epsilon,
        "sensitivity": policy.dp_clip_norm,
        "clip_norm": policy.dp_clip_norm,
        "noise_standard_deviation": release.noise_stddev,
        "pre_clip_max_norm": release.pre_clip_max_norm,
        "clipped_matter_count": release.clipped_contribution_count,
        "group_size": group_size,
        "release_id": release_id,
        "seed_hash": release.seed_hash,
        "ledger_id": ledger.ledger_id,
        "ledger_policy_digest": ledger.policy_digest,
        "ledger_entry_hash": ledger_entry["entry_hash"],
        "clipped_sufficient_stats_digest": _vector_digest(release.clipped_values),
        "noised_sufficient_stats_digest": _vector_digest(release.values),
        "local_jsonl_fsync_readback_confirmed": True,
        "authoritative_ledger_receipt_verified": False,
        "parameters_are_synthetic_policy_placeholders": True,
        "seed_is_synthetic_replay_only": True,
        "secret_seed_authority_verified": False,
        "production_privacy_guarantee_claimed": False,
        "calibrated_value_included": False,
    }
    release_digest = calibration_release_digest(
        {"request_digest": request_digest, "dp": dp_payload}
    )
    dp_record = CalibrationDpRecord(**dp_payload, release_digest=release_digest)
    return CalibrationLeakageProof(
        proof_id=_proof_id_for_digest(release_digest),
        request_id=parsed.request_id,
        estimator_id=parsed.estimator_id,
        parameter=parsed.parameter,
        corpus_version_ref=parsed.corpus_version_ref,
        screen_version=parsed.screen_version,
        path="dp",
        status="candidate",
        refusal_reasons=[],
        methodology=base.methodology,
        kanon=base.kanon,
        lomo=base.lomo,
        dp=dp_record,
        reconstruction=reconstruction,
        utility=utility,
        determinism=CalibrationDeterminismRecord(
            aggregate_byte_identical=None,
            rebuilt=deterministic_rebuild,
            aggregate_input_digest=request_digest,
            dp_seed_hash=release.seed_hash,
        ),
        group_privacy=CalibrationGroupPrivacyRecord(
            unit=policy.protected_unit,
            max_group_size=group_size,
            effective_rho=effective_rho,
            effective_epsilon=group_report.epsilon,
            accounting_rule="zcdp_group_privacy_k_squared_rho",
        ),
        generated_at=generated_at or datetime.now(UTC).replace(microsecond=0).isoformat(),
    )


def _missing_dp_policy_fields(policy: CalibrationPreflightPolicy) -> list[str]:
    values = {
        "protected_unit": policy.protected_unit,
        "minimum_distinct_matters": policy.minimum_distinct_matters,
        "dominance_threshold": policy.dominance_threshold,
        "lomo_delta_limit": policy.lomo_delta_limit,
        "adversary_model": policy.adversary_model,
        "reconstruction_chance_rate": policy.reconstruction_chance_rate,
        "reconstruction_tolerance": policy.reconstruction_tolerance,
        "dp_rho": policy.dp_rho,
        "dp_report_delta": policy.dp_report_delta,
        "dp_clip_norm": policy.dp_clip_norm,
        "dp_rho_cap": policy.dp_rho_cap,
        "dp_max_noise_to_signal_ratio": policy.dp_max_noise_to_signal_ratio,
    }
    return [field for field, value in values.items() if value is None or value == ""]


def _refused_dp_proof(
    base: CalibrationLeakageProof,
    reasons: list[str],
    *,
    utility: dict[str, bool | float | None | str] | None = None,
    reconstruction: CalibrationReconstructionRecord | None = None,
) -> CalibrationLeakageProof:
    payload = base.model_dump(mode="json")
    payload.update(
        {
            "proof_id": _proof_id_for_digest(base.determinism.aggregate_input_digest),
            "path": "refused",
            "status": "refused",
            "refusal_reasons": list(dict.fromkeys(reasons)),
            "dp": None,
            "utility": utility or base.utility,
            "reconstruction": (
                reconstruction.model_dump(mode="json") if reconstruction else base.reconstruction
            ),
            "determinism": CalibrationDeterminismRecord(
                aggregate_byte_identical=True,
                rebuilt=True,
                aggregate_input_digest=base.determinism.aggregate_input_digest,
            ),
            "group_privacy": CalibrationGroupPrivacyRecord(
                unit=base.group_privacy.unit,
                max_group_size=base.group_privacy.max_group_size,
            ),
        }
    )
    return CalibrationLeakageProof.model_validate(payload)


def _dp_release_digest(request_digest: str, record: CalibrationDpRecord) -> str:
    return calibration_release_digest(
        {
            "request_digest": request_digest,
            "dp": record.model_dump(mode="json", exclude={"release_digest"}),
        }
    )


def _vector_digest(values: tuple[float, ...]) -> str:
    encoded = json.dumps(list(values), separators=(",", ":"), ensure_ascii=True)
    return f"sha256:{sha256(encoded.encode('utf-8')).hexdigest()}"


def _dp_release_id(request_digest: str, seed_hash: str) -> str:
    return (
        "calibrationdp_" + sha256(f"{request_digest}|{seed_hash}".encode("utf-8")).hexdigest()[:20]
    )


def _refusal_reasons(
    request: CalibrationPreflightRequest,
    *,
    distinct_matters: int,
    distinct_protected_units: int,
    top1_leverage: float,
    lomo_delta: float | None,
) -> list[str]:
    reasons: list[str] = []
    policy = request.policy
    if policy.protected_unit is None:
        reasons.append("missing_protected_unit")
    if policy.minimum_distinct_matters is None:
        reasons.append("missing_minimum_distinct_matters_K")
    if policy.dominance_threshold is None:
        reasons.append("missing_dominance_threshold")
    if policy.lomo_delta_limit is None:
        reasons.append("missing_lomo_delta_limit")
    if not policy.adversary_model:
        reasons.append("missing_adversary_model")
    if policy.reconstruction_recovered_rate is None or policy.reconstruction_chance_rate is None:
        reasons.append("missing_reconstruction_test_metrics")
    elif not _reconstruction_passed(policy):
        reasons.append("reconstruction_test_failed")
    if policy.dp_route_required:
        reasons.append("dp_route_required_candidate_run_not_supplied")

    if (
        policy.minimum_distinct_matters is not None
        and distinct_protected_units < policy.minimum_distinct_matters
    ):
        reasons.append("insufficient_distinct_protected_units_for_aggregate_only")
    if policy.dominance_threshold is not None and top1_leverage > policy.dominance_threshold:
        reasons.append("dominance_threshold_exceeded_dp_path_not_implemented")
    if (
        policy.lomo_delta_limit is not None
        and lomo_delta is not None
        and lomo_delta > policy.lomo_delta_limit
    ):
        reasons.append("lomo_delta_limit_exceeded_dp_path_not_implemented")
    return reasons


def _dominance_ok(
    policy: CalibrationPreflightPolicy,
    top1_leverage: float,
    lomo_delta: float | None,
) -> bool:
    if policy.dominance_threshold is None or policy.lomo_delta_limit is None or lomo_delta is None:
        return False
    return top1_leverage <= policy.dominance_threshold and lomo_delta <= policy.lomo_delta_limit


def _reconstruction_passed(policy: CalibrationPreflightPolicy) -> bool:
    if policy.reconstruction_recovered_rate is None or policy.reconstruction_chance_rate is None:
        return False
    return policy.reconstruction_recovered_rate <= (
        policy.reconstruction_chance_rate + policy.reconstruction_margin
    )


def _max_group_size(matters: list[CalibrationInputMatter]) -> int:
    counts: dict[str, int] = {}
    for matter in matters:
        counts[matter.protected_unit_id] = counts.get(matter.protected_unit_id, 0) + 1
    return max(counts.values(), default=0)


def _protected_unit_contributions(request: CalibrationPreflightRequest) -> dict[str, float]:
    grouped: dict[str, float] = {}
    for matter in request.matters:
        unit_id = (
            matter.matter_id
            if request.policy.protected_unit == "matter"
            else matter.protected_unit_id
        )
        grouped[unit_id] = grouped.get(unit_id, 0.0) + matter.contribution
    return grouped


def _matter_contributions(request: CalibrationPreflightRequest) -> dict[str, float]:
    grouped: dict[str, float] = {}
    for matter in request.matters:
        grouped[matter.matter_id] = grouped.get(matter.matter_id, 0.0) + matter.contribution
    return grouped


def _aggregate_digest(request: CalibrationPreflightRequest) -> str:
    matter_payloads = [matter.model_dump(mode="json") for matter in request.matters]
    payload = {
        "request_id": request.request_id,
        "estimator_id": request.estimator_id,
        "parameter": request.parameter,
        "corpus_version_ref": request.corpus_version_ref,
        "screen_version": request.screen_version,
        "runtime_scope": request.runtime_scope,
        "candidate_only": request.candidate_only,
        "publish_calibrated_value": request.publish_calibrated_value,
        "methodology": CalibrationMethodologyRecord().model_dump(mode="json"),
        "policy": request.policy.model_dump(mode="json"),
        "matters": sorted(
            matter_payloads,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        ),
        "matter_contributions": _matter_contributions(request),
        "protected_unit_contributions": _protected_unit_contributions(request),
    }
    encoded = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    return f"sha256:{sha256(encoded.encode('utf-8')).hexdigest()}"


def _proof_id_for_digest(aggregate_digest: str) -> str:
    return "calibrationleakageproof_" + sha256(aggregate_digest.encode("utf-8")).hexdigest()[:20]
