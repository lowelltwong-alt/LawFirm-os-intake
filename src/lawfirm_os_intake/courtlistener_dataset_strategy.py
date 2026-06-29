from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import CourtListenerDatasetStrategyCheck, CourtListenerDatasetStrategyReport
from .rust_transition_policy import RUST_TRANSITION_POLICY_REF, load_rust_transition_policy
from .util import new_id, now_iso, write_json


COURTLISTENER_DATASET_STRATEGY_REF = "config/courtlistener-dataset-strategy.yaml"
COURTLISTENER_DATASET_STRATEGY_REPORT_FILENAME = "courtlistener_dataset_strategy_report.json"
COURTLISTENER_DATASET_STRATEGY_NOTES_FILENAME = "courtlistener_dataset_strategy_report.md"

REQUIRED_ENDPOINT_PATHS = {
    "/search/",
    "/dockets/",
    "/docket-entries/",
    "/recap-documents/",
    "/parties/",
    "/attorneys/",
    "/courts/",
    "/citation-lookup/",
}

REQUIRED_STARTER_MATTER_FAMILIES = {
    "single_plaintiff_employment_discrimination",
    "retaliation",
    "fmla",
    "ada_employment",
    "single_plaintiff_wage_and_hour_flsa",
}

REQUIRED_POSITIVE_DOCUMENT_TYPES = {
    "complaint",
    "summons",
    "notice_of_removal",
    "state_court_complaint_attached_to_notice_of_removal",
    "civil_cover_sheet",
    "answer",
    "early_motion_to_dismiss",
    "initial_scheduling_order",
    "right_to_sue_letter_attached",
    "eeoc_charge_attached",
    "unknown",
}

REQUIRED_NEGATIVE_CASE_STAGES = {
    "post_discovery",
    "dispositive_motion",
    "trial",
    "post_judgment",
    "appellate",
    "unknown",
}

PROHIBITED_POSITIVE_DOCUMENT_TYPES = {
    "interrogatories",
    "requests_for_production",
    "requests_for_admission",
    "deposition_transcripts",
    "expert_reports",
    "summary_judgment_records",
    "trial_exhibits",
    "trial_transcripts",
    "fee_petitions",
    "appellate_briefs",
}

REQUIRED_FALSE_PERMISSIONS = {
    "allow_pacer_purchase",
    "allow_recap_fetch_purchase",
    "allow_uploads",
    "allow_court_writes",
    "allow_sealed_or_restricted_requests",
    "allow_real_client_data",
    "allow_privileged_data",
}

REQUIRED_RUST_SHADOW_SCOPE = {
    "courtlistener_snapshot_normalization",
    "offline_corpus_manifest_indexing",
    "source_hashing",
    "document_label_offset_indexing",
}

REQUIRED_RUST_FORBIDDEN_SCOPE = {
    "legal_classification",
    "party_role_assignment",
    "conflict_clearance",
    "budget_decisioning",
    "training_corpus_admission",
    "public_record_download_or_purchase",
}

REQUIRED_RUST_GATES = {
    "hot_path_performance_profile",
    "python_reference_golden_parity",
    "courtlistener_fixture_no_network",
    "synthetic_fixture_and_holdout_parity",
    "schema_compatibility_export",
    "orchestrator_adapter_review",
}


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"expected YAML mapping: {path}")
    return payload


def _list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value]


def _check(
    check_id: str,
    passed: bool,
    message: str,
    details: dict[str, Any] | None = None,
) -> CourtListenerDatasetStrategyCheck:
    return CourtListenerDatasetStrategyCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        details=details or {},
    )


def _endpoint_paths(config: dict[str, Any]) -> list[str]:
    endpoints = config.get("endpoint_families")
    if not isinstance(endpoints, list):
        return []
    return [str(endpoint.get("path", "")) for endpoint in endpoints if isinstance(endpoint, dict)]


def _source_profile_ids(config: dict[str, Any]) -> list[str]:
    profiles = config.get("source_profiles")
    if not isinstance(profiles, list):
        return []
    return [
        str(profile.get("profile_id", ""))
        for profile in profiles
        if isinstance(profile, dict) and profile.get("profile_id")
    ]


def build_courtlistener_dataset_strategy_report(
    *,
    repo_root: str | Path,
    strategy_config_path: str | Path | None = None,
) -> CourtListenerDatasetStrategyReport:
    root = Path(repo_root)
    config_ref = (
        str(Path(strategy_config_path))
        if strategy_config_path is not None
        else COURTLISTENER_DATASET_STRATEGY_REF
    )
    config_path = (
        Path(strategy_config_path) if strategy_config_path is not None else root / config_ref
    )
    config = _load_yaml(config_path)
    policy = load_rust_transition_policy()

    source_modes = config.get("source_modes", {})
    permissions = config.get("permissions", {})
    practice = config.get("practice_area_strategy", {})
    case_selection = config.get("case_selection", {})
    rust_shadow = config.get("rust_shadow_acceleration", {})

    endpoint_paths = _endpoint_paths(config)
    starter_families = _list(practice.get("starter_matter_families"))
    positive_document_types = _list(config.get("positive_document_types"))
    excluded_positive_document_types = _list(config.get("excluded_positive_document_types"))
    negative_case_stage_labels = _list(config.get("negative_case_stage_labels"))
    source_profile_ids = _source_profile_ids(config)
    rust_shadow_scope = _list(rust_shadow.get("allowed_shadow_scope"))
    rust_forbidden_scope = _list(rust_shadow.get("forbidden_scope"))
    required_rust_gates = _list(rust_shadow.get("required_gates"))

    missing_endpoints = sorted(REQUIRED_ENDPOINT_PATHS - set(endpoint_paths))
    unsafe_permissions = sorted(
        permission
        for permission in REQUIRED_FALSE_PERMISSIONS
        if permissions.get(permission) is not False
    )
    missing_starter_families = sorted(REQUIRED_STARTER_MATTER_FAMILIES - set(starter_families))
    missing_positive_types = sorted(REQUIRED_POSITIVE_DOCUMENT_TYPES - set(positive_document_types))
    positive_stage_leaks = sorted(
        PROHIBITED_POSITIVE_DOCUMENT_TYPES.intersection(positive_document_types)
    )
    missing_negative_stages = sorted(
        REQUIRED_NEGATIVE_CASE_STAGES - set(negative_case_stage_labels)
    )
    missing_rust_shadow_scope = sorted(REQUIRED_RUST_SHADOW_SCOPE - set(rust_shadow_scope))
    missing_rust_forbidden_scope = sorted(REQUIRED_RUST_FORBIDDEN_SCOPE - set(rust_forbidden_scope))
    missing_rust_gates = sorted(REQUIRED_RUST_GATES - set(required_rust_gates))
    missing_policy_scope = sorted(
        {"courtlistener_snapshot_normalization", "offline_corpus_manifest_indexing"}
        - set(policy.candidate_rust_hot_path_scope)
    )

    checks = [
        _check(
            "source_modes_default_offline",
            source_modes.get("offline_fixture_mode") is True
            and source_modes.get("allow_live_calls") is False,
            "CourtListener source mode defaults to offline fixtures with live calls disabled.",
            {
                "offline_fixture_mode": source_modes.get("offline_fixture_mode"),
                "allow_live_calls": source_modes.get("allow_live_calls"),
            },
        ),
        _check(
            "purchasing_uploads_and_court_writes_disabled",
            not unsafe_permissions,
            "PACER purchase, RECAP Fetch purchase, uploads, court writes, sealed requests, real-client data, and privileged data are disabled.",
            {"unsafe_permissions": unsafe_permissions},
        ),
        _check(
            "required_endpoint_families_modeled",
            not missing_endpoints,
            "Required CourtListener endpoint families are modeled before any live adapter.",
            {"missing_endpoint_paths": missing_endpoints},
        ),
        _check(
            "labor_employment_starter_corpus_selected",
            practice.get("primary_practice_area") == "labor_employment"
            and not missing_starter_families,
            "Labor and employment is the first corpus with the required starter matter families.",
            {
                "primary_practice_area": practice.get("primary_practice_area"),
                "missing_starter_matter_families": missing_starter_families,
            },
        ),
        _check(
            "early_case_window_and_negative_routing_declared",
            case_selection.get("first_docket_days_min") == 90
            and case_selection.get("first_docket_days_max") == 120
            and not missing_positive_types
            and not positive_stage_leaks
            and not missing_negative_stages,
            "The strategy keeps positive intake examples in the first 90-120 days and routes later-stage documents as negative/routing examples.",
            {
                "missing_positive_document_types": missing_positive_types,
                "prohibited_positive_document_types_present": positive_stage_leaks,
                "missing_negative_case_stage_labels": missing_negative_stages,
            },
        ),
        _check(
            "removal_state_pleadings_proxy_profile_present",
            "courtlistener_removal_state_pleadings_proxy" in source_profile_ids,
            "The removal-packet state-court starter pleading proxy is explicitly declared.",
            {"source_profile_ids": source_profile_ids},
        ),
        _check(
            "rust_shadow_acceleration_governed",
            rust_shadow.get("no_rust_runtime_added") is True
            and rust_shadow.get("rust_replacement_allowed") is False
            and not missing_rust_shadow_scope
            and not missing_rust_forbidden_scope
            and not missing_rust_gates
            and not missing_policy_scope,
            "Rust remains shadow-only for deterministic corpus mechanics and is covered by transition gates.",
            {
                "missing_rust_shadow_scope": missing_rust_shadow_scope,
                "missing_rust_forbidden_scope": missing_rust_forbidden_scope,
                "missing_rust_gates": missing_rust_gates,
                "missing_policy_scope": missing_policy_scope,
            },
        ),
        _check(
            "no_runtime_side_effects_or_training_claims",
            True,
            "The audit performs no public ingestion, no live calls, no connector writes, no Lake/SQLite writes, no Rust runtime creation, and no training pipeline creation.",
        ),
    ]
    status = (
        "blocked_courtlistener_dataset_strategy"
        if any(check.status == "failed" for check in checks)
        else "ready_for_human_dataset_strategy_review"
    )

    return CourtListenerDatasetStrategyReport(
        courtlistener_dataset_strategy_report_id=new_id("courtlistenerdataset"),
        status=status,
        strategy_config_ref=config_ref,
        rust_transition_policy_ref=RUST_TRANSITION_POLICY_REF,
        source_id=str(config.get("source_id", "")),
        base_url=str(config.get("base_url", "")),
        token_env_var=str(config.get("token_env_var", "")),
        offline_fixture_mode=source_modes.get("offline_fixture_mode") is True,
        allow_live_calls=source_modes.get("allow_live_calls") is True,
        endpoint_paths=endpoint_paths,
        primary_practice_area=practice.get("primary_practice_area"),
        starter_matter_families=starter_families,
        positive_document_types=positive_document_types,
        excluded_positive_document_types=excluded_positive_document_types,
        negative_case_stage_labels=negative_case_stage_labels,
        source_profile_ids=source_profile_ids,
        rust_shadow_scope=rust_shadow_scope,
        rust_forbidden_scope=rust_forbidden_scope,
        required_rust_gates=required_rust_gates,
        pacer_purchase_allowed=permissions.get("allow_pacer_purchase") is True,
        recap_fetch_purchase_allowed=permissions.get("allow_recap_fetch_purchase") is True,
        uploads_allowed=permissions.get("allow_uploads") is True,
        court_writes_allowed=permissions.get("allow_court_writes") is True,
        sealed_or_restricted_requests_allowed=(
            permissions.get("allow_sealed_or_restricted_requests") is True
        ),
        real_client_data_allowed=permissions.get("allow_real_client_data") is True,
        privileged_data_allowed=permissions.get("allow_privileged_data") is True,
        checks=checks,
        generated_at=now_iso(),
    )


def render_courtlistener_dataset_strategy_report(
    report: CourtListenerDatasetStrategyReport,
) -> str:
    lines = [
        "# CourtListener Dataset Strategy Report",
        "",
        f"**Report ID:** {report.courtlistener_dataset_strategy_report_id}",
        f"**Status:** {report.status}",
        f"**Config:** `{report.strategy_config_ref}`",
        f"**Rust policy:** `{report.rust_transition_policy_ref}`",
        "",
        "## Boundary",
        "",
        f"- Offline fixture mode: {report.offline_fixture_mode}",
        f"- Live calls allowed: {report.allow_live_calls}",
        f"- PACER purchase allowed: {report.pacer_purchase_allowed}",
        f"- RECAP Fetch purchase allowed: {report.recap_fetch_purchase_allowed}",
        f"- Uploads allowed: {report.uploads_allowed}",
        f"- Court writes allowed: {report.court_writes_allowed}",
        f"- Real-client data allowed: {report.real_client_data_allowed}",
        f"- Rust runtime added: {report.rust_runtime_added}",
        f"- Rust replacement allowed: {report.rust_replacement_allowed}",
        f"- Training pipeline created: {report.training_pipeline_created}",
        "",
        "## Corpus",
        "",
        f"- Primary practice area: {report.primary_practice_area}",
        "- Starter matter families:",
        *(f"  - {family}" for family in report.starter_matter_families),
        "",
        "## Rust Shadow Scope",
        "",
        *(f"- {item}" for item in report.rust_shadow_scope),
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.extend([f"- `{check.check_id}`: {check.status}", f"  {check.message}"])
        failed_details = {
            key: value for key, value in check.details.items() if isinstance(value, list) and value
        }
        for key, value in failed_details.items():
            lines.append(f"  - {key}: {', '.join(str(item) for item in value)}")
    lines.extend(
        [
            "",
            "This report is a planning and governance artifact only. It does not ingest public "
            "records, make live calls, create a training pipeline, add a Rust runtime, or "
            "authorize conflicts, matter opening, budget approval, or learning promotion.",
            "",
        ]
    )
    return "\n".join(lines)


def run_courtlistener_dataset_strategy_audit(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    strategy_config_path: str | Path | None = None,
) -> tuple[CourtListenerDatasetStrategyReport, Path]:
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report = build_courtlistener_dataset_strategy_report(
        repo_root=repo_root,
        strategy_config_path=strategy_config_path,
    )
    report_path = run_dir / COURTLISTENER_DATASET_STRATEGY_REPORT_FILENAME
    notes_path = run_dir / COURTLISTENER_DATASET_STRATEGY_NOTES_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    notes_path.write_text(render_courtlistener_dataset_strategy_report(report), encoding="utf-8")
    return report, run_dir
