"""DT4 — driver-stratified synthetic matter generator (generation-spec v2).

Deterministic, candidate-only, synthetic-only. The load-bearing property: every
explicit driver level is OBSERVABLE as verbatim evidence inside the rendered
documents (fail-closed), and the documents never state the computed budget —
dollars come only from the canonical pricing engine downstream.
"""

import pytest

from lawfirm_os_intake.driver_taxonomy import build_explicit_canonical_profile
from lawfirm_os_intake.models import StratifiedCorpusManifest, StratifiedSyntheticMatter
from lawfirm_os_intake.pipeline_eval import load_reference_class_bands
from lawfirm_os_intake.canonical_pricing import build_canonical_priced_work_plan
from lawfirm_os_intake.stratified_corpus_generator import (
    generate_stratified_corpus,
    load_stratified_corpus,
)


def test_explicit_profile_fail_closed(repo_root):
    with pytest.raises(ValueError):
        build_explicit_canonical_profile({"mystery_driver": "x"}, repo_root=repo_root)
    with pytest.raises(ValueError):
        build_explicit_canonical_profile({"damages_severity": "apocalyptic"}, repo_root=repo_root)
    profile = build_explicit_canonical_profile(
        {"damages_severity": "catastrophic", "implicated_specialties": "3_plus"},
        repo_root=repo_root,
    )
    by_id = {a.driver_id: a for a in profile.assignments}
    assert by_id["damages_severity"].source == "explicit"
    assert by_id["medical_record_volume"].status == "not_elicited"


def test_generation_is_deterministic(repo_root):
    _, first = generate_stratified_corpus(repo_root=repo_root)
    _, second = generate_stratified_corpus(repo_root=repo_root)
    assert first.corpus_digest == second.corpus_digest
    assert first.corpus_id == second.corpus_id


def test_frozen_corpus_matches_regeneration(repo_root):
    matters, manifest = load_stratified_corpus(repo_root)
    _, regenerated = generate_stratified_corpus(repo_root=repo_root)
    assert manifest.corpus_digest == regenerated.corpus_digest
    assert len(matters) == manifest.case_count


def test_stratification_coverage(repo_root):
    matters, manifest = load_stratified_corpus(repo_root)
    assert manifest.case_count >= 150
    assert len(manifest.subtype_counts) == 7
    for subtype in manifest.subtype_counts:
        difficulties = {m.difficulty for m in matters if m.subtype == subtype}
        assert difficulties == {"clear", "moderate", "hard"}, subtype
    # The hard/high-cost anchor is pinned by the contract's subtype priors.
    for matter in matters:
        if matter.subtype == "birth_injury_obstetric":
            assert matter.explicit_driver_levels["damages_severity"] == "catastrophic"
            assert matter.explicit_driver_levels["implicated_specialties"] == "3_plus"


def test_every_driver_is_observable_in_documents(repo_root):
    matters, _ = load_stratified_corpus(repo_root)
    for matter in matters:
        assert set(matter.observable_driver_evidence) == set(matter.explicit_driver_levels)
    # Removing evidence for a driver fails closed.
    dumped = matters[0].model_dump()
    removed = next(iter(dumped["observable_driver_evidence"]))
    del dumped["observable_driver_evidence"][removed]
    with pytest.raises(ValueError):
        StratifiedSyntheticMatter.model_validate(dumped)
    # Evidence that does not appear in any document fails closed.
    dumped = matters[0].model_dump()
    key = next(iter(dumped["observable_driver_evidence"]))
    dumped["observable_driver_evidence"][key] = "this snippet appears nowhere"
    with pytest.raises(ValueError):
        StratifiedSyntheticMatter.model_validate(dumped)


def test_budget_is_deterministic_and_recomputable(repo_root):
    matters, _ = load_stratified_corpus(repo_root)
    for matter in matters[:: max(1, len(matters) // 5)]:
        profile = build_explicit_canonical_profile(
            matter.explicit_driver_levels, repo_root=repo_root
        )
        plan = build_canonical_priced_work_plan(profile, repo_root=repo_root)
        assert plan.plan_id == matter.plan_id
        assert plan.total_dollars_minor_units == matter.canonical_total_minor_units


def test_documents_never_state_the_budget(repo_root):
    matters, _ = load_stratified_corpus(repo_root)
    for matter in matters:
        amount = f"${matter.canonical_total_minor_units // 100:,}"
        for doc in matter.documents:
            assert f" {amount} " not in f" {doc.text} "
    # Injecting the computed total into a document fails closed.
    dumped = matters[0].model_dump()
    amount = f"${dumped['canonical_total_minor_units'] // 100:,}"
    dumped["documents"][0]["text"] += f" The defense budget is {amount}."
    with pytest.raises(ValueError):
        StratifiedSyntheticMatter.model_validate(dumped)


def test_holdout_is_frozen_and_seed_bound(repo_root):
    matters, manifest = load_stratified_corpus(repo_root)
    assert manifest.holdout_count > 0
    _, other_seed = generate_stratified_corpus(repo_root=repo_root, seed=999)
    assert other_seed.holdout_split_digest != manifest.holdout_split_digest


def test_manifest_fail_closed(repo_root):
    _, manifest = load_stratified_corpus(repo_root)
    dumped = manifest.model_dump()
    dumped["case_count"] += 1
    with pytest.raises(ValueError):
        StratifiedCorpusManifest.model_validate(dumped)
    dumped = manifest.model_dump()
    subtype = next(iter(dumped["subtype_counts"]))
    dumped["subtype_counts"][subtype] += 1
    with pytest.raises(ValueError):
        StratifiedCorpusManifest.model_validate(dumped)


def test_budget_to_exposure_ratio_within_reference_band(repo_root):
    matters, _ = load_stratified_corpus(repo_root)
    bands = load_reference_class_bands(repo_root / "config/synthetic-reference-class-bands.yaml")[
        "bands"
    ]["medical_malpractice"]
    for matter in matters:
        ratio = matter.canonical_total_minor_units / matter.exposure_minor_units
        assert bands["min_budget_to_exposure_ratio"] <= ratio
        assert ratio <= bands["max_budget_to_exposure_ratio"]


def test_difficulty_controls_signal_and_distractors(repo_root):
    matters, _ = load_stratified_corpus(repo_root)
    for matter in matters:
        if matter.difficulty == "clear":
            assert len(matter.signal_terms_used) >= 3
            assert matter.distractor_terms_used == []
        if matter.difficulty == "hard":
            assert len(matter.distractor_terms_used) >= 2
