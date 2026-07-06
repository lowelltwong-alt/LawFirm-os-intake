from __future__ import annotations

from typing import Any


CHECKED_INVARIANTS = ["I1", "I2", "I4", "I5", "I6", "I8", "I10", "I13", "I15"]
INVARIANT_SET_VERSION = "fable-bk2-2026-07-06"


def _payload(value: Any) -> dict[str, Any]:
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json")
    if isinstance(value, dict):
        return value
    raise TypeError("budget invariant audit requires a BudgetProposal or dict payload")


def _amount(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    return None


def _close(left: float | None, right: float | None, tolerance: float = 0.01) -> bool:
    if left is None or right is None:
        return left is right
    return abs(left - right) <= tolerance


def _violation(
    invariant_id: str,
    code: str,
    message: str,
    path: str,
    *,
    expected: Any = None,
    actual: Any = None,
) -> dict[str, Any]:
    return {
        "invariant_id": invariant_id,
        "code": code,
        "message": message,
        "path": path,
        "expected": expected,
        "actual": actual,
        "severity": "error",
    }


def _line_path(index: int, field: str) -> str:
    return f"$.lines[{index}].{field}"


def _check_amount_nonnegative(
    violations: list[dict[str, Any]],
    invariant_id: str,
    value: Any,
    path: str,
) -> None:
    amount = _amount(value)
    if amount is not None and amount < 0:
        violations.append(
            _violation(
                invariant_id,
                "negative_amount",
                "budget arithmetic fields must be non-negative",
                path,
                expected=">= 0",
                actual=value,
            )
        )


def _check_range(
    violations: list[dict[str, Any]],
    line: dict[str, Any],
    *,
    point_field: str,
    min_field: str,
    max_field: str,
    path_prefix: str,
) -> None:
    point = _amount(line.get(point_field))
    minimum = _amount(line.get(min_field))
    maximum = _amount(line.get(max_field))
    for field, value in (
        (point_field, point),
        (min_field, minimum),
        (max_field, maximum),
    ):
        _check_amount_nonnegative(violations, "I2", value, f"{path_prefix}.{field}")
    if point is None or minimum is None or maximum is None:
        return
    if minimum - point > 0.01 or point - maximum > 0.01:
        violations.append(
            _violation(
                "I2",
                "line_range_out_of_order",
                f"{min_field} must be <= {point_field} <= {max_field}",
                f"{path_prefix}.{point_field}",
                expected={"min": minimum, "point": point, "max": maximum},
                actual=point,
            )
        )


def _priced_lines(lines: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        line
        for line in lines
        if _amount(line.get("hourly_rate")) is not None
        and _amount(line.get("estimated_fees")) is not None
    ]


def _line_fee_min(line: dict[str, Any]) -> float:
    hours = _amount(line.get("estimated_hours_min"))
    if hours is None:
        hours = _amount(line.get("estimated_hours")) or 0.0
    return round(hours * (_amount(line.get("hourly_rate")) or 0.0), 2)


def _line_fee_max(line: dict[str, Any]) -> float:
    hours = _amount(line.get("estimated_hours_max"))
    if hours is None:
        hours = _amount(line.get("estimated_hours")) or 0.0
    return round(hours * (_amount(line.get("hourly_rate")) or 0.0), 2)


def _line_expense_min(line: dict[str, Any]) -> float:
    amount = _amount(line.get("estimated_expenses_min"))
    if amount is None:
        amount = _amount(line.get("estimated_expenses")) or 0.0
    return amount


def _line_expense_max(line: dict[str, Any]) -> float:
    amount = _amount(line.get("estimated_expenses_max"))
    if amount is None:
        amount = _amount(line.get("estimated_expenses")) or 0.0
    return amount


def _scenario_payloads(payload: dict[str, Any]) -> list[dict[str, Any]]:
    scenario_set = payload.get("scenario_set")
    if not isinstance(scenario_set, dict):
        return []
    scenarios = scenario_set.get("scenarios") or []
    return [scenario for scenario in scenarios if isinstance(scenario, dict)]


def _scenario_for_id(payload: dict[str, Any], scenario_id: str | None) -> dict[str, Any] | None:
    if not scenario_id:
        return None
    for scenario in _scenario_payloads(payload):
        if scenario.get("scenario_id") == scenario_id:
            return scenario
    return None


def _scenario_phase_set(scenario: dict[str, Any]) -> list[str]:
    raw = scenario.get("included_phase_ids") or []
    return [str(item) for item in raw if item is not None]


def _scenario_order_key(scenario: dict[str, Any]) -> tuple[int, str]:
    return (len(_scenario_phase_set(scenario)), str(scenario.get("scenario_id") or ""))


def _check_total_additivity(
    violations: list[dict[str, Any]],
    *,
    invariant_id: str,
    path_prefix: str,
    subtotal_fees: Any,
    subtotal_expenses: Any,
    contingency_amount: Any,
    total: Any,
) -> None:
    fees = _amount(subtotal_fees)
    expenses = _amount(subtotal_expenses)
    contingency = _amount(contingency_amount)
    proposed_total = _amount(total)
    if fees is None or expenses is None or contingency is None or proposed_total is None:
        return
    expected = round(fees + expenses + contingency, 2)
    if not _close(expected, proposed_total):
        violations.append(
            _violation(
                invariant_id,
                "total_additivity_mismatch",
                "budget total must equal fees plus expenses plus contingency",
                f"{path_prefix}.total",
                expected=expected,
                actual=total,
            )
        )


def _check_contingency(
    violations: list[dict[str, Any]],
    *,
    path_prefix: str,
    subtotal_fees: Any,
    contingency_percent: Any,
    contingency_amount: Any,
    field_name: str,
) -> None:
    fees = _amount(subtotal_fees)
    percent = _amount(contingency_percent)
    amount = _amount(contingency_amount)
    if fees is None or percent is None or amount is None:
        return
    expected = round(fees * percent / 100, 2)
    if not _close(expected, amount):
        violations.append(
            _violation(
                "I13",
                "contingency_mismatch",
                "contingency must be calculated only from subtotal fees",
                f"{path_prefix}.{field_name}",
                expected=expected,
                actual=contingency_amount,
            )
        )


def audit_budget_invariants(proposal: Any) -> list[dict[str, Any]]:
    payload = _payload(proposal)
    violations: list[dict[str, Any]] = []
    lines = [line for line in payload.get("lines") or [] if isinstance(line, dict)]

    for index, line in enumerate(lines):
        hours = _amount(line.get("estimated_hours"))
        rate = _amount(line.get("hourly_rate"))
        fees = _amount(line.get("estimated_fees"))
        if rate is not None and hours is not None:
            expected_fees = round(hours * rate, 2)
            if not _close(expected_fees, fees):
                violations.append(
                    _violation(
                        "I1",
                        "line_fee_mismatch",
                        "estimated_fees must equal estimated_hours times hourly_rate",
                        _line_path(index, "estimated_fees"),
                        expected=expected_fees,
                        actual=line.get("estimated_fees"),
                    )
                )
        _check_range(
            violations,
            line,
            point_field="estimated_hours",
            min_field="estimated_hours_min",
            max_field="estimated_hours_max",
            path_prefix=f"$.lines[{index}]",
        )
        _check_range(
            violations,
            line,
            point_field="estimated_expenses",
            min_field="estimated_expenses_min",
            max_field="estimated_expenses_max",
            path_prefix=f"$.lines[{index}]",
        )

    line_fee_sum = round(sum(_amount(line.get("estimated_fees")) or 0.0 for line in lines), 2)
    line_expense_sum = round(
        sum(_amount(line.get("estimated_expenses")) or 0.0 for line in lines), 2
    )
    pricing_status = payload.get("pricing_status")
    if pricing_status == "priced" and not _close(
        line_fee_sum, _amount(payload.get("subtotal_fees"))
    ):
        violations.append(
            _violation(
                "I4",
                "subtotal_fee_mismatch",
                "subtotal_fees must equal the sum of priced budget line fees",
                "$.subtotal_fees",
                expected=line_fee_sum,
                actual=payload.get("subtotal_fees"),
            )
        )
    if not _close(line_expense_sum, _amount(payload.get("subtotal_expenses"))):
        violations.append(
            _violation(
                "I4",
                "subtotal_expense_mismatch",
                "subtotal_expenses must equal the sum of budget line expenses",
                "$.subtotal_expenses",
                expected=line_expense_sum,
                actual=payload.get("subtotal_expenses"),
            )
        )
    _check_total_additivity(
        violations,
        invariant_id="I4",
        path_prefix="$",
        subtotal_fees=payload.get("subtotal_fees"),
        subtotal_expenses=payload.get("subtotal_expenses"),
        contingency_amount=payload.get("contingency_amount"),
        total=payload.get("total_proposed_budget"),
    )
    _check_contingency(
        violations,
        path_prefix="$",
        subtotal_fees=payload.get("subtotal_fees"),
        contingency_percent=payload.get("contingency_percent"),
        contingency_amount=payload.get("contingency_amount"),
        field_name="contingency_amount",
    )

    selected_scenario_id = payload.get("scenario_name")
    selected_scenario = _scenario_for_id(payload, selected_scenario_id)
    if selected_scenario is not None and len(_priced_lines(lines)) == len(lines):
        expected_fee_min = round(sum(_line_fee_min(line) for line in lines), 2)
        expected_fee_max = round(sum(_line_fee_max(line) for line in lines), 2)
        expected_expense_min = round(sum(_line_expense_min(line) for line in lines), 2)
        expected_expense_max = round(sum(_line_expense_max(line) for line in lines), 2)
        if not _close(expected_fee_min, _amount(selected_scenario.get("subtotal_fees_min"))):
            violations.append(
                _violation(
                    "I5",
                    "scenario_fee_min_mismatch",
                    "selected scenario fee minimum must honor explicit line zeroes",
                    "$.scenario_set.scenarios.selected.subtotal_fees_min",
                    expected=expected_fee_min,
                    actual=selected_scenario.get("subtotal_fees_min"),
                )
            )
        if not _close(expected_fee_max, _amount(selected_scenario.get("subtotal_fees_max"))):
            violations.append(
                _violation(
                    "I5",
                    "scenario_fee_max_mismatch",
                    "selected scenario fee maximum must match line maximum math",
                    "$.scenario_set.scenarios.selected.subtotal_fees_max",
                    expected=expected_fee_max,
                    actual=selected_scenario.get("subtotal_fees_max"),
                )
            )
        if not _close(
            expected_expense_min,
            _amount(selected_scenario.get("subtotal_expenses_min")),
        ):
            violations.append(
                _violation(
                    "I5",
                    "scenario_expense_min_mismatch",
                    "selected scenario expense minimum must honor explicit line zeroes",
                    "$.scenario_set.scenarios.selected.subtotal_expenses_min",
                    expected=expected_expense_min,
                    actual=selected_scenario.get("subtotal_expenses_min"),
                )
            )
        if not _close(
            expected_expense_max,
            _amount(selected_scenario.get("subtotal_expenses_max")),
        ):
            violations.append(
                _violation(
                    "I5",
                    "scenario_expense_max_mismatch",
                    "selected scenario expense maximum must match line maximum math",
                    "$.scenario_set.scenarios.selected.subtotal_expenses_max",
                    expected=expected_expense_max,
                    actual=selected_scenario.get("subtotal_expenses_max"),
                )
            )

    scenarios = _scenario_payloads(payload)
    for scenario_index, scenario in enumerate(scenarios):
        scenario_path = f"$.scenario_set.scenarios[{scenario_index}]"
        included_phase_ids = _scenario_phase_set(scenario)
        resolution_phase = scenario.get("resolution_phase")
        if not included_phase_ids:
            violations.append(
                _violation(
                    "I6",
                    "scenario_without_included_phases",
                    "budget scenario must declare the included phase prefix",
                    f"{scenario_path}.included_phase_ids",
                    expected="non-empty phase prefix",
                    actual=scenario.get("included_phase_ids"),
                )
            )
        elif resolution_phase not in included_phase_ids:
            violations.append(
                _violation(
                    "I6",
                    "scenario_resolution_phase_not_included",
                    "scenario resolution_phase must be included in its phase prefix",
                    f"{scenario_path}.resolution_phase",
                    expected=included_phase_ids,
                    actual=resolution_phase,
                )
            )
        elif included_phase_ids[-1] != resolution_phase:
            violations.append(
                _violation(
                    "I6",
                    "scenario_resolution_phase_not_prefix_cutoff",
                    "scenario included phases must end at resolution_phase",
                    f"{scenario_path}.included_phase_ids",
                    expected=f"last phase == {resolution_phase}",
                    actual=included_phase_ids,
                )
            )
        if len(included_phase_ids) != len(set(included_phase_ids)):
            violations.append(
                _violation(
                    "I6",
                    "scenario_duplicate_included_phase",
                    "scenario included phase prefix must not contain duplicates",
                    f"{scenario_path}.included_phase_ids",
                    expected="unique phases",
                    actual=included_phase_ids,
                )
            )
        _check_total_additivity(
            violations,
            invariant_id="I5",
            path_prefix=scenario_path,
            subtotal_fees=scenario.get("subtotal_fees_min"),
            subtotal_expenses=scenario.get("subtotal_expenses_min"),
            contingency_amount=scenario.get("contingency_amount_min"),
            total=scenario.get("total_budget_min"),
        )
        _check_total_additivity(
            violations,
            invariant_id="I5",
            path_prefix=scenario_path,
            subtotal_fees=scenario.get("subtotal_fees_max"),
            subtotal_expenses=scenario.get("subtotal_expenses_max"),
            contingency_amount=scenario.get("contingency_amount_max"),
            total=scenario.get("total_budget_max"),
        )
        _check_contingency(
            violations,
            path_prefix=scenario_path,
            subtotal_fees=scenario.get("subtotal_fees"),
            contingency_percent=scenario.get("contingency_percent"),
            contingency_amount=scenario.get("contingency_amount"),
            field_name="contingency_amount",
        )
        _check_contingency(
            violations,
            path_prefix=scenario_path,
            subtotal_fees=scenario.get("subtotal_fees_min"),
            contingency_percent=scenario.get("contingency_percent"),
            contingency_amount=scenario.get("contingency_amount_min"),
            field_name="contingency_amount_min",
        )
        _check_contingency(
            violations,
            path_prefix=scenario_path,
            subtotal_fees=scenario.get("subtotal_fees_max"),
            contingency_percent=scenario.get("contingency_percent"),
            contingency_amount=scenario.get("contingency_amount_max"),
            field_name="contingency_amount_max",
        )

    phase_ordered_scenarios = sorted(scenarios, key=_scenario_order_key)
    for previous, current in zip(
        phase_ordered_scenarios,
        phase_ordered_scenarios[1:],
        strict=False,
    ):
        previous_phases = _scenario_phase_set(previous)
        current_phases = _scenario_phase_set(current)
        if previous_phases != current_phases[: len(previous_phases)]:
            violations.append(
                _violation(
                    "I6",
                    "scenario_phase_prefix_not_nested",
                    "later budget scenarios must include all phases from earlier scenarios",
                    "$.scenario_set.scenarios",
                    expected=previous_phases,
                    actual=current_phases,
                )
            )

    scenario_set = payload.get("scenario_set")
    if isinstance(scenario_set, dict) and scenarios:
        if scenario_set.get("monotonic_total_order") is not True:
            violations.append(
                _violation(
                    "I8",
                    "scenario_monotonic_order_not_verified",
                    "budget scenarios must be monotonic when sorted by phase cutoff",
                    "$.scenario_set.monotonic_total_order",
                    expected=True,
                    actual=scenario_set.get("monotonic_total_order"),
                )
            )
        order_basis = scenario_set.get("total_order_basis")
        if order_basis == "total_hours":
            ordered_values = [
                _amount(scenario.get("total_hours")) for scenario in phase_ordered_scenarios
            ]
        else:
            ordered_values = [
                _amount(scenario.get("total_proposed_budget"))
                for scenario in phase_ordered_scenarios
            ]
        comparable_values = [value for value in ordered_values if value is not None]
        if len(comparable_values) == len(ordered_values) and any(
            comparable_values[index] > comparable_values[index + 1] + 0.01
            for index in range(len(comparable_values) - 1)
        ):
            violations.append(
                _violation(
                    "I8",
                    "scenario_monotonic_value_mismatch",
                    "budget scenario values must be non-decreasing by phase cutoff",
                    "$.scenario_set.scenarios",
                    expected="non-decreasing phase-ordered values",
                    actual=comparable_values,
                )
            )

        probabilities = [scenario.get("probability") for scenario in scenarios]
        all_probabilities_present = all(_amount(value) is not None for value in probabilities)
        any_probability_present = any(_amount(value) is not None for value in probabilities)
        all_priced = all(
            _amount(scenario.get("total_proposed_budget")) is not None for scenario in scenarios
        )
        expected_total = _amount(scenario_set.get("expected_total"))
        if all_probabilities_present:
            probability_sum = round(
                sum(_amount(value) or 0.0 for value in probabilities),
                6,
            )
            probability_sum_close = abs(probability_sum - 1.0) <= 0.000001
            if probability_sum_close and all_priced:
                if expected_total is None:
                    violations.append(
                        _violation(
                            "I10",
                            "scenario_expected_value_missing",
                            "expected_total must be present when probabilities sum to 1 and all scenarios are priced",
                            "$.scenario_set.expected_total",
                            expected="weighted scenario total",
                            actual=None,
                        )
                    )
                else:
                    priced_totals = [
                        _amount(scenario.get("total_proposed_budget")) or 0.0
                        for scenario in scenarios
                    ]
                    if (
                        expected_total < min(priced_totals) - 0.01
                        or expected_total > max(priced_totals) + 0.01
                    ):
                        violations.append(
                            _violation(
                                "I10",
                                "scenario_expected_value_out_of_bounds",
                                "expected_total must fall within scenario point totals",
                                "$.scenario_set.expected_total",
                                expected={"min": min(priced_totals), "max": max(priced_totals)},
                                actual=expected_total,
                            )
                        )
            elif expected_total is not None:
                violations.append(
                    _violation(
                        "I10",
                        "scenario_expected_value_not_allowed",
                        "expected_total must be absent unless probabilities sum to 1 and all scenarios are priced",
                        "$.scenario_set.expected_total",
                        expected=None,
                        actual=expected_total,
                    )
                )
            if not probability_sum_close:
                issue_codes = set(scenario_set.get("policy_issue_codes") or [])
                if "scenario_probability_sum_not_one" not in issue_codes:
                    violations.append(
                        _violation(
                            "I10",
                            "scenario_probability_sum_unflagged",
                            "scenario probability sums other than 1 require a human-review policy issue",
                            "$.scenario_set.policy_issue_codes",
                            expected="scenario_probability_sum_not_one",
                            actual=sorted(issue_codes),
                        )
                    )
        elif any_probability_present and expected_total is not None:
            violations.append(
                _violation(
                    "I10",
                    "scenario_partial_probability_expected_value",
                    "partial scenario probabilities cannot produce expected_total",
                    "$.scenario_set.expected_total",
                    expected=None,
                    actual=expected_total,
                )
            )

    projection = payload.get("carrier_compliant_projection")
    if isinstance(projection, dict):
        basis = projection.get("basis") or {}
        if basis.get("contingency_allowed") is False and not _close(
            0.0,
            _amount(projection.get("compliant_contingency_amount")),
        ):
            violations.append(
                _violation(
                    "I13",
                    "compliant_contingency_disallowed_mismatch",
                    "compliant contingency must be zero when the carrier projection disallows it",
                    "$.carrier_compliant_projection.compliant_contingency_amount",
                    expected=0,
                    actual=projection.get("compliant_contingency_amount"),
                )
            )

    if pricing_status == "hours_only":
        for field in ("subtotal_fees", "total_proposed_budget", "contingency_amount"):
            if payload.get(field) is not None:
                violations.append(
                    _violation(
                        "I15",
                        "hours_only_priced_field_present",
                        "hours-only budgets must not expose fee, contingency, or total amounts",
                        f"$.{field}",
                        expected=None,
                        actual=payload.get(field),
                    )
                )

    return violations


def build_budget_invariant_report(
    proposal: Any,
    *,
    budget_proposal_ref: str | None = None,
) -> dict[str, Any]:
    violations = audit_budget_invariants(proposal)
    return {
        "schema_version": "0.1",
        "report_type": "budget_invariant_report",
        "invariant_set_version": INVARIANT_SET_VERSION,
        "checked_invariants": CHECKED_INVARIANTS,
        "status": "passed" if not violations else "failed",
        "violation_count": len(violations),
        "violations": violations,
        "budget_proposal_ref": budget_proposal_ref,
        "candidate_only": True,
        "not_authorized_for_client_submission": True,
        "external_writes_performed": False,
        "non_authoritative": True,
    }


def enforce_budget_invariant_report(report: dict[str, Any]) -> None:
    if report.get("status") != "passed":
        raise ValueError("budget invariant report failed")
