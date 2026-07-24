"""LW1 — scaled synthetic corpus generator (World-Builder-lite).

Deterministic, seeded, candidate-only, synthetic-only. Ground truth known by
construction; a declared difficulty model prevents tautological routing accuracy
(P1); the train/holdout split is frozen and leak-proof (P2); regeneration is
byte-identical (P9).
"""

import pytest

from lawfirm_os_intake.routing_eval import _synthetic_context, route_decision
from lawfirm_os_intake.synthetic_corpus_generator import (
    DEFAULT_CORPUS_SEED,
    build_bundle_and_segments,
    build_corpus_manifest,
    generate_corpus,
    load_corpus,
    load_corpus_manifest,
)
from lawfirm_os_intake.models import GeneratedSyntheticCase, SyntheticCorpusManifest
from lawfirm_os_intake.workers import classify_matter


def test_corpus_is_deterministic_across_regenerations():
    first = generate_corpus()
    second = generate_corpus()
    assert [case.content_digest for case in first] == [case.content_digest for case in second]
    m1 = build_corpus_manifest(first, generated_at="2026-07-23T00:00:00Z")
    m2 = build_corpus_manifest(second, generated_at="2026-07-23T00:00:00Z")
    assert m1.corpus_digest == m2.corpus_digest
    assert m1.holdout_split_digest == m2.holdout_split_digest


def test_frozen_corpus_matches_regeneration(repo_root):
    frozen_cases = load_corpus(repo_root)
    frozen_manifest = load_corpus_manifest(repo_root)
    regenerated = generate_corpus(corpus_seed=frozen_manifest.corpus_seed)
    assert [case.content_digest for case in frozen_cases] == [
        case.content_digest for case in regenerated
    ]
    rebuilt = build_corpus_manifest(
        regenerated,
        corpus_seed=frozen_manifest.corpus_seed,
        generated_at=frozen_manifest.generated_at,
    )
    assert rebuilt.corpus_digest == frozen_manifest.corpus_digest
    assert rebuilt.holdout_split_digest == frozen_manifest.holdout_split_digest


def test_manifest_reconciles_fail_closed(repo_root):
    manifest = load_corpus_manifest(repo_root)
    dumped = manifest.model_dump()
    # Tamper a case's split without updating the digest -> rejected.
    dumped["cases"][0]["holdout_split"] = (
        "train" if dumped["cases"][0]["holdout_split"] == "holdout" else "holdout"
    )
    with pytest.raises(ValueError):
        SyntheticCorpusManifest.model_validate(dumped)


def test_holdout_split_is_stable_and_leak_proof():
    # P2: the split is a seeded hash of case_id; it does not depend on generation
    # order and is reproduced identically, so a later probe cannot leak across it.
    cases = generate_corpus()
    by_id = {case.case_id: case.holdout_split for case in cases}
    again = {case.case_id: case.holdout_split for case in generate_corpus()}
    assert by_id == again
    # A different corpus seed reassigns the split (proof the split is seed-bound).
    other = {case.case_id: case.holdout_split for case in generate_corpus(corpus_seed=1)}
    assert other != by_id


def test_difficulty_is_not_tautological():
    # P1: at least one hard/distractor case must make the deterministic router
    # disagree with the ground-truth family (route to a distractor or abstain);
    # otherwise the corpus would report accuracy ~1.0 by construction.
    cases = generate_corpus()
    disagreements = 0
    for case in cases:
        if case.difficulty != "hard":
            continue
        bundle, segments = build_bundle_and_segments(case)
        _inbound, matter, _posture = classify_matter(bundle, segments, _synthetic_context())
        routed_family, decision, _reason = route_decision(matter)
        if decision != "route" or routed_family != case.ground_truth_family:
            disagreements += 1
    assert disagreements > 0


def test_clear_cases_carry_genuine_signal_terms():
    for case in generate_corpus():
        if case.difficulty == "clear" and case.variant != "missing_attachment":
            assert case.signal_terms_used
            assert not (set(case.signal_terms_used) & set(case.distractor_terms_used))


def test_injection_line_is_flagged_and_label_integrity_holds():
    cases = generate_corpus()
    injection = [case for case in cases if case.variant == "injection_as_text"]
    assert injection
    for case in injection:
        risk_lines = [line for line in case.rendered_lines if line.source_instruction_risk]
        assert len(risk_lines) == 1
        # The injection line carries no genuine family signal terms.
        assert all(term not in risk_lines[0].text for term in case.signal_terms_used)


def test_missing_attachment_expects_abstention():
    cases = generate_corpus()
    missing = [case for case in cases if case.variant == "missing_attachment"]
    assert missing
    for case in missing:
        assert case.expected_decision == "abstain"
        assert case.signal_terms_used == []


def test_tampered_case_total_is_rejected(repo_root):
    case = load_corpus(repo_root)[0]
    dumped = case.model_dump()
    dumped["difficulty"] = "clear"
    dumped["signal_terms_used"] = []
    with pytest.raises(ValueError):
        GeneratedSyntheticCase.model_validate(dumped)


def test_corpus_seed_default_is_pinned():
    assert DEFAULT_CORPUS_SEED == 20260723
