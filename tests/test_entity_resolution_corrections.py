from lawfirm_os_intake.cli import main
from lawfirm_os_intake.entity_resolution_corrections import (
    REPORT_FILENAME,
    build_entity_resolution_correction_report,
)
from lawfirm_os_intake.matter_link_keys import compare_entity_names, load_matter_link_policy
from lawfirm_os_intake.models import EntityResolutionCorrectionRecord, EvidenceRef, SourceBundle
from lawfirm_os_intake.util import digest_text, load_json, write_json


FIXED_TIME = "2026-07-10T00:00:00Z"


def _bundle(repo_root):
    return SourceBundle.model_validate(
        load_json(
            repo_root
            / "examples/synthetic/matter-linking/entity-resolution-correction.source-bundle.json"
        )
    )


def _ref(bundle, value):
    source = bundle.sources[0]
    start = source.text.index(value)
    end = start + len(value)
    return EvidenceRef(
        source_id=source.source_id,
        segment_id=f"{source.source_id}:source_text",
        start_offset=start,
        end_offset=end,
        sha256=digest_text(value),
    )


def _record(repo_root, bundle, *, outcome="confirm_alias_table_candidate", bad_hash=False):
    policy = load_matter_link_policy(repo_root / "config/matter-link-policy.yaml")
    left, right = "Sierra Staffing LLC", "Sierra Staffing Inc"
    left_ref, right_ref = _ref(bundle, left), _ref(bundle, right)
    if bad_hash:
        left_ref = left_ref.model_copy(update={"sha256": "sha256:not-the-source"})
    decision = {
        "correction_id": "entity-correction-001",
        "comparison": compare_entity_names(left, right, policy).model_dump(mode="json"),
        "left_evidence_refs": [left_ref.model_dump(mode="json")],
        "right_evidence_refs": [right_ref.model_dump(mode="json")],
        "outcome": outcome,
        "decision_reason": "Synthetic reviewer preserved the suffix conflict and requested a candidate alias-table diff.",
        "reviewer_id": "synthetic-reviewer-001",
        "reviewed_at": FIXED_TIME,
        "proposed_local_table_change": "alias_edge"
        if outcome == "confirm_alias_table_candidate"
        else "none",
        "red_team_notes": [
            "Suffix disagreement can represent distinct legal entities; no merge is asserted."
        ],
    }
    return EntityResolutionCorrectionRecord.model_validate(
        {
            "entity_resolution_correction_record_id": "entity-resolution-correction-record-001",
            "run_id": "synthetic-run-001",
            "preflight_packet_id": "synthetic-preflight-001",
            "source_bundle_id": bundle.bundle_id,
            "reviewer_id": "synthetic-reviewer-001",
            "reviewed_at": FIXED_TIME,
            "decisions": [decision],
        }
    )


def test_entity_correction_preserves_source_bound_hold_and_emits_only_candidates(repo_root):
    bundle = _bundle(repo_root)
    report, candidates, dad_draft = build_entity_resolution_correction_report(
        bundle=bundle,
        source_bundle_ref="fixture",
        record=_record(repo_root, bundle),
        generated_at=FIXED_TIME,
    )
    assert report.status == "entity_resolution_corrections_ready_for_review"
    assert report.alias_table_candidate_count == 1
    assert report.lake_write_performed is False
    assert report.silent_learning_performed is False
    assert candidates[0].local_event_label == "human_entity_resolution_correction"
    assert candidates[0].canonical_promotion_required is True
    assert dad_draft["emitted_to_outbox"] is False


def test_entity_correction_fails_closed_when_evidence_hash_does_not_match(repo_root):
    bundle = _bundle(repo_root)
    report, _, _ = build_entity_resolution_correction_report(
        bundle=bundle,
        source_bundle_ref="fixture",
        record=_record(repo_root, bundle, bad_hash=True),
        generated_at=FIXED_TIME,
    )
    assert report.status == "blocked_entity_resolution_corrections"
    assert {check.check_id for check in report.checks if check.status == "failed"} == {
        "all_correction_evidence_is_exact_and_hash_bound"
    }


def test_entity_correction_cli_writes_local_candidate_artifacts(repo_root, tmp_path):
    bundle = _bundle(repo_root)
    bundle_path, record_path = tmp_path / "bundle.json", tmp_path / "record.json"
    write_json(bundle_path, bundle.model_dump(mode="json"))
    write_json(record_path, _record(repo_root, bundle).model_dump(mode="json"))
    assert (
        main(
            [
                "audit-entity-resolution-corrections",
                "--source-bundle",
                str(bundle_path),
                "--correction-record",
                str(record_path),
                "--out-dir",
                str(tmp_path / "out"),
                "--generated-at",
                FIXED_TIME,
            ]
        )
        == 0
    )
    payload = load_json(tmp_path / "out" / REPORT_FILENAME)
    assert payload["candidate_only"] is True
    assert payload["lake_write_performed"] is False
