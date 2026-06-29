from __future__ import annotations

from .models import DataScopeGateCheck, DataScopeGateReport, SourceBundle
from .util import new_id, now_iso


DATA_POLICY_REF = "config/data_policy.yaml#synthetic_only"
PUBLIC_DATA_POLICY_REF = "config/data_policy.yaml#public_data_posture"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    policy_refs: list[str] | None = None,
) -> DataScopeGateCheck:
    return DataScopeGateCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        policy_refs=policy_refs or [DATA_POLICY_REF],
    )


def build_data_scope_gate_report(run_id: str, bundle: SourceBundle) -> DataScopeGateReport:
    checks = [
        _check(
            "data_origin_is_synthetic",
            bundle.data_origin == "synthetic",
            "Starter runtime accepts synthetic source bundles only.",
            [DATA_POLICY_REF],
        ),
        _check(
            "no_real_client_data_flag",
            bundle.contains_real_client_data is False,
            "Source bundle must not contain real client data.",
            [DATA_POLICY_REF],
        ),
        _check(
            "no_real_matter_data_flag",
            bundle.contains_real_matter_data is False,
            "Source bundle must not contain real matter data.",
            [DATA_POLICY_REF],
        ),
        _check(
            "no_privileged_data_flag",
            bundle.contains_privileged_data is False,
            "Source bundle must not contain privileged material.",
            [DATA_POLICY_REF],
        ),
        _check(
            "public_reference_not_runtime_ingested",
            bundle.data_origin != "public_reference",
            "Public-reference data is catalog/planning-only and cannot enter this runtime.",
            [PUBLIC_DATA_POLICY_REF],
        ),
    ]
    failed = [check.check_id for check in checks if check.status == "failed"]
    status = "blocked" if failed else "passed"
    blocked_state = "data_scope_gate_failed" if failed else None
    return DataScopeGateReport(
        data_scope_gate_report_id=new_id("datascope"),
        run_id=run_id,
        bundle_id=bundle.bundle_id,
        status=status,
        blocked_state=blocked_state,
        data_origin=bundle.data_origin,
        contains_real_client_data=bundle.contains_real_client_data,
        contains_real_matter_data=bundle.contains_real_matter_data,
        contains_privileged_data=bundle.contains_privileged_data,
        source_count=len(bundle.sources),
        policy_refs=[DATA_POLICY_REF, PUBLIC_DATA_POLICY_REF],
        checks=checks,
        generated_at=now_iso(),
    )


def enforce_data_scope_gate_report(report: DataScopeGateReport) -> None:
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    if report.status != "passed":
        failed.append(report.blocked_state or "data_scope_gate_status")
    if report.raw_payload_written is not False:
        failed.append("raw_payload_written")
    if report.external_writes_performed is not False:
        failed.append("external_writes_performed")
    if report.public_data_direct_ingestion_allowed is not False:
        failed.append("public_data_direct_ingestion_allowed")
    if report.non_authoritative is not True:
        failed.append("non_authoritative")
    if not failed:
        return
    raise ValueError("data scope gate failed: " + ", ".join(failed))
