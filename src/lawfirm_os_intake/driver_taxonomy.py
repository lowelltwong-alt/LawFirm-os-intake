"""Budget-driver-taxonomy@v1 adapter — intake ↔ substrate reconciliation.

The canonical driver taxonomy lives in the semantic-substrate repo
(``docs/poc/budget-driver-taxonomy.v1.candidate.json``) and is vendored here as a
byte-pinned copy (``config/budget-driver-taxonomy.v1.json``). This module:

1. **Loads the contract fail-closed** — the vendored copy's sha256 (with newline
   normalization) must equal ``EXPECTED_CONTRACT_DIGEST``; any drift refuses.
2. **Maps the legacy sizing drivers onto the canonical set** — intake's 5 drivers
   (``party_count``, ``injury_severity``, ``liability_clarity``, ``exposure_band``,
   ``venue``) become canonical assignments via the contract's
   ``legacy_intake_mapping``; unknown keys or level values are fail-closed errors.
3. **Makes every un-elicited canonical driver an explicit assumption** — a
   ``not_elicited`` assignment with a rule-attributed assumption note (neutral
   multiplier 1.0), never a silent default. Required-but-missing drivers raise the
   existing ``missing_required_budget_driver`` exception trigger (typed for review,
   not auto-blocked).

Candidate-only, synthetic-only; ``reference_class_only``; dollars stay
deterministic from governed rates. The conformance gate
(``scripts/validate_driver_taxonomy_conformance.py``) fails the build if intake's
sizing-driver set ever diverges from the pinned contract again.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .models import CanonicalDriverAssignment, CanonicalDriverProfile
from .util import digest_json

CONTRACT_REF = "config/budget-driver-taxonomy.v1.json"
EXPECTED_CONTRACT_DIGEST = "4fd1f971b46f8983f8bac0f9b81cb2310f69a3853c9d2adb2ea3e227d3403185"

_NOT_ELICITED_NOTE = (
    "not elicited at intake; neutral multiplier 1.0 applied as a rule-attributed "
    "assumption per budget-driver-taxonomy@1.0.0-candidate"
)


def _contract_digest(path: Path) -> str:
    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return hashlib.sha256(raw).hexdigest()


def load_driver_taxonomy(
    repo_root: str | Path, *, contract_path: str | Path | None = None
) -> dict[str, Any]:
    """Load the vendored canonical driver contract, digest-pinned fail-closed."""

    path = Path(contract_path) if contract_path is not None else Path(repo_root) / CONTRACT_REF
    digest = _contract_digest(path)
    if digest != EXPECTED_CONTRACT_DIGEST:
        raise ValueError(
            "budget-driver-taxonomy contract digest mismatch: expected "
            f"{EXPECTED_CONTRACT_DIGEST}, found {digest}; refusing to load a "
            "drifted or tampered contract"
        )
    contract = json.loads(path.read_text(encoding="utf-8"))
    if contract.get("status") != "candidate" or contract.get("candidate_only") is not True:
        raise ValueError("driver taxonomy contract must be candidate-only")
    if contract.get("calibrated") is not False:
        raise ValueError("driver taxonomy contract must not claim calibration")
    if contract.get("contains_real_firm_data") is not False:
        raise ValueError("real firm data is prohibited in the driver taxonomy contract")
    return contract


def line_driver_ids(contract: dict[str, Any], line_id: str) -> list[str]:
    """Canonical driver ids for a line: universal (minus overridden) + line drivers."""

    line = contract["lines"][line_id]
    overridden = set(line.get("universal_overrides", {}).keys())
    universal = [
        d["driver_id"] for d in contract["universal_drivers"] if d["driver_id"] not in overridden
    ]
    return universal + [d["driver_id"] for d in line["drivers"]]


def _driver_defs(contract: dict[str, Any], line_id: str) -> dict[str, dict[str, Any]]:
    line = contract["lines"][line_id]
    overridden = set(line.get("universal_overrides", {}).keys())
    defs: dict[str, dict[str, Any]] = {
        d["driver_id"]: d for d in contract["universal_drivers"] if d["driver_id"] not in overridden
    }
    for d in line["drivers"]:
        defs[d["driver_id"]] = d
    return defs


def _band_party_count(value: Any, bands: dict[str, str]) -> str:
    count = int(value)
    if count < 1:
        raise ValueError(f"party_count must be >= 1, got {count}")
    if count == 1:
        return bands["1"]
    if count <= 3:
        return bands["2_3"]
    return bands["4_plus"]


def build_canonical_driver_profile(
    legacy_sizing_drivers: dict[str, Any],
    *,
    repo_root: str | Path,
    line_id: str = "medical_malpractice_defense",
) -> CanonicalDriverProfile:
    """Map legacy sizing drivers onto the canonical set, fail-closed."""

    contract = load_driver_taxonomy(repo_root)
    mapping = contract["legacy_intake_mapping"]
    if mapping["line_id"] != line_id:
        raise ValueError(
            f"legacy mapping is declared for line {mapping['line_id']!r}, not {line_id!r}"
        )
    defs = _driver_defs(contract, line_id)

    elicited: dict[str, CanonicalDriverAssignment] = {}
    posture_flags: dict[str, str] = {}

    for key, raw_value in legacy_sizing_drivers.items():
        spec = mapping["keys"].get(key)
        if spec is None:
            raise ValueError(f"unknown legacy sizing driver {key!r}; refusing to drop it silently")
        kind = spec["kind"]
        if kind == "posture_flag_passthrough":
            posture_flags[key] = str(raw_value)
            continue
        if kind == "canonical_banded_int":
            level = _band_party_count(raw_value, spec["bands"])
        elif kind == "canonical_level_map":
            levels = spec["levels"]
            if str(raw_value) not in levels:
                raise ValueError(
                    f"legacy driver {key!r} has unknown level {raw_value!r}; "
                    f"known levels: {sorted(levels)}"
                )
            level = levels[str(raw_value)]
        else:
            raise ValueError(f"unknown legacy mapping kind {kind!r}")
        canonical_id = spec["canonical_driver"]
        definition = defs.get(canonical_id)
        if definition is None:
            raise ValueError(
                f"legacy mapping targets {canonical_id!r} which is not a driver of {line_id!r}"
            )
        elicited[canonical_id] = CanonicalDriverAssignment(
            driver_id=canonical_id,
            layer=definition["layer"],
            level=level,
            status="elicited",
            source="legacy_mapping",
            mapping_note=spec.get("note", ""),
        )

    assignments: list[CanonicalDriverAssignment] = []
    required_missing: list[str] = []
    for driver_id in line_driver_ids(contract, line_id):
        if driver_id in elicited:
            assignments.append(elicited[driver_id])
            continue
        definition = defs[driver_id]
        assignments.append(
            CanonicalDriverAssignment(
                driver_id=driver_id,
                layer=definition["layer"],
                status="not_elicited",
                assumption_note=_NOT_ELICITED_NOTE,
            )
        )
        if definition.get("required", False):
            required_missing.append(driver_id)

    not_elicited_ids = [a.driver_id for a in assignments if a.status == "not_elicited"]
    basis = {
        "line_id": line_id,
        "contract_digest": EXPECTED_CONTRACT_DIGEST,
        "assignments": [(a.driver_id, a.status, a.level) for a in assignments],
        "posture_flags": posture_flags,
    }
    profile_id = "driverprofile-" + digest_json(basis).removeprefix("sha256:")[:16]
    return CanonicalDriverProfile(
        profile_id=profile_id,
        line_id=line_id,
        contract_id=contract["contract_id"],
        contract_version=contract["version"],
        contract_digest=EXPECTED_CONTRACT_DIGEST,
        assignments=assignments,
        posture_flags=posture_flags,
        not_elicited_driver_ids=not_elicited_ids,
        required_missing_driver_ids=required_missing,
        exception_candidates=(["missing_required_budget_driver"] if required_missing else []),
    )
