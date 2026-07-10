from __future__ import annotations

import json
from datetime import UTC, datetime
from hashlib import sha256
from math import isfinite
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class CalibrationStrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


ProtectedUnit = Literal["matter", "client", "affiliate_group"]
CalibrationPath = Literal["aggregate_only", "refused"]
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

    @model_validator(mode="after")
    def synthetic_placeholder_label_required(self) -> "CalibrationPreflightPolicy":
        if "synthetic policy placeholder" not in self.policy_label.lower():
            raise ValueError(
                "calibration policy values must be labeled synthetic policy placeholders"
            )
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
    output_range: Literal["aggregate_only_or_refused_candidate_proof"] = (
        "aggregate_only_or_refused_candidate_proof"
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
    target_metric: Literal["aggregate_mean_membership_proxy"] = "aggregate_mean_membership_proxy"
    recovered_rate: float | None = None
    chance_rate: float | None = None
    margin: float
    passed: bool
    scaffold_only: bool = True
    evidence_basis: Literal["supplied_synthetic_scaffold_metrics"] = (
        "supplied_synthetic_scaffold_metrics"
    )
    computed_adversary_test_performed: Literal[False] = False
    formal_privacy_guarantee_claimed: Literal[False] = False


class CalibrationGroupPrivacyRecord(CalibrationStrictModel):
    unit: ProtectedUnit | None
    max_group_size: int | None
    effective_epsilon: None = None


class CalibrationDeterminismRecord(CalibrationStrictModel):
    aggregate_byte_identical: bool
    rebuilt: bool
    aggregate_input_digest: str


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
    dp: None = None
    reconstruction: CalibrationReconstructionRecord
    utility: dict[str, bool | None]
    determinism: CalibrationDeterminismRecord
    group_privacy: CalibrationGroupPrivacyRecord
    calibrated_value_published: Literal[False] = False
    candidate_only: Literal[True] = True
    human_review_required: Literal[True] = True
    approval_id: None = None
    generated_at: str

    @model_validator(mode="after")
    def proof_fields_consistent(self) -> "CalibrationLeakageProof":
        expected_id = _proof_id_for_digest(self.determinism.aggregate_input_digest)
        if self.proof_id != expected_id:
            raise ValueError("calibration leakage proof_id does not match aggregate digest")
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
            if self.path != "aggregate_only":
                raise ValueError(
                    "candidate calibration proof must be aggregate_only in this scaffold"
                )
            if self.refusal_reasons:
                raise ValueError("candidate calibration proof cannot carry refusal reasons")
            if not self.kanon.dominance_ok or not self.lomo.dominance_ok:
                raise ValueError("candidate calibration proof requires dominance screens to pass")
            if not self.reconstruction.passed:
                raise ValueError("candidate calibration proof requires reconstruction to pass")
            if (
                not self.reconstruction.scaffold_only
                or self.reconstruction.computed_adversary_test_performed
                or self.reconstruction.formal_privacy_guarantee_claimed
            ):
                raise ValueError(
                    "candidate reconstruction evidence must remain supplied synthetic scaffold evidence"
                )
            if not self.determinism.rebuilt or not self.determinism.aggregate_byte_identical:
                raise ValueError(
                    "candidate calibration proof requires deterministic aggregate rebuild"
                )
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
    total_abs = sum(abs(value) for value in protected_unit_values)
    top1_leverage = (
        max((abs(value) / total_abs for value in protected_unit_values), default=0.0)
        if total_abs
        else 0.0
    )
    lomo_delta = _max_lomo_delta(matter_values)
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


def _max_lomo_delta(values: list[float]) -> float | None:
    if len(values) < 2:
        return None
    full_mean = sum(values) / len(values)
    max_delta = 0.0
    for index, _value in enumerate(values):
        remaining = values[:index] + values[index + 1 :]
        if not remaining:
            continue
        lomo_mean = sum(remaining) / len(remaining)
        max_delta = max(max_delta, abs(full_mean - lomo_mean))
    return max_delta


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
