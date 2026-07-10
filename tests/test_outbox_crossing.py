from __future__ import annotations

from copy import deepcopy
import json

import pytest

from lawfirm_os_intake.lessons import (
    TRUSTED_SYNTHETIC_CONTEXT_DIGEST,
    build_lesson_disclosure_proof,
    published_projection_snapshot_digest,
    synthetic_lesson_fixture_digest,
)
from lawfirm_os_intake.outbox import (
    CrossingProof,
    CrossingRequest,
    SensitivityLabel,
    build_crossing_proof,
    crossing_request_digest,
    scan_residue,
)
from lawfirm_os_intake.util import load_json


def _lesson_request(repo_root, case_id="lesson-kanon-generalize"):
    fixture = load_json(
        repo_root
        / "examples/synthetic/lessons/qrd-disclosure-cases.synthetic-policy-placeholder.json"
    )
    case = next(item for item in fixture["cases"] if item["case_id"] == case_id)
    published_lessons = deepcopy(case["published_lessons"])
    return {
        "request_id": "synthetic-ifc-qrd-request",
        "lesson": deepcopy(case["lesson"]),
        "policy": deepcopy(fixture["policy"]),
        "lattice": deepcopy(fixture["lattice"]),
        "universe": deepcopy(fixture["universe"]),
        "synthetic_lesson_fixture_digest": synthetic_lesson_fixture_digest(case["lesson"]),
        "synthetic_context_digest": TRUSTED_SYNTHETIC_CONTEXT_DIGEST,
        "publication_snapshot_id": "synthetic-qrd-publication-snapshot-v1",
        "publication_snapshot_digest": published_projection_snapshot_digest(published_lessons),
        "authoritative_publication_snapshot_verified": False,
        "published_lessons": published_lessons,
    }


def _request(repo_root):
    raw = load_json(repo_root / "examples/synthetic/outbox/ifc-crossing-cases.synthetic.json")
    request = deepcopy(raw["request"])
    lesson_request = _lesson_request(repo_root)
    request["lesson_disclosure_request"] = lesson_request
    request["lesson_disclosure_proof"] = build_lesson_disclosure_proof(
        lesson_request, generated_at="2026-07-10T00:00:00+00:00"
    ).model_dump(mode="json")
    return request


def test_clean_local_evidence_is_still_blocked_by_qrd_authority(repo_root):
    proof = build_crossing_proof(_request(repo_root))

    assert proof.local_scanner_evidence.clean is True
    assert proof.local_scanner_evidence.scanned_signal_count > 0
    assert proof.local_lattice_evidence.effective_label is SensitivityLabel.candidate
    assert proof.local_lattice_evidence.label_within_candidate_boundary is True
    assert proof.local_scanner_and_lattice_candidate is True
    assert proof.qrd_binding.local_mechanism_candidate is True
    assert proof.qrd_binding.disclosure_status == "blocked"
    assert proof.qrd_binding.authoritative_publication_snapshot_verified is False
    assert proof.qrd_binding.authenticated_human_disclosure_review_verified is False
    assert proof.overall_status == "blocked"
    assert proof.actual_crossing_asserted is False
    assert proof.dad_receiver_schema_authority_verified is False
    assert proof.authenticated_human_crossing_review_verified is False
    assert proof.blocking_reasons == (
        "qrd_disclosure_not_candidate",
        "qrd_publication_snapshot_not_authoritative",
        "qrd_human_review_not_authenticated",
        "dad_receiver_schema_not_authoritative",
        "human_crossing_review_not_authenticated",
        "owning_repo_review_not_verified",
    )
    assert proof.guarantee == "deterministic_declared_pattern_residue_check"
    assert proof.formal_noninterference_guarantee_claimed is False
    assert proof.owning_repo_review_verified is False


def test_currency_is_blocked_without_echoing_the_signal():
    result = scan_residue(("USD 12.50",), scope_confirmed_synthetic=True)

    assert "currency_or_rate_detected" in result.reason_codes
    assert result.raw_signal_values_included is False


def test_specific_carrier_identifier_is_blocked_without_echoing_the_signal():
    result = scan_residue(("carrier_alpha",), scope_confirmed_synthetic=True)

    assert "specific_carrier_identifier_detected" in result.reason_codes
    assert result.raw_signal_values_included is False


def test_any_nonempty_free_text_signal_is_blocked():
    result = scan_residue(("unstructured narrative",), scope_confirmed_synthetic=True)

    assert result.clean is False
    assert "free_text_signal_present" in result.reason_codes


def test_label_above_candidate_is_recorded_as_local_lattice_evidence(repo_root):
    request = _request(repo_root)
    request["content_labels"] = ["internal"]

    proof = build_crossing_proof(request)

    assert proof.local_scanner_evidence.clean is True
    assert proof.local_lattice_evidence.effective_label is SensitivityLabel.internal
    assert proof.local_lattice_evidence.label_within_candidate_boundary is False
    assert proof.local_scanner_and_lattice_candidate is False
    assert "label_above_candidate" in proof.blocking_reasons
    assert proof.overall_status == "blocked"


def test_mixed_label_join_is_candidate(repo_root):
    request = _request(repo_root)
    request["content_labels"] = ["candidate", "public"]

    proof = build_crossing_proof(request)

    assert proof.local_lattice_evidence.effective_label is SensitivityLabel.candidate
    assert proof.local_lattice_evidence.candidate_crossing_max is SensitivityLabel.candidate


def test_distinct_safe_source_label_sets_produce_distinct_proofs(repo_root):
    mixed = _request(repo_root)
    candidate_only = deepcopy(mixed)
    candidate_only["content_labels"] = ["candidate"]

    mixed_proof = build_crossing_proof(mixed)
    candidate_proof = build_crossing_proof(candidate_only)

    assert mixed_proof.local_lattice_evidence.source_labels == (
        SensitivityLabel.candidate,
        SensitivityLabel.public,
    )
    assert mixed_proof.proof_id != candidate_proof.proof_id


def test_pii_and_privilege_signals_are_blocked():
    result = scan_residue(
        ("person@example.test", "attorney-client work product"),
        scope_confirmed_synthetic=True,
    )

    assert "pii_detected" in result.reason_codes
    assert "privilege_or_work_product_detected" in result.reason_codes


def test_residue_scanner_refuses_unconfirmed_scope():
    with pytest.raises(ValueError, match="confirmed synthetic scope"):
        scan_residue(("synthetic signal",))


def test_specific_carrier_identifier_separator_variants_are_blocked():
    for signal in ("carrier-alpha", "carrier:alpha", "specific-carrier"):
        result = scan_residue((signal,), scope_confirmed_synthetic=True)
        assert "specific_carrier_identifier_detected" in result.reason_codes


def test_relabeled_real_looking_input_fails_closed(repo_root):
    request = _request(repo_root)
    request["contains_matter_data"] = True

    with pytest.raises(ValueError):
        CrossingRequest.model_validate(request)


def test_forged_qrd_proof_request_pair_fails_closed(repo_root):
    request = _request(repo_root)
    request["lesson_disclosure_request"] = _lesson_request(repo_root, "lesson-freetext-block")

    with pytest.raises(ValueError, match="QRD proof does not match"):
        build_crossing_proof(request)


def test_duplicate_content_labels_fail_closed(repo_root):
    request = _request(repo_root)
    request["content_labels"] = ["candidate", "candidate"]

    with pytest.raises(ValueError, match="content labels must be unique"):
        build_crossing_proof(request)


def test_request_rejects_arbitrary_free_text_input(repo_root):
    request = _request(repo_root)
    request["untrusted_signals"] = ["unstructured narrative"]

    with pytest.raises(ValueError):
        build_crossing_proof(request)


def test_external_request_digest_is_deterministic_and_order_independent(repo_root):
    first = _request(repo_root)
    reordered = deepcopy(first)
    reordered["content_labels"] = list(reversed(reordered["content_labels"]))

    assert crossing_request_digest(first) == crossing_request_digest(reordered)
    assert build_crossing_proof(first) == build_crossing_proof(reordered)


def test_crossing_proof_serialization_is_gate_safe(repo_root):
    request = _request(repo_root)
    proof = build_crossing_proof(request)
    encoded = json.dumps(proof.model_dump(mode="json"), sort_keys=True)

    assert "synthetic-qrd-matter" not in encoded
    assert "carrier_alpha" not in encoded
    assert '"crossing_request_digest":' not in encoded
    assert proof.sensitive_crossing_request_digest_included is False
    assert proof.support_ids_included is False
    assert proof.original_rare_values_included is False
    assert proof.free_text_included is False
    assert proof.prohibited_text_included is False
    assert proof.outbox_mutation_performed is False
    assert proof.send_performed is False
    assert proof.dad_contact_performed is False
    assert proof.network_access_performed is False
    assert proof.sibling_write_performed is False
    assert proof.auto_promotion_performed is False
    assert proof.legal_or_compliance_authority_exercised is False


def test_crossing_proof_rejects_formal_noninterference_claim(repo_root):
    proof = build_crossing_proof(_request(repo_root)).model_dump(mode="json")
    proof["formal_noninterference_guarantee_claimed"] = True

    with pytest.raises(ValueError):
        CrossingProof.model_validate_json(json.dumps(proof))


def test_crossing_proof_rejects_inconsistent_lattice_evidence(repo_root):
    proof = build_crossing_proof(_request(repo_root)).model_dump(mode="json")
    proof["local_lattice_evidence"]["effective_label"] = "internal"

    with pytest.raises(ValueError):
        CrossingProof.model_validate_json(json.dumps(proof))
