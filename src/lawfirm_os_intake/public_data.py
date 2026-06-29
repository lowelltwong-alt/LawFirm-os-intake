from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


PUBLIC_DATA_CATALOG_REF = "examples/public/catalog.yaml"
PUBLIC_DATA_POLICY_REF = "config/data_policy.yaml"
PUBLIC_EXAMPLES_ALLOWED_FILES = {"README.md", "catalog.yaml"}
FORBIDDEN_CATALOG_FIELDS = {
    "bulk_dataset_path",
    "case_document",
    "content",
    "document_text",
    "download_path",
    "downloaded_path",
    "local_path",
    "party_records",
    "payload",
    "raw_payload",
    "text",
}


def _yaml_dict(path: Path, failures: list[str]) -> dict[str, Any]:
    if not path.is_file():
        failures.append(f"missing:{path}")
        return {}
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        failures.append(f"invalid_yaml:{path}")
        return {}
    if not isinstance(payload, dict):
        failures.append(f"not_mapping:{path}")
        return {}
    return payload


def validate_public_data_boundary(repo_root: str | Path) -> tuple[bool, dict[str, Any]]:
    root = Path(repo_root)
    failures: list[str] = []
    catalog_path = root / PUBLIC_DATA_CATALOG_REF
    policy_path = root / PUBLIC_DATA_POLICY_REF
    public_dir = root / "examples/public"
    catalog = _yaml_dict(catalog_path, failures)
    policy = _yaml_dict(policy_path, failures)

    unexpected_public_files = []
    if public_dir.is_dir():
        unexpected_public_files = sorted(
            str(path.relative_to(public_dir))
            for path in public_dir.rglob("*")
            if path.is_file()
            and str(path.relative_to(public_dir)) not in PUBLIC_EXAMPLES_ALLOWED_FILES
        )
    else:
        failures.append("missing_public_examples_dir")
    if unexpected_public_files:
        failures.append("public_examples_contains_non_catalog_files")

    posture = policy.get("public_data_posture") if isinstance(policy, dict) else None
    if policy.get("runtime_mode") != "synthetic_only":
        failures.append("policy_runtime_mode_not_synthetic_only")
    allowed_origins = policy.get("allowed_data_origins")
    if not isinstance(allowed_origins, list) or set(allowed_origins) != {"synthetic"}:
        failures.append("policy_allows_non_synthetic_origin")
    if not isinstance(posture, dict):
        failures.append("policy_public_data_posture_missing")
        posture = {}
    if posture.get("status") != "planning_only":
        failures.append("policy_public_data_not_planning_only")
    if posture.get("direct_ingestion_allowed") is not False:
        failures.append("policy_direct_ingestion_allowed")

    sources = catalog.get("sources") if isinstance(catalog, dict) else None
    if catalog.get("status") != "planning_only":
        failures.append("catalog_not_planning_only")
    if not isinstance(sources, list) or not sources:
        failures.append("catalog_sources_missing")
        sources = []

    ingesting_sources: list[str] = []
    incomplete_sources: list[str] = []
    sources_with_payload_fields: list[str] = []
    for source in sources:
        if not isinstance(source, dict):
            failures.append("catalog_source_not_mapping")
            continue
        source_id = str(source.get("source_id", "unknown"))
        if source.get("direct_runtime_ingestion") is not False:
            ingesting_sources.append(source_id)
        if not source.get("source_id") or not source.get("url") or not source.get("useful_for"):
            incomplete_sources.append(source_id)
        if FORBIDDEN_CATALOG_FIELDS.intersection(source):
            sources_with_payload_fields.append(source_id)

    if ingesting_sources:
        failures.append("catalog_source_allows_direct_runtime_ingestion")
    if incomplete_sources:
        failures.append("catalog_source_metadata_incomplete")
    if sources_with_payload_fields:
        failures.append("catalog_source_contains_payload_field")

    details: dict[str, Any] = {
        "catalog_ref": PUBLIC_DATA_CATALOG_REF,
        "policy_ref": PUBLIC_DATA_POLICY_REF,
        "source_count": len(sources),
        "unexpected_public_files": unexpected_public_files,
        "direct_ingestion_source_ids": ingesting_sources,
        "incomplete_source_ids": incomplete_sources,
        "payload_field_source_ids": sources_with_payload_fields,
        "failures": failures,
    }
    return not failures, details
