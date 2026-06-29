#!/usr/bin/env python3
"""Validate the local mirror of the upstream LawFirm OS governance dependency map."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
MIRROR = ROOT / ".ai" / "control" / "governance-dependency-map-mirror.json"
EXPECTED_OWNER_REPO = "LawFirm-os-intake"

REQUIRED_TOP_LEVEL = {
    "object_type",
    "trust_zone",
    "lifecycle_status",
    "provenance_note",
    "reason_for_inclusion",
    "schema_version",
    "mirror_id",
    "owner_repo",
    "upstream_dependency_map",
    "local_enforcement",
    "authority",
    "watched_local_governance_surfaces",
    "required_behavior",
}

REQUIRED_UPSTREAM = {
    "repo": "LawFirm-os-semantic-substrate",
    "path": "registry/governance-dependency-map.json",
    "artifact_id": "LFGD-008",
    "rule": "governance_map_update_gate",
    "source_of_truth": True,
}

REQUIRED_WATCHED = {
    ".ai/control/governance-dependency-map-mirror.json",
    ".github/workflows/",
    "AGENTS.md",
    "AI_TABLE_OF_CONTENTS.md",
    "AI_WORK_START_HERE.md",
    "GOVERNANCE_BOUNDARY.md",
    "README.md",
    "contracts.lock.json",
    "repo_topology.yaml",
    "scripts/validate_governance_dependency_map_mirror.py",
    "skill-agent-manifest.json",
    "tests/test_governance_dependency_map_mirror.py",
    "workflow/",
}

REQUIRED_SURFACE_PHRASES = {
    "AI_WORK_START_HERE.md": [
        "governance dependency-map mirror",
        ".ai/control/governance-dependency-map-mirror.json",
        "registry/governance-dependency-map.json",
    ],
    "AI_TABLE_OF_CONTENTS.md": [
        ".ai/control/governance-dependency-map-mirror.json",
        "scripts/validate_governance_dependency_map_mirror.py",
        "upstream governance dependency map",
    ],
    "GOVERNANCE_BOUNDARY.md": [
        ".ai/control/governance-dependency-map-mirror.json",
        "upstream governance dependency map",
    ],
    "README.md": [
        ".ai/control/governance-dependency-map-mirror.json",
        "upstream governance dependency map",
    ],
}


class MirrorValidationError(ValueError):
    """Raised when the local governance dependency-map mirror is invalid."""


def _rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def _normalize_path(path: str) -> str:
    normalized = path.replace("\\", "/")
    if normalized.startswith("./"):
        return normalized[2:]
    return normalized


def _matches_path_rule(path: str, rule: str) -> bool:
    path = _normalize_path(path)
    rule = _normalize_path(rule)
    if rule.endswith("/") or rule.endswith("_"):
        return path.startswith(rule)
    return path == rule


def _read_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise MirrorValidationError(f"{_rel(path)} unreadable: {exc}") from exc
    if not isinstance(data, dict):
        raise MirrorValidationError(f"{_rel(path)} must be a JSON object")
    return data


def _require_strings(data: dict[str, Any], key: str, label: str) -> list[str]:
    value = data.get(key)
    if not isinstance(value, list) or not value:
        raise MirrorValidationError(f"{label}.{key} must be a non-empty list")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise MirrorValidationError(f"{label}.{key} must contain only non-empty strings")
    return value


def validate_governance_dependency_map_mirror(path: Path = MIRROR) -> dict[str, Any]:
    data = _read_json(path)
    missing = sorted(REQUIRED_TOP_LEVEL - set(data))
    if missing:
        raise MirrorValidationError(f"{_rel(path)} missing keys: {missing}")
    if data["object_type"] != "governance_dependency_map_mirror":
        raise MirrorValidationError(
            f"{_rel(path)} object_type must be governance_dependency_map_mirror"
        )
    if data["schema_version"] != "governance_dependency_map_mirror.v1":
        raise MirrorValidationError(
            f"{_rel(path)} schema_version must be governance_dependency_map_mirror.v1"
        )
    if data["owner_repo"] != EXPECTED_OWNER_REPO:
        raise MirrorValidationError(f"{_rel(path)} owner_repo must be {EXPECTED_OWNER_REPO}")

    upstream = data["upstream_dependency_map"]
    if not isinstance(upstream, dict):
        raise MirrorValidationError(f"{_rel(path)} upstream_dependency_map must be an object")
    for key, expected in REQUIRED_UPSTREAM.items():
        if upstream.get(key) != expected:
            raise MirrorValidationError(
                f"{_rel(path)} upstream_dependency_map.{key} must be {expected!r}"
            )

    authority = data["authority"]
    if not isinstance(authority, dict):
        raise MirrorValidationError(f"{_rel(path)} authority must be an object")
    false_keys = (
        "local_repo_may_override_upstream_dependency_map",
        "local_repo_may_weaken_upstream_governance",
        "local_repo_may_treat_local_convenience_as_governance_authority",
        "local_repo_may_define_canonical_schema_route_event_or_taxonomy_authority",
        "local_repo_may_ingest_real_client_or_matter_data",
        "local_repo_may_make_conflict_conclusions",
        "local_repo_may_approve_or_submit_budgets",
        "local_repo_may_open_matters_or_authorize_engagement",
        "local_repo_may_authorize_external_writes_or_production_automation",
    )
    for key in false_keys:
        if authority.get(key) is not False:
            raise MirrorValidationError(f"{_rel(path)} authority.{key} must be false")
    if authority.get("local_repo_must_stop_if_upstream_map_conflicts") is not True:
        raise MirrorValidationError(
            f"{_rel(path)} authority.local_repo_must_stop_if_upstream_map_conflicts must be true"
        )

    watched = set(_require_strings(data, "watched_local_governance_surfaces", _rel(path)))
    missing_watched = sorted(REQUIRED_WATCHED - watched)
    if missing_watched:
        raise MirrorValidationError(f"{_rel(path)} missing watched surfaces: {missing_watched}")

    enforcement = data["local_enforcement"]
    if not isinstance(enforcement, dict):
        raise MirrorValidationError(f"{_rel(path)} local_enforcement must be an object")
    for rel in enforcement.values():
        if (
            isinstance(rel, str)
            and rel.endswith((".json", ".md", ".py", ".yml", ".yaml"))
            and not (ROOT / rel).exists()
        ):
            raise MirrorValidationError(
                f"{_rel(path)} references missing local enforcement surface: {rel}"
            )

    for rel, phrases in REQUIRED_SURFACE_PHRASES.items():
        text = (ROOT / rel).read_text(encoding="utf-8")
        missing_phrases = [phrase for phrase in phrases if phrase not in text]
        if missing_phrases:
            raise MirrorValidationError(f"{rel} missing phrase(s): {missing_phrases}")

    return data


def _git_changed_files(base_ref: str) -> list[str]:
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", f"{base_ref}...HEAD"],
            cwd=ROOT,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except subprocess.CalledProcessError as exc:
        raise MirrorValidationError(
            f"could not compute changed files against {base_ref}: {exc.stderr.strip()}"
        ) from exc
    return [line.strip() for line in result.stdout.splitlines() if line.strip()]


def validate_changed_path_gate(
    *,
    changed_files: list[str],
    mirror_path: Path = MIRROR,
    mirror_updated: bool | None = None,
) -> None:
    data = validate_governance_dependency_map_mirror(mirror_path)
    watched_rules = tuple(data["watched_local_governance_surfaces"])
    normalized = [_normalize_path(path) for path in changed_files]
    watched_changed = [
        path for path in normalized if any(_matches_path_rule(path, rule) for rule in watched_rules)
    ]
    if mirror_updated is None:
        mirror_updated = _rel(mirror_path) in normalized
    if watched_changed and not mirror_updated:
        raise MirrorValidationError(
            "governance dependency-map mirror must be updated when watched governance paths change: "
            + ", ".join(watched_changed)
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-ref", default="origin/main")
    parser.add_argument("--changed-file", action="append", default=[])
    parser.add_argument("--mirror-updated", choices=["true", "false"], default=None)
    args = parser.parse_args(argv)

    try:
        validate_governance_dependency_map_mirror()
        mirror_updated = None if args.mirror_updated is None else args.mirror_updated == "true"
        if args.changed_file:
            changed_files = args.changed_file
        elif mirror_updated is True:
            changed_files = [_rel(MIRROR)]
        else:
            changed_files = _git_changed_files(args.base_ref)
        validate_changed_path_gate(changed_files=changed_files, mirror_updated=mirror_updated)
    except MirrorValidationError as exc:
        print(f"Governance dependency-map mirror validation failed: {exc}", file=sys.stderr)
        return 1
    print("Governance dependency-map mirror validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
