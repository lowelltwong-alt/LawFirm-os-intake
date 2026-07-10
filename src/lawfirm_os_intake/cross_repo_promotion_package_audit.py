from __future__ import annotations

from pathlib import Path

from .models import (
    CrossRepoPromotionPackage,
    CrossRepoPromotionPackageAuditCheck,
    CrossRepoPromotionPackageAuditReport,
)
from .util import digest_text, load_json, now_iso, write_json


REPO_ROOT = Path(__file__).resolve().parents[2]
PROMOTION_PACKAGE_AUDIT_REPORT_FILENAME = "cross_repo_promotion_package_audit_report.json"
PROMOTION_PACKAGE_AUDIT_NOTES_FILENAME = "cross_repo_promotion_package_audit_report.md"

REQUIRED_TARGET_REPOS = {
    "LawFirm-os-semantic-substrate",
    "LawFirm-os-orchestrator",
    "LawFirm-os-exceptions-lake-runtime",
    "LawFirm-os-skills-registry",
    "LawFirm-os-legal-knowledge-runtime",
}

CONTRACT_PREFIX_BY_TARGET = {
    "LawFirm-os-semantic-substrate": "semantic-substrate://",
    "LawFirm-os-orchestrator": "orchestrator://",
    "LawFirm-os-exceptions-lake-runtime": "exception-lake://",
    "LawFirm-os-skills-registry": "skills-registry://",
    "LawFirm-os-legal-knowledge-runtime": "legal-knowledge-runtime://",
}

REQUIRED_HIGH_RISK_PROPOSAL_IDS = [
    "substrate.matter-link-and-entity-candidates.v0_1",
    "orchestrator.cross-bundle-matter-link-state.v0_1",
    "orchestrator.carrier-rejection-capture-appeal.v0_1",
    "lake.carrier-rejection-admission.v0_1",
    "lkr.rate-benchmark-snapshot.v0_1",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _check(
    check_id: str,
    passed: bool,
    message: str,
    *,
    proposal_ids: list[str] | None = None,
    artifact_refs: list[str] | None = None,
    blocking_refs: list[str] | None = None,
) -> CrossRepoPromotionPackageAuditCheck:
    return CrossRepoPromotionPackageAuditCheck(
        check_id=check_id,
        status="passed" if passed else "failed",
        message=message,
        proposal_ids=proposal_ids or [],
        artifact_refs=artifact_refs or [],
        blocking_refs=blocking_refs or ([] if passed else artifact_refs or []),
    )


def _safe_origin_ref(ref: str) -> bool:
    path = Path(ref)
    return not path.is_absolute() and ".." not in path.parts


def build_cross_repo_promotion_package_audit_report(
    *,
    promotion_package: CrossRepoPromotionPackage,
    promotion_package_ref: str,
    repo_root: str | Path = REPO_ROOT,
    generated_at: str | None = None,
) -> CrossRepoPromotionPackageAuditReport:
    root = Path(repo_root)
    proposal_ids = [proposal.proposal_id for proposal in promotion_package.proposals]
    artifact_refs = [
        ref for proposal in promotion_package.proposals for ref in proposal.candidate_artifact_refs
    ]
    unsafe_refs = [ref for ref in artifact_refs if not _safe_origin_ref(ref)]
    missing_artifacts = [
        ref for ref in artifact_refs if _safe_origin_ref(ref) and not (root / ref).is_file()
    ]
    mismatched_contract_refs = [
        f"{proposal.proposal_id}:{ref}"
        for proposal in promotion_package.proposals
        for ref in proposal.proposed_contract_refs
        if not ref.startswith(CONTRACT_PREFIX_BY_TARGET[proposal.target_repo])
    ]
    missing_high_risk = [
        proposal_id
        for proposal_id in REQUIRED_HIGH_RISK_PROPOSAL_IDS
        if proposal_id not in proposal_ids
    ]
    incomplete_proposals = [
        proposal.proposal_id
        for proposal in promotion_package.proposals
        if not proposal.candidate_artifact_refs
        or not proposal.proposed_contract_refs
        or not proposal.required_governance_actions
        or not proposal.promotion_blockers
    ]
    target_repos = set(promotion_package.target_repos)
    checks = [
        _check(
            "promotion_target_repos_exact_and_unique",
            len(promotion_package.target_repos) == len(target_repos)
            and target_repos == REQUIRED_TARGET_REPOS,
            "Promotion package names each required owner repo exactly once.",
            artifact_refs=sorted(target_repos),
            blocking_refs=sorted(target_repos.symmetric_difference(REQUIRED_TARGET_REPOS)),
        ),
        _check(
            "promotion_proposal_ids_unique",
            len(proposal_ids) == len(set(proposal_ids)),
            "Promotion proposal IDs are unique.",
            proposal_ids=proposal_ids,
            blocking_refs=[
                proposal_id for proposal_id in proposal_ids if proposal_ids.count(proposal_id) > 1
            ],
        ),
        _check(
            "promotion_artifact_refs_stay_in_origin_repo",
            not unsafe_refs,
            "Candidate artifact refs are origin-repo relative and do not traverse outside intake.",
            artifact_refs=artifact_refs,
            blocking_refs=unsafe_refs,
        ),
        _check(
            "promotion_artifact_refs_resolve",
            not missing_artifacts,
            "Every candidate artifact ref resolves in the intake repository.",
            artifact_refs=artifact_refs,
            blocking_refs=missing_artifacts,
        ),
        _check(
            "promotion_contract_refs_match_owner_namespace",
            not mismatched_contract_refs,
            "Candidate contract refs use the namespace owned by their target repo.",
            proposal_ids=proposal_ids,
            blocking_refs=mismatched_contract_refs,
        ),
        _check(
            "promotion_high_risk_wave_coverage_complete",
            not missing_high_risk,
            "Persistent linking, carrier lifecycle, and rate benchmark candidates are routed to owners.",
            proposal_ids=REQUIRED_HIGH_RISK_PROPOSAL_IDS,
            blocking_refs=missing_high_risk,
        ),
        _check(
            "promotion_proposals_have_review_material",
            not incomplete_proposals,
            "Every proposal supplies source artifacts, candidate contracts, owner actions, and blockers.",
            proposal_ids=proposal_ids,
            blocking_refs=incomplete_proposals,
        ),
    ]
    failed_checks = [check for check in checks if check.status == "failed"]
    observed_high_risk = [
        proposal_id
        for proposal_id in REQUIRED_HIGH_RISK_PROPOSAL_IDS
        if proposal_id in proposal_ids
    ]
    return CrossRepoPromotionPackageAuditReport(
        promotion_package_audit_report_id=_stable_id(
            "promotionpackageaudit",
            f"{promotion_package.package_id}|{promotion_package_ref}|{proposal_ids}",
        ),
        status=(
            "ready_for_owner_adoption" if not failed_checks else "blocked_promotion_package_audit"
        ),
        source_promotion_package_id=promotion_package.package_id,
        source_promotion_package_ref=promotion_package_ref,
        target_repo_count=len(promotion_package.target_repos),
        proposal_count=len(promotion_package.proposals),
        target_repos=promotion_package.target_repos,
        required_high_risk_proposal_ids=REQUIRED_HIGH_RISK_PROPOSAL_IDS,
        observed_high_risk_proposal_ids=observed_high_risk,
        checks=checks,
        generated_at=generated_at or now_iso(),
    )


def render_cross_repo_promotion_package_audit_report(
    report: CrossRepoPromotionPackageAuditReport,
) -> str:
    lines = [
        "# Cross-Repo Promotion Package Audit",
        "",
        f"**Report ID:** {report.promotion_package_audit_report_id}",
        f"**Status:** {report.status}",
        f"**Promotion package:** `{report.source_promotion_package_ref}`",
        f"**Target repos:** {report.target_repo_count}",
        f"**Proposals:** {report.proposal_count}",
        "",
        "## Required High-Risk Coverage",
        "",
        *(f"- Required: `{proposal_id}`" for proposal_id in report.required_high_risk_proposal_ids),
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        blockers = (
            " Blocking refs: " + ", ".join(f"`{ref}`" for ref in check.blocking_refs)
            if check.blocking_refs
            else ""
        )
        lines.append(f"- {check.check_id}: {check.status}; {check.message}{blockers}")
    lines.extend(
        [
            "",
            "## Boundary",
            "",
            "This audit reads only intake-local candidate references. It does not create issues, write a sibling repo, promote canon, admit Lake records, or apply learning.",
            "",
        ]
    )
    return "\n".join(lines)


def run_cross_repo_promotion_package_audit(
    *,
    promotion_package_path: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = REPO_ROOT,
) -> tuple[CrossRepoPromotionPackageAuditReport, Path]:
    package_path = Path(promotion_package_path)
    package = CrossRepoPromotionPackage.model_validate(load_json(package_path))
    report = build_cross_repo_promotion_package_audit_report(
        promotion_package=package,
        promotion_package_ref=str(package_path),
        repo_root=repo_root,
    )
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / PROMOTION_PACKAGE_AUDIT_REPORT_FILENAME, report.model_dump(mode="json"))
    (run_dir / PROMOTION_PACKAGE_AUDIT_NOTES_FILENAME).write_text(
        render_cross_repo_promotion_package_audit_report(report), encoding="utf-8"
    )
    return report, run_dir
