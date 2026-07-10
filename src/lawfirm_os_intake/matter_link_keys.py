from __future__ import annotations

from pathlib import Path
import re
import unicodedata
from typing import Any

import yaml

from .models import (
    EntityComparisonResult,
    EntityNormalizationResult,
    EvidenceRef,
    MatterLinkKey,
    MatterLinkKeyExtractionCheck,
    MatterLinkKeyExtractionReport,
    MatterLinkKeySet,
    SourceBundle,
    SourceItem,
)
from .util import digest_json, digest_text, load_json, now_iso, write_json


DEFAULT_MATTER_LINK_POLICY_PATH = Path("config/matter-link-policy.yaml")
MATTER_LINK_KEY_EXTRACTION_REPORT_FILENAME = "matter_link_key_extraction_report.json"
MATTER_LINK_KEY_EXTRACTION_NOTES_FILENAME = "matter_link_key_extraction_report.md"

REQUIRED_NEXT_GATES = [
    "human_matter_linking_review",
    "no_budget_amount_until_cluster_and_roles_confirmed",
    "no_matter_opening_without_official_authority",
    "no_lake_or_sqlite_write_from_matter_link_keys",
]

BASE_EXCEPTION_LABELS = [
    "matter_link_key_extraction_candidate",
    "human_matter_linking_confirmation_required",
    "no_matter_identity_asserted",
]


def run_matter_link_key_extraction(
    *,
    input_path: str | Path,
    out_dir: str | Path,
    policy_path: str | Path = DEFAULT_MATTER_LINK_POLICY_PATH,
    generated_at: str | None = None,
) -> tuple[MatterLinkKeyExtractionReport, Path]:
    source_path = Path(input_path)
    policy_ref = Path(policy_path)
    bundle = SourceBundle.model_validate(load_json(source_path))
    policy = load_matter_link_policy(policy_ref)
    report = build_matter_link_key_extraction_report(
        bundle=bundle,
        policy=policy,
        policy_ref=str(policy_ref),
        generated_at=generated_at or now_iso(),
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / MATTER_LINK_KEY_EXTRACTION_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / MATTER_LINK_KEY_EXTRACTION_NOTES_FILENAME).write_text(
        render_matter_link_key_extraction_report(report),
        encoding="utf-8",
    )
    return report, run_dir


def load_matter_link_policy(policy_path: str | Path) -> dict[str, Any]:
    payload = yaml.safe_load(Path(policy_path).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("matter-link policy must be a YAML object")
    if payload.get("status") != "local_candidate":
        raise ValueError("matter-link policy must remain local_candidate")
    if payload.get("candidate_only") is not True:
        raise ValueError("matter-link policy must be candidate_only=true")
    if payload.get("contains_real_firm_data") is not False:
        raise ValueError("matter-link policy must declare contains_real_firm_data=false")
    if payload.get("external_writes_authorized") is not False:
        raise ValueError("matter-link policy must not authorize external writes")
    if not isinstance(payload.get("extraction_rules"), list):
        raise ValueError("matter-link policy requires extraction_rules")
    if not isinstance(payload.get("entity_normalization"), dict):
        raise ValueError("matter-link policy requires entity_normalization")
    _validate_entity_edges(payload["entity_normalization"])
    return payload


def build_matter_link_key_extraction_report(
    *,
    bundle: SourceBundle,
    policy: dict[str, Any],
    policy_ref: str,
    generated_at: str,
) -> MatterLinkKeyExtractionReport:
    _validate_entity_edges(_entity_normalization_policy(policy))
    key_sets = [
        extract_matter_link_keys_for_source(
            source=source, bundle_id=bundle.bundle_id, policy=policy
        )
        for source in bundle.sources
    ]
    checks = _checks(bundle=bundle, policy=policy, key_sets=key_sets)
    status = (
        "blocked_matter_link_key_extraction"
        if any(check.status == "failed" for check in checks)
        else "matter_link_keys_extracted_for_review"
    )
    labels = sorted(
        {
            *BASE_EXCEPTION_LABELS,
            *(
                ["matter_link_key_extraction_gap"]
                if any(key_set.extraction_gaps for key_set in key_sets)
                else []
            ),
        }
    )
    report_core = {
        "bundle_id": bundle.bundle_id,
        "document_ids": [key_set.document_id for key_set in key_sets],
        "key_count": sum(len(key_set.keys) for key_set in key_sets),
        "policy_sha256": digest_json(policy),
    }
    return MatterLinkKeyExtractionReport(
        matter_link_key_extraction_report_id=(
            "matter_link_key_extraction_" + digest_json(report_core).removeprefix("sha256:")[:16]
        ),
        status=status,
        bundle_id=bundle.bundle_id,
        policy_ref=policy_ref,
        policy_sha256=digest_json(policy),
        document_count=len(key_sets),
        key_count=sum(len(key_set.keys) for key_set in key_sets),
        key_sets=key_sets,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        candidate_exception_lake_labels=labels,
        generated_at=generated_at,
    )


def extract_matter_link_keys_for_source(
    *,
    source: SourceItem,
    bundle_id: str,
    policy: dict[str, Any],
) -> MatterLinkKeySet:
    keys: list[MatterLinkKey] = []
    gaps: list[str] = []
    sender_identity = _sender_identity(source)
    text = source.text or ""
    if not text:
        gaps.append("source_text_empty_or_unreadable")
    for rule in _extraction_rules(policy):
        flags = re.IGNORECASE
        if rule.get("multiline"):
            flags |= re.MULTILINE
        pattern = re.compile(str(rule["pattern"]), flags=flags)
        for match in pattern.finditer(text):
            span = _captured_value_span(match, text)
            if span is None:
                continue
            start_offset, end_offset, raw_value = span
            normalized_value = normalize_key_value(
                key_type=str(rule["key_type"]),
                raw_value=raw_value,
                sender_identity=sender_identity,
                policy=policy,
            )
            evidence_ref = EvidenceRef(
                source_id=source.source_id,
                segment_id=f"{source.source_id}:source_text",
                start_offset=start_offset,
                end_offset=end_offset,
                sha256=digest_text(text[start_offset:end_offset]),
            )
            key_core = {
                "source_id": source.source_id,
                "key_type": str(rule["key_type"]),
                "normalized_value": normalized_value,
                "start_offset": start_offset,
                "end_offset": end_offset,
                "extraction_rule_id": str(rule["rule_id"]),
            }
            keys.append(
                MatterLinkKey(
                    key_id="matter_link_key_" + digest_json(key_core).removeprefix("sha256:")[:20],
                    key_type=rule["key_type"],
                    raw_value=raw_value,
                    normalized_value=normalized_value,
                    tier=rule["tier"],
                    evidence_refs=[evidence_ref],
                    extraction_rule_id=str(rule["rule_id"]),
                )
            )
    if not keys and "source_text_empty_or_unreadable" not in gaps:
        gaps.append("no_extractable_link_keys")
    return MatterLinkKeySet(
        document_id=source.source_id,
        bundle_id=bundle_id,
        sender_identity=sender_identity,
        keys=_dedupe_keys(keys),
        extraction_gaps=sorted(gaps),
    )


def normalize_key_value(
    *,
    key_type: str,
    raw_value: str,
    sender_identity: str,
    policy: dict[str, Any],
) -> str:
    value = raw_value.strip().strip(".,;:")
    normalization = policy.get("key_type_normalization", {})
    if key_type in set(normalization.get("compact_upper", [])):
        return _compact(value).upper()
    if key_type in set(normalization.get("compact_casefold", [])):
        return _compact(value).casefold()
    if key_type in set(normalization.get("sender_namespaced_compact_upper", [])):
        return f"{_sender_namespace(sender_identity)}|{_compact(value).upper()}"
    if key_type == "party_pair":
        return _normalize_named_pair(
            value,
            separator=" and claimant ",
            left_label="insured_or_employer",
            right_label="claimant_or_employee",
            policy=policy,
        )
    if key_type == "employer_employee_pair":
        return _normalize_named_pair(
            value,
            separator=" and employee ",
            left_label="insured_or_employer",
            right_label="claimant_or_employee",
            policy=policy,
        )
    if key_type in set(normalization.get("entity_like", [])):
        return normalize_entity_name(value, policy).base_value
    return _compact(value).casefold()


def normalize_entity_name(raw_value: str, policy: dict[str, Any]) -> EntityNormalizationResult:
    config = _entity_normalization_policy(policy)
    value = unicodedata.normalize("NFC", raw_value).casefold()
    value = value.replace("&", " and ")
    value = re.sub(r"[.,'\"()/-]", " ", value)
    tokens = [token for token in re.sub(r"\s+", " ", value).strip().split(" ") if token]
    rewrites_applied: list[str] = []
    rewrites = {str(key): str(value) for key, value in config.get("token_rewrites", {}).items()}
    rewritten_tokens: list[str] = []
    for token in tokens:
        replacement = rewrites.get(token, token)
        if replacement != token:
            rewrites_applied.append(f"{token}->{replacement}")
        rewritten_tokens.append(replacement)
    normalized_value = " ".join(rewritten_tokens)
    suffixes = set(_normalized_suffixes(config.get("legal_suffixes", [])))
    suffix_stripped = None
    base_tokens = list(rewritten_tokens)
    if base_tokens and base_tokens[-1] in suffixes:
        suffix_stripped = base_tokens[-1]
        base_tokens = base_tokens[:-1]
    base_value = " ".join(base_tokens) or normalized_value
    return EntityNormalizationResult(
        raw_value=raw_value,
        normalized_value=normalized_value,
        base_value=base_value,
        suffix_stripped=suffix_stripped,
        rewrites_applied=rewrites_applied,
        residual_terms_stripped=[],
        normalization_rule_ids=[
            "N1_unicode_nfc_casefold",
            "N2_punctuation_whitespace",
            "N3_end_legal_suffix_strip_recorded",
            "N4_declared_token_rewrites",
        ],
    )


def compare_entity_names(
    left_raw: str,
    right_raw: str,
    policy: dict[str, Any],
) -> EntityComparisonResult:
    left = normalize_entity_name(left_raw, policy)
    right = normalize_entity_name(right_raw, policy)
    if left_raw == right_raw:
        return _comparison(
            left=left,
            right=right,
            comparison_rung="E1_exact",
            outcome="match",
            disposition="raw_exact",
            decision_rule_ids=["E1_exact_raw_match"],
        )
    if left.normalized_value == right.normalized_value:
        return _comparison(
            left=left,
            right=right,
            comparison_rung="E2_normalized_exact",
            outcome="match",
            disposition="normalized_exact",
            decision_rule_ids=["E2_normalized_exact"],
        )
    declared_edge = _declared_entity_edge(left=left, right=right, policy=policy)
    if declared_edge is not None:
        edge_id = str(declared_edge["edge_id"])
        relationship_type = str(declared_edge["relationship_type"])
        status = str(declared_edge["status"])
        if relationship_type == "alias":
            if status == "reviewed_local_candidate":
                return _comparison(
                    left=left,
                    right=right,
                    comparison_rung="E3_declared_alias",
                    outcome="match",
                    disposition="declared_alias",
                    decision_rule_ids=[f"E3_declared_alias:{edge_id}"],
                )
            return _comparison(
                left=left,
                right=right,
                comparison_rung="E4_declared_structure",
                outcome="hold",
                disposition="unreviewed_structure_edge",
                decision_rule_ids=[f"H4_unreviewed_alias_edge:{edge_id}"],
            )
        if status == "reviewed_local_candidate":
            return _comparison(
                left=left,
                right=right,
                comparison_rung="E4_declared_structure",
                outcome="related",
                disposition="related_distinct",
                decision_rule_ids=[f"E4_declared_structure:{relationship_type}:{edge_id}"],
            )
        return _comparison(
            left=left,
            right=right,
            comparison_rung="E4_declared_structure",
            outcome="hold",
            disposition="unreviewed_structure_edge",
            decision_rule_ids=[f"H4_unreviewed_structure_edge:{edge_id}"],
        )
    if left.base_value == right.base_value:
        if (
            left.suffix_stripped
            and right.suffix_stripped
            and left.suffix_stripped != right.suffix_stripped
        ):
            return _comparison(
                left=left,
                right=right,
                comparison_rung="E5_suffix_residual",
                outcome="hold",
                disposition="suffix_conflict",
                decision_rule_ids=["H2_suffix_conflict"],
            )
        return _comparison(
            left=left,
            right=right,
            comparison_rung="E2_normalized_exact",
            outcome="match",
            disposition="normalized_exact",
            decision_rule_ids=["E2_one_sided_or_same_suffix_exact"],
        )
    if _is_possible_affiliate(left.base_value, right.base_value, policy):
        return _comparison(
            left=left,
            right=right,
            comparison_rung="E5_suffix_residual",
            outcome="hold",
            disposition="possible_affiliate",
            decision_rule_ids=["H3_prefix_residual_possible_affiliate"],
        )
    return _comparison(
        left=left,
        right=right,
        comparison_rung="E6_no_match",
        outcome="no_match",
        disposition="no_match",
        decision_rule_ids=["E6_no_similarity_or_acronym_inference"],
    )


def render_matter_link_key_extraction_report(report: MatterLinkKeyExtractionReport) -> str:
    failed = [check for check in report.checks if check.status == "failed"]
    lines = [
        "# Matter Link Key Extraction Report",
        "",
        f"- Report ID: `{report.matter_link_key_extraction_report_id}`",
        f"- Status: `{report.status}`",
        f"- Bundle ID: `{report.bundle_id}`",
        f"- Documents: `{report.document_count}`",
        f"- Keys: `{report.key_count}`",
        f"- Failed checks: `{len(failed)}`",
        "- Boundary: candidate-only, synthetic-only, no clustering, no matter identity asserted.",
        "",
        "## Documents",
    ]
    for key_set in report.key_sets:
        lines.append(f"- `{key_set.document_id}`: {len(key_set.keys)} key(s)")
        for gap in key_set.extraction_gaps:
            lines.append(f"  - gap: `{gap}`")
    return "\n".join(lines) + "\n"


def _comparison(
    *,
    left: EntityNormalizationResult,
    right: EntityNormalizationResult,
    comparison_rung: str,
    outcome: str,
    disposition: str,
    decision_rule_ids: list[str],
) -> EntityComparisonResult:
    return EntityComparisonResult(
        left=left,
        right=right,
        comparison_rung=comparison_rung,
        outcome=outcome,
        disposition=disposition,
        decision_rule_ids=decision_rule_ids,
        review_required=outcome == "hold",
        alias_proposal_required=disposition == "possible_affiliate",
    )


def _checks(
    *,
    bundle: SourceBundle,
    policy: dict[str, Any],
    key_sets: list[MatterLinkKeySet],
) -> list[MatterLinkKeyExtractionCheck]:
    checks: list[MatterLinkKeyExtractionCheck] = []
    checks.append(
        _check(
            "source_bundle_is_synthetic",
            bundle.data_origin == "synthetic"
            and not bundle.contains_real_client_data
            and not bundle.contains_real_matter_data
            and not bundle.contains_privileged_data,
            "Source bundle is synthetic and carries no real client, matter, or privileged flags.",
            document_ids=[source.source_id for source in bundle.sources],
        )
    )
    checks.append(
        _check(
            "policy_candidate_only_no_writes",
            policy.get("status") == "local_candidate"
            and policy.get("candidate_only") is True
            and policy.get("contains_real_firm_data") is False
            and policy.get("external_writes_authorized") is False,
            "Matter-link policy remains local candidate config with no external-write authority.",
        )
    )
    keys = [key for key_set in key_sets for key in key_set.keys]
    checks.append(
        _check(
            "all_extracted_keys_have_evidence_refs",
            all(key.evidence_refs for key in keys),
            "Every extracted key has at least one source-bound evidence ref.",
            key_ids=[key.key_id for key in keys if not key.evidence_refs],
        )
    )
    checks.append(
        _check(
            "sender_identity_not_emitted_as_key",
            all(key.key_type != "sender_identity" for key in keys),
            "Sender identity is recorded only as namespace/context, never as a linking key.",
        )
    )
    checks.append(
        _check(
            "no_clustering_or_identity_assertion",
            True,
            "This stage extracts candidate keys only; it does not cluster or assert matter identity.",
        )
    )
    checks.append(
        _check(
            "no_fuzzy_or_acronym_inference",
            True,
            "Entity normalization uses closed deterministic rules only.",
        )
    )
    checks.append(
        _check(
            "no_external_lake_or_sqlite_writes",
            True,
            "The extractor writes only local run artifacts under the requested output directory.",
        )
    )
    return checks


def _check(
    check_id: str,
    condition: bool,
    message: str,
    *,
    document_ids: list[str] | None = None,
    key_ids: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> MatterLinkKeyExtractionCheck:
    return MatterLinkKeyExtractionCheck(
        check_id=check_id,
        status="passed" if condition else "failed",
        message=message,
        document_ids=document_ids or [],
        key_ids=key_ids or [],
        blocking_refs=blocking_refs or ([] if condition else [check_id]),
    )


def _extraction_rules(policy: dict[str, Any]) -> list[dict[str, Any]]:
    rules = policy.get("extraction_rules", [])
    return [rule for rule in rules if isinstance(rule, dict)]


def _entity_normalization_policy(policy: dict[str, Any]) -> dict[str, Any]:
    config = policy.get("entity_normalization", {})
    if not isinstance(config, dict):
        raise ValueError("matter-link policy entity_normalization must be an object")
    return config


def _validate_entity_edges(config: dict[str, Any]) -> None:
    edges = config.get("alias_edges", [])
    if not isinstance(edges, list):
        raise ValueError("matter-link policy alias_edges must be a list")
    seen_ids: set[str] = set()
    reviewed_directed: dict[str, dict[str, set[str]]] = {}
    allowed_relationships = {
        "alias",
        "subsidiary_of",
        "staffing_agency_for",
        "peo_of",
        "franchise_of",
        "insured_dba",
    }
    for edge in edges:
        if not isinstance(edge, dict):
            raise ValueError("matter-link policy alias edge must be an object")
        edge_id = edge.get("edge_id")
        left = edge.get("left")
        right = edge.get("right")
        relationship = edge.get("relationship_type")
        status = edge.get("status")
        if not all(isinstance(value, str) and value.strip() for value in (edge_id, left, right)):
            raise ValueError("matter-link policy alias edge requires edge_id, left, and right")
        if edge_id in seen_ids:
            raise ValueError("matter-link policy alias edge IDs must be unique")
        seen_ids.add(edge_id)
        if relationship not in allowed_relationships:
            raise ValueError("matter-link policy alias edge has unsupported relationship_type")
        if status not in {"reviewed_local_candidate", "proposed"}:
            raise ValueError(
                "matter-link policy alias edge must be reviewed_local_candidate or proposed"
            )
        left_normalized = normalize_entity_name(left, {"entity_normalization": config}).base_value
        right_normalized = normalize_entity_name(right, {"entity_normalization": config}).base_value
        if left_normalized == right_normalized:
            raise ValueError("matter-link policy alias edge cannot self-reference")
        if relationship != "alias" and status == "reviewed_local_candidate":
            reviewed_directed.setdefault(relationship, {}).setdefault(left_normalized, set()).add(
                right_normalized
            )
    for relationship, graph in reviewed_directed.items():
        if _has_directed_cycle(graph):
            raise ValueError(
                f"matter-link policy reviewed {relationship} edges cannot contain a cycle"
            )


def _has_directed_cycle(graph: dict[str, set[str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        for neighbor in graph.get(node, set()):
            if visit(neighbor):
                return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in graph)


def _declared_entity_edge(
    *,
    left: EntityNormalizationResult,
    right: EntityNormalizationResult,
    policy: dict[str, Any],
) -> dict[str, Any] | None:
    config = _entity_normalization_policy(policy)
    candidates: list[dict[str, Any]] = []
    for edge in config.get("alias_edges", []):
        if not isinstance(edge, dict):
            continue
        edge_left = normalize_entity_name(str(edge["left"]), policy).base_value
        edge_right = normalize_entity_name(str(edge["right"]), policy).base_value
        if {edge_left, edge_right} == {left.base_value, right.base_value}:
            candidates.append(edge)
    if not candidates:
        return None
    return sorted(candidates, key=lambda edge: str(edge["edge_id"]))[0]


def _captured_value_span(match: re.Match[str], text: str) -> tuple[int, int, str] | None:
    if "value" not in match.groupdict():
        return None
    raw = match.group("value")
    if raw is None:
        return None
    stripped = raw.strip()
    if not stripped:
        return None
    leading = len(raw) - len(raw.lstrip())
    trailing = len(raw) - len(raw.rstrip())
    start = match.start("value") + leading
    end = match.end("value") - trailing
    if end <= start:
        return None
    return start, end, text[start:end]


def _sender_identity(source: SourceItem) -> str:
    metadata = source.metadata
    for key in ("from", "sender", "sender_email"):
        value = metadata.get(key)
        if isinstance(value, str) and value.strip():
            return _normalize_sender(value)
    match = re.search(r"(?im)^From:\s*(?P<sender>[^\n]+)", source.text or "")
    if match:
        return _normalize_sender(match.group("sender"))
    return "unknown_sender"


def _normalize_sender(value: str) -> str:
    match = re.search(r"[\w.+-]+@[\w.-]+", value)
    if match:
        return match.group(0).casefold()
    return re.sub(r"\s+", " ", value.casefold()).strip() or "unknown_sender"


def _sender_namespace(sender_identity: str) -> str:
    if "@" in sender_identity:
        return sender_identity.split("@", maxsplit=1)[1]
    return sender_identity


def _compact(value: str) -> str:
    return re.sub(r"[-. /#]", "", value.strip())


def _normalize_named_pair(
    raw_value: str,
    *,
    separator: str,
    left_label: str,
    right_label: str,
    policy: dict[str, Any],
) -> str:
    normalized = raw_value.casefold()
    if separator not in normalized:
        return normalize_entity_name(raw_value, policy).base_value
    left_raw, right_raw = re.split(re.escape(separator), raw_value, maxsplit=1, flags=re.IGNORECASE)
    left = normalize_entity_name(left_raw, policy).base_value
    right = normalize_entity_name(right_raw, policy).base_value
    return f"{left_label}={left}|{right_label}={right}"


def _normalized_suffixes(values: list[Any]) -> list[str]:
    suffixes: list[str] = []
    for value in values:
        suffix = re.sub(r"[.,'\"()&/-]", " ", str(value).casefold())
        suffix = re.sub(r"\s+", " ", suffix).strip()
        if suffix:
            suffixes.append(suffix)
    return suffixes


def _is_possible_affiliate(left_base: str, right_base: str, policy: dict[str, Any]) -> bool:
    left_tokens = left_base.split()
    right_tokens = right_base.split()
    if _has_prefix_residual(shorter=left_tokens, longer=right_tokens):
        return True
    if _has_prefix_residual(shorter=right_tokens, longer=left_tokens):
        return True
    residuals = [
        str(value).casefold()
        for value in _entity_normalization_policy(policy).get(
            "residual_vocabulary",
            [],
        )
    ]
    return (
        _strip_residual_terms(left_base, residuals) == right_base
        or _strip_residual_terms(
            right_base,
            residuals,
        )
        == left_base
    )


def _has_prefix_residual(*, shorter: list[str], longer: list[str]) -> bool:
    if len(longer) <= len(shorter):
        return False
    if longer[: len(shorter)] != shorter:
        return False
    return len(longer) - len(shorter) >= 2


def _strip_residual_terms(value: str, residuals: list[str]) -> str:
    stripped = value
    for residual in sorted(residuals, key=len, reverse=True):
        stripped = re.sub(rf"\b{re.escape(residual)}\b", " ", stripped)
    return re.sub(r"\s+", " ", stripped).strip()


def _dedupe_keys(keys: list[MatterLinkKey]) -> list[MatterLinkKey]:
    deduped: dict[tuple[str, str, int, int, str], MatterLinkKey] = {}
    for key in keys:
        ref = key.evidence_refs[0]
        deduped[
            (key.key_type, key.normalized_value, ref.start_offset, ref.end_offset, ref.sha256)
        ] = key
    return [deduped[key] for key in sorted(deduped)]
