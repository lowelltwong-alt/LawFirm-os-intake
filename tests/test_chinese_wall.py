from __future__ import annotations

import json
from copy import deepcopy

import pytest
from pydantic import ValidationError

from lawfirm_os_intake.conflicts import (
    ChineseWallRequest,
    WallDecision,
    build_chinese_wall_proof,
    build_chinese_wall_violation_candidate,
    chinese_wall_request_digest,
)
from lawfirm_os_intake.util import load_json


def _fixture(repo_root):
    return load_json(
        repo_root
        / "examples/synthetic/conflicts/chinese-wall-cases.synthetic-policy-placeholder.json"
    )


def _request(repo_root, case_id: str) -> dict:
    fixture = _fixture(repo_root)
    case = next(item for item in fixture["cases"] if item["case_id"] == case_id)
    return {
        **deepcopy(case["request"]),
        "data_class": "synthetic_fixture",
        "runtime_scope": "synthetic_candidate",
        "candidate_only": True,
        "lesson_status": "candidate",
        "adversity_graph": deepcopy(fixture["adversity_graph"]),
        "synthetic_adversity_graph_digest": fixture["trusted_synthetic_adversity_graph_digest"],
        "synthetic_case_manifest_digest": fixture["trusted_synthetic_case_manifest_digest"],
        "provenance_scope": "synthetic_firm_wide_fixture",
        "trusted_synthetic_firm_wide_provenance_snapshot_pinned": True,
        "synthetic_firm_wide_imputation_required": True,
        "authoritative_firm_wide_provenance_manifest_verified": False,
        "consuming_context_scope_known": True,
        "contains_real_data": False,
        "contains_private_data": False,
        "contains_client_data": False,
        "contains_matter_data": False,
        "contains_real_carrier_data": False,
        "contains_privileged_content": False,
        "contains_work_product": False,
    }


@pytest.mark.parametrize(
    ("case_id", "expected"),
    [
        ("chw-same-side-ok", WallDecision.same_side_candidate),
        ("chw-cross-wall-block", WallDecision.cross_wall_block),
        ("chw-firm-wide-imputation", WallDecision.cross_wall_block),
        ("chw-unreviewed-edge-holds", WallDecision.unreviewed_edge_hold),
        ("chw-unknown-relation-holds", WallDecision.unknown_relation_hold),
    ],
)
def test_synthetic_chinese_wall_cases_are_deterministic(repo_root, case_id, expected):
    request = _request(repo_root, case_id)
    first = build_chinese_wall_proof(request)
    second = build_chinese_wall_proof(request)

    assert first == second
    assert first.local_evaluation.decision is expected
    assert first.overall_status == "blocked"
    assert first.lesson_fire_performed is False
    assert first.conflict_clearance_asserted is False
    assert first.counsel_adversity_classes_authority_verified is False
    assert chinese_wall_request_digest(request).startswith("sha256:")


def test_same_side_is_only_a_local_candidate(repo_root):
    proof = build_chinese_wall_proof(_request(repo_root, "chw-same-side-ok"))

    assert proof.local_evaluation.local_wall_candidate is True
    assert [reason.value for reason in proof.blocking_reasons] == [
        "authoritative_firm_wide_imputation_not_verified",
        "counsel_adversity_classes_not_authoritative",
        "authenticated_human_conflicts_review_not_verified",
        "owning_repo_review_not_verified",
    ]


def test_cross_wall_builds_sanitized_candidate_without_lake_write(repo_root):
    proof = build_chinese_wall_proof(_request(repo_root, "chw-cross-wall-block"))
    candidate = build_chinese_wall_violation_candidate(proof)

    assert proof.local_evaluation.reviewed_adverse_pair_count == 1
    assert proof.synthetic_firm_wide_imputation_applied is True
    assert proof.trusted_synthetic_provenance_snapshot_pinned is True
    assert proof.authoritative_firm_wide_imputation_verified is False
    assert candidate is not None
    assert candidate.reason_code == "synthetic_chinese_wall_violation_candidate"
    assert candidate.exception_lake_write_performed is False
    assert candidate.external_action_performed is False
    serialized = proof.model_dump_json()
    assert "synthetic-coi-class-alpha" not in serialized
    assert "synthetic-coi-class-beta" not in serialized


def test_unreviewed_and_unknown_relationships_hold_without_inference(repo_root):
    unreviewed = build_chinese_wall_proof(_request(repo_root, "chw-unreviewed-edge-holds"))
    unknown = build_chinese_wall_proof(_request(repo_root, "chw-unknown-relation-holds"))

    assert unreviewed.local_evaluation.unreviewed_pair_count == 1
    assert unreviewed.local_evaluation.relationship_inference_performed is False
    assert unknown.local_evaluation.unknown_pair_count == 1
    assert unknown.local_evaluation.relationship_inference_performed is False
    assert build_chinese_wall_violation_candidate(unreviewed) is None
    assert build_chinese_wall_violation_candidate(unknown) is None


@pytest.mark.parametrize(
    ("path", "unsafe_value"),
    [
        (("contains_real_data",), True),
        (("contains_privileged_content",), True),
        (("synthetic_firm_wide_imputation_required",), False),
        (("authoritative_firm_wide_provenance_manifest_verified",), True),
        (("synthetic_firm_wide_provenance_snapshot_digest",), "sha256:" + ("0" * 64)),
        (("request_id",), "synthetic-unlisted-wall-request"),
        (("consuming_matter_class_ids", 0), "synthetic-coi-class-beta"),
        (("adversity_graph", "adversity_inference_performed"), True),
        (
            ("adversity_graph", "counsel_adversity_classes_authority_verified"),
            True,
        ),
        (("adversity_graph", "conflict_classes", 0, "member_ref_count"), 3),
    ],
)
def test_request_rejects_real_scope_authority_and_optional_imputation(
    repo_root,
    path,
    unsafe_value,
):
    request = _request(repo_root, "chw-same-side-ok")
    target = request
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = unsafe_value

    with pytest.raises(ValidationError):
        ChineseWallRequest.model_validate_json(json.dumps(request))
