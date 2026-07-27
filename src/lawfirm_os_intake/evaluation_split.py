"""Audit the development/holdout partition that gates comparative scoring.

Why this exists
---------------
Comparative evaluation only means something if the cases it scores were not
also used to build the thing being scored. This repo already had holdout
machinery, but it answered other questions:

* ``SyntheticFixtureExpansionHoldoutSpec`` is a coverage audit — which risk
  dimensions have fixtures — not a scoring boundary.
* ``holdout_excluded_from_prompt_assembly`` keeps a case out of model-visible
  context. That is leakage prevention at prompt-assembly time, not a rule about
  which cases may be developed against.
* Several inbound fixtures are named ``holdout-*``, but a filename convention
  is not enforcement: nothing failed if a "holdout" case was used during
  development, and nothing noticed if its content changed.

This module makes the partition **data with pinned content digests** and then
verifies the properties that make a comparative result trustworthy. The digest
pin is the part that matters: if a holdout fixture is edited after the split was
reviewed, "held out" silently means something different than it did when the
numbers were produced. Here that breaks the audit loudly instead.

The audit is evidence, not authority. It scores nothing, promotes nothing, and
does not decide whether a comparative result is publishable — a human does.
"""

from __future__ import annotations

from pathlib import Path

from .models import (
    EvaluationSplitAssignment,
    EvaluationSplitAuditReport,
    EvaluationSplitCheck,
    EvaluationSplitManifest,
)
from .util import digest_text, load_json, now_iso, write_json

EVALUATION_SPLIT_AUDIT_REPORT_FILENAME = "evaluation_split_audit_report.json"
EVALUATION_SPLIT_AUDIT_NOTES_FILENAME = "evaluation_split_audit_report.md"

REQUIRED_NEXT_GATES = [
    "human_review_of_split_before_any_comparative_claim",
    "re_review_of_split_after_any_holdout_fixture_change",
    "no_tuning_against_holdout_cases",
]


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}_{digest_text(value).split(':', maxsplit=1)[1][:20]}"


def _digest_file(path: Path) -> str:
    """Digest a fixture by its bytes, normalising line endings.

    Windows checkouts may rewrite line endings, which would otherwise make an
    untouched fixture look contaminated.
    """

    raw = path.read_bytes().replace(b"\r\n", b"\n")
    return digest_text(raw.decode("utf-8"))


def _check(
    check_id: str, ok: bool, message: str, offending: list[str] | None = None
) -> EvaluationSplitCheck:
    return EvaluationSplitCheck(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        offending_refs=sorted(offending or []),
    )


def build_evaluation_split_audit_report(
    *,
    manifest: EvaluationSplitManifest,
    repo_root: Path,
    split_manifest_ref: str,
    generated_at: str | None = None,
) -> EvaluationSplitAuditReport:
    """Verify a split manifest against the fixtures actually on disk."""

    checks: list[EvaluationSplitCheck] = []

    holdout = [item for item in manifest.assignments if item.partition == "holdout"]
    development = [item for item in manifest.assignments if item.partition == "development"]

    missing = [
        item.fixture_ref
        for item in manifest.assignments
        if not (repo_root / item.fixture_ref).is_file()
    ]
    checks.append(
        _check(
            "all_assigned_fixtures_exist",
            not missing,
            "Every fixture named in the split manifest exists on disk.",
            missing,
        )
    )

    # The contamination control. A digest mismatch means the fixture changed
    # after the split was reviewed, so any comparative number produced against
    # the old content is no longer attributable to this split.
    drifted: list[str] = []
    for item in manifest.assignments:
        path = repo_root / item.fixture_ref
        if not path.is_file():
            continue
        if _digest_file(path) != item.fixture_digest:
            drifted.append(item.fixture_ref)
    checks.append(
        _check(
            "pinned_fixture_digests_match_disk",
            not drifted,
            "No fixture changed after the split was reviewed and pinned.",
            drifted,
        )
    )

    # A gold spec attached to a development case must not describe a holdout
    # case: that is how expected holdout answers leak into development.
    leaked_gold: list[str] = []
    holdout_gold = {ref for item in holdout for ref in item.gold_refs}
    for item in development:
        for ref in item.gold_refs:
            if ref in holdout_gold:
                leaked_gold.append(ref)
    checks.append(
        _check(
            "no_gold_shared_between_partitions",
            not leaked_gold,
            "No gold specification is claimed by both a development and a holdout case.",
            leaked_gold,
        )
    )

    # Every gold file referenced must exist, or the partition is describing
    # expectations that cannot be checked.
    missing_gold = [
        ref
        for item in manifest.assignments
        for ref in item.gold_refs
        if not (repo_root / ref).is_file()
    ]
    checks.append(
        _check(
            "all_referenced_gold_exists",
            not missing_gold,
            "Every gold specification referenced by the split exists on disk.",
            missing_gold,
        )
    )

    checks.append(
        _check(
            "holdout_partition_reserved",
            bool(holdout),
            "At least one case is reserved for evaluation only.",
        )
    )
    checks.append(
        _check(
            "development_partition_retained",
            bool(development),
            "At least one case remains available for development.",
        )
    )

    # Holdout cases must be reserved by the manifest, not merely by filename;
    # and a case named holdout-* that the manifest puts in development is a
    # contradiction worth surfacing rather than silently resolving.
    misfiled = [
        item.fixture_ref
        for item in development
        if Path(item.fixture_ref).name.startswith("holdout-")
    ]
    checks.append(
        _check(
            "no_holdout_named_fixture_in_development",
            not misfiled,
            "No fixture named holdout-* is assigned to the development partition.",
            misfiled,
        )
    )

    failed = any(check.status == "failed" for check in checks)
    core = {
        "split_id": manifest.split_id,
        "split_manifest_ref": split_manifest_ref,
        "assignments": [
            {"fixture_ref": item.fixture_ref, "partition": item.partition}
            for item in sorted(manifest.assignments, key=lambda entry: entry.fixture_ref)
        ],
    }
    return EvaluationSplitAuditReport(
        report_id=_stable_id("evaluationsplitaudit", repr(sorted(core.items()))),
        split_id=manifest.split_id,
        split_manifest_ref=split_manifest_ref,
        generated_at=generated_at or now_iso(),
        status="failed" if failed else "passed",
        development_count=len(development),
        holdout_count=len(holdout),
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
    )


def render_evaluation_split_audit_report(report: EvaluationSplitAuditReport) -> str:
    lines = [
        "# Evaluation Split Audit",
        "",
        f"- Split: `{report.split_id}`",
        f"- Manifest: `{report.split_manifest_ref}`",
        f"- Status: **{report.status}**",
        f"- Development cases: {report.development_count}",
        f"- Holdout cases reserved: {report.holdout_count}",
        "",
        "## Checks",
        "",
        "| Check | Status | Detail |",
        "|---|---|---|",
    ]
    for check in report.checks:
        detail = check.message
        if check.offending_refs:
            detail += " Offending: " + ", ".join(f"`{ref}`" for ref in check.offending_refs)
        lines.append(f"| `{check.check_id}` | {check.status} | {detail} |")
    lines += [
        "",
        "## Boundary",
        "",
        "This audit is deterministic evidence about the partition. It scores no case,",
        "ranks no implementation strategy, promotes nothing, and performs no external",
        "or Lake write. A passing audit means a comparative result *may* be attributed",
        "to this split; it does not mean any such result exists or is publishable.",
        "",
        "## Required Next Gates",
        "",
    ]
    lines += [f"- {gate}" for gate in report.required_next_gates]
    return "\n".join(lines) + "\n"


def enforce_evaluation_split_audit_report(report: EvaluationSplitAuditReport) -> None:
    """Fail closed on a contaminated or incoherent split."""

    failed = [check.check_id for check in report.checks if check.status == "failed"]
    if failed:
        raise ValueError("evaluation split audit failed: " + ", ".join(sorted(failed)))


def run_evaluation_split_audit(
    *,
    split_manifest_path: str | Path,
    out_dir: str | Path,
    repo_root: str | Path = ".",
    generated_at: str | None = None,
) -> tuple[EvaluationSplitAuditReport, Path]:
    manifest = EvaluationSplitManifest.model_validate(load_json(split_manifest_path))
    root = Path(repo_root)
    report = build_evaluation_split_audit_report(
        manifest=manifest,
        repo_root=root,
        split_manifest_ref=str(Path(split_manifest_path).as_posix()),
        generated_at=generated_at,
    )
    target = Path(out_dir)
    target.mkdir(parents=True, exist_ok=True)
    write_json(target / EVALUATION_SPLIT_AUDIT_REPORT_FILENAME, report.model_dump(mode="json"))
    (target / EVALUATION_SPLIT_AUDIT_NOTES_FILENAME).write_text(
        render_evaluation_split_audit_report(report), encoding="utf-8", newline="\n"
    )
    return report, target


def build_split_assignment(
    *,
    repo_root: Path,
    fixture_ref: str,
    partition: str,
    rationale: str,
    gold_refs: list[str] | None = None,
) -> EvaluationSplitAssignment:
    """Helper for authoring a manifest: pins the current on-disk digest."""

    return EvaluationSplitAssignment(
        fixture_ref=fixture_ref,
        partition=partition,  # type: ignore[arg-type]
        fixture_digest=_digest_file(repo_root / fixture_ref),
        rationale=rationale,
        gold_refs=sorted(gold_refs or []),
    )
