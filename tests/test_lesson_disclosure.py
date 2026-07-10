from __future__ import annotations

from copy import deepcopy
import json

import pytest

from lawfirm_os_intake.lessons import (
    GeneralizationLattice,
    LessonAtom,
    LessonDisclosureProof,
    LessonDisclosureRequest,
    PublishedLessonProjection,
    ReviewedSyntheticUniverse,
    TRUSTED_SYNTHETIC_CONTEXT_DIGEST,
    TRUSTED_SYNTHETIC_LESSON_DIGESTS,
    build_lesson_disclosure_proof,
    check_differencing,
    lesson_disclosure_request_digest,
    published_projection_snapshot_digest,
    synthetic_lesson_fixture_digest,
)
from lawfirm_os_intake.reviewed_learning_gate import (
    LESSON_DISCLOSURE_PROOF_REQUIRED_GATES,
    build_reviewed_learning_gate_report,
    validate_lesson_disclosure_gate,
)
from lawfirm_os_intake.util import load_json


def _fixture(repo_root):
    return load_json(
        repo_root
        / "examples/synthetic/lessons/qrd-disclosure-cases.synthetic-policy-placeholder.json"
    )


def _request(repo_root, case_id):
    raw = _fixture(repo_root)
    case = next(item for item in raw["cases"] if item["case_id"] == case_id)
    published_lessons = deepcopy(case["published_lessons"])
    return {
        "request_id": f"synthetic-{case_id}",
        "lesson": deepcopy(case["lesson"]),
        "policy": deepcopy(raw["policy"]),
        "lattice": deepcopy(raw["lattice"]),
        "universe": deepcopy(raw["universe"]),
        "synthetic_lesson_fixture_digest": synthetic_lesson_fixture_digest(case["lesson"]),
        "synthetic_context_digest": TRUSTED_SYNTHETIC_CONTEXT_DIGEST,
        "publication_snapshot_id": "synthetic-qrd-publication-snapshot-v1",
        "publication_snapshot_digest": published_projection_snapshot_digest(published_lessons),
        "authoritative_publication_snapshot_verified": False,
        "published_lessons": published_lessons,
    }


def _proof(repo_root, case_id="lesson-kanon-generalize"):
    return build_lesson_disclosure_proof(
        _request(repo_root, case_id),
        generated_at="2026-07-10T00:00:00+00:00",
    )


def test_fixture_lesson_manifest_is_complete_and_exact(repo_root):
    raw = _fixture(repo_root)

    assert {
        synthetic_lesson_fixture_digest(case["lesson"]) for case in raw["cases"]
    } == TRUSTED_SYNTHETIC_LESSON_DIGESTS


def test_specific_lesson_climbs_deterministically_to_synthetic_k(repo_root):
    proof = _proof(repo_root)

    assert proof.status == "blocked"
    assert proof.local_mechanism_candidate is True
    assert proof.refusal_reasons == ("authoritative_publication_snapshot_not_verified",)
    assert [(atom.dimension, atom.value) for atom in proof.atoms] == [
        ("carrier", "carrier_tier_regional")
    ]
    assert [step.model_dump() for step in proof.generalization_path] == [
        {
            "dimension": "carrier",
            "to_value": "carrier_tier_regional",
            "from_value_included": False,
        }
    ]
    assert proof.anonymity.anonymity_set == 3
    assert proof.anonymity.sensitive_outcome_diversity == 3
    assert proof.anonymity.l_diversity_ok is True
    assert proof.guarantee == "bounded_reident_under_declared_adversary"
    assert proof.formal_privacy_guarantee_claimed is False
    assert proof.authenticated_human_disclosure_review_verified is False
    assert proof.differencing_check.authoritative_publication_snapshot_verified is False
    assert proof.sensitive_request_digest_included is False
    assert proof.adversary_capabilities == (
        "combines_published_lessons",
        "knows_all_but_target_support",
        "knows_reviewed_universe",
    )
    assert proof.applies_when == ("applies_matching_operational_context",)
    assert proof.does_not_apply_when == ("not_for_strategy_or_unknown_context",)
    assert proof.danger_if_misapplied == "danger_overgeneralized_candidate_rule"


def test_proof_excludes_support_matter_ids_and_free_text(repo_root):
    proof = _proof(repo_root)
    encoded = json.dumps(proof.model_dump(mode="json"), sort_keys=True)

    assert "synthetic-qrd-matter" not in encoded
    assert "carrier_alpha" not in encoded
    assert "input_digest" not in encoded
    assert proof.support_matter_ids_included is False
    assert proof.free_text_lint.free_text_included_in_proof is False
    assert proof.free_text_lint.free_text_consumed_as_signal is False


def test_top_of_lattice_below_k_is_suppressed(repo_root):
    raw = _fixture(repo_root)
    universe = ReviewedSyntheticUniverse.model_validate(raw["universe"])
    lattice = GeneralizationLattice.model_validate(raw["lattice"])

    result = lattice.minimal_generalization(
        (LessonAtom(dimension="carrier", value="carrier_alpha", atom_class="operational"),),
        universe,
        7,
        2,
    )

    assert result.suppressed is True
    assert len(result.anonymity_set) == 6


def test_top_of_lattice_below_sensitive_outcome_diversity_is_suppressed(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    request["policy"]["minimum_sensitive_outcome_diversity"] = 5
    request["synthetic_context_digest"] = "sha256:" + ("0" * 64)

    with pytest.raises(ValueError):
        build_lesson_disclosure_proof(request)


def test_l_diversity_uses_explicit_sensitive_outcome_attribute(repo_root):
    raw = _fixture(repo_root)
    universe_payload = deepcopy(raw["universe"])
    for matter in universe_payload["matters"]:
        matter["sensitive_outcome_code"] = "synthetic_outcome_a"
    universe = ReviewedSyntheticUniverse.model_validate(universe_payload)
    lattice = GeneralizationLattice.model_validate(raw["lattice"])

    result = lattice.minimal_generalization(
        (LessonAtom(dimension="carrier", value="carrier_alpha", atom_class="operational"),),
        universe,
        3,
        2,
    )

    assert result.suppressed is True
    assert result.sensitive_outcome_diversity == 1
    assert len(result.anonymity_set) == 6


def test_strategy_atom_is_blocked_not_generalized(repo_root):
    proof = _proof(repo_root, "lesson-privilege-block")

    assert proof.status == "blocked"
    assert proof.privilege_screen.strategy_atoms_present is True
    assert proof.privilege_screen.blocking_atom_count == 1
    assert proof.privilege_screen.blocking_atom_keys_included is False
    assert "strategy_atom_blocked_not_generalized" in proof.refusal_reasons
    assert proof.generalization_path == ()
    assert proof.atoms == ()
    assert proof.strategy_atoms_generalized is False


def test_nonempty_free_text_is_blocked_from_disclosure(repo_root):
    proof = _proof(repo_root, "lesson-freetext-block")
    encoded = json.dumps(proof.model_dump(mode="json"), sort_keys=True)

    assert proof.status == "blocked"
    assert proof.free_text_lint.signal_bearing_free_text_present is True
    assert "signal_bearing_free_text_blocked" in proof.refusal_reasons
    assert "synthetic advisory text" not in encoded


def test_cross_lesson_differencing_suppresses_new_lesson_without_ids(repo_root):
    proof = _proof(repo_root, "lesson-differencing")

    assert proof.status == "blocked"
    assert proof.differencing_check.narrows_below_K is True
    assert proof.differencing_check.suppressed is True
    assert "cross_lesson_differencing_below_K_qual" in proof.refusal_reasons
    assert proof.differencing_check.intersections[0].anonymity_set == 1
    assert proof.differencing_check.support_matter_ids_included is False


def test_support_threshold_cannot_change_outside_pinned_context(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    request["policy"]["k_support"] = 2

    with pytest.raises(ValueError, match="pinned synthetic fixture"):
        build_lesson_disclosure_proof(request)


def test_unknown_lattice_value_fails_closed(repo_root):
    raw = _fixture(repo_root)
    universe = ReviewedSyntheticUniverse.model_validate(raw["universe"])
    lattice = GeneralizationLattice.model_validate(raw["lattice"])

    with pytest.raises(ValueError, match="unknown lattice value"):
        lattice.minimal_generalization(
            (
                LessonAtom(
                    dimension="carrier",
                    value="unknown-carrier",
                    atom_class="operational",
                ),
            ),
            universe,
            3,
            2,
        )


def test_mutated_support_cannot_bypass_pinned_lesson_manifest(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    request["lesson"]["support_matter_ids"] = ["synthetic-qrd-matter-002"]

    with pytest.raises(ValueError, match="synthetic fixture digest"):
        build_lesson_disclosure_proof(request)


def test_adversary_model_is_a_closed_placeholder_id_not_free_text(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    request["policy"]["adversary_model"] = "synthetic adversary placeholder prose"

    with pytest.raises(ValueError):
        LessonDisclosureRequest.model_validate(request)


def test_atom_value_cannot_be_free_text_or_unreviewed_prose(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    request["lesson"]["atoms"][0]["value"] = "Carrier Alpha narrative"

    with pytest.raises(ValueError):
        LessonDisclosureRequest.model_validate(request)


def test_generalization_cannot_enter_strategy_partition(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    request["policy"]["strategy_atom_keys"].append("carrier:carrier_tier_regional")

    with pytest.raises(ValueError, match="pinned synthetic fixture"):
        build_lesson_disclosure_proof(request)


def test_published_strategy_projection_blocks_differencing_input(repo_root):
    request = _request(repo_root, "lesson-differencing")
    request["published_lessons"][0]["atoms"][0]["atom_class"] = "strategy"
    request["publication_snapshot_digest"] = published_projection_snapshot_digest(
        request["published_lessons"]
    )

    proof = build_lesson_disclosure_proof(request)

    assert proof.status == "blocked"
    assert proof.refusal_reasons == (
        "authoritative_publication_snapshot_not_verified",
        "published_projection_contains_strategy_atom",
    )


def test_real_or_private_scope_flags_are_rejected_as_extra_input(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    request["lesson"]["contains_real_matter_data"] = True

    with pytest.raises(ValueError):
        LessonDisclosureRequest.model_validate(request)


def test_relabelled_real_looking_context_cannot_replace_pinned_fixture(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    request["lesson"]["atoms"][0]["value"] = "realcarrierx"
    request["lattice"]["parents"]["carrier"]["realcarrierx"] = "carrier_tier_regional"
    request["universe"]["matters"][0]["attributes"]["carrier"] = "realcarrierx"

    with pytest.raises(ValueError, match="synthetic fixture digest"):
        LessonDisclosureRequest.model_validate(request)


def test_omitting_published_projection_cannot_produce_releasable_status(repo_root):
    request = _request(repo_root, "lesson-differencing")
    request["published_lessons"] = []
    request["publication_snapshot_digest"] = published_projection_snapshot_digest([])

    proof = build_lesson_disclosure_proof(request)

    assert proof.local_mechanism_candidate is True
    assert proof.status == "blocked"
    assert proof.refusal_reasons == ("authoritative_publication_snapshot_not_verified",)


def test_differencing_uses_lattice_meet_for_ancestor_predicates(repo_root):
    raw = _fixture(repo_root)
    universe = ReviewedSyntheticUniverse.model_validate(raw["universe"])
    lattice = GeneralizationLattice.model_validate(raw["lattice"])
    published_lessons = tuple(
        PublishedLessonProjection.model_validate(item)
        for item in [
            {
                "lesson_id": "synthetic-published-regional-carrier",
                "atoms": [
                    {
                        "dimension": "carrier",
                        "value": "carrier_tier_regional",
                        "atom_class": "operational",
                    }
                ],
            },
            {
                "lesson_id": "synthetic-published-mountain-west",
                "atoms": [
                    {
                        "dimension": "jurisdiction",
                        "value": "mountain_west",
                        "atom_class": "operational",
                    }
                ],
            },
        ]
    )

    result = check_differencing(
        candidate_atoms=(
            LessonAtom(dimension="carrier", value="any_carrier", atom_class="operational"),
        ),
        published_lessons=published_lessons,
        universe=universe,
        lattice=lattice,
        k_qual=3,
    )

    assert result.narrows_below_k is True
    assert any(
        len(item.matter_ids) == 1 and len(item.published_lesson_ids) == 2
        for item in result.intersections
    )


def test_digest_and_proof_are_order_independent(repo_root):
    first = _request(repo_root, "lesson-kanon-generalize")
    reordered = deepcopy(first)
    reordered["universe"]["matters"] = list(reversed(reordered["universe"]["matters"]))
    reordered["policy"]["allowed_context_codes"] = list(
        reversed(reordered["policy"]["allowed_context_codes"])
    )

    first_proof = build_lesson_disclosure_proof(first, generated_at="2026-07-10T00:00:00+00:00")
    reordered_proof = build_lesson_disclosure_proof(
        reordered, generated_at="2026-07-10T00:00:00+00:00"
    )

    assert reordered_proof == first_proof


def test_gate_refuses_missing_proof():
    check = validate_lesson_disclosure_gate(
        lesson_id="synthetic-lesson",
        lesson_disclosure_proof=None,
    )

    assert check.status == "failed"
    assert check.check_id == "lesson_disclosure_proof_required"


def test_gate_stays_blocked_without_authenticated_human_review(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    proof = build_lesson_disclosure_proof(request)

    check = validate_lesson_disclosure_gate(
        lesson_id=proof.lesson_id,
        lesson_disclosure_proof=proof,
        lesson_disclosure_request=request,
        expected_lesson_input_digest=lesson_disclosure_request_digest(request),
        approval_id="approval:human-disclosure-review-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "lesson_disclosure_proof_promotion_gate"
    assert "authenticated_human_disclosure_review_not_verified" in check.message
    assert LESSON_DISCLOSURE_PROOF_REQUIRED_GATES == [
        "valid_lesson_disclosure_proof",
        "external_lesson_request_digest_anchor",
        "bounded_reident_under_declared_adversary_only",
        "authenticated_human_disclosure_review",
        "owning_repo_review",
        "no_lesson_publication_or_dad_crossing_from_intake",
    ]


def test_gate_rejects_forged_authenticated_review(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    proof = build_lesson_disclosure_proof(request)
    forged = proof.model_dump(mode="json")
    forged["authenticated_human_disclosure_review_verified"] = True

    check = validate_lesson_disclosure_gate(
        lesson_id=proof.lesson_id,
        lesson_disclosure_proof=forged,
        lesson_disclosure_request=request,
        expected_lesson_input_digest=lesson_disclosure_request_digest(request),
        approval_id="approval:human-disclosure-review-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "lesson_disclosure_proof_valid"


def test_gate_rejects_forged_request_and_proof_against_external_digest(repo_root):
    original_request = _request(repo_root, "lesson-kanon-generalize")
    forged_request = _request(repo_root, "lesson-freetext-block")
    forged = build_lesson_disclosure_proof(forged_request)

    check = validate_lesson_disclosure_gate(
        lesson_id=forged.lesson_id,
        lesson_disclosure_proof=forged,
        lesson_disclosure_request=forged_request,
        expected_lesson_input_digest=lesson_disclosure_request_digest(original_request),
        approval_id="approval:human-disclosure-review-0001",
    )

    assert check.status == "failed"
    assert check.check_id == "lesson_disclosure_proof_request_binding"
    assert "expected_digest_does_not_match_rebuilt_request" in check.message


def test_reviewed_learning_report_exposes_lesson_gate_without_candidate(repo_root):
    request = _request(repo_root, "lesson-kanon-generalize")
    proof = build_lesson_disclosure_proof(request)

    report = build_reviewed_learning_gate_report(
        lesson_disclosure_gate_requests=[
            {
                "lesson_id": proof.lesson_id,
                "lesson_disclosure_proof": proof.model_dump(mode="json"),
                "lesson_disclosure_request": request,
                "expected_lesson_input_digest": lesson_disclosure_request_digest(request),
                "approval_id": "approval:human-disclosure-review-0001",
                "proof_ref": "synthetic-qrd-proof",
            }
        ]
    )

    assert report.status == "failed"
    assert report.candidate_count == 0
    assert report.candidates == []
    assert any(
        check.check_id == "lesson_disclosure_gate_review_inputs_visible"
        and check.status == "passed"
        and check.candidate_ids == [proof.proof_id]
        for check in report.checks
    )
    assert any(
        check.check_id == "lesson_disclosure_proof_promotion_gate" and check.status == "failed"
        for check in report.checks
    )


def test_proof_model_rejects_formal_privacy_claim(repo_root):
    proof = _proof(repo_root).model_dump(mode="json")
    proof["formal_privacy_guarantee_claimed"] = True

    with pytest.raises(ValueError):
        LessonDisclosureProof.model_validate(proof)


def test_proof_model_rejects_arbitrary_refusal_text(repo_root):
    proof = _proof(repo_root).model_dump(mode="json")
    proof["refusal_reasons"] = ["attacker supplied narrative"]

    with pytest.raises(ValueError):
        LessonDisclosureProof.model_validate(proof)
