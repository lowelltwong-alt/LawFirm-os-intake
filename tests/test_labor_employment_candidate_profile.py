from pathlib import Path

import pytest

from lawfirm_os_intake.context import load_profile
from lawfirm_os_intake.models import ContextBoundaryReport
from lawfirm_os_intake.util import load_json
from lawfirm_os_intake.workflow import run_preflight
from lawfirm_os_intake.workers import _contains_lexical_term


L_E_PROFILE_REF = "context/synthetic-profiles/labor-employment-candidate.yaml"
INSURANCE_PROFILE_REF = "context/synthetic-profiles/insurance-defense.yaml"
FIXTURE_ROOT = "examples/synthetic/labor-employment/executable-fixtures"


def _evidence_signatures(candidate):
    return [
        (ref.source_id, ref.start_offset, ref.end_offset, ref.sha256)
        for ref in candidate.observed_evidence_refs
    ]


@pytest.mark.parametrize(
    ("fixture_name", "expected_label"),
    [
        ("le-discrimination-harassment-clean", "discrimination_harassment"),
        ("le-retaliation-wrongful-termination-messy-thread", "retaliation_wrongful_termination"),
        ("le-wage-hour-clean", "wage_hour_flsa_state"),
        ("le-class-collective-clean", "class_collective_paga_representative"),
        ("le-ada-fmla-clean", "ada_fmla_accommodation_leave"),
        ("le-restrictive-covenant-messy-thread", "restrictive_covenant_trade_secret"),
        ("le-epli-carrier-clean", "epli_carrier_assignment"),
        ("le-admin-exhaustion-clean", "administrative_exhaustion_agency_record"),
    ],
)
def test_labor_employment_candidate_context_changes_ranking_not_evidence(
    repo_root, tmp_path, fixture_name, expected_label
):
    bundle_path = repo_root / FIXTURE_ROOT / f"{fixture_name}.source-bundle.json"
    candidate_packet, candidate_dir = run_preflight(
        bundle_path,
        repo_root / L_E_PROFILE_REF,
        tmp_path / "candidate",
    )
    insurance_packet, _ = run_preflight(
        bundle_path,
        repo_root / INSURANCE_PROFILE_REF,
        tmp_path / "insurance",
    )

    assert [segment.sha256 for segment in candidate_packet.segments] == [
        segment.sha256 for segment in insurance_packet.segments
    ]
    assert [item.model_dump(mode="json") for item in candidate_packet.source_inventory] == [
        item.model_dump(mode="json") for item in insurance_packet.source_inventory
    ]

    candidate_by_label = {item.label: item for item in candidate_packet.matter_family_candidates}
    insurance_by_label = {item.label: item for item in insurance_packet.matter_family_candidates}
    assert candidate_by_label.keys() == insurance_by_label.keys()
    for label in candidate_by_label:
        candidate_item = candidate_by_label[label]
        insurance_item = insurance_by_label[label]
        assert _evidence_signatures(candidate_item) == _evidence_signatures(insurance_item)
        assert candidate_item.source_evidence_status == insurance_item.source_evidence_status
        assert candidate_item.support_summary == insurance_item.support_summary

    candidate = candidate_by_label[expected_label]
    insurance = insurance_by_label[expected_label]
    assert candidate.confidence > insurance.confidence
    assert (
        candidate.source_evidence_status == insurance.source_evidence_status == "observed_support"
    )
    assert candidate.calibration_label == insurance.calibration_label == "observed"
    assert candidate.context_signal_refs == [
        "practice-profile://synthetic-labor-employment-candidate.v0_1/"
        f"matter_family_priors/{expected_label}"
    ]
    assert insurance.context_signal_refs == []

    unknown = candidate_by_label["unknown"]
    assert unknown.source_evidence_status == "unknown_option"
    assert candidate_packet.status == "human_intake_review_required"
    assert candidate_packet.human_confirmation_required is True
    assert candidate_packet.escalation.required is True

    context_report = ContextBoundaryReport.model_validate(
        load_json(candidate_dir / "context_boundary_report.json")
    )
    assert context_report.status == "passed"
    assert context_report.practice_context_is_observed_evidence is False
    assert context_report.human_confirmation_required is True


@pytest.mark.parametrize(
    ("text", "term", "expected"),
    [
        ("The notice says right-to-sue, then lists a date.", "right-to-sue", True),
        ("ADA. review remains pending.", "ada", True),
        ("The wage/hour; packet is synthetic.", "wage/hour", True),
        ("Metadata from the Canada office.", "ada", False),
        ("A paginated appendix.", "paga", False),
    ],
)
def test_lexical_term_boundaries_preserve_punctuation(text, term, expected):
    assert _contains_lexical_term(text, term) is expected


def test_right_to_sue_collision_stays_two_observed_candidates(repo_root, tmp_path):
    packet, _ = run_preflight(
        repo_root / FIXTURE_ROOT / "le-admin-exhaustion-clean.source-bundle.json",
        repo_root / L_E_PROFILE_REF,
        tmp_path,
    )
    by_label = {item.label: item for item in packet.matter_family_candidates}

    discrimination = by_label["discrimination_harassment"]
    exhaustion = by_label["administrative_exhaustion_agency_record"]
    assert discrimination.source_evidence_status == "observed_support"
    assert exhaustion.source_evidence_status == "observed_support"
    assert "right-to-sue" in discrimination.support_summary
    assert "right-to-sue" in exhaustion.support_summary
    assert discrimination.candidate_id != exhaustion.candidate_id
    assert by_label["unknown"].source_evidence_status == "unknown_option"
    assert packet.human_confirmation_required is True


def test_short_ada_token_does_not_match_inside_other_words(repo_root, tmp_path):
    packet, _ = run_preflight(
        repo_root / FIXTURE_ROOT / "le-ada-token-boundary-adversarial.source-bundle.json",
        repo_root / L_E_PROFILE_REF,
        tmp_path,
    )
    by_label = {item.label: item for item in packet.matter_family_candidates}
    candidate = by_label["ada_fmla_accommodation_leave"]

    assert candidate.source_evidence_status == "source_anchor_only"
    assert candidate.calibration_label == "context_influenced"
    assert candidate.support_summary == (
        "No direct lexical signal; retained for comparison/context prior."
    )
    assert candidate.context_signal_refs == [
        "practice-profile://synthetic-labor-employment-candidate.v0_1/"
        "matter_family_priors/ada_fmla_accommodation_leave"
    ]
    assert by_label["unknown"].source_evidence_status == "unknown_option"
    assert packet.human_confirmation_required is True


def test_labor_employment_candidate_profile_has_no_pricing_or_budget_authority(repo_root):
    profile_path = repo_root / L_E_PROFILE_REF
    profile = load_profile(profile_path)
    manifest = load_json(
        repo_root / "examples/synthetic/labor-employment/"
        "labor-employment-executable-fixtures-manifest.json"
    )

    assert manifest["candidate_only"] is True
    assert manifest["not_promoted_canon"] is True
    assert profile["candidate_only"] is True
    assert profile["not_promoted_canon"] is True
    assert profile["contains_real_firm_data"] is False
    assert profile["default_side"] == "varies"
    assert profile["budget_template_ids"] == []
    assert "synthetic_hourly_rates" not in profile
    assert "budget_templates" not in profile
    assert "rate_card_ref" not in profile
    assert "carrier_guideline_ref" not in profile
    assert set(profile["matter_family_priors"]) == {
        "discrimination_harassment",
        "retaliation_wrongful_termination",
        "wage_hour_flsa_state",
        "class_collective_paga_representative",
        "ada_fmla_accommodation_leave",
        "restrictive_covenant_trade_secret",
        "epli_carrier_assignment",
        "administrative_exhaustion_agency_record",
    }
    assert Path(profile_path).is_file()
