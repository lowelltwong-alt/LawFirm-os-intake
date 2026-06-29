from __future__ import annotations

from .ingestion import validate_ingestion_result
from .models import (
    IngestionResult,
    RustIngestionReadinessCheck,
    RustIngestionReadinessReport,
    SourceBundle,
)
from .rust_transition_policy import RUST_TRANSITION_POLICY_REF, load_rust_transition_policy
from .util import digest_text, new_id, now_iso


def _check(
    check_id: str,
    passed: bool,
    message: str,
    details: dict[str, object] | None = None,
) -> RustIngestionReadinessCheck:
    return RustIngestionReadinessCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        details=details or {},
    )


def _adapter_boundary_check(result: IngestionResult) -> RustIngestionReadinessCheck:
    passed = (
        result.adapter_kind == "python_reference_ingestion_adapter"
        and result.parity_contract == "rust_ready_ingestion_v0_1"
        and result.rust_replacement_allowed is False
    )
    return _check(
        "adapter_boundary_locked",
        passed,
        "Ingestion is still the Python reference oracle; Rust replacement is not authorized.",
        {
            "adapter_kind": result.adapter_kind,
            "parity_contract": result.parity_contract,
            "rust_replacement_allowed": result.rust_replacement_allowed,
        },
    )


def _inventory_coverage_check(
    bundle: SourceBundle, result: IngestionResult
) -> RustIngestionReadinessCheck:
    source_ids = [source.source_id for source in bundle.sources]
    inventory_ids = [item.source_id for item in result.source_inventory]
    missing_ids = sorted(set(source_ids) - set(inventory_ids))
    extra_ids = sorted(set(inventory_ids) - set(source_ids))
    duplicate_inventory_ids = sorted(
        {source_id for source_id in inventory_ids if inventory_ids.count(source_id) > 1}
    )
    passed = not missing_ids and not extra_ids and not duplicate_inventory_ids
    return _check(
        "source_inventory_covers_bundle",
        passed,
        "Source inventory has exactly one row for each source bundle item.",
        {
            "source_count": len(source_ids),
            "inventory_count": len(inventory_ids),
            "missing_source_ids": missing_ids,
            "extra_source_ids": extra_ids,
            "duplicate_inventory_source_ids": duplicate_inventory_ids,
        },
    )


def _inventory_hash_check(
    bundle: SourceBundle, result: IngestionResult
) -> RustIngestionReadinessCheck:
    sources_by_id = {source.source_id: source for source in bundle.sources}
    mismatches: list[dict[str, object]] = []
    for item in result.source_inventory:
        source = sources_by_id.get(item.source_id)
        if source is None:
            continue
        expected_hash = digest_text(source.text)
        if item.source_sha256 != expected_hash or item.character_count != len(source.text):
            mismatches.append(
                {
                    "source_id": item.source_id,
                    "expected_sha256": expected_hash,
                    "actual_sha256": item.source_sha256,
                    "expected_character_count": len(source.text),
                    "actual_character_count": item.character_count,
                }
            )
    return _check(
        "source_inventory_hashes_recomputed",
        not mismatches,
        "Source inventory hashes and character counts recompute from source text.",
        {"mismatches": mismatches},
    )


def _segment_integrity_check(
    bundle: SourceBundle, result: IngestionResult
) -> RustIngestionReadinessCheck:
    sources_by_id = {source.source_id: source for source in bundle.sources}
    issues: list[dict[str, object]] = []
    for segment in result.segments:
        source = sources_by_id.get(segment.source_id)
        if source is None:
            issues.append(
                {
                    "segment_id": segment.segment_id,
                    "issue": "unknown_source_id",
                    "source_id": segment.source_id,
                }
            )
            continue
        if (
            segment.start_offset < 0
            or segment.end_offset < segment.start_offset
            or segment.end_offset > len(source.text)
        ):
            issues.append(
                {
                    "segment_id": segment.segment_id,
                    "issue": "offset_out_of_source_bounds",
                    "source_id": segment.source_id,
                    "start_offset": segment.start_offset,
                    "end_offset": segment.end_offset,
                    "source_length": len(source.text),
                }
            )
        expected_hash = digest_text(segment.text)
        if segment.sha256 != expected_hash:
            issues.append(
                {
                    "segment_id": segment.segment_id,
                    "issue": "segment_hash_mismatch",
                    "expected_sha256": expected_hash,
                    "actual_sha256": segment.sha256,
                }
            )
    return _check(
        "segments_preserve_offsets_and_hashes",
        not issues,
        "Segments stay inside their source bounds and hashes recompute from segment text.",
        {"issues": issues},
    )


def _ingestion_validation_check(result: IngestionResult) -> RustIngestionReadinessCheck:
    try:
        validate_ingestion_result(result)
    except ValueError as exc:
        return _check(
            "segment_evidence_refs_match_segments",
            False,
            "Ingestion result failed deterministic parity validation.",
            {"error": str(exc)},
        )
    return _check(
        "segment_evidence_refs_match_segments",
        True,
        "Every segment evidence ref matches its segment source ID, offsets, and hash.",
    )


def _legal_scope_absence_check(result: IngestionResult) -> RustIngestionReadinessCheck:
    forbidden_fields = [
        "party_candidates",
        "matter_family_candidates",
        "representation_posture_candidates",
        "conflict_search_terms",
        "budget_lines",
        "human_confirmation_required",
    ]
    present = [field for field in forbidden_fields if hasattr(result, field)]
    return _check(
        "legal_scope_absent_from_ingestion_result",
        not present,
        "The Rust-ready ingestion artifact contains no legal classification or decision fields.",
        {"unexpected_fields": present},
    )


def build_rust_ingestion_readiness_report(
    *,
    run_id: str,
    bundle: SourceBundle,
    ingestion_result: IngestionResult,
) -> RustIngestionReadinessReport:
    policy = load_rust_transition_policy()
    checks = [
        _adapter_boundary_check(ingestion_result),
        _inventory_coverage_check(bundle, ingestion_result),
        _inventory_hash_check(bundle, ingestion_result),
        _segment_integrity_check(bundle, ingestion_result),
        _ingestion_validation_check(ingestion_result),
        _legal_scope_absence_check(ingestion_result),
    ]
    status = "failed" if any(check.status == "failed" for check in checks) else "passed"
    return RustIngestionReadinessReport(
        rust_ingestion_readiness_report_id=new_id("rust_ingestion_ready"),
        run_id=run_id,
        ingestion_result_id=ingestion_result.ingestion_result_id,
        bundle_id=ingestion_result.bundle_id,
        status=status,
        current_adapter_kind=ingestion_result.adapter_kind,
        parity_contract=ingestion_result.parity_contract,
        rust_transition_policy_ref=RUST_TRANSITION_POLICY_REF,
        rust_replacement_allowed=ingestion_result.rust_replacement_allowed,
        eligible_hot_path_scope=policy.eligible_hot_path_scope,
        forbidden_rust_scope=policy.forbidden_rust_scope,
        required_parity_dimensions=policy.required_parity_dimensions,
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_rust_ingestion_readiness(report: RustIngestionReadinessReport) -> None:
    if report.status != "passed":
        failures = ", ".join(check.check_id for check in report.checks if check.status == "failed")
        raise ValueError(f"rust ingestion readiness failed: {failures}")
