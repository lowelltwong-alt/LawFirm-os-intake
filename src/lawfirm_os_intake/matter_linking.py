from __future__ import annotations

from collections import defaultdict
from itertools import combinations
from pathlib import Path

from .models import (
    MatterClusterProposal,
    MatterLinkDecisionRecord,
    MatterLinkKey,
    MatterLinkKeyExtractionReport,
    MatterLinkKeySet,
    MatterLinkingClusterCheck,
    MatterLinkingClusterReport,
)
from .util import digest_json, load_json, now_iso, write_json


MATTER_CLUSTER_PROPOSALS_FILENAME = "matter_cluster_proposals.json"
MATTER_LINK_DECISIONS_FILENAME = "matter_link_decisions.jsonl"
MATTER_LINKING_CLUSTER_NOTES_FILENAME = "matter_linking_cluster_report.md"

REQUIRED_NEXT_GATES = [
    "human_matter_linking_review",
    "no_budget_amount_until_cluster_and_roles_confirmed",
    "no_matter_opening_without_official_authority",
    "no_lake_or_sqlite_write_from_matter_linking_clusters",
]

BASE_EXCEPTION_LABELS = [
    "matter_link_cluster_candidate",
    "human_matter_linking_confirmation_required",
    "no_matter_identity_asserted",
]

STRONG_KEY_TYPES = {"claim_number", "docket_ref"}
MEDIUM_KEY_TYPES = {
    "policy_number",
    "adjuster_ref",
    "party_pair",
    "employer_employee_pair",
    "email_thread",
    "attachment_identity",
}
WEAK_KEY_TYPES = {"counsel_ref", "incident_date_party", "subsidiary_alias"}


def run_matter_linking_clusters(
    *,
    key_extraction_report_path: str | Path,
    out_dir: str | Path,
    generated_at: str | None = None,
) -> tuple[MatterLinkingClusterReport, Path]:
    source_path = Path(key_extraction_report_path)
    key_report = MatterLinkKeyExtractionReport.model_validate(load_json(source_path))
    report = build_matter_linking_cluster_report(
        key_report=key_report,
        generated_at=generated_at or now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / MATTER_CLUSTER_PROPOSALS_FILENAME, report.model_dump(mode="json"))
    _write_decisions_jsonl(run_dir / MATTER_LINK_DECISIONS_FILENAME, report.decisions)
    (run_dir / MATTER_LINKING_CLUSTER_NOTES_FILENAME).write_text(
        render_matter_linking_cluster_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def build_matter_linking_cluster_report(
    *,
    key_report: MatterLinkKeyExtractionReport,
    generated_at: str,
) -> MatterLinkingClusterReport:
    key_sets = sorted(key_report.key_sets, key=lambda key_set: key_set.document_id)
    decisions = _pairwise_decisions(key_sets)
    clusters = _cluster_proposals(key_sets=key_sets, decisions=decisions)
    checks = _checks(
        key_report=key_report, key_sets=key_sets, decisions=decisions, clusters=clusters
    )
    labels = sorted(
        {
            *BASE_EXCEPTION_LABELS,
            *(
                ["matter_link_ambiguity_requires_review"]
                if any(cluster.disposition != "proposed_link" for cluster in clusters)
                else []
            ),
            *(
                ["matter_link_conflict_requires_review"]
                if any(cluster.ambiguity_class == "conflicted" for cluster in clusters)
                else []
            ),
        }
    )
    status = (
        "blocked_matter_linking_cluster_validation"
        if any(check.status == "failed" for check in checks)
        else "matter_linking_clusters_proposed_for_review"
    )
    report_core = {
        "source_report": key_report.matter_link_key_extraction_report_id,
        "bundle_id": key_report.bundle_id,
        "decision_ids": [decision.decision_id for decision in decisions],
        "cluster_ids": [cluster.cluster_id for cluster in clusters],
    }
    return MatterLinkingClusterReport(
        matter_linking_cluster_report_id=(
            "matter_linking_clusters_" + digest_json(report_core).removeprefix("sha256:")[:16]
        ),
        status=status,
        source_matter_link_key_extraction_report_id=(
            key_report.matter_link_key_extraction_report_id
        ),
        bundle_id=key_report.bundle_id,
        document_count=len(key_sets),
        decision_count=len(decisions),
        cluster_count=len(clusters),
        conflicted_cluster_count=sum(
            1 for cluster in clusters if cluster.ambiguity_class == "conflicted"
        ),
        hold_cluster_count=sum(
            1 for cluster in clusters if cluster.disposition == "hold_for_more_documents"
        ),
        proposed_link_cluster_count=sum(
            1 for cluster in clusters if cluster.disposition == "proposed_link"
        ),
        decisions=decisions,
        clusters=clusters,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        candidate_exception_lake_labels=labels,
        generated_at=generated_at,
    )


def render_matter_linking_cluster_report(report: MatterLinkingClusterReport) -> str:
    lines = [
        "# Matter Linking Cluster Report",
        "",
        f"- Report ID: `{report.matter_linking_cluster_report_id}`",
        f"- Status: `{report.status}`",
        f"- Bundle ID: `{report.bundle_id}`",
        f"- Decisions: `{report.decision_count}`",
        f"- Clusters: `{report.cluster_count}`",
        f"- Conflicted clusters: `{report.conflicted_cluster_count}`",
        "- Boundary: candidate-only cluster proposals; no matter identity asserted.",
        "",
        "## Clusters",
    ]
    for cluster in report.clusters:
        docs = ", ".join(f"`{document_id}`" for document_id in cluster.document_ids)
        lines.append(
            f"- `{cluster.cluster_id}`: {cluster.ambiguity_class}, "
            f"{cluster.disposition}, docs {docs}"
        )
    return "\n".join(lines) + "\n"


def _pairwise_decisions(key_sets: list[MatterLinkKeySet]) -> list[MatterLinkDecisionRecord]:
    decisions: list[MatterLinkDecisionRecord] = []
    for left, right in combinations(key_sets, 2):
        decisions.append(_decide_pair(left, right))
    return sorted(decisions, key=lambda decision: decision.decision_id)


def _decide_pair(left: MatterLinkKeySet, right: MatterLinkKeySet) -> MatterLinkDecisionRecord:
    left_keys = list(left.keys)
    right_keys = list(right.keys)
    if not left_keys or not right_keys:
        return _decision(
            left=left,
            right=right,
            rule_id="R14_insufficient_keys",
            outcome="hold",
            ambiguity_signal="insufficient_keys",
            supporting_keys=[],
            conflicting_keys=[],
            note="At least one document has no extractable matter-link keys.",
        )

    bridge_conflicts = _bridge_conflict_keys(left_keys, right_keys)
    if bridge_conflicts:
        return _decision(
            left=left,
            right=right,
            rule_id="B2_bridge_document_multiple_strong_keys",
            outcome="block",
            ambiguity_signal="bridge_document_matches_multiple_strong_keys",
            supporting_keys=_matching_keys(left_keys, right_keys, key_types=STRONG_KEY_TYPES),
            conflicting_keys=bridge_conflicts,
            note="A document carries multiple strong keys and would bridge distinct clusters.",
        )

    strong_conflicts = _conflicting_keys(left_keys, right_keys, key_types=STRONG_KEY_TYPES)
    same_thread = _matching_keys(left_keys, right_keys, key_types={"email_thread"})
    if same_thread and strong_conflicts:
        return _decision(
            left=left,
            right=right,
            rule_id="R5_thread_drift_strong_key_conflict",
            outcome="block",
            ambiguity_signal="thread_drift",
            supporting_keys=same_thread,
            conflicting_keys=strong_conflicts,
            note="Documents share an email thread but contain conflicting strong keys.",
        )
    if strong_conflicts:
        return _decision(
            left=left,
            right=right,
            rule_id="R1_strong_key_disagreement",
            outcome="split",
            ambiguity_signal="strong_key_disagreement",
            supporting_keys=[],
            conflicting_keys=strong_conflicts,
            note="Strong matter-link keys disagree.",
        )

    matching_strong = _matching_keys(left_keys, right_keys, key_types=STRONG_KEY_TYPES)
    if matching_strong:
        party_conflicts = _conflicting_keys(left_keys, right_keys, key_types={"party_pair"})
        if party_conflicts:
            return _decision(
                left=left,
                right=right,
                rule_id="R3_strong_key_reuse_conflict",
                outcome="block",
                ambiguity_signal="strong_key_reuse_conflict",
                supporting_keys=matching_strong,
                conflicting_keys=party_conflicts,
                note="Same strong key appears with conflicting party-pair context.",
            )
        return _decision(
            left=left,
            right=right,
            rule_id="R2_same_strong_key",
            outcome="merge",
            ambiguity_signal="same_strong_key",
            supporting_keys=[
                *_matching_keys(left_keys, right_keys, key_types=STRONG_KEY_TYPES),
                *_matching_keys(left_keys, right_keys, key_types=MEDIUM_KEY_TYPES),
                *_matching_keys(left_keys, right_keys, key_types=WEAK_KEY_TYPES),
            ],
            conflicting_keys=[],
            note="Documents share a strong matter-link key with no conflicting party context.",
        )

    matching_policy = _matching_keys(left_keys, right_keys, key_types={"policy_number"})
    policy_conflicts = _conflicting_keys(
        left_keys,
        right_keys,
        key_types={"party_pair", "incident_date_party"},
    )
    if matching_policy and policy_conflicts:
        return _decision(
            left=left,
            right=right,
            rule_id="R4_shared_policy_different_claim_context",
            outcome="split",
            ambiguity_signal="shared_policy_different_claim_context",
            supporting_keys=matching_policy,
            conflicting_keys=policy_conflicts,
            note="Policy number is shared infrastructure and claim context differs.",
        )
    if same_thread:
        return _decision(
            left=left,
            right=right,
            rule_id="R6_same_email_thread",
            outcome="merge",
            ambiguity_signal="same_email_thread",
            supporting_keys=same_thread,
            conflicting_keys=[],
            note="Documents share an email thread and no stronger conflict fired.",
        )
    matching_adjuster_ref = _matching_keys(left_keys, right_keys, key_types={"adjuster_ref"})
    if matching_adjuster_ref:
        return _decision(
            left=left,
            right=right,
            rule_id="R7_same_adjuster_ref",
            outcome="merge",
            ambiguity_signal="same_adjuster_ref",
            supporting_keys=matching_adjuster_ref,
            conflicting_keys=[],
            note="Documents share a sender-namespaced adjuster reference.",
        )
    matching_party_pair = _matching_keys(left_keys, right_keys, key_types={"party_pair"})
    if matching_party_pair:
        matching_incident_date = _matching_keys(
            left_keys,
            right_keys,
            key_types={"incident_date_party"},
        )
        if matching_incident_date:
            return _decision(
                left=left,
                right=right,
                rule_id="R8_same_party_pair_and_incident_date",
                outcome="merge",
                ambiguity_signal="same_party_pair_and_incident_date",
                supporting_keys=[*matching_party_pair, *matching_incident_date],
                conflicting_keys=[],
                note="Documents share a party pair and incident/date-of-loss candidate.",
            )
        return _decision(
            left=left,
            right=right,
            rule_id="R9_same_party_pair_without_same_incident_date",
            outcome="hold",
            ambiguity_signal="same_party_pair_without_same_incident_date",
            supporting_keys=matching_party_pair,
            conflicting_keys=[],
            note="Same party pair may represent multiple incidents; hold for review.",
        )
    matching_attachment = _matching_keys(left_keys, right_keys, key_types={"attachment_identity"})
    if matching_attachment:
        return _decision(
            left=left,
            right=right,
            rule_id="R10_same_attachment_identity",
            outcome="merge",
            ambiguity_signal="same_attachment_identity",
            supporting_keys=matching_attachment,
            conflicting_keys=[],
            note="Documents share an exact attachment identity.",
        )
    weak_matches = _matching_keys(left_keys, right_keys, key_types=WEAK_KEY_TYPES)
    if weak_matches:
        return _decision(
            left=left,
            right=right,
            rule_id="R11_weak_key_only",
            outcome="hold",
            ambiguity_signal="weak_key_only",
            supporting_keys=weak_matches,
            conflicting_keys=[],
            note="Only weak matter-link keys agree; hold for more evidence.",
        )
    return _decision(
        left=left,
        right=right,
        rule_id="R0_no_link_key_agreement",
        outcome="hold",
        ambiguity_signal="no_link_key_agreement",
        supporting_keys=[],
        conflicting_keys=[],
        note="No deterministic link key agreement was found.",
    )


def _decision(
    *,
    left: MatterLinkKeySet,
    right: MatterLinkKeySet,
    rule_id: str,
    outcome: str,
    ambiguity_signal: str,
    supporting_keys: list[MatterLinkKey],
    conflicting_keys: list[MatterLinkKey],
    note: str,
) -> MatterLinkDecisionRecord:
    left_id, right_id = sorted([left.document_id, right.document_id])
    key = {
        "left": left_id,
        "right": right_id,
        "rule_id": rule_id,
        "outcome": outcome,
        "supporting_key_ids": sorted({key.key_id for key in supporting_keys}),
        "conflicting_key_ids": sorted({key.key_id for key in conflicting_keys}),
    }
    return MatterLinkDecisionRecord(
        decision_id="matter_link_decision_" + digest_json(key).removeprefix("sha256:")[:20],
        left_document_id=left_id,
        right_document_id=right_id,
        rule_id=rule_id,
        outcome=outcome,  # type: ignore[arg-type]
        ambiguity_signal=ambiguity_signal,
        supporting_key_ids=key["supporting_key_ids"],
        conflicting_key_ids=key["conflicting_key_ids"],
        note=note,
    )


def _cluster_proposals(
    *,
    key_sets: list[MatterLinkKeySet],
    decisions: list[MatterLinkDecisionRecord],
) -> list[MatterClusterProposal]:
    document_ids = [key_set.document_id for key_set in key_sets]
    parent = {document_id: document_id for document_id in document_ids}

    def find(document_id: str) -> str:
        while parent[document_id] != document_id:
            parent[document_id] = parent[parent[document_id]]
            document_id = parent[document_id]
        return document_id

    def union(left: str, right: str) -> None:
        root_left = find(left)
        root_right = find(right)
        if root_left == root_right:
            return
        first, second = sorted([root_left, root_right])
        parent[second] = first

    for decision in decisions:
        if decision.outcome in {"merge", "block"}:
            union(decision.left_document_id, decision.right_document_id)

    by_root: dict[str, list[str]] = defaultdict(list)
    for document_id in document_ids:
        by_root[find(document_id)].append(document_id)

    keys_by_id = {key.key_id: key for key_set in key_sets for key in key_set.keys}
    key_sets_by_document = {key_set.document_id: key_set for key_set in key_sets}
    proposals: list[MatterClusterProposal] = []
    for members in sorted([sorted(values) for values in by_root.values()]):
        member_set = set(members)
        internal_decisions = [
            decision
            for decision in decisions
            if decision.left_document_id in member_set and decision.right_document_id in member_set
        ]
        all_member_keys = [
            key for document_id in members for key in key_sets_by_document[document_id].keys
        ]
        supporting_key_ids = sorted(
            {key_id for decision in internal_decisions for key_id in decision.supporting_key_ids}
        )
        conflicting_key_ids = sorted(
            {
                key_id
                for decision in internal_decisions
                if decision.outcome in {"split", "block"}
                for key_id in decision.conflicting_key_ids
            }
        )
        if not internal_decisions:
            supporting_key_ids = sorted({key.key_id for key in all_member_keys})
        supporting_keys = [
            keys_by_id[key_id] for key_id in supporting_key_ids if key_id in keys_by_id
        ]
        conflicting_keys = [
            keys_by_id[key_id] for key_id in conflicting_key_ids if key_id in keys_by_id
        ]
        blocking_decisions = [
            decision for decision in internal_decisions if decision.outcome in {"split", "block"}
        ]
        ambiguity_class, disposition = _cluster_classification(
            members=members,
            supporting_keys=supporting_keys,
            conflicting_keys=conflicting_keys,
            blocking_decisions=blocking_decisions,
        )
        rule_ids = sorted(
            {decision.rule_id for decision in internal_decisions}
            or ({"single_document_candidate"} if all_member_keys else {"R14_insufficient_keys"})
        )
        decision_ids = sorted(decision.decision_id for decision in internal_decisions)
        cluster_core = {
            "bundle_docs": members,
            "ambiguity_class": ambiguity_class,
            "disposition": disposition,
            "rule_ids": rule_ids,
        }
        proposals.append(
            MatterClusterProposal(
                cluster_id="matter_cluster_"
                + digest_json(cluster_core).removeprefix("sha256:")[:16],
                document_ids=members,
                ambiguity_class=ambiguity_class,
                supporting_keys=supporting_keys,
                conflicting_keys=conflicting_keys,
                disposition=disposition,
                decision_rule_ids=rule_ids,
                decision_ids=decision_ids,
                blocking_decision_ids=sorted(
                    decision.decision_id for decision in blocking_decisions
                ),
            )
        )
    return sorted(proposals, key=lambda proposal: proposal.cluster_id)


def _cluster_classification(
    *,
    members: list[str],
    supporting_keys: list[MatterLinkKey],
    conflicting_keys: list[MatterLinkKey],
    blocking_decisions: list[MatterLinkDecisionRecord],
) -> tuple[str, str]:
    if conflicting_keys or blocking_decisions:
        return "conflicted", "blocked_conflict"
    supporting_types = {key.key_type for key in supporting_keys}
    has_strong = bool(supporting_types & STRONG_KEY_TYPES)
    has_medium = bool(supporting_types & MEDIUM_KEY_TYPES)
    has_weak = bool(supporting_types & WEAK_KEY_TYPES)
    if has_strong and len(supporting_types) >= 2:
        return "corroborated_multi_key", "proposed_link"
    if has_strong:
        return "single_strong_key", "proposed_link"
    if has_medium:
        return "medium_key_only", "hold_for_more_documents"
    if has_weak or members:
        return "weak_key_only", "hold_for_more_documents"
    return "weak_key_only", "hold_for_more_documents"


def _checks(
    *,
    key_report: MatterLinkKeyExtractionReport,
    key_sets: list[MatterLinkKeySet],
    decisions: list[MatterLinkDecisionRecord],
    clusters: list[MatterClusterProposal],
) -> list[MatterLinkingClusterCheck]:
    expected_decisions = len(key_sets) * (len(key_sets) - 1) // 2
    all_keys = [key for key_set in key_sets for key in key_set.keys]
    document_ids = [key_set.document_id for key_set in key_sets]
    clustered_documents = sorted(
        {document_id for cluster in clusters for document_id in cluster.document_ids}
    )
    checks = [
        _check(
            "source_key_extraction_report_ready",
            key_report.status == "matter_link_keys_extracted_for_review",
            "Matter-link clustering consumes only a ready key-extraction report.",
        ),
        _check(
            "all_keys_have_evidence_refs",
            all(key.evidence_refs for key in all_keys),
            "Every key used by clustering has source-bound evidence refs.",
        ),
        _check(
            "pairwise_matrix_complete",
            len(decisions) == expected_decisions,
            "Decision matrix contains one record for every unordered document pair.",
        ),
        _check(
            "cluster_partition_covers_documents_once",
            sorted(document_ids) == clustered_documents
            and sum(len(cluster.document_ids) for cluster in clusters) == len(document_ids),
            "Cluster proposals partition input documents exactly once.",
        ),
        _check(
            "no_sender_identity_keys",
            all(key.key_type != "sender_identity" for key in all_keys),
            "Sender identity is never used as a linking key.",
        ),
        _check(
            "no_budget_conflict_or_matter_authority",
            True,
            "Clustering emits review proposals only and performs no downstream authority action.",
        ),
    ]
    return checks


def _check(
    check_id: str,
    condition: bool,
    message: str,
    *,
    document_ids: list[str] | None = None,
    decision_ids: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> MatterLinkingClusterCheck:
    return MatterLinkingClusterCheck(
        check_id=check_id,
        status="passed" if condition else "failed",
        message=message,
        document_ids=document_ids or [],
        decision_ids=decision_ids or [],
        blocking_refs=blocking_refs or ([] if condition else [check_id]),
    )


def _matching_keys(
    left_keys: list[MatterLinkKey],
    right_keys: list[MatterLinkKey],
    *,
    key_types: set[str],
) -> list[MatterLinkKey]:
    matches: list[MatterLinkKey] = []
    for key_type in sorted(key_types):
        left_by_value = _values_for_type(left_keys, key_type)
        right_by_value = _values_for_type(right_keys, key_type)
        for value in sorted(set(left_by_value) & set(right_by_value)):
            matches.extend(left_by_value[value])
            matches.extend(right_by_value[value])
    return _dedupe_key_objects(matches)


def _conflicting_keys(
    left_keys: list[MatterLinkKey],
    right_keys: list[MatterLinkKey],
    *,
    key_types: set[str],
) -> list[MatterLinkKey]:
    conflicts: list[MatterLinkKey] = []
    for key_type in sorted(key_types):
        left_by_value = _values_for_type(left_keys, key_type)
        right_by_value = _values_for_type(right_keys, key_type)
        if left_by_value and right_by_value and set(left_by_value) != set(right_by_value):
            for value in sorted(set(left_by_value) | set(right_by_value)):
                conflicts.extend(left_by_value.get(value, []))
                conflicts.extend(right_by_value.get(value, []))
    return _dedupe_key_objects(conflicts)


def _bridge_conflict_keys(
    left_keys: list[MatterLinkKey],
    right_keys: list[MatterLinkKey],
) -> list[MatterLinkKey]:
    conflicts: list[MatterLinkKey] = []
    for key_type in sorted(STRONG_KEY_TYPES):
        left_by_value = _values_for_type(left_keys, key_type)
        right_by_value = _values_for_type(right_keys, key_type)
        if len(left_by_value) > 1 and set(left_by_value) & set(right_by_value):
            for keys in left_by_value.values():
                conflicts.extend(keys)
            for value in sorted(set(left_by_value) & set(right_by_value)):
                conflicts.extend(right_by_value[value])
        if len(right_by_value) > 1 and set(right_by_value) & set(left_by_value):
            for keys in right_by_value.values():
                conflicts.extend(keys)
            for value in sorted(set(right_by_value) & set(left_by_value)):
                conflicts.extend(left_by_value[value])
    return _dedupe_key_objects(conflicts)


def _values_for_type(keys: list[MatterLinkKey], key_type: str) -> dict[str, list[MatterLinkKey]]:
    values: dict[str, list[MatterLinkKey]] = defaultdict(list)
    for key in keys:
        if key.key_type == key_type:
            values[key.normalized_value].append(key)
    return values


def _dedupe_key_objects(keys: list[MatterLinkKey]) -> list[MatterLinkKey]:
    by_id = {key.key_id: key for key in keys}
    return [by_id[key_id] for key_id in sorted(by_id)]


def _write_decisions_jsonl(path: Path, decisions: list[MatterLinkDecisionRecord]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(decision.model_dump_json() + "\n" for decision in decisions),
        encoding="utf-8",
    )
