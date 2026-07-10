import math
import pickle

import pytest

from lawfirm_os_intake.privacy import (
    GaussianMechanism,
    SyntheticPrivacyScope,
    SyntheticReplaySeed,
    clip_l2,
)


def test_l2_clipping_bounds_vector_norm():
    clipped = clip_l2((3.0, 4.0), 2.0)

    assert clipped == pytest.approx((1.2, 1.6))
    assert math.sqrt(sum(value * value for value in clipped)) == pytest.approx(2.0)


def test_gaussian_noise_replays_deterministically_and_proof_has_hash_only():
    mechanism = GaussianMechanism(
        clip_norm=2.0, rho=0.5, replay_seed=SyntheticReplaySeed(b"a" * 32)
    )
    scope = SyntheticPrivacyScope()

    first = mechanism.release((3.0, 4.0), release_id="synthetic-release-1", scope=scope)
    second = mechanism.release((3.0, 4.0), release_id="synthetic-release-1", scope=scope)

    assert first == second
    assert first.clipped_values == pytest.approx((1.2, 1.6))
    assert (
        first.seed_hash
        == "sha256:" + "3ba3f5f43b92602683c19aee62a20342b084dd5971ddd33808d81a328879a547"
    )
    assert not hasattr(first, "seed")
    assert first.formal_production_privacy_claimed is False
    with pytest.raises(TypeError, match="never be serialized"):
        pickle.dumps(SyntheticReplaySeed(b"a" * 32))


def test_distinct_seeds_produce_separate_noise():
    scope = SyntheticPrivacyScope()
    first = GaussianMechanism(clip_norm=1.0, rho=1.0, replay_seed=SyntheticReplaySeed(b"a" * 32))
    second = GaussianMechanism(clip_norm=1.0, rho=1.0, replay_seed=SyntheticReplaySeed(b"b" * 32))

    assert (
        first.release((1.0,), release_id="synthetic-release", scope=scope).noise
        != second.release((1.0,), release_id="synthetic-release", scope=scope).noise
    )


def test_release_sum_clips_each_protected_contribution_before_pooling():
    mechanism = GaussianMechanism(
        clip_norm=2.0, rho=0.5, replay_seed=SyntheticReplaySeed(b"c" * 32)
    )

    release = mechanism.release_sum(
        [(3.0, 4.0), (0.0, 1.0)],
        release_id="synthetic-pooled-release",
        scope=SyntheticPrivacyScope(),
    )

    assert release.clipped_values == pytest.approx((1.2, 2.6))
    assert release.pre_clip_max_norm == pytest.approx(5.0)
    assert release.clipped_contribution_count == 1


@pytest.mark.parametrize(
    "kwargs",
    [
        {"data_class": "real_matter"},
        {"runtime_scope": "production"},
        {"candidate_only": False},
        {"contains_real_client_data": True},
        {"contains_real_matter_data": True},
        {"contains_carrier_private_data": True},
        {"contains_privileged_data": True},
    ],
)
def test_invalid_or_private_scope_is_rejected(kwargs):
    with pytest.raises(ValueError):
        SyntheticPrivacyScope(**kwargs)
