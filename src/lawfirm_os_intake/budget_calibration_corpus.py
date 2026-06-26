from __future__ import annotations

from collections import Counter
from hashlib import sha256
from pathlib import Path
from typing import Any

from .models import (
    BudgetCalibrationArtifactKind,
    BudgetCalibrationCorpusArtifact,
    BudgetCalibrationCorpusCheck,
    BudgetCalibrationCorpusReport,
    BudgetCalibrationEligibility,
    BudgetCalibrationRole,
)
from .util import digest_text, load_json, new_id, now_iso, write_json


BUDGET_CALIBRATION_CORPUS_REPORT_FILENAME = "budget_calibration_corpus_report.json"
BUDGET_CALIBRATION_CORPUS_NOTES_FILENAME = "budget_calibration_corpus_report.md"

REQUIRED_NEXT_GATES = [
    "human_corpus_review",
    "synthetic_fixture_result_binding",
    "shadow_eval_before_learning",
    "owning_repo_review",
    "no_silent_profile_or_template_mutation",
]

MUTATION_FLAGS = [
    "calibration_applied",
    "profile_mutation_performed",
    "template_mutation_performed",
    "budget_mutation_performed",
    "carrier_guideline_mutation_performed",
    "lake_write_performed",
    "sqlite_write_performed",
    "external_writes_performed",
    "silent_learning_performed",
]


def _relative_ref(path: Path, repo_root: Path | None) -> str:
    if repo_root is not None:
        try:
            return path.relative_to(repo_root).as_posix()
        except ValueError:
            pass
    return str(path)


def _sha256(path: Path) -> str:
    return "sha256:" + sha256(path.read_bytes()).hexdigest()


def _kind_for_path(path: Path) -> BudgetCalibrationArtifactKind:
    parts = {part.lower() for part in path.parts}
    name = path.name.lower()
    if "inbound" in parts:
        return "intake_source_fixture"
    if "confirmations" in parts:
        return "human_confirmation_fixture"
    if "budget-review" in parts:
        return "budget_review_fixture"
    if "actuals" in parts:
        return "actuals_fixture"
    if "carrier-rejections" in parts:
        return "carrier_rejection_fixture"
    if "gold" in parts:
        return "reviewed_gold_fixture"
    if "learning" in parts and name.startswith("shadow-eval-result"):
        return "learning_shadow_eval_fixture"
    if "learning" in parts:
        return "learning_gate_fixture"
    return "unclassified_json_fixture"


def _role_for_kind(kind: BudgetCalibrationArtifactKind) -> BudgetCalibrationRole:
    if kind in {"intake_source_fixture", "human_confirmation_fixture"}:
        return "input_context_fixture"
    if kind in {"budget_review_fixture", "actuals_fixture", "carrier_rejection_fixture"}:
        return "outcome_evidence_fixture"
    if kind == "reviewed_gold_fixture":
        return "reviewed_baseline_fixture"
    if kind == "learning_shadow_eval_fixture":
        return "shadow_eval_fixture"
    if kind == "learning_gate_fixture":
        return "learning_gate_fixture"
    return "unclassified_supporting_fixture"


def _scope_failures(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    failures: list[str] = []
    if payload.get("data_origin") not in {None, "synthetic"}:
        failures.append(f"data_origin={payload.get('data_origin')}")
    if payload.get("synthetic_only") is False:
        failures.append("synthetic_only=false")
    if payload.get("contains_real_client_data") is True:
        failures.append("contains_real_client_data=true")
    if payload.get("contains_real_matter_data") is True:
        failures.append("contains_real_matter_data=true")
    if payload.get("contains_privileged_data") is True:
        failures.append("contains_privileged_data=true")
    return failures


def _boundary_failures(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    return [flag for flag in MUTATION_FLAGS if payload.get(flag) is True]


def _support_refs(payload: Any) -> list[str]:
    if not isinstance(payload, dict):
        return []
    refs: list[str] = []
    for key in (
        "source_ref",
        "source_gate_report_ref",
        "source_budget_proposal_ref",
        "carrier_rejection_learning_report_ref",
        "budget_revision_report_ref",
        "budget_actual_comparison_report_ref",
    ):
        value = payload.get(key)
        if isinstance(value, str) and value:
            refs.append(value)
    for key in ("support_refs", "source_report_refs", "fixture_result_refs"):
        value = payload.get(key)
        if isinstance(value, list):
            refs.extend(str(item) for item in value if item)
    return sorted(dict.fromkeys(refs))


def _eligibility(
    role: BudgetCalibrationRole,
    scope_failures: list[str],
    boundary_failures: list[str],
) -> BudgetCalibrationEligibility:
    if scope_failures:
        return "blocked_real_or_privileged_data"
    if boundary_failures:
        return "blocked_boundary_violation"
    if role in {
        "outcome_evidence_fixture",
        "reviewed_baseline_fixture",
        "learning_gate_fixture",
        "shadow_eval_fixture",
    }:
        return "eligible_for_synthetic_calibration_review"
    return "supporting_context_only"


def _artifact(
    path: Path, corpus_root: Path, repo_root: Path | None
) -> BudgetCalibrationCorpusArtifact:
    payload = load_json(path)
    rel = _relative_ref(path, repo_root)
    kind = _kind_for_path(path.relative_to(corpus_root))
    role = _role_for_kind(kind)
    scope = _scope_failures(payload)
    boundary = _boundary_failures(payload)
    return BudgetCalibrationCorpusArtifact(
        artifact_id="budgetcorpusartifact_" + digest_text(rel).split(":", maxsplit=1)[1][:20],
        artifact_ref=rel,
        artifact_kind=kind,
        calibration_role=role,
        eligibility=_eligibility(role, scope, boundary),
        sha256=_sha256(path),
        data_origin=payload.get("data_origin") if isinstance(payload, dict) else None,
        synthetic_only=payload.get("synthetic_only") if isinstance(payload, dict) else None,
        contains_real_client_data=(
            payload.get("contains_real_client_data") if isinstance(payload, dict) else None
        ),
        contains_real_matter_data=(
            payload.get("contains_real_matter_data") if isinstance(payload, dict) else None
        ),
        contains_privileged_data=(
            payload.get("contains_privileged_data") if isinstance(payload, dict) else None
        ),
        scope_failures=scope,
        boundary_failures=boundary,
        support_refs=_support_refs(payload),
    )


def _check(
    check_id: str,
    status: str,
    message: str,
    artifact_refs: list[str] | None = None,
) -> BudgetCalibrationCorpusCheck:
    return BudgetCalibrationCorpusCheck(
        check_id=check_id,
        status=status,  # type: ignore[arg-type]
        message=message,
        artifact_refs=artifact_refs or [],
    )


def build_budget_calibration_corpus_report(
    corpus_root: str | Path,
    *,
    repo_root: str | Path | None = None,
) -> BudgetCalibrationCorpusReport:
    corpus_path = Path(corpus_root).resolve()
    repo_path = Path(repo_root).resolve() if repo_root is not None else None
    if not corpus_path.exists():
        checks = [
            _check(
                "corpus_root_exists",
                "failed",
                f"Corpus root does not exist: {corpus_path}",
            )
        ]
        return BudgetCalibrationCorpusReport(
            corpus_report_id=new_id("budgetcorpus"),
            status="failed",
            corpus_root_ref=_relative_ref(corpus_path, repo_path),
            artifact_count=0,
            eligible_artifact_count=0,
            supporting_artifact_count=0,
            blocked_artifact_count=0,
            artifacts=[],
            checks=checks,
            required_next_gates=REQUIRED_NEXT_GATES,
            generated_at=now_iso(),
        )

    artifacts: list[BudgetCalibrationCorpusArtifact] = []
    parse_failures: list[str] = []
    for path in sorted(corpus_path.rglob("*.json")):
        try:
            artifacts.append(_artifact(path, corpus_path, repo_path))
        except ValueError as exc:
            parse_failures.append(f"{_relative_ref(path, repo_path)}: {exc}")

    blocked_refs = [
        artifact.artifact_ref
        for artifact in artifacts
        if artifact.eligibility in {"blocked_real_or_privileged_data", "blocked_boundary_violation"}
    ]
    eligible = [
        artifact
        for artifact in artifacts
        if artifact.eligibility == "eligible_for_synthetic_calibration_review"
    ]
    supporting = [
        artifact for artifact in artifacts if artifact.eligibility == "supporting_context_only"
    ]
    kind_counts = Counter(artifact.artifact_kind for artifact in artifacts)
    role_counts = Counter(artifact.calibration_role for artifact in artifacts)
    kinds = {artifact.artifact_kind for artifact in artifacts}
    checks = [
        _check("corpus_root_exists", "passed", "Corpus root exists."),
        _check(
            "json_parse",
            "passed" if not parse_failures else "failed",
            "All corpus JSON files parse." if not parse_failures else "; ".join(parse_failures),
        ),
        _check(
            "synthetic_only_scope",
            "passed" if not blocked_refs else "failed",
            "No real, privileged, production, mutation, Lake, SQLite, or external-write flags were found.",
            blocked_refs,
        ),
        _check(
            "outcome_evidence_present",
            "passed"
            if {"budget_review_fixture", "actuals_fixture", "carrier_rejection_fixture"} <= kinds
            else "warning",
            "Budget review, actuals, and carrier rejection outcome fixtures are present.",
        ),
        _check(
            "shadow_eval_fixtures_present",
            "passed" if "learning_shadow_eval_fixture" in kinds else "warning",
            "Learning shadow-eval fixture results are present.",
        ),
        _check(
            "calibration_not_applied",
            "passed",
            "Corpus audit is manifest-only and does not apply calibration or learning.",
        ),
    ]
    if parse_failures or any(check.status == "failed" for check in checks):
        status = "blocked_real_or_privileged_data" if blocked_refs else "failed"
    elif not artifacts:
        status = "empty_corpus"
    elif eligible:
        status = "synthetic_corpus_ready_for_review"
    else:
        status = "empty_corpus"

    return BudgetCalibrationCorpusReport(
        corpus_report_id=new_id("budgetcorpus"),
        status=status,  # type: ignore[arg-type]
        corpus_root_ref=_relative_ref(corpus_path, repo_path),
        artifact_count=len(artifacts),
        eligible_artifact_count=len(eligible),
        supporting_artifact_count=len(supporting),
        blocked_artifact_count=len(blocked_refs),
        artifact_kind_counts=dict(sorted(kind_counts.items())),
        calibration_role_counts=dict(sorted(role_counts.items())),
        artifacts=artifacts,
        checks=checks,
        required_next_gates=REQUIRED_NEXT_GATES,
        generated_at=now_iso(),
    )


def render_budget_calibration_corpus_report(report: BudgetCalibrationCorpusReport) -> str:
    lines = [
        "# Budget Calibration Corpus Report",
        "",
        f"**Report ID:** {report.corpus_report_id}",
        f"**Status:** {report.status}",
        f"**Corpus root:** {report.corpus_root_ref}",
        f"**Artifacts:** {report.artifact_count}",
        f"**Eligible for synthetic calibration review:** {report.eligible_artifact_count}",
        f"**Supporting only:** {report.supporting_artifact_count}",
        f"**Blocked:** {report.blocked_artifact_count}",
        "",
        "## Boundary",
        "",
        f"- Candidate only: {report.candidate_only}",
        f"- Synthetic only: {report.synthetic_only}",
        f"- Calibration applied: {report.calibration_applied}",
        f"- Profile mutation performed: {report.profile_mutation_performed}",
        f"- Template mutation performed: {report.template_mutation_performed}",
        f"- Budget mutation performed: {report.budget_mutation_performed}",
        f"- Carrier guideline mutation performed: {report.carrier_guideline_mutation_performed}",
        f"- Lake write performed: {report.lake_write_performed}",
        f"- SQLite write performed: {report.sqlite_write_performed}",
        f"- External writes performed: {report.external_writes_performed}",
        f"- Silent learning performed: {report.silent_learning_performed}",
        "",
        "## Required Next Gates",
        "",
        *(f"- {gate}" for gate in report.required_next_gates),
        "",
        "## Checks",
        "",
    ]
    for check in report.checks:
        lines.append(f"- {check.check_id}: {check.status}; {check.message}")
    lines.extend(["", "## Artifact Kind Counts", ""])
    for kind, count in report.artifact_kind_counts.items():
        lines.append(f"- {kind}: {count}")
    lines.extend(["", "## Artifacts", ""])
    for artifact in report.artifacts:
        lines.append(
            f"- `{artifact.artifact_ref}`: {artifact.artifact_kind}; "
            f"role={artifact.calibration_role}; eligibility={artifact.eligibility}"
        )
        if artifact.scope_failures or artifact.boundary_failures:
            lines.append(
                "  Failures: " + ", ".join([*artifact.scope_failures, *artifact.boundary_failures])
            )
    lines.extend(
        [
            "",
            "This corpus report classifies candidate evidence only. It does not calibrate, mutate, promote, write Lake records, or authorize real-data use.",
            "",
        ]
    )
    return "\n".join(lines)


def run_budget_calibration_corpus_audit(
    *,
    corpus_root: str | Path,
    out_dir: str | Path,
    repo_root: str | Path | None = None,
) -> tuple[BudgetCalibrationCorpusReport, Path]:
    report = build_budget_calibration_corpus_report(corpus_root, repo_root=repo_root)
    run_dir = Path(out_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    write_json(
        run_dir / BUDGET_CALIBRATION_CORPUS_REPORT_FILENAME,
        report.model_dump(mode="json"),
    )
    (run_dir / BUDGET_CALIBRATION_CORPUS_NOTES_FILENAME).write_text(
        render_budget_calibration_corpus_report(report),
        encoding="utf-8",
    )
    return report, run_dir
