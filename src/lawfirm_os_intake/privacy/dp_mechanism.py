"""Standard-library Gaussian releases for synthetic candidate evaluation only."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
import hmac
import json
import math
from typing import Iterable


@dataclass(frozen=True, slots=True)
class SyntheticPrivacyScope:
    """Explicitly limits these primitives to non-production synthetic fixtures."""

    data_class: str = "synthetic_fixture"
    runtime_scope: str = "synthetic_candidate"
    candidate_only: bool = True
    contains_real_client_data: bool = False
    contains_real_matter_data: bool = False
    contains_carrier_private_data: bool = False
    contains_privileged_data: bool = False

    def __post_init__(self) -> None:
        if self.data_class != "synthetic_fixture" or self.runtime_scope != "synthetic_candidate":
            raise ValueError("privacy primitives accept synthetic_fixture candidate scope only")
        if not self.candidate_only:
            raise ValueError("privacy primitives are candidate_only")
        if any(
            (
                self.contains_real_client_data,
                self.contains_real_matter_data,
                self.contains_carrier_private_data,
                self.contains_privileged_data,
            )
        ):
            raise ValueError("privacy primitives reject real, private, or privileged scopes")


class SyntheticReplaySeed:
    """Deterministic synthetic test material, never a production secrecy boundary."""

    __slots__ = ("__seed", "seed_hash")

    def __init__(self, seed: bytes) -> None:
        if not isinstance(seed, bytes) or len(seed) < 16:
            raise ValueError("synthetic replay seed must be at least 16 bytes")
        self.__seed = seed
        self.seed_hash = "sha256:" + sha256(seed).hexdigest()

    def _uniform(self, context: str) -> float:
        if not isinstance(context, str) or not context:
            raise ValueError("release context must be a non-empty string")
        material = hmac.new(self.__seed, context.encode("utf-8"), sha256).digest()
        integer = int.from_bytes(material, "big")
        return (integer + 0.5) / (2**256)

    def _standard_normal(self, context: str, index: int) -> float:
        # Deterministic Box-Muller replay avoids depending on random.Random internals.
        u1 = self._uniform(f"{context}|{index}|u1")
        u2 = self._uniform(f"{context}|{index}|u2")
        return math.sqrt(-2.0 * math.log(u1)) * math.cos(2.0 * math.pi * u2)

    def __reduce_ex__(self, protocol: int) -> object:
        raise TypeError("synthetic replay seeds must never be serialized")


@dataclass(frozen=True, slots=True)
class GaussianRelease:
    values: tuple[float, ...]
    clipped_values: tuple[float, ...]
    noise: tuple[float, ...]
    clip_norm: float
    rho: float
    noise_stddev: float
    seed_hash: str
    scope: SyntheticPrivacyScope
    pre_clip_max_norm: float = 0.0
    clipped_contribution_count: int = 0
    formal_production_privacy_claimed: bool = False


def clip_l2(vector: Iterable[float], clip_norm: float) -> tuple[float, ...]:
    """Return an L2-clipped vector without mutating caller-owned values."""
    values = tuple(float(value) for value in vector)
    if not values:
        raise ValueError("vector must not be empty")
    if not math.isfinite(clip_norm) or clip_norm <= 0:
        raise ValueError("clip_norm must be finite and positive")
    if not all(math.isfinite(value) for value in values):
        raise ValueError("vector values must be finite")
    norm = math.sqrt(sum(value * value for value in values))
    if norm <= clip_norm:
        return values
    scale = clip_norm / norm
    return tuple(value * scale for value in values)


class GaussianMechanism:
    """A deterministic-replay Gaussian mechanism over L2-clipped vectors.

    The standard deviation follows the zCDP calibration ``C / sqrt(2 * rho)``
    for L2 sensitivity ``C``. This is deliberately not wired to production.
    """

    def __init__(self, *, clip_norm: float, rho: float, replay_seed: SyntheticReplaySeed) -> None:
        if not math.isfinite(clip_norm) or clip_norm <= 0:
            raise ValueError("clip_norm must be finite and positive")
        if not math.isfinite(rho) or rho <= 0:
            raise ValueError("rho must be finite and positive")
        if not isinstance(replay_seed, SyntheticReplaySeed):
            raise TypeError("replay_seed must be a SyntheticReplaySeed")
        self.clip_norm = float(clip_norm)
        self.rho = float(rho)
        self._replay_seed = replay_seed
        self.noise_stddev = self.clip_norm / math.sqrt(2.0 * self.rho)

    def release(
        self,
        vector: Iterable[float],
        *,
        release_id: str,
        scope: SyntheticPrivacyScope,
    ) -> GaussianRelease:
        if not isinstance(scope, SyntheticPrivacyScope):
            raise TypeError("scope must be a SyntheticPrivacyScope")
        original = tuple(float(value) for value in vector)
        clipped = clip_l2(original, self.clip_norm)
        return self._release_clipped_query(
            clipped,
            release_id=release_id,
            scope=scope,
            pre_clip_max_norm=math.sqrt(sum(value * value for value in original)),
            clipped_contribution_count=int(original != clipped),
        )

    def release_sum(
        self,
        contributions: Iterable[Iterable[float]],
        *,
        release_id: str,
        scope: SyntheticPrivacyScope,
    ) -> GaussianRelease:
        """Clip each protected contribution, pool, then noise the sufficient-stat sum."""
        if not isinstance(scope, SyntheticPrivacyScope):
            raise TypeError("scope must be a SyntheticPrivacyScope")
        rows = [tuple(float(value) for value in row) for row in contributions]
        if not rows or not rows[0]:
            raise ValueError("release_sum requires non-empty contribution vectors")
        width = len(rows[0])
        if any(len(row) != width for row in rows):
            raise ValueError("release_sum contribution vectors must have a stable width")
        norms = [math.sqrt(sum(value * value for value in row)) for row in rows]
        clipped_rows = [clip_l2(row, self.clip_norm) for row in rows]
        pooled = tuple(sum(row[index] for row in clipped_rows) for index in range(width))
        return self._release_clipped_query(
            pooled,
            release_id=release_id,
            scope=scope,
            pre_clip_max_norm=max(norms),
            clipped_contribution_count=sum(
                1 for original, clipped in zip(rows, clipped_rows) if original != clipped
            ),
        )

    def _release_clipped_query(
        self,
        clipped_query: tuple[float, ...],
        *,
        release_id: str,
        scope: SyntheticPrivacyScope,
        pre_clip_max_norm: float,
        clipped_contribution_count: int,
    ) -> GaussianRelease:
        context = json.dumps(
            {
                "release_id": release_id,
                "dimension": len(clipped_query),
                "rho": self.rho,
                "clip_norm": self.clip_norm,
            },
            sort_keys=True,
            separators=(",", ":"),
        )
        noise = tuple(
            self._replay_seed._standard_normal(context, index) * self.noise_stddev
            for index, _value in enumerate(clipped_query)
        )
        return GaussianRelease(
            values=tuple(value + perturbation for value, perturbation in zip(clipped_query, noise)),
            clipped_values=clipped_query,
            noise=noise,
            clip_norm=self.clip_norm,
            rho=self.rho,
            noise_stddev=self.noise_stddev,
            seed_hash=self._replay_seed.seed_hash,
            scope=scope,
            pre_clip_max_norm=pre_clip_max_norm,
            clipped_contribution_count=clipped_contribution_count,
        )
