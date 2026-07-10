"""Local synthetic zCDP JSONL scaffold with hash-chain consistency checks."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from hashlib import sha256
import json
import math
import os
from pathlib import Path
from typing import Any

from .dp_mechanism import SyntheticPrivacyScope


SYNTHETIC_RESET_POLICY_PLACEHOLDER = (
    "synthetic_placeholder_no_production_reset_or_parameter_policy_authorized"
)
_GENESIS_HASH = "sha256:genesis"


class ZCDPBudgetExceeded(ValueError):
    """Raised before a ledger write would exceed the configured synthetic cap."""


@dataclass(frozen=True, slots=True)
class ZCDPReport:
    rho: float
    delta: float
    epsilon: float
    formula: str = "epsilon = rho + 2 * sqrt(rho * log(1/delta))"
    formal_production_privacy_claimed: bool = False


def zcdp_to_epsilon_delta(rho: float, delta: float) -> ZCDPReport:
    if not math.isfinite(rho) or rho < 0:
        raise ValueError("rho must be finite and non-negative")
    if not math.isfinite(delta) or not 0 < delta < 1:
        raise ValueError("delta must be strictly between zero and one")
    return ZCDPReport(rho=rho, delta=delta, epsilon=rho + 2 * math.sqrt(rho * math.log(1 / delta)))


class ZCDPLedger:
    """Local JSONL accountant; sequential composition is sum(rho).

    Group privacy uses the Bun-Steinke bound: a group of size ``k`` consumes
    ``k**2 * rho``. Reset and parameter-selection policy remains an explicitly
    unresolved synthetic placeholder, never a production authorization. The
    file is not an authority-owned, transactional, or tamper-resistant ledger.
    """

    def __init__(
        self,
        path: str | Path,
        *,
        rho_cap: float,
        scope: SyntheticPrivacyScope,
        ledger_id: str = "synthetic-zcdp-ledger",
        policy_label: str = "Synthetic policy placeholder for CAL-DP tests only",
    ) -> None:
        if not math.isfinite(rho_cap) or rho_cap <= 0:
            raise ValueError("rho_cap must be finite and positive")
        if not isinstance(scope, SyntheticPrivacyScope):
            raise TypeError("scope must be a SyntheticPrivacyScope")
        if not ledger_id or not isinstance(ledger_id, str):
            raise ValueError("ledger_id must be a non-empty string")
        if "synthetic policy placeholder" not in policy_label.lower():
            raise ValueError("zCDP ledger policy must remain a synthetic policy placeholder")
        self.path = Path(path)
        self.rho_cap = float(rho_cap)
        self.scope = scope
        self.ledger_id = ledger_id
        self.policy_label = policy_label
        self.reset_policy = SYNTHETIC_RESET_POLICY_PLACEHOLDER
        self.policy_digest = self._policy_digest()
        self._entries = self._load_and_validate()
        if self.consumed_rho > self.rho_cap:
            raise ValueError("existing ledger consumption exceeds the configured rho cap")

    @property
    def entries(self) -> tuple[dict[str, Any], ...]:
        return tuple(self._entries)

    @property
    def consumed_rho(self) -> float:
        return sum(float(entry["effective_rho"]) for entry in self._entries)

    @property
    def remaining_rho(self) -> float:
        return self.rho_cap - self.consumed_rho

    def report(self, delta: float) -> ZCDPReport:
        return zcdp_to_epsilon_delta(self.consumed_rho, delta)

    def append(
        self,
        *,
        release_id: str,
        rho: float,
        group_size: int = 1,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        if not isinstance(release_id, str) or not release_id:
            raise ValueError("release_id must be a non-empty string")
        if not math.isfinite(rho) or rho <= 0:
            raise ValueError("rho must be finite and positive")
        if not isinstance(group_size, int) or isinstance(group_size, bool) or group_size < 1:
            raise ValueError("group_size must be a positive integer")
        if created_at is not None and (not isinstance(created_at, str) or not created_at):
            raise ValueError("created_at must be a non-empty string when supplied")
        self._entries = self._load_and_validate()
        if any(entry["release_id"] == release_id for entry in self._entries):
            raise ValueError("ledger already contains this release_id")
        effective_rho = float(rho) * group_size**2
        if self.consumed_rho + effective_rho > self.rho_cap:
            raise ZCDPBudgetExceeded("zCDP rho cap exhausted; refusing before ledger write")
        payload: dict[str, Any] = {
            "sequence": len(self._entries) + 1,
            "ledger_id": self.ledger_id,
            "policy_digest": self.policy_digest,
            "rho_cap": self.rho_cap,
            "release_id": release_id,
            "rho": float(rho),
            "group_size": group_size,
            "effective_rho": effective_rho,
            "composition": "sequential_sum_rho",
            "group_privacy": "bun_steinke_k_squared_rho",
            "scope": asdict(self.scope),
            "reset_policy": self.reset_policy,
            "created_at": created_at or datetime.now(UTC).replace(microsecond=0).isoformat(),
            "previous_hash": self._entries[-1]["entry_hash"] if self._entries else _GENESIS_HASH,
        }
        entry = {**payload, "entry_hash": self._hash_entry(payload)}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        encoded = json.dumps(entry, sort_keys=True, separators=(",", ":")) + "\n"
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(encoded)
            handle.flush()
            os.fsync(handle.fileno())
        self._entries.append(entry)
        return entry

    def _load_and_validate(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        entries: list[dict[str, Any]] = []
        previous_hash = _GENESIS_HASH
        with self.path.open("r", encoding="utf-8") as handle:
            for expected_sequence, line in enumerate(handle, start=1):
                if not line.strip():
                    raise ValueError("ledger contains a blank line")
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError("ledger contains invalid JSON") from exc
                if not isinstance(entry, dict) or entry.get("sequence") != expected_sequence:
                    raise ValueError("ledger sequence validation failed")
                if entry.get("previous_hash") != previous_hash:
                    raise ValueError("ledger hash chain validation failed")
                supplied_hash = entry.get("entry_hash")
                payload = {key: value for key, value in entry.items() if key != "entry_hash"}
                if supplied_hash != self._hash_entry(payload):
                    raise ValueError("ledger entry hash validation failed")
                if entry.get("scope") != asdict(self.scope):
                    raise ValueError("ledger scope does not match synthetic-only scope")
                if entry.get("ledger_id") != self.ledger_id:
                    raise ValueError("ledger_id does not match the configured synthetic ledger")
                if entry.get("policy_digest") != self.policy_digest:
                    raise ValueError("ledger policy digest does not match the configured policy")
                if entry.get("rho_cap") != self.rho_cap:
                    raise ValueError("ledger rho cap does not match the configured policy")
                if entry.get("reset_policy") != self.reset_policy:
                    raise ValueError("ledger reset policy is not the synthetic placeholder")
                self._validate_accounting_entry(entry)
                previous_hash = supplied_hash
                entries.append(entry)
        return entries

    @staticmethod
    def _validate_accounting_entry(entry: dict[str, Any]) -> None:
        rho = entry.get("rho")
        group_size = entry.get("group_size")
        effective_rho = entry.get("effective_rho")
        if (
            not isinstance(entry.get("release_id"), str)
            or not entry["release_id"]
            or isinstance(rho, bool)
            or not isinstance(rho, (int, float))
            or not math.isfinite(rho)
            or rho <= 0
            or not isinstance(group_size, int)
            or isinstance(group_size, bool)
            or group_size < 1
            or isinstance(effective_rho, bool)
            or not isinstance(effective_rho, (int, float))
            or not math.isfinite(effective_rho)
            or not math.isclose(effective_rho, rho * group_size**2, rel_tol=0.0, abs_tol=0.0)
        ):
            raise ValueError("ledger accounting entry validation failed")
        if entry.get("composition") != "sequential_sum_rho":
            raise ValueError("ledger composition is not sequential zCDP composition")
        if entry.get("group_privacy") != "bun_steinke_k_squared_rho":
            raise ValueError("ledger group privacy is not Bun-Steinke k-squared rho")

    @staticmethod
    def _hash_entry(payload: dict[str, Any]) -> str:
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":"))
        return "sha256:" + sha256(encoded.encode("utf-8")).hexdigest()

    def _policy_digest(self) -> str:
        payload = {
            "ledger_id": self.ledger_id,
            "policy_label": self.policy_label,
            "rho_cap": self.rho_cap,
            "scope": asdict(self.scope),
            "reset_policy": self.reset_policy,
            "group_privacy": "bun_steinke_k_squared_rho",
            "composition": "sequential_sum_rho",
        }
        return self._hash_entry(payload)
