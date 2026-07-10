from __future__ import annotations

from hashlib import sha256
from pathlib import Path
import re

from .models import (
    Crosswalk,
    CrosswalkAuditFinding,
    CrosswalkAuditReport,
    RunEvent,
)
from .util import append_jsonl, load_json, now_iso, write_json


CROSSWALK_AUDIT_REPORT_FILENAME = "crosswalk_audit_report.json"

CROSSWALK_PROHIBITED_ACTIONS = [
    "do_not_treat_local_crosswalk_as_canonical",
    "do_not_promote_candidate_targets_to_substrate_canon",
    "do_not_invent_sali_iris_or_utbms_ledes_codes_as_pinned",
    "do_not_guess_mappings_for_unknown_terms",
    "do_not_commit_public_standard_payloads",
    "do_not_bypass_human_review_for_crosswalk_promotion",
    "do_not_use_crosswalks_as_budget_or_rejection_business_logic",
]

CANDIDATE_TARGET_PREFIX_BY_SYSTEM = {
    "sali_lmss": "sali_lmss_candidate:",
    "utbms_ledes": "utbms_ledes_candidate:",
    "ledes_error_dimension": "ledes_error_dimension_candidate:",
}

UTBMS_LIKE_FAMILY_LABEL_PATTERN = re.compile(
    r"^utbms_ledes_candidate:.*(?:phase-family-|task-|expense-)[LAED]\d",
    re.IGNORECASE,
)

PINNED_TARGET_PATTERNS_BY_SYSTEM = {
    "sali_lmss": [
        re.compile(r"^https?://.*(?:sali|lmss)", re.IGNORECASE),
        re.compile(r"^(?:sali|lmss):", re.IGNORECASE),
    ],
    "utbms_ledes": [
        re.compile(r"^(?:utbms|ledes):", re.IGNORECASE),
        re.compile(r"^[LAE]\d{3}$", re.IGNORECASE),
        re.compile(r"^LEDES\d{4}", re.IGNORECASE),
    ],
    "ledes_error_dimension": [
        re.compile(r"^(?:utbms|ledes):", re.IGNORECASE),
        re.compile(r"^LEDES[_-]?[A-Z0-9]+$", re.IGNORECASE),
    ],
}

BUSINESS_LOGIC_MODULE_REFS = [
    "src/lawfirm_os_intake/budget.py",
    "src/lawfirm_os_intake/rejections.py",
    "src/lawfirm_os_intake/guidelines.py",
    "src/lawfirm_os_intake/workflow.py",
    "src/lawfirm_os_intake/workers.py",
    "src/lawfirm_os_intake/benchmarks.py",
    "src/lawfirm_os_intake/conflicts.py",
]

BUSINESS_LOGIC_CROSSWALK_TERMS = [
    "crosswalks import",
    "import lawfirm_os_intake.crosswalks",
    "load_crosswalk",
    "audit_crosswalks",
    "Crosswalk",
    "fixtures/synthetic/crosswalks",
]

# Candidate source provenance templates. These describe where a human reviewer
# would verify each target system; they are NOT downloaded payloads and no
# standard content is committed. Review status stays candidate_unverified.
PROVENANCE_BY_SYSTEM = {
    "sali_lmss": {
        "source_url": "https://github.com/sali-legal/LMSS",
        "source_version_or_date": "LMSS.owl (version not pinned; candidate reference only)",
        "license_terms_note": (
            "SALI LMSS is a legal matter standards vocabulary. Verify the current "
            "LMSS license and the exact IRI before any promotion. No LMSS payload "
            "is committed here."
        ),
    },
    "utbms_ledes": {
        "source_url": "https://utbms.com/",
        "source_version_or_date": "UTBMS code sets (version not pinned; candidate reference only)",
        "license_terms_note": (
            "UTBMS task/expense codes and LEDES billing formats are maintained by "
            "the UTBMS/LEDES committees. Verify current code sets and licensing "
            "terms before any promotion. No UTBMS/LEDES payload is committed here."
        ),
    },
    "ledes_error_dimension": {
        "source_url": "https://ledes.org/",
        "source_version_or_date": "LEDES e-billing error/rejection dimensions (version not pinned; candidate reference only)",
        "license_terms_note": (
            "LEDES e-billing rejection codes are maintained by LEDES.org. These "
            "are error-dimension candidates inspired by LEDES, not pinned LEDES "
            "codes. Verify before any promotion. No LEDES payload is committed."
        ),
    },
}


def _stable_id(prefix: str, seed: str) -> str:
    return f"{prefix}-{sha256(seed.encode('utf-8')).hexdigest()[:12]}"


def _is_dual_human_reviewed(entry) -> bool:
    return (
        entry.review_status == "human_reviewed"
        and entry.provenance.review_status == "human_reviewed"
    )


def _is_utbms_like_candidate_family_label(target: str) -> bool:
    """UTBMS-like mnemonic tokens inside candidate family labels are not exact codes."""
    normalized = target.strip()
    if not normalized.startswith("utbms_ledes_candidate:"):
        return False
    if UTBMS_LIKE_FAMILY_LABEL_PATTERN.search(normalized):
        return True
    return "-family-" in normalized.lower()


def load_crosswalk(path: str | Path) -> Crosswalk:
    """Load and validate a single crosswalk fixture."""
    return Crosswalk.model_validate(load_json(path))


def _canonical_claim_violations(cw: Crosswalk) -> list[CrosswalkAuditFinding]:
    findings: list[CrosswalkAuditFinding] = []
    if cw.not_promoted_canon is not True:
        findings.append(
            CrosswalkAuditFinding(
                crosswalk_id=cw.crosswalk_id,
                finding_id="not_promoted_canon_must_be_true",
                severity="blocker",
                issue="crosswalk declares not_promoted_canon=false; local crosswalks cannot be canonical",
            )
        )
    if cw.candidate_only is not True:
        findings.append(
            CrosswalkAuditFinding(
                crosswalk_id=cw.crosswalk_id,
                finding_id="candidate_only_must_be_true",
                severity="blocker",
                issue="crosswalk declares candidate_only=false; all crosswalks are candidate-only",
            )
        )
    if cw.data_origin != "synthetic":
        findings.append(
            CrosswalkAuditFinding(
                crosswalk_id=cw.crosswalk_id,
                finding_id="data_origin_must_be_synthetic",
                severity="blocker",
                issue=f"data_origin={cw.data_origin}; only synthetic crosswalks are permitted here",
            )
        )
    return findings


def _entry_findings(cw: Crosswalk) -> list[CrosswalkAuditFinding]:
    findings: list[CrosswalkAuditFinding] = []
    for entry in cw.entries:
        if entry.candidate_only is not True:
            findings.append(
                CrosswalkAuditFinding(
                    crosswalk_id=cw.crosswalk_id,
                    finding_id="entry_candidate_only_must_be_true",
                    severity="blocker",
                    issue="entry declares candidate_only=false",
                    entry_local_term=entry.local_term,
                )
            )
        # Provenance presence: source_url and license_terms_note must be non-empty.
        prov = entry.provenance
        if not prov.source_url.strip() or not prov.license_terms_note.strip():
            findings.append(
                CrosswalkAuditFinding(
                    crosswalk_id=cw.crosswalk_id,
                    finding_id="entry_missing_provenance",
                    severity="blocker",
                    issue="entry lacks source_url or license_terms_note provenance",
                    entry_local_term=entry.local_term,
                )
            )
        if not prov.review_status or prov.review_status == "unknown":
            findings.append(
                CrosswalkAuditFinding(
                    crosswalk_id=cw.crosswalk_id,
                    finding_id="entry_missing_review_status",
                    severity="blocker",
                    issue="entry provenance review_status is missing or unknown",
                    entry_local_term=entry.local_term,
                )
            )
        # Unknowns must stay explicit, never guessed.
        is_unmapped = entry.candidate_target_system == "unmapped"
        if is_unmapped:
            if entry.candidate_target.lower() not in {"unmapped", "unknown"}:
                findings.append(
                    CrosswalkAuditFinding(
                        crosswalk_id=cw.crosswalk_id,
                        finding_id="unmapped_entry_has_guessed_target",
                        severity="blocker",
                        issue=(
                            "unmapped entry must keep candidate_target as 'unmapped', "
                            "not a guessed target"
                        ),
                        entry_local_term=entry.local_term,
                    )
                )
            if entry.confidence != "unknown":
                findings.append(
                    CrosswalkAuditFinding(
                        crosswalk_id=cw.crosswalk_id,
                        finding_id="unmapped_entry_confidence_not_unknown",
                        severity="blocker",
                        issue="unmapped entry must keep confidence='unknown'",
                        entry_local_term=entry.local_term,
                    )
                )
        else:
            human_reviewed = _is_dual_human_reviewed(entry)
            # High-confidence mapped entries require dual human review on entry + provenance.
            if entry.confidence == "high" and not human_reviewed:
                findings.append(
                    CrosswalkAuditFinding(
                        crosswalk_id=cw.crosswalk_id,
                        finding_id="high_confidence_requires_dual_human_review",
                        severity="blocker",
                        issue=(
                            "mapped entry claims high confidence but entry.review_status and "
                            "provenance.review_status are not both human_reviewed"
                        ),
                        entry_local_term=entry.local_term,
                    )
                )
            expected_prefix = CANDIDATE_TARGET_PREFIX_BY_SYSTEM.get(entry.candidate_target_system)
            if (
                expected_prefix
                and not human_reviewed
                and not entry.candidate_target.startswith(expected_prefix)
            ):
                findings.append(
                    CrosswalkAuditFinding(
                        crosswalk_id=cw.crosswalk_id,
                        finding_id="unverified_candidate_target_prefix_violation",
                        severity="blocker",
                        issue=(
                            "unverified mapped entry must use an explicit candidate target "
                            f"prefix ({expected_prefix}); local crosswalks must not look like "
                            "pinned standard identifiers"
                        ),
                        entry_local_term=entry.local_term,
                    )
                )
            if not human_reviewed and _looks_like_pinned_target(
                entry.candidate_target_system,
                entry.candidate_target,
            ):
                findings.append(
                    CrosswalkAuditFinding(
                        crosswalk_id=cw.crosswalk_id,
                        finding_id="unverified_pinned_standard_target",
                        severity="blocker",
                        issue=(
                            "unverified mapped entry looks like a pinned SALI/UTBMS/LEDES "
                            "identifier; exact standard IDs require human review and owning-repo "
                            "promotion before use"
                        ),
                        entry_local_term=entry.local_term,
                    )
                )
    return findings


def _looks_like_pinned_target(system: str, target: str) -> bool:
    return any(
        pattern.search(target.strip())
        for pattern in PINNED_TARGET_PATTERNS_BY_SYSTEM.get(system, [])
    )


def _business_logic_dependency_findings(
    repo_root: str | Path | None,
) -> list[CrosswalkAuditFinding]:
    if repo_root is None:
        return []
    root = Path(repo_root)
    findings: list[CrosswalkAuditFinding] = []
    for module_ref in BUSINESS_LOGIC_MODULE_REFS:
        path = root / module_ref
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        matched_terms = [term for term in BUSINESS_LOGIC_CROSSWALK_TERMS if term in text]
        if matched_terms:
            findings.append(
                CrosswalkAuditFinding(
                    crosswalk_id="crosswalk-safety-gate",
                    finding_id="crosswalk_used_as_business_logic_dependency",
                    severity="blocker",
                    issue=(
                        f"{module_ref} references crosswalk audit/mapping terms "
                        f"{sorted(matched_terms)}. Crosswalks are review metadata only, "
                        "not required budget, guideline, benchmark, workflow, or rejection logic."
                    ),
                )
            )
    return findings


def audit_crosswalks(
    crosswalks: list[Crosswalk],
    *,
    repo_root: str | Path | None = None,
) -> CrosswalkAuditReport:
    findings: list[CrosswalkAuditFinding] = []
    entry_count = 0
    mapped_count = 0
    unmapped_count = 0
    canonical_claim_count = 0
    candidate_only_violation_count = 0
    entries_missing_provenance_count = 0
    entries_missing_review_status_count = 0
    guessed_mapping_count = 0
    high_confidence_dual_review_violation_count = 0
    utbms_like_candidate_family_label_count = 0
    unverified_pinned_target_count = 0
    candidate_target_prefix_violation_count = 0
    workflow_dependency_violation_count = 0

    for cw in crosswalks:
        cw_findings = _canonical_claim_violations(cw) + _entry_findings(cw)
        findings.extend(cw_findings)
        for f in cw_findings:
            if f.severity == "blocker":
                if f.finding_id == "not_promoted_canon_must_be_true":
                    canonical_claim_count += 1
                if f.finding_id in {
                    "candidate_only_must_be_true",
                    "entry_candidate_only_must_be_true",
                }:
                    candidate_only_violation_count += 1
                if f.finding_id == "entry_missing_provenance":
                    entries_missing_provenance_count += 1
                if f.finding_id == "entry_missing_review_status":
                    entries_missing_review_status_count += 1
                if f.finding_id in {
                    "unmapped_entry_has_guessed_target",
                    "unmapped_entry_confidence_not_unknown",
                    "high_confidence_requires_dual_human_review",
                }:
                    guessed_mapping_count += 1
                if f.finding_id == "high_confidence_requires_dual_human_review":
                    high_confidence_dual_review_violation_count += 1
                if f.finding_id == "unverified_pinned_standard_target":
                    unverified_pinned_target_count += 1
                if f.finding_id == "unverified_candidate_target_prefix_violation":
                    candidate_target_prefix_violation_count += 1
        for entry in cw.entries:
            entry_count += 1
            if _is_utbms_like_candidate_family_label(entry.candidate_target):
                utbms_like_candidate_family_label_count += 1
            if entry.candidate_target_system == "unmapped":
                unmapped_count += 1
            else:
                mapped_count += 1

    dependency_findings = _business_logic_dependency_findings(repo_root)
    findings.extend(dependency_findings)
    workflow_dependency_violation_count = sum(
        1
        for finding in dependency_findings
        if finding.finding_id == "crosswalk_used_as_business_logic_dependency"
    )

    has_blocker = any(f.severity == "blocker" for f in findings)
    seed = "|".join(
        [
            str(len(crosswalks)),
            str(entry_count),
            str(mapped_count),
            str(unmapped_count),
            str(canonical_claim_count),
            str(guessed_mapping_count),
            str(high_confidence_dual_review_violation_count),
            str(utbms_like_candidate_family_label_count),
            str(unverified_pinned_target_count),
            str(candidate_target_prefix_violation_count),
            str(workflow_dependency_violation_count),
        ]
    )
    return CrosswalkAuditReport(
        report_id=_stable_id("xwalkaudit", seed),
        generated_at=now_iso(),
        status="blocked" if has_blocker else "passed",
        acceptance_gate_status="blocked" if has_blocker else "accepted_with_restrictions",
        crosswalk_count=len(crosswalks),
        entry_count=entry_count,
        mapped_entry_count=mapped_count,
        unmapped_entry_count=unmapped_count,
        canonical_claim_count=canonical_claim_count,
        candidate_only_violation_count=candidate_only_violation_count,
        entries_missing_provenance_count=entries_missing_provenance_count,
        entries_missing_review_status_count=entries_missing_review_status_count,
        guessed_mapping_count=guessed_mapping_count,
        high_confidence_dual_review_violation_count=high_confidence_dual_review_violation_count,
        utbms_like_candidate_family_label_count=utbms_like_candidate_family_label_count,
        exact_standard_code_verified=False,
        unverified_pinned_target_count=unverified_pinned_target_count,
        candidate_target_prefix_violation_count=candidate_target_prefix_violation_count,
        workflow_dependency_violation_count=workflow_dependency_violation_count,
        findings=findings,
        crosswalk_refs=[cw.crosswalk_id for cw in crosswalks],
        candidate_only=True,
        not_promoted_canon=True,
        prohibited_actions=CROSSWALK_PROHIBITED_ACTIONS,
        display_banner={
            "warning": (
                "These mappings are candidate/unverified and not legal, billing, SALI, "
                "LEDES, UTBMS, or substrate canon."
            ),
            "candidate_only": True,
            "not_promoted_canon": True,
            "accepted_with_restrictions": not has_blocker,
            "review_status_required_before_promotion": "human_reviewed",
            "high_confidence_requires_dual_human_review": True,
            "exact_standard_code_verified": False,
            "utbms_like_candidate_family_label_count": utbms_like_candidate_family_label_count,
            "candidate_family_label_note": (
                "UTBMS-like strings such as task-L310-family-* are mnemonic candidate "
                "families, not exact SALI/LEDES/UTBMS canon."
            ),
            "blocked_actions": [
                "canonical_use",
                "budget_logic_dependency",
                "rejection_logic_dependency",
                "guideline_logic_dependency",
                "lake_write",
                "external_submission",
            ],
        },
        not_authorized_for_canonical_use=True,
        not_authorized_for_budget_logic=True,
        not_authorized_for_rejection_logic=True,
    )


def build_crosswalk_audit_report(
    crosswalk_paths: list[str | Path],
    *,
    repo_root: str | Path | None = None,
) -> tuple[list[Crosswalk], CrosswalkAuditReport]:
    crosswalks = [load_crosswalk(p) for p in crosswalk_paths]
    report = audit_crosswalks(crosswalks, repo_root=repo_root)
    return crosswalks, report


def run_crosswalk_audit_report(
    crosswalk_paths: list[str | Path],
    out_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> tuple[list[Crosswalk], CrosswalkAuditReport, Path]:
    root = Path(repo_root) if repo_root is not None else Path.cwd()
    crosswalks, report = build_crosswalk_audit_report(crosswalk_paths, repo_root=root)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    report_path = run_dir / CROSSWALK_AUDIT_REPORT_FILENAME
    write_json(report_path, report.model_dump(mode="json"))
    append_jsonl(
        run_dir / "run_ledger.jsonl",
        RunEvent(
            run_id=report.report_id,
            step_index=0,
            step_name="crosswalk_audit_report_built",
            status="completed" if report.status == "passed" else "blocked",
            timestamp=now_iso(),
            input_refs=[str(p) for p in crosswalk_paths],
            output_refs=[str(report_path)],
        ).model_dump(mode="json"),
    )
    return crosswalks, report, run_dir
