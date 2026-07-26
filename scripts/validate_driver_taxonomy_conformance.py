"""Conformance gate: intake must not drift from the canonical driver taxonomy.

The intake↔substrate driver drift happened because nothing enforced alignment.
This gate makes re-drift a red build instead of a silent gap:

1. The vendored contract's digest must equal the pin in ``driver_taxonomy.py``
   (an edited or stale vendored copy fails).
2. Every driver in the intake case-sizing policy must be covered by the
   contract's ``legacy_intake_mapping`` (a new sizing driver without a mapping
   fails), and the mapping must not cover phantom keys the policy lacks.
3. Every canonical target in the mapping must exist in the mapped line's driver
   set, with every mapped level valid.

Run: ``python scripts/validate_driver_taxonomy_conformance.py``
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from lawfirm_os_intake.driver_taxonomy import (  # noqa: E402
    EXPECTED_CONTRACT_DIGEST,
    CONTRACT_REF,
    _contract_digest,
    _driver_defs,
    load_driver_taxonomy,
)

SIZING_POLICY_REF = "config/synthetic-case-sizing-policy.yaml"


def run_conformance_checks(
    repo_root: str | Path, *, contract_override: dict[str, Any] | None = None
) -> list[str]:
    """Return a list of human-readable failures; empty means conformant."""

    root = Path(repo_root)
    failures: list[str] = []

    digest = _contract_digest(root / CONTRACT_REF)
    if digest != EXPECTED_CONTRACT_DIGEST:
        failures.append(
            f"vendored contract digest {digest} != pinned {EXPECTED_CONTRACT_DIGEST}; "
            "re-vendor from the substrate and update the pin deliberately"
        )
        return failures

    contract = contract_override if contract_override is not None else load_driver_taxonomy(root)
    mapping = contract["legacy_intake_mapping"]
    mapped_keys = set(mapping["keys"].keys())

    policy = yaml.safe_load((root / SIZING_POLICY_REF).read_text(encoding="utf-8"))
    policy_keys = {d["driver_id"] for d in policy["drivers"]}

    unmapped = policy_keys - mapped_keys
    if unmapped:
        failures.append(f"sizing-policy drivers with no legacy mapping (drift): {sorted(unmapped)}")
    phantom = mapped_keys - policy_keys
    if phantom:
        failures.append(
            f"legacy mapping covers keys absent from the sizing policy: {sorted(phantom)}"
        )

    line_id = mapping["line_id"]
    defs = _driver_defs(contract, line_id)
    for key, spec in mapping["keys"].items():
        if spec["kind"] == "posture_flag_passthrough":
            continue
        canonical = spec["canonical_driver"]
        definition = defs.get(canonical)
        if definition is None:
            failures.append(
                f"mapping for {key!r} targets {canonical!r}, not a driver of {line_id!r}"
            )
            continue
        valid_levels = {level["level"] for level in definition["levels"]}
        targets = (
            set(spec["bands"].values())
            if spec["kind"] == "canonical_banded_int"
            else set(spec["levels"].values())
        )
        bad = targets - valid_levels
        if bad:
            failures.append(
                f"mapping for {key!r} produces invalid levels {sorted(bad)} "
                f"for driver {canonical!r} (valid: {sorted(valid_levels)})"
            )

    return failures


def main() -> int:
    failures = run_conformance_checks(REPO_ROOT)
    if failures:
        print("Driver-taxonomy conformance FAILED:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("Driver-taxonomy conformance passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
