from __future__ import annotations

from pathlib import Path
from typing import Any

from .budget_invariants import audit_budget_invariants
from .util import load_json, write_json


def _is_number(value: Any) -> bool:
    return isinstance(value, int | float) and not isinstance(value, bool)


def _amount(value: Any) -> float | None:
    return float(value) if _is_number(value) else None


def _close(left: float | None, right: float | None, tolerance: float = 0.01) -> bool:
    if left is None or right is None:
        return left is right
    return abs(left - right) <= tolerance


def _violation(
    code: str,
    message: str,
    path: str,
    expected: Any = None,
    actual: Any = None,
) -> dict[str, Any]:
    return {
        "code": code,
        "message": message,
        "path": path,
        "expected": expected,
        "actual": actual,
    }


def _check_range(
    violations: list[dict[str, Any]],
    payload: dict[str, Any],
    *,
    point: str,
    minimum: str,
    maximum: str,
    path: str,
) -> None:
    point_value = _amount(payload.get(point))
    min_value = _amount(payload.get(minimum))
    max_value = _amount(payload.get(maximum))
    if point_value is None or min_value is None or max_value is None:
        return
    if min_value - point_value > 0.01 or point_value - max_value > 0.01:
        violations.append(
            _violation(
                "range_point_outside_bounds",
                f"{point} must be between {minimum} and {maximum}",
                path,
                {"min": min_value, "max": max_value},
                point_value,
            )
        )


def _scenario_payloads(payload: dict[str, Any]) -> list[dict[str, Any]]:
    scenario_set = payload.get("scenario_set")
    if isinstance(scenario_set, dict):
        scenarios = scenario_set.get("scenarios") or []
        return [scenario for scenario in scenarios if isinstance(scenario, dict)]
    scenarios = payload.get("scenarios") or []
    return [scenario for scenario in scenarios if isinstance(scenario, dict)]


def _selected_scenario(payload: dict[str, Any]) -> dict[str, Any] | None:
    scenario_set = payload.get("scenario_set")
    selected_id = None
    if isinstance(scenario_set, dict):
        selected_id = scenario_set.get("selected_scenario_id")
    selected_id = selected_id or payload.get("scenario_name")
    for scenario in _scenario_payloads(payload):
        if scenario.get("scenario_id") == selected_id:
            return scenario
    return None


def check_budget_coherence(payload: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    lines = [line for line in payload.get("lines") or [] if isinstance(line, dict)]
    pricing_status = payload.get("pricing_status")
    if pricing_status == "priced":
        subtotal = round(sum(float(line.get("estimated_fees") or 0) for line in lines), 2)
        if not _close(subtotal, _amount(payload.get("subtotal_fees"))):
            violations.append(
                _violation(
                    "line_sum_mismatch",
                    "baseline subtotal_fees must equal sum of budget line fees",
                    "$.subtotal_fees",
                    subtotal,
                    payload.get("subtotal_fees"),
                )
            )
        expected_total = round(
            subtotal
            + float(payload.get("subtotal_expenses") or 0)
            + float(payload.get("contingency_amount") or 0),
            2,
        )
        if not _close(expected_total, _amount(payload.get("total_proposed_budget"))):
            violations.append(
                _violation(
                    "proposal_total_mismatch",
                    "baseline total must equal fees plus expenses plus contingency",
                    "$.total_proposed_budget",
                    expected_total,
                    payload.get("total_proposed_budget"),
                )
            )
    _check_range(
        violations,
        payload,
        point="headline_total_proposed_budget",
        minimum="headline_total_proposed_budget_min",
        maximum="headline_total_proposed_budget_max",
        path="$.headline_total_proposed_budget",
    )
    for index, scenario in enumerate(_scenario_payloads(payload)):
        scenario_path = f"$.scenario_set.scenarios[{index}]"
        _check_range(
            violations,
            scenario,
            point="total_proposed_budget",
            minimum="total_budget_min",
            maximum="total_budget_max",
            path=f"{scenario_path}.total_proposed_budget",
        )
    selected = _selected_scenario(payload)
    if selected is not None:
        headline_checks = {
            "headline_subtotal_fees": selected.get("subtotal_fees"),
            "headline_subtotal_expenses": selected.get("subtotal_expenses"),
            "headline_contingency_amount": selected.get("contingency_amount"),
            "headline_total_proposed_budget": selected.get("total_proposed_budget"),
            "headline_total_proposed_budget_min": selected.get("total_budget_min"),
            "headline_total_proposed_budget_max": selected.get("total_budget_max"),
        }
        for key, expected in headline_checks.items():
            if not _close(_amount(expected), _amount(payload.get(key))):
                violations.append(
                    _violation(
                        "headline_field_mismatch",
                        f"{key} must match the selected scenario",
                        f"$.{key}",
                        expected,
                        payload.get(key),
                    )
                )
    allowed_basis = {
        "template_default",
        "driver_adjusted",
        "human_confirmed",
        "benchmark_cell",
        "unknown",
    }
    for index, line in enumerate(lines):
        basis = line.get("estimate_basis")
        if basis not in allowed_basis:
            violations.append(
                _violation(
                    "invalid_estimate_basis",
                    "budget line estimate_basis must use an allowed candidate value",
                    f"$.lines[{index}].estimate_basis",
                    sorted(allowed_basis),
                    basis,
                )
            )
        if line.get("estimated_fees") is not None and not line.get("estimate_basis_refs"):
            violations.append(
                _violation(
                    "missing_estimate_basis_refs",
                    "priced budget lines must identify estimate basis refs",
                    f"$.lines[{index}].estimate_basis_refs",
                    "non-empty",
                    line.get("estimate_basis_refs"),
                )
            )
        if line.get("evidence_refs"):
            violations.append(
                _violation(
                    "budget_line_evidence_smearing",
                    "budget lines must keep estimate basis separate from source evidence",
                    f"$.lines[{index}].evidence_refs",
                    [],
                    line.get("evidence_refs"),
                )
            )
    banner = payload.get("display_banner") or {}
    if pricing_status != "insufficient_information" and (
        not banner.get("candidate_only") or not banner.get("not_authorized_for_client_submission")
    ):
        violations.append(
            _violation(
                "missing_display_boundary_banner",
                "display_banner must carry candidate-only and no-submission boundary fields",
                "$.display_banner",
                "candidate/no-submission banner",
                banner,
            )
        )
    return violations


def check_projection_coherence(payload: dict[str, Any]) -> list[dict[str, Any]]:
    violations: list[dict[str, Any]] = []
    total_delta = _amount(payload.get("total_delta"))
    buckets = [
        "task_hour_cap_delta",
        "rate_cap_delta",
        "expense_cap_delta",
        "disallowed_delta",
        "contingency_delta",
        "staffing_rule_delta",
    ]
    bucket_sum = round(sum(float(payload.get(bucket) or 0) for bucket in buckets), 2)
    if total_delta is not None and not _close(bucket_sum, total_delta):
        violations.append(
            _violation(
                "projection_delta_partition_mismatch",
                "carrier projection delta buckets must sum exactly to total_delta",
                "$.total_delta",
                bucket_sum,
                total_delta,
            )
        )
    expected_over_cap = round(
        float(payload.get("rate_cap_delta") or 0) + float(payload.get("expense_cap_delta") or 0),
        2,
    )
    if not _close(expected_over_cap, _amount(payload.get("over_cap_amount"))):
        violations.append(
            _violation(
                "legacy_over_cap_mismatch",
                "legacy over_cap_amount must be derived from rate and expense cap buckets",
                "$.over_cap_amount",
                expected_over_cap,
                payload.get("over_cap_amount"),
            )
        )
    if not _close(
        _amount(payload.get("disallowed_delta")),
        _amount(payload.get("disallowed_amount")),
    ):
        violations.append(
            _violation(
                "legacy_disallowed_mismatch",
                "legacy disallowed_amount must equal disallowed_delta",
                "$.disallowed_amount",
                payload.get("disallowed_delta"),
                payload.get("disallowed_amount"),
            )
        )
    proposed_total = _amount(payload.get("proposed_total"))
    compliant_total = _amount(payload.get("compliant_total"))
    total_delta_signed = _amount(payload.get("total_delta_signed"))
    if (
        proposed_total is not None
        and compliant_total is not None
        and total_delta_signed is not None
        and not _close(round(proposed_total - compliant_total, 2), total_delta_signed)
    ):
        violations.append(
            _violation(
                "projection_signed_delta_mismatch",
                "signed carrier projection delta must equal proposed_total minus compliant_total",
                "$.total_delta_signed",
                round(proposed_total - compliant_total, 2),
                payload.get("total_delta_signed"),
            )
        )
    unknown_rate = any(
        line.get("rate_unknown_for_reshaped_role") for line in payload.get("lines") or []
    )
    if unknown_rate and payload.get("projection_pricing_status") != "hours_only_partial":
        violations.append(
            _violation(
                "projection_pricing_status_mismatch",
                "missing reshaped-role rates must mark projection hours_only_partial",
                "$.projection_pricing_status",
                "hours_only_partial",
                payload.get("projection_pricing_status"),
            )
        )
    return violations


def validate_budget_artifacts(
    budget_proposal_path: str | Path,
    carrier_projection_path: str | Path | None = None,
    report_out: str | Path | None = None,
) -> dict[str, Any]:
    budget_payload = load_json(budget_proposal_path)
    violations = check_budget_coherence(budget_payload)
    violations.extend(audit_budget_invariants(budget_payload))
    if carrier_projection_path:
        violations.extend(check_projection_coherence(load_json(carrier_projection_path)))
    report = {
        "status": "passed" if not violations else "failed",
        "violation_count": len(violations),
        "violations": violations,
        "candidate_only": True,
        "not_authorized_for_client_submission": True,
    }
    if report_out:
        write_json(report_out, report)
    return report
