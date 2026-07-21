"""Mutation checks for serialized synthetic workbench trust claims."""

from copy import deepcopy

import pytest

from lawfirm_os_intake.models import (
    SyntheticActualsWorkbenchReport,
    SyntheticBudgetConfigurationWorkbenchReport,
    SyntheticBudgetInputWorkbenchReport,
    SyntheticGuidelineProjectionWorkbenchReport,
    SyntheticRateCardWorkbenchReport,
    SyntheticRejectionAppealWorkbenchReport,
    _round_money,
)
from lawfirm_os_intake.util import load_json


FIXTURE_ROOT = "apps/legal-intake-budget/src/fixtures"
WORKBENCH_HASH_CASES = [
    (
        "rate_card",
        SyntheticRateCardWorkbenchReport,
        "demo-synthetic-rate-card-workbench-report.json",
    ),
    (
        "actuals",
        SyntheticActualsWorkbenchReport,
        "demo-synthetic-actuals-workbench-report.json",
    ),
    (
        "budget_input",
        SyntheticBudgetInputWorkbenchReport,
        "demo-synthetic-budget-input-workbench-report.json",
    ),
    (
        "guideline_projection",
        SyntheticGuidelineProjectionWorkbenchReport,
        "demo-synthetic-guideline-projection-workbench-report.json",
    ),
    (
        "rejection_appeal",
        SyntheticRejectionAppealWorkbenchReport,
        "demo-synthetic-rejection-appeal-workbench-report.json",
    ),
    (
        "configuration",
        SyntheticBudgetConfigurationWorkbenchReport,
        "demo-synthetic-budget-configuration-workbench-report.json",
    ),
]
INVALID_DIGESTS = [
    "sha256:not-a-hash",
    "sha256:" + "a" * 63,
    "sha256:" + "A" * 64,
    "sha1:" + "a" * 40,
]


def _fixture(repo_root, filename):
    return load_json(repo_root / FIXTURE_ROOT / filename)


def _sha256_paths(value, prefix=()):
    if isinstance(value, dict):
        for key, child in value.items():
            path = (*prefix, key)
            if key.endswith("_sha256"):
                yield path
            yield from _sha256_paths(child, path)
    elif isinstance(value, list):
        for index, child in enumerate(value):
            yield from _sha256_paths(child, (*prefix, index))


def _set_path(payload, path, value):
    target = payload
    for part in path[:-1]:
        target = target[part]
    target[path[-1]] = value


@pytest.mark.parametrize("invalid_digest", INVALID_DIGESTS)
@pytest.mark.parametrize(
    ("case_id", "model", "filename"),
    WORKBENCH_HASH_CASES,
    ids=[case[0] for case in WORKBENCH_HASH_CASES],
)
def test_workbench_models_reject_every_malformed_source_digest(
    repo_root, case_id, model, filename, invalid_digest
):
    source = _fixture(repo_root, filename)
    digest_paths = list(_sha256_paths(source))
    assert digest_paths, f"{case_id} fixture must expose source digests"

    for field_path in digest_paths:
        payload = deepcopy(source)
        _set_path(payload, field_path, invalid_digest)
        with pytest.raises(ValueError, match="hash|digest|provenance"):
            model.model_validate(payload)


def test_actuals_model_recomputes_displayed_rows_instead_of_trusting_headlines(repo_root):
    payload = deepcopy(_fixture(repo_root, "demo-synthetic-actuals-workbench-report.json"))
    payload["comparison"]["phase_comparisons"][0]["actual_total"] += 1

    with pytest.raises(ValueError, match="row components do not reconcile"):
        SyntheticActualsWorkbenchReport.model_validate(payload)


def test_guideline_model_recomputes_displayed_lines_instead_of_trusting_headlines(repo_root):
    payload = deepcopy(
        _fixture(repo_root, "demo-synthetic-guideline-projection-workbench-report.json")
    )
    payload["views"][0]["projection"]["lines"][0]["compliant_line_total"] += 1

    with pytest.raises(ValueError, match="compliant line total mismatch"):
        SyntheticGuidelineProjectionWorkbenchReport.model_validate(payload)


def test_actuals_model_recomputes_row_components_instead_of_trusting_row_total(repo_root):
    payload = deepcopy(_fixture(repo_root, "demo-synthetic-actuals-workbench-report.json"))
    payload["comparison"]["phase_comparisons"][0]["actual_fees"] += 1

    with pytest.raises(ValueError, match="row components do not reconcile"):
        SyntheticActualsWorkbenchReport.model_validate(payload)


def test_guideline_model_connects_projection_totals_to_reported_delta(repo_root):
    payload = deepcopy(
        _fixture(repo_root, "demo-synthetic-guideline-projection-workbench-report.json")
    )
    projection = payload["views"][0]["projection"]
    projection["lines"][0]["compliant_fees"] -= 1
    projection["lines"][0]["compliant_line_total"] -= 1
    projection["compliant_subtotal_fees"] -= 1
    projection["compliant_total"] -= 1

    with pytest.raises(ValueError, match="delta does not match totals"):
        SyntheticGuidelineProjectionWorkbenchReport.model_validate(payload)


def test_guideline_model_rejects_null_pricing_in_priced_projection(repo_root):
    payload = deepcopy(
        _fixture(repo_root, "demo-synthetic-guideline-projection-workbench-report.json")
    )
    projection = payload["views"][0]["projection"]
    projection["lines"][0]["proposed_fees"] = None
    projection["lines"][0]["proposed_line_total"] = None
    projection["proposed_subtotal_fees"] -= 4000
    projection["proposed_total"] -= 4000
    payload["proposal_total"] -= 4000
    payload["views"][0]["net_delta"] -= 4000
    payload["views"][0]["gross_increases"] += 4000

    with pytest.raises(ValueError, match="requires complete pricing"):
        SyntheticGuidelineProjectionWorkbenchReport.model_validate(payload)


@pytest.mark.parametrize(("value", "expected"), [(2.675, 2.68), (-2.675, -2.68)])
def test_workbench_money_rounding_is_explicit_half_up(value, expected):
    assert _round_money(value) == expected


def test_actuals_model_recomputes_headline_total_variance_amount(repo_root):
    payload = deepcopy(_fixture(repo_root, "demo-synthetic-actuals-workbench-report.json"))
    payload["comparison"]["total_variance_amount"] = 1.0

    with pytest.raises(ValueError, match="total variance does not reconcile"):
        SyntheticActualsWorkbenchReport.model_validate(payload)


def test_actuals_model_recomputes_headline_total_variance_percent(repo_root):
    payload = deepcopy(_fixture(repo_root, "demo-synthetic-actuals-workbench-report.json"))
    payload["comparison"]["total_variance_percent"] = 0.1

    with pytest.raises(ValueError, match="total variance does not reconcile"):
        SyntheticActualsWorkbenchReport.model_validate(payload)


def test_actuals_model_recomputes_displayed_row_variance(repo_root):
    payload = deepcopy(_fixture(repo_root, "demo-synthetic-actuals-workbench-report.json"))
    payload["comparison"]["phase_comparisons"][0]["variance_amount"] = 999999.0

    with pytest.raises(ValueError, match="row variance does not reconcile"):
        SyntheticActualsWorkbenchReport.model_validate(payload)


def test_budget_input_model_reconciles_report_total_to_lines(repo_root):
    payload = deepcopy(_fixture(repo_root, "demo-synthetic-budget-input-workbench-report.json"))
    payload["total_proposed_budget"] += 45909.0

    with pytest.raises(ValueError, match="totals do not reconcile"):
        SyntheticBudgetInputWorkbenchReport.model_validate(payload)


def test_budget_input_model_reconciles_subtotals_to_lines(repo_root):
    payload = deepcopy(_fixture(repo_root, "demo-synthetic-budget-input-workbench-report.json"))
    payload["subtotal_fees"] += 1.0

    with pytest.raises(ValueError, match="totals do not reconcile"):
        SyntheticBudgetInputWorkbenchReport.model_validate(payload)
