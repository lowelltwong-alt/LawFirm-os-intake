from __future__ import annotations

from pathlib import Path

from .models import (
    MatterLinkHumanDecision,
    MatterLinkKeyExtractionReport,
    MatterLinkRunExport,
    MatterLinkingClusterReport,
)
from .util import digest_json, load_json, now_iso, write_json


MATTER_LINK_RUN_EXPORT_FILENAME = "matter_link_run_export.json"
MATTER_LINK_RUN_EXPORT_NOTES_FILENAME = "matter_link_run_export.md"

REQUIRED_NEXT_GATES = [
    "orchestrator_owner_review_for_persistent_matter_link_state",
    "human_matter_linking_review_before_identity_or_budget_scope",
    "no_intake_local_persistence_or_cross_bundle_state",
    "exception_lake_owner_review_before_admission",
]


def run_matter_link_run_export(
    *,
    matter_link_key_extraction_report_path: str | Path,
    matter_linking_cluster_report_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[MatterLinkRunExport, Path]:
    key_report_path = Path(matter_link_key_extraction_report_path)
    cluster_report_path = Path(matter_linking_cluster_report_path)
    key_report = MatterLinkKeyExtractionReport.model_validate(load_json(key_report_path))
    cluster_report = MatterLinkingClusterReport.model_validate(load_json(cluster_report_path))
    export = build_matter_link_run_export(
        key_report=key_report,
        cluster_report=cluster_report,
        generated_at=generated_at or now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / MATTER_LINK_RUN_EXPORT_FILENAME, export.model_dump(mode="json"))
    (run_dir / MATTER_LINK_RUN_EXPORT_NOTES_FILENAME).write_text(
        render_matter_link_run_export(export), encoding="utf-8"
    )
    return export, run_dir


def build_matter_link_run_export(
    *,
    key_report: MatterLinkKeyExtractionReport,
    cluster_report: MatterLinkingClusterReport,
    generated_at: str,
    human_link_decisions: list[MatterLinkHumanDecision] | None = None,
) -> MatterLinkRunExport:
    if key_report.status != "matter_link_keys_extracted_for_review":
        raise ValueError("matter link run export requires a reviewable key extraction report")
    if cluster_report.status != "matter_linking_clusters_proposed_for_review":
        raise ValueError("matter link run export requires a reviewable cluster report")
    if (
        cluster_report.source_matter_link_key_extraction_report_id
        != key_report.matter_link_key_extraction_report_id
    ):
        raise ValueError("matter link run export source reports do not match")
    if cluster_report.bundle_id != key_report.bundle_id:
        raise ValueError("matter link run export source bundle IDs do not match")
    export_core = {
        "bundle_id": key_report.bundle_id,
        "key_report_id": key_report.matter_link_key_extraction_report_id,
        "cluster_report_id": cluster_report.matter_linking_cluster_report_id,
        "key_set_ids": [key_set.document_id for key_set in key_report.key_sets],
        "cluster_ids": [proposal.cluster_id for proposal in cluster_report.clusters],
        "decision_ids": [record.decision_id for record in cluster_report.decisions],
    }
    return MatterLinkRunExport(
        matter_link_run_export_id="matter_link_run_export_"
        + digest_json(export_core).removeprefix("sha256:")[:20],
        status="ready_for_orchestrator_candidate_review",
        bundle_id=key_report.bundle_id,
        source_matter_link_key_extraction_report_id=key_report.matter_link_key_extraction_report_id,
        source_matter_linking_cluster_report_id=cluster_report.matter_linking_cluster_report_id,
        key_sets=key_report.key_sets,
        cluster_proposals=cluster_report.clusters,
        decision_records=cluster_report.decisions,
        human_link_decisions=human_link_decisions or [],
        candidate_exception_lake_labels=sorted(
            {
                *key_report.candidate_exception_lake_labels,
                *cluster_report.candidate_exception_lake_labels,
                "cross_bundle_matter_link_state_owner_review_required",
            }
        ),
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=generated_at,
    )


def render_matter_link_run_export(export: MatterLinkRunExport) -> str:
    return "\n".join(
        [
            "# Matter Link Run Export",
            "",
            f"- Export ID: `{export.matter_link_run_export_id}`",
            f"- Bundle ID: `{export.bundle_id}`",
            f"- Candidate key sets: `{len(export.key_sets)}`",
            f"- Candidate cluster proposals: `{len(export.cluster_proposals)}`",
            f"- Replayable decision records: `{len(export.decision_records)}`",
            f"- Human decisions eligible for Orchestrator review: `{len(export.human_link_decisions)}`",
            f"- Prior Orchestrator context consumed: `{export.prior_context_consumed is not None}`",
            "- Boundary: this is immutable intake candidate evidence; Orchestrator owns any persistent state.",
            "",
        ]
    )
