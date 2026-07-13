from pathlib import Path

import pytest

from lawfirm_os_intake.cli import main
from lawfirm_os_intake.models import (
    BudgetActualsSource,
    BudgetProposal,
    CarrierRejectionCaptureSourceBundle,
    CrossRepoContractProofReport,
    PilotReviewStoryReport,
    SourceBundle,
)
from lawfirm_os_intake.pilot_review_story import (
    PILOT_REVIEW_STORY_REPORT_FILENAME,
    _validate_inputs,
    run_pilot_review_story,
)
from lawfirm_os_intake.util import load_json


STORY = Path("examples/synthetic/pilot-review/epli-assignment-pilot-review-story.json")


def test_pilot_review_story_assembles_a_source_bound_l_and_e_dossier(tmp_path):
    report, out_dir = run_pilot_review_story(
        story_path=STORY,
        out_dir=tmp_path / "pilot",
        generated_at="2026-07-12T00:00:00Z",
    )

    persisted = PilotReviewStoryReport.model_validate(
        load_json(out_dir / PILOT_REVIEW_STORY_REPORT_FILENAME)
    )
    assert persisted == report
    assert report.status == "ready_for_human_review"
    assert report.source_count == 4
    assert len(report.source_hashes_by_id) == report.source_count
    assert report.matter_linking_state == "resolved_single_candidate_pending_human_confirmation"
    assert report.official_matter_number_status == "not_available"
    assert report.budget_proposal_total == 54090.0
    assert report.budget_display_state == "withheld_pending_matter_link_and_role_review"
    assert report.carrier_projection_state == "not_available_without_pinned_candidate_guideline"
    assert report.carrier_rejected_amount == 3900.0
    assert report.carrier_recovered_amount == 900.0
    assert report.carrier_write_down_amount == 1200.0
    assert (
        report.actuals_learning_state
        == "synthetic_actuals_variance_requires_human_review_no_learning"
    )
    assert report.actuals_source_id == "le-actuals-epli-carrier-clean.v0_1"
    assert report.actuals_total == 60350.0
    assert report.actuals_variance_amount == 6260.0
    assert report.actuals_variance_status == "variance_review_required"
    assert "human_actuals_variance_review" in report.required_next_gates
    assert "labor_employment_actual_variance_candidate" in report.candidate_exception_lake_labels
    assert (
        report.story_fixture_ref
        == "examples/synthetic/pilot-review/epli-assignment-pilot-review-story.json"
    )
    assert all("C:" not in stage.artifact_ref for stage in report.stages)
    assert (out_dir / "matter-linking" / "matter_linking_preflight_report.json").is_file()


def test_pilot_review_story_never_turns_candidate_evidence_into_an_action(tmp_path):
    report, _ = run_pilot_review_story(
        story_path=STORY,
        out_dir=tmp_path / "pilot",
        generated_at="2026-07-12T00:00:00Z",
    )

    assert report.human_review_required is True
    assert report.not_authorized_for_external_write is True
    assert report.not_authorized_for_lake_write is True
    assert report.not_authorized_for_sqlite_write is True
    assert report.not_authorized_for_budget_submission is True
    assert report.not_authorized_for_matter_opening is True
    assert report.not_authorized_for_conflict_clearance is True
    assert report.not_authorized_for_calibration is True
    assert report.lake_write_performed is False
    assert report.sqlite_write_performed is False
    assert report.external_writes_performed is False
    assert report.budget_submission_authorized is False
    assert report.matter_opening_authorized is False
    assert report.conflict_clearance_authorized is False
    assert report.silent_learning_performed is False
    actuals_stage = next(stage for stage in report.stages if stage.stage_id == "actuals_learning")
    assert actuals_stage.status == "ready_for_human_review"
    assert actuals_stage.required_next_gate == "human_actuals_variance_review"


def test_pilot_review_story_is_deterministic_and_keeps_generic_proof_out_of_case_evidence(tmp_path):
    first, _ = run_pilot_review_story(
        story_path=STORY,
        out_dir=tmp_path / "first",
        generated_at="2026-07-12T00:00:00Z",
    )
    second, _ = run_pilot_review_story(
        story_path=STORY,
        out_dir=tmp_path / "second",
        generated_at="2026-07-12T00:00:00Z",
    )

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert (
        first.cross_repo_contract_proof_scope
        == "generic_synthetic_boundary_proof_not_case_evidence"
    )
    owner_stage = next(stage for stage in first.stages if stage.stage_id == "owner_handoff")
    assert owner_stage.status == "passed"
    assert "generic synthetic proof" in owner_stage.summary.lower()


def test_pilot_review_story_refuses_duplicate_carrier_notices_before_totaling_amounts():
    story = load_json(STORY)
    source_bundle = SourceBundle.model_validate(load_json(story["source_bundle_ref"]))
    budget = BudgetProposal.model_validate(load_json(story["budget_proposal_ref"]))
    actuals_source = BudgetActualsSource.model_validate(load_json(story["actuals_source_ref"]))
    carrier_bundle = CarrierRejectionCaptureSourceBundle.model_validate(
        load_json(story["carrier_rejection_ref"])
    )
    duplicate_carrier_bundle = carrier_bundle.model_copy(
        update={"notices": [*carrier_bundle.notices, carrier_bundle.notices[0]]}
    )
    contract_proof = CrossRepoContractProofReport.model_validate(
        load_json(story["cross_repo_contract_proof_ref"])
    )

    with pytest.raises(ValueError, match="duplicate carrier rejection notices"):
        _validate_inputs(
            payload=story,
            source_bundle=source_bundle,
            budget=budget,
            actuals_source=actuals_source,
            carrier_bundle=duplicate_carrier_bundle,
            contract_proof=contract_proof,
        )


def test_pilot_review_story_cli_writes_only_to_requested_run_directory(tmp_path):
    out_dir = tmp_path / "pilot"
    code = main(
        [
            "build-pilot-review-story",
            "--story",
            str(STORY),
            "--out-dir",
            str(out_dir),
            "--generated-at",
            "2026-07-12T00:00:00Z",
        ]
    )

    assert code == 0
    report = load_json(out_dir / PILOT_REVIEW_STORY_REPORT_FILENAME)
    assert report["status"] == "ready_for_human_review"
    assert report["external_writes_performed"] is False
    assert report["lake_write_performed"] is False
    assert report["sqlite_write_performed"] is False
