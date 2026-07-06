from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import (
    SkillsRegistrySpecialistCandidate,
    SkillsRegistrySpecialistReviewCheck,
    SkillsRegistrySpecialistReviewReport,
)
from .util import append_jsonl, digest_text, load_json, now_iso, write_json


SKILLS_REGISTRY_SPECIALIST_REVIEW_REPORT_FILENAME = "skills_registry_specialist_review_report.json"
SKILLS_REGISTRY_SPECIALIST_REVIEW_NOTES_FILENAME = "skills_registry_specialist_review_report.md"
SKILLS_REGISTRY_SPECIALIST_CANDIDATES_FILENAME = "skills_registry_specialist_candidates.jsonl"
SKILLS_REGISTRY_SPECIALIST_PACKET_DIRNAME = "skills_registry_specialist_packets"

DEFAULT_MANIFEST_REF = "skill-agent-manifest.json"
DEFAULT_PROMPT_REGISTRY_REF = "prompts/registry.yaml"
TARGET_REPO = "LawFirm-os-skills-registry"
ALLOWED_WRITE_SCOPES = {"none", "local_run_artifacts_only", "local_proposal_only"}
TOOL_DENYLIST = [
    "network",
    "external_write",
    "production_connector",
    "email_write",
    "billing_write",
    "carrier_portal_write",
    "court_write",
    "conflicts_write",
    "matter_opening_write",
]
REQUIRED_NEXT_GATES = [
    "skills_registry_owner_review",
    "prompt_hash_review",
    "tool_authority_review",
    "eval_suite_review_before_promotion",
    "revocation_path_review",
    "no_skill_promotion_from_intake",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return payload


def _repo_ref(repo_root: Path, path: Path) -> str:
    return path.resolve().relative_to(repo_root.resolve()).as_posix()


def _resolve_repo_ref(repo_root: Path, ref: str) -> Path | None:
    target = Path(ref)
    resolved = target.resolve() if target.is_absolute() else (repo_root / target).resolve()
    try:
        resolved.relative_to(repo_root.resolve())
    except ValueError:
        return None
    return resolved


def _prompt_registry(prompt_registry_path: Path) -> dict[str, dict[str, Any]]:
    registry = _load_yaml(prompt_registry_path)
    prompts = registry.get("prompts", [])
    if not isinstance(prompts, list):
        raise ValueError("prompt registry prompts must be a list")
    return {str(entry.get("prompt_ref")): entry for entry in prompts if isinstance(entry, dict)}


def _manifest_workers(manifest: dict[str, Any]) -> list[str]:
    workers = manifest.get("workers", [])
    if not isinstance(workers, list):
        raise ValueError("skill-agent manifest workers must be a list")
    return [str(worker) for worker in workers]


def _manifest_harnesses(manifest: dict[str, Any]) -> list[str]:
    harnesses = manifest.get("harnesses", [])
    if not isinstance(harnesses, list):
        raise ValueError("skill-agent manifest harnesses must be a list")
    return [str(harness) for harness in harnesses]


def _as_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item) for item in value]
    return [str(value)]


def _normalized_raw_source_access(value: Any) -> str:
    if isinstance(value, bool):
        return "raw_source_bundle" if value else "no_raw_source_access"
    return str(value)


def _accepted_context_classes(worker: dict[str, Any]) -> list[str]:
    raw_access = worker.get("raw_source_access")
    if raw_access is True:
        return ["synthetic_source_bundle", "metadata_only_source_inventory"]
    if raw_access == "bounded_packet_only":
        return ["bounded_ambiguity_packet", "source_bound_candidate_summary"]
    if raw_access == "structured_segments_only":
        return ["structured_segments", "source_bound_evidence_refs"]
    return ["validated_structured_candidates", "human_confirmed_facts_when_required"]


def _forbidden_context_classes(worker_id: str) -> list[str]:
    forbidden = [
        "real_client_data",
        "real_matter_data",
        "privileged_or_confidential_content",
        "production_connector_payloads",
        "cross_matter_corpus",
        "unbounded_raw_payload_fanout",
    ]
    if worker_id != "source-reader":
        forbidden.append("raw_source_bundle")
    return forbidden


def _evidence_requirements(worker: dict[str, Any]) -> list[str]:
    requirements = _as_list(worker.get("requirements"))
    evidenceish = [
        requirement
        for requirement in requirements
        if any(term in requirement.lower() for term in ("evidence", "source", "hash", "offset"))
    ]
    return evidenceish or [
        "typed input artifact refs",
        "typed output artifact refs",
        "human review gate before legal or external action",
    ]


def _owner_actions(worker_id: str) -> list[str]:
    return [
        f"Review `{worker_id}` as a draft candidate specialist, not a promoted skill.",
        "Confirm prompt hash, accepted context classes, forbidden context classes, tool authority, eval coverage, and revocation path.",
        "Decide draft, reject, or request revision inside Skills Registry before any reusable trust record exists.",
    ]


def _acceptance_checks(worker_id: str) -> list[str]:
    checks = [
        "Prompt hash matches the prompt file and registry entry.",
        "Allowed tools are empty and external/network/production connector tools are denied.",
        "Input and output schema refs are present and reviewable.",
        "Human gate remains required before any legal conclusion or external action.",
        "Real data approval remains false.",
    ]
    if worker_id == "frontier-adjudicator":
        checks.append(
            "Frontier adjudication remains bounded-packet-only and cannot replace human review."
        )
    return checks


def _red_team_notes(worker_id: str) -> list[str]:
    notes = [
        "Long prompts can look like governed skills before supply-chain review; this packet is only candidate evidence.",
        "Tool authority must stay deny-by-default because a promoted specialist could otherwise become a connector bypass.",
        "Practice context and model analysis must not become observed evidence.",
    ]
    if worker_id == "frontier-adjudicator":
        notes.append(
            "The frontier adjudicator is the highest-risk specialist and must remain deny-by-default."
        )
    return notes


def _candidate_packet_refs(candidates: list[SkillsRegistrySpecialistCandidate]) -> list[str]:
    refs: list[str] = []
    for candidate in candidates:
        refs.extend(
            [
                (
                    f"{SKILLS_REGISTRY_SPECIALIST_PACKET_DIRNAME}/"
                    f"{candidate.worker_id}.skills_registry_specialist_candidate.json"
                ),
                (
                    f"{SKILLS_REGISTRY_SPECIALIST_PACKET_DIRNAME}/"
                    f"{candidate.worker_id}.skills_registry_specialist_candidate.md"
                ),
            ]
        )
    return refs


def _schema_exists(repo_root: Path, ref: str) -> bool:
    resolved = _resolve_repo_ref(repo_root, ref)
    if resolved is None:
        return False
    try:
        resolved.relative_to((repo_root / "schemas").resolve())
    except ValueError:
        return False
    return resolved.is_file()


def _candidate_from_worker(
    *,
    repo_root: Path,
    agent_path: Path,
    worker: dict[str, Any],
    prompts: dict[str, dict[str, Any]],
) -> SkillsRegistrySpecialistCandidate:
    worker_id = str(worker.get("worker_id", ""))
    prompt_ref = str(worker.get("prompt_ref", worker_id))
    prompt_entry = prompts.get(prompt_ref, {})
    prompt_file = repo_root / "prompts" / f"{prompt_ref}.md"
    prompt_hash = str(prompt_entry.get("sha256", "sha256:missing"))
    prompt_hash_verified = False
    if prompt_file.is_file():
        prompt_hash_verified = digest_text(prompt_file.read_text(encoding="utf-8")) == prompt_hash
    input_schema_ref = str(worker.get("input_schema_ref", ""))
    output_schema_ref = str(worker.get("output_schema_ref", ""))
    input_schema_exists = bool(input_schema_ref) and _schema_exists(repo_root, input_schema_ref)
    output_schema_exists = bool(output_schema_ref) and _schema_exists(repo_root, output_schema_ref)
    missing = [
        field
        for field in (
            "worker_id",
            "version",
            "purpose",
            "model_class",
            "prompt_ref",
            "raw_source_access",
            "cross_matter_access",
            "network_access",
            "write_scope",
            "allowed_tools",
            "input_schema_ref",
            "output_schema_ref",
            "human_gate_required",
            "revocation_owner",
            "requirements",
            "prohibited",
        )
        if field not in worker
    ]
    if prompt_ref not in prompts:
        missing.append("prompt_registry_entry")
    if not prompt_file.is_file():
        missing.append("prompt_file")
    if not prompt_hash_verified:
        missing.append("prompt_hash_verified")
    if not input_schema_exists:
        missing.append("input_schema_exists")
    if not output_schema_exists:
        missing.append("output_schema_exists")
    if worker.get("cross_matter_access") is not False:
        missing.append("cross_matter_access_false")
    if worker.get("network_access") is not False:
        missing.append("network_access_false")
    if str(worker.get("write_scope", "")) not in ALLOWED_WRITE_SCOPES:
        missing.append("allowed_write_scope")
    if worker.get("human_gate_required") is not True:
        missing.append("human_gate_required_true")
    if worker.get("revocation_owner") != TARGET_REPO:
        missing.append("revocation_owner_skills_registry")
    if worker_id == "frontier-adjudicator" and worker.get("raw_source_access") != (
        "bounded_packet_only"
    ):
        missing.append("frontier_adjudicator_bounded_packet_only")
    approved_for_real_data = bool(prompt_entry.get("approved_for_real_data", True))
    if approved_for_real_data:
        missing.append("approved_for_real_data_false")
    allowed_tools = _as_list(worker.get("allowed_tools"))
    if allowed_tools:
        missing.append("allowed_tools_empty")
    status = "blocked_by_specialist_metadata_gap" if missing else "ready_for_skills_registry_review"
    return SkillsRegistrySpecialistCandidate(
        specialist_candidate_id=_stable_id(
            "skillsspecialist",
            "|".join([worker_id, str(worker.get("version", "")), prompt_hash, str(agent_path)]),
        ),
        worker_id=worker_id,
        version=str(worker.get("version", "")),
        agent_ref=_repo_ref(repo_root, agent_path),
        prompt_ref=prompt_ref,
        prompt_file_ref=_repo_ref(repo_root, prompt_file)
        if prompt_file.exists()
        else str(prompt_file),
        prompt_hash=prompt_hash,
        prompt_hash_verified=prompt_hash_verified,
        prompt_lifecycle=str(prompt_entry.get("lifecycle", "")),
        approved_for_real_data=False,
        purpose=str(worker.get("purpose", "")),
        model_class=str(worker.get("model_class", "")),
        raw_source_access=_normalized_raw_source_access(worker.get("raw_source_access")),
        cross_matter_access=False,
        network_access=False,
        write_scope=str(worker.get("write_scope", "")),
        allowed_tool_refs=allowed_tools,
        tool_denylist=TOOL_DENYLIST,
        input_schema_ref=input_schema_ref,
        output_schema_ref=output_schema_ref,
        input_schema_exists=input_schema_exists,
        output_schema_exists=output_schema_exists,
        requirements=_as_list(worker.get("requirements")),
        prohibited_actions=_as_list(worker.get("prohibited")),
        accepted_context_classes=_accepted_context_classes(worker),
        forbidden_context_classes=_forbidden_context_classes(worker_id),
        evidence_requirements=_evidence_requirements(worker),
        human_gate_required=True,
        revocation_owner=TARGET_REPO,
        status=status,
        missing_metadata_fields=sorted(set(missing)),
        required_owner_actions=_owner_actions(worker_id),
        acceptance_checks=_acceptance_checks(worker_id),
        red_team_notes=_red_team_notes(worker_id),
    )


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    artifact_refs: list[str] | None = None,
    worker_ids: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> SkillsRegistrySpecialistReviewCheck:
    return SkillsRegistrySpecialistReviewCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        artifact_refs=artifact_refs or [],
        worker_ids=worker_ids or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _build_checks(
    *,
    manifest_worker_ids: list[str],
    actual_worker_ids: list[str],
    candidates: list[SkillsRegistrySpecialistCandidate],
    missing_worker_ids: list[str],
    unexpected_worker_ids: list[str],
    missing_harness_refs: list[str],
    manifest_ref: str,
    prompt_registry_ref: str,
) -> list[SkillsRegistrySpecialistReviewCheck]:
    blocked_candidates = [
        candidate
        for candidate in candidates
        if candidate.status == "blocked_by_specialist_metadata_gap"
    ]
    return [
        _check(
            "manifest_workers_all_have_agent_files",
            not missing_worker_ids,
            "Every worker declared in skill-agent-manifest.json has a matching agent YAML.",
            artifact_refs=[manifest_ref],
            worker_ids=manifest_worker_ids,
            blocking_refs=missing_worker_ids,
        ),
        _check(
            "no_unmanifested_agent_workers",
            not unexpected_worker_ids,
            "No agent YAML introduces a worker outside the manifest.",
            artifact_refs=["agents/"],
            worker_ids=actual_worker_ids,
            blocking_refs=unexpected_worker_ids,
        ),
        _check(
            "manifest_harness_refs_exist",
            not missing_harness_refs,
            "Every harness declared in skill-agent-manifest.json exists locally.",
            artifact_refs=[manifest_ref, "harnesses/"],
            worker_ids=manifest_worker_ids,
            blocking_refs=missing_harness_refs,
        ),
        _check(
            "prompt_registry_complete_and_hash_verified",
            all(candidate.prompt_hash_verified for candidate in candidates),
            "Each specialist prompt has a registry entry and the registry hash matches the prompt file.",
            artifact_refs=[prompt_registry_ref],
            worker_ids=[candidate.worker_id for candidate in candidates],
            blocking_refs=[
                candidate.worker_id
                for candidate in candidates
                if not candidate.prompt_hash_verified
            ],
        ),
        _check(
            "specialist_schema_refs_present_and_existing",
            all(
                candidate.input_schema_exists and candidate.output_schema_exists
                for candidate in candidates
            ),
            "Each specialist declares existing input and output schema refs.",
            artifact_refs=[candidate.agent_ref for candidate in candidates],
            worker_ids=[candidate.worker_id for candidate in candidates],
            blocking_refs=[
                candidate.worker_id
                for candidate in candidates
                if not (candidate.input_schema_exists and candidate.output_schema_exists)
            ],
        ),
        _check(
            "no_network_cross_matter_or_external_tools",
            all(
                candidate.network_access is False
                and candidate.cross_matter_access is False
                and not candidate.allowed_tool_refs
                for candidate in candidates
            ),
            "Specialists allow no network, cross-matter access, or external tools.",
            artifact_refs=[candidate.agent_ref for candidate in candidates],
            worker_ids=[candidate.worker_id for candidate in candidates],
        ),
        _check(
            "real_data_and_promotion_disabled",
            all(
                candidate.approved_for_real_data is False
                and candidate.real_data_approved is False
                and candidate.skill_promoted is False
                for candidate in candidates
            ),
            "Specialists are not approved for real data and no skill promotion is performed.",
            artifact_refs=[manifest_ref, prompt_registry_ref],
            worker_ids=[candidate.worker_id for candidate in candidates],
        ),
        _check(
            "frontier_adjudicator_deny_by_default",
            any(
                candidate.worker_id == "frontier-adjudicator"
                and candidate.raw_source_access == "bounded_packet_only"
                and candidate.human_gate_required is True
                and not candidate.allowed_tool_refs
                for candidate in candidates
            ),
            "Frontier adjudicator remains bounded-packet-only, no-tools, and human-gated.",
            artifact_refs=["agents/frontier-adjudicator.yaml"],
            worker_ids=["frontier-adjudicator"],
        ),
        _check(
            "all_specialists_ready_for_owner_review",
            not blocked_candidates,
            "Every specialist candidate has enough metadata for Skills Registry owner review.",
            artifact_refs=[candidate.agent_ref for candidate in candidates],
            worker_ids=[candidate.worker_id for candidate in candidates],
            blocking_refs=[candidate.worker_id for candidate in blocked_candidates],
        ),
    ]


def build_skills_registry_specialist_review_report(
    *,
    repo_root: str | Path,
    manifest_path: str | Path,
    prompt_registry_path: str | Path,
) -> SkillsRegistrySpecialistReviewReport:
    root = Path(repo_root).resolve()
    manifest_file = Path(manifest_path)
    prompt_registry_file = Path(prompt_registry_path)
    if not manifest_file.is_absolute():
        manifest_file = root / manifest_file
    if not prompt_registry_file.is_absolute():
        prompt_registry_file = root / prompt_registry_file
    manifest_ref = _repo_ref(root, manifest_file)
    prompt_registry_ref = _repo_ref(root, prompt_registry_file)
    manifest = load_json(manifest_file)
    if not isinstance(manifest, dict):
        raise ValueError("skill-agent manifest must be a JSON object")
    worker_refs = _manifest_workers(manifest)
    harness_refs = _manifest_harnesses(manifest)
    missing_harness_refs = [
        harness_ref
        for harness_ref in harness_refs
        if (resolved := _resolve_repo_ref(root, harness_ref)) is None or not resolved.is_file()
    ]
    prompt_entries = _prompt_registry(prompt_registry_file)
    candidates: list[SkillsRegistrySpecialistCandidate] = []
    actual_worker_ids: list[str] = []
    missing_worker_ids: list[str] = []
    for worker_ref in worker_refs:
        worker_path = _resolve_repo_ref(root, worker_ref)
        if worker_path is None or not worker_path.is_file():
            missing_worker_ids.append(worker_ref)
            continue
        worker = _load_yaml(worker_path)
        worker_id = str(worker.get("worker_id", ""))
        actual_worker_ids.append(worker_id)
        candidates.append(
            _candidate_from_worker(
                repo_root=root,
                agent_path=worker_path,
                worker=worker,
                prompts=prompt_entries,
            )
        )
    manifest_worker_ids = [candidate.worker_id for candidate in candidates] + [
        worker_ref for worker_ref in missing_worker_ids
    ]
    manifest_worker_set = {Path(ref).stem for ref in worker_refs}
    actual_agent_worker_ids = []
    for agent_file in sorted((root / "agents").glob("*.yaml")):
        worker = _load_yaml(agent_file)
        actual_agent_worker_ids.append(str(worker.get("worker_id", "")))
    unexpected_worker_ids = sorted(set(actual_agent_worker_ids) - manifest_worker_set)
    ready_count = sum(
        1 for candidate in candidates if candidate.status == "ready_for_skills_registry_review"
    )
    blocked_count = len(candidates) - ready_count
    checks = _build_checks(
        manifest_worker_ids=manifest_worker_ids,
        actual_worker_ids=actual_agent_worker_ids,
        candidates=candidates,
        missing_worker_ids=missing_worker_ids,
        unexpected_worker_ids=unexpected_worker_ids,
        missing_harness_refs=missing_harness_refs,
        manifest_ref=manifest_ref,
        prompt_registry_ref=prompt_registry_ref,
    )
    failed = [check for check in checks if check.status == "failed"]
    return SkillsRegistrySpecialistReviewReport(
        specialist_review_report_id=_stable_id(
            "skillsregistryspecialistreview",
            "|".join(
                [
                    str(manifest.get("manifest_id", "")),
                    manifest_ref,
                    prompt_registry_ref,
                    "|".join(harness_refs),
                    "|".join(candidate.specialist_candidate_id for candidate in candidates),
                ]
            ),
        ),
        status=(
            "blocked_by_specialist_metadata_gaps"
            if failed
            or blocked_count
            or missing_worker_ids
            or unexpected_worker_ids
            or missing_harness_refs
            else "skills_registry_specialist_review_ready"
        ),
        manifest_ref=manifest_ref,
        prompt_registry_ref=prompt_registry_ref,
        expected_harness_count=len(harness_refs),
        missing_harness_refs=missing_harness_refs,
        expected_worker_count=len(worker_refs),
        candidate_count=len(candidates),
        ready_candidate_count=ready_count,
        blocked_candidate_count=blocked_count,
        missing_worker_ids=missing_worker_ids,
        unexpected_worker_ids=unexpected_worker_ids,
        prompt_hash_count=len(prompt_entries),
        candidates=candidates,
        candidate_packet_refs=_candidate_packet_refs(candidates),
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_skills_registry_specialist_review_report(
    report: SkillsRegistrySpecialistReviewReport,
) -> str:
    lines = [
        "# Skills Registry Specialist Review Report",
        "",
        f"**Report ID:** {report.specialist_review_report_id}",
        f"**Status:** {report.status}",
        f"**Target repo:** {report.target_repo}",
        f"**Manifest:** `{report.manifest_ref}`",
        f"**Prompt registry:** `{report.prompt_registry_ref}`",
        f"**Expected harnesses:** {report.expected_harness_count}",
        f"**Missing harness refs:** {', '.join(report.missing_harness_refs) if report.missing_harness_refs else 'none'}",
        f"**Ready candidates:** {report.ready_candidate_count}",
        f"**Blocked candidates:** {report.blocked_candidate_count}",
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        suffix = ""
        if check.blocking_refs:
            suffix = " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{suffix}")
    lines.extend(["", "## Specialist Candidates", ""])
    for candidate in report.candidates:
        lines.extend(
            [
                f"### {candidate.worker_id}",
                "",
                f"- Status: {candidate.status}",
                f"- Agent ref: `{candidate.agent_ref}`",
                f"- Prompt ref: `{candidate.prompt_ref}`",
                f"- Prompt hash verified: {candidate.prompt_hash_verified}",
                f"- Model class: {candidate.model_class}",
                f"- Raw source access: {candidate.raw_source_access}",
                f"- Write scope: {candidate.write_scope}",
                f"- Input schema: `{candidate.input_schema_ref}`",
                f"- Output schema: `{candidate.output_schema_ref}`",
                f"- Missing metadata fields: {', '.join(candidate.missing_metadata_fields) if candidate.missing_metadata_fields else 'none'}",
                "- Required owner actions:",
                *(f"  - [ ] {action}" for action in candidate.required_owner_actions),
                "- Acceptance checks:",
                *(f"  - [ ] {check}" for check in candidate.acceptance_checks),
                "- Red-team notes:",
                *(f"  - {note}" for note in candidate.red_team_notes),
                "",
            ]
        )
    lines.extend(
        [
            "## Boundary Flags",
            "",
            f"- Skill promoted: {report.skill_promoted}",
            f"- Skill trust record created: {report.skill_trust_record_created}",
            f"- Dynamic agent created: {report.dynamic_agent_created}",
            f"- Model provider enabled: {report.model_provider_enabled}",
            f"- Real data approved: {report.real_data_approved}",
            f"- External tools allowed: {report.external_tools_allowed}",
            f"- GitHub issue created: {report.github_issue_created}",
            f"- GitHub PR created: {report.github_pr_created}",
            f"- GitHub write performed: {report.github_write_performed}",
            f"- Sibling repo write performed: {report.sibling_repo_write_performed}",
            f"- Promotion authorized: {report.promotion_authorized}",
            f"- Lake write performed: {report.lake_write_performed}",
            f"- SQLite write performed: {report.sqlite_write_performed}",
            f"- External writes performed: {report.external_writes_performed}",
            f"- Silent learning performed: {report.silent_learning_performed}",
            "",
            "This report is local candidate metadata for Skills Registry review only. It does not promote skills, create trust records, add dynamic agents, enable providers, create issues or PRs, write sibling repos, or approve real data.",
            "",
        ]
    )
    return "\n".join(lines)


def render_skills_registry_specialist_candidate_packet(
    candidate: SkillsRegistrySpecialistCandidate,
) -> str:
    lines = [
        f"# Skills Registry Specialist Candidate: {candidate.worker_id}",
        "",
        f"**Candidate ID:** {candidate.specialist_candidate_id}",
        f"**Status:** {candidate.status}",
        f"**Agent ref:** `{candidate.agent_ref}`",
        f"**Prompt ref:** `{candidate.prompt_ref}`",
        f"**Prompt hash:** `{candidate.prompt_hash}`",
        f"**Prompt hash verified:** {candidate.prompt_hash_verified}",
        f"**Input schema:** `{candidate.input_schema_ref}`",
        f"**Output schema:** `{candidate.output_schema_ref}`",
        f"**Raw source access:** {candidate.raw_source_access}",
        f"**Write scope:** {candidate.write_scope}",
        f"**Missing metadata fields:** {', '.join(candidate.missing_metadata_fields) if candidate.missing_metadata_fields else 'none'}",
        "",
        "## Accepted Context",
        "",
        *(f"- {context_class}" for context_class in candidate.accepted_context_classes),
        "",
        "## Forbidden Context",
        "",
        *(f"- {context_class}" for context_class in candidate.forbidden_context_classes),
        "",
        "## Evidence Requirements",
        "",
        *(f"- {requirement}" for requirement in candidate.evidence_requirements),
        "",
        "## Required Owner Actions",
        "",
        *(f"- [ ] {action}" for action in candidate.required_owner_actions),
        "",
        "## Acceptance Checks",
        "",
        *(f"- [ ] {check}" for check in candidate.acceptance_checks),
        "",
        "## Red-Team Notes",
        "",
        *(f"- {note}" for note in candidate.red_team_notes),
        "",
        "## Boundary Flags",
        "",
        f"- Skill promoted: {candidate.skill_promoted}",
        f"- Skill trust record created: {candidate.skill_trust_record_created}",
        f"- Dynamic agent created: {candidate.dynamic_agent_created}",
        f"- Model provider enabled: {candidate.model_provider_enabled}",
        f"- Real data approved: {candidate.real_data_approved}",
        f"- External tools allowed: {candidate.external_tools_allowed}",
        f"- GitHub write performed: {candidate.github_write_performed}",
        f"- Sibling repo write performed: {candidate.sibling_repo_write_performed}",
        f"- Promotion authorized: {candidate.promotion_authorized}",
        f"- Lake write performed: {candidate.lake_write_performed}",
        f"- SQLite write performed: {candidate.sqlite_write_performed}",
        f"- External writes performed: {candidate.external_writes_performed}",
        f"- Silent learning performed: {candidate.silent_learning_performed}",
        "",
        "This packet is candidate-only Skills Registry owner-review evidence.",
        "",
    ]
    return "\n".join(lines)


def run_skills_registry_specialist_review(
    *,
    repo_root: str | Path,
    out_dir: str | Path,
    manifest_path: str | Path = DEFAULT_MANIFEST_REF,
    prompt_registry_path: str | Path = DEFAULT_PROMPT_REGISTRY_REF,
) -> tuple[SkillsRegistrySpecialistReviewReport, Path]:
    report = build_skills_registry_specialist_review_report(
        repo_root=repo_root,
        manifest_path=manifest_path,
        prompt_registry_path=prompt_registry_path,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    candidates_path = run_dir / SKILLS_REGISTRY_SPECIALIST_CANDIDATES_FILENAME
    if candidates_path.exists():
        candidates_path.unlink()
    packet_dir = run_dir / SKILLS_REGISTRY_SPECIALIST_PACKET_DIRNAME
    packet_dir.mkdir(parents=True, exist_ok=True)
    for existing in packet_dir.glob("*"):
        if existing.is_file():
            existing.unlink()
    for candidate in report.candidates:
        append_jsonl(candidates_path, candidate.model_dump(mode="json"))
        write_json(
            packet_dir / f"{candidate.worker_id}.skills_registry_specialist_candidate.json",
            candidate.model_dump(mode="json"),
        )
        (packet_dir / f"{candidate.worker_id}.skills_registry_specialist_candidate.md").write_text(
            render_skills_registry_specialist_candidate_packet(candidate),
            encoding="utf-8",
        )
    write_json(
        run_dir / SKILLS_REGISTRY_SPECIALIST_REVIEW_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / SKILLS_REGISTRY_SPECIALIST_REVIEW_NOTES_FILENAME).write_text(
        render_skills_registry_specialist_review_report(report),
        encoding="utf-8",
    )
    return report, run_dir
