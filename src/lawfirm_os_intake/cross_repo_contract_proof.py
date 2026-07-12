from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
from hashlib import sha256

from .models import CrossRepoContractProofReport, OrchestratorOwnerReviewRequest
from .util import digest_text, load_json, now_iso, write_json


CROSS_REPO_CONTRACT_PROOF_REPORT_FILENAME = "cross_repo_contract_proof_report.json"
CROSS_REPO_CONTRACT_PROOF_NOTES_FILENAME = "cross_repo_contract_proof_report.md"


def _stable_id(*parts: str) -> str:
    return "crossrepocontractproof_" + digest_text("|".join(parts)).split(":", 1)[1][:20]


def _bare_digest(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _run(command: list[str], *, cwd: Path, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)


def _repo_commit(repo_root: Path, *, required_path: Path) -> str:
    if not (repo_root / ".git").exists():
        raise ValueError(f"owner repo is not a git worktree: {repo_root}")
    if not required_path.is_file():
        raise ValueError(f"owner repo is missing required validation surface: {required_path}")
    status = _run(["git", "status", "--porcelain"], cwd=repo_root, env=os.environ.copy())
    if status.returncode != 0:
        raise ValueError(
            f"could not inspect owner worktree status: {repo_root}: {status.stderr.strip()}"
        )
    if status.stdout.strip():
        raise ValueError(f"owner worktree must be clean for contract proof: {repo_root}")
    commit = _run(["git", "rev-parse", "HEAD"], cwd=repo_root, env=os.environ.copy())
    if commit.returncode != 0 or not commit.stdout.strip():
        raise ValueError(f"could not resolve owner commit: {repo_root}: {commit.stderr.strip()}")
    return commit.stdout.strip()


def _owner_env(repo_root: Path) -> dict[str, str]:
    env = os.environ.copy()
    src = str(repo_root / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


def _load_json_stdout(result: subprocess.CompletedProcess[str], *, label: str) -> dict[str, object]:
    if result.returncode != 0:
        raise ValueError(f"{label} failed ({result.returncode}): {result.stderr.strip()}")
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} did not emit JSON: {result.stdout!r}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} emitted a non-object JSON payload")
    return payload


def _require_path(value: object, *, root: Path, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} is missing a path")
    path = Path(value).resolve()
    try:
        path.relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"{label} must stay inside the requested output directory") from exc
    if not path.is_file():
        raise ValueError(f"{label} does not exist: {path}")
    return path


def _expect(payload: dict[str, object], field: str, expected: object, *, label: str) -> None:
    if payload.get(field) != expected:
        raise ValueError(f"{label} expected {field}={expected!r}, got {payload.get(field)!r}")


def render_cross_repo_contract_proof(report: CrossRepoContractProofReport) -> str:
    return "\n".join(
        [
            "# Cross-Repo Contract Proof",
            "",
            f"**Proof ID:** {report.contract_proof_id}",
            f"**Status:** {report.status}",
            f"**Intake request:** `{report.request_ref}`",
            f"**Orchestrator commit:** `{report.orchestrator_commit}`",
            f"**Exception Lake commit:** `{report.exception_lake_commit}`",
            "",
            "## Verified Handoff",
            "",
            f"- Orchestrator owner packet: `{report.owner_packet_ref}`",
            f"- Orchestrator status: `{report.owner_packet_status}`",
            f"- Lake review packet: `{report.lake_review_packet_ref}`",
            f"- Lake review status: `{report.lake_review_packet_status}`",
            f"- Lake validator status: `{report.lake_validation_status}`",
            "",
            "## Boundary",
            "",
            "- Synthetic and candidate-only evidence only.",
            "- The expected result remains blocked for owner and human review.",
            "- No Lake/SQLite admission, connector call, external write, budget submission, matter opening, or conflict clearance is authorized.",
            "",
        ]
    )


def run_cross_repo_contract_proof(
    *,
    request_path: str | Path,
    orchestrator_root: str | Path,
    exception_lake_root: str | Path,
    out_dir: str | Path,
) -> tuple[CrossRepoContractProofReport, Path]:
    request_file = Path(request_path).resolve()
    raw_request = load_json(request_file)
    if not isinstance(raw_request, dict):
        raise ValueError("cross-repo contract proof request must be a JSON object")
    if raw_request.get("synthetic") is not True or any(
        (
            raw_request.get("contains_real_firm_data") is True,
            raw_request.get("contains_real_client_data") is True,
            raw_request.get("contains_real_matter_data") is True,
            raw_request.get("contains_privileged_data") is True,
        )
    ):
        raise ValueError("cross-repo contract proof accepts synthetic no-real-data requests only")
    request = OrchestratorOwnerReviewRequest.model_validate(raw_request)

    orchestrator_repo = Path(orchestrator_root).resolve()
    lake_repo = Path(exception_lake_root).resolve()
    proof_root = Path(out_dir).resolve()
    proof_root.mkdir(parents=True, exist_ok=True)
    if proof_root.is_relative_to(orchestrator_repo) or proof_root.is_relative_to(lake_repo):
        raise ValueError("contract proof output must not be written inside an owner repository")

    orchestrator_commit = _repo_commit(
        orchestrator_repo,
        required_path=orchestrator_repo / "src/lawfirm_os_orchestrator/cli.py",
    )
    lake_commit = _repo_commit(
        lake_repo,
        required_path=lake_repo / "scripts/validate_intake_lake_admission_review_packet.py",
    )
    orchestrator_out = proof_root / "orchestrator"
    ledger_out = proof_root / "ledger"
    owner_result = _run(
        [
            sys.executable,
            "-m",
            "lawfirm_os_orchestrator",
            "intake",
            "prepare-owner-packet",
            "--input",
            str(request_file),
            "--out-dir",
            str(orchestrator_out),
            "--ledger-dir",
            str(ledger_out),
            "--stdout",
            "json",
        ],
        cwd=orchestrator_repo,
        env=_owner_env(orchestrator_repo),
    )
    owner_summary = _load_json_stdout(owner_result, label="Orchestrator owner-packet command")
    _expect(
        owner_summary, "status", "blocked_pending_owner_review", label="Orchestrator owner packet"
    )
    _expect(owner_summary, "lake_handoff_allowed", False, label="Orchestrator owner packet")
    _expect(
        owner_summary,
        "not_authorized_for_client_submission",
        True,
        label="Orchestrator owner packet",
    )
    owner_packet = _require_path(
        owner_summary.get("packet_path"), root=proof_root, label="owner packet"
    )

    lake_out = proof_root / "lake-review"
    lake_result = _run(
        [
            sys.executable,
            "-m",
            "lawfirm_os_orchestrator",
            "intake",
            "build-lake-admission-review-packet",
            "--owner-packet",
            str(owner_packet),
            "--out-dir",
            str(lake_out),
            "--ledger-dir",
            str(ledger_out),
            "--stdout",
            "json",
        ],
        cwd=orchestrator_repo,
        env=_owner_env(orchestrator_repo),
    )
    lake_summary = _load_json_stdout(lake_result, label="Orchestrator Lake-review command")
    _expect(
        lake_summary,
        "status",
        "blocked_pending_exception_lake_owner_review",
        label="Orchestrator Lake review packet",
    )
    _expect(lake_summary, "lake_handoff_allowed", False, label="Orchestrator Lake review packet")
    _expect(
        lake_summary,
        "sqlite_write_authorized_now",
        False,
        label="Orchestrator Lake review packet",
    )
    lake_packet = _require_path(
        lake_summary.get("packet_path"), root=proof_root, label="Lake review packet"
    )

    validation_report = proof_root / "exception_lake_validation_report.json"
    lake_validation = _run(
        [
            sys.executable,
            "scripts/validate_intake_lake_admission_review_packet.py",
            "--packet",
            str(lake_packet),
            "--report-out",
            str(validation_report),
        ],
        cwd=lake_repo,
        env=_owner_env(lake_repo),
    )
    if lake_validation.returncode != 0:
        raise ValueError(
            "Exception Lake admission-review validator failed "
            f"({lake_validation.returncode}): {lake_validation.stderr.strip()}"
        )
    validation_payload = load_json(validation_report)
    if not isinstance(validation_payload, dict):
        raise ValueError("Exception Lake validator emitted a non-object report")
    _expect(
        validation_payload,
        "status",
        "passed_candidate_packet_validation",
        label="Exception Lake validation",
    )
    for flag in (
        "admission_allowed_now",
        "lake_write_authority_now",
        "sqlite_write_authorized_now",
        "raw_payload_storage_allowed",
    ):
        _expect(validation_payload, flag, False, label="Exception Lake validation")

    report = CrossRepoContractProofReport(
        contract_proof_id=_stable_id(request.request_id, orchestrator_commit, lake_commit),
        status="passed_candidate_contract_proof",
        request_id=request.request_id,
        request_ref=str(request_file),
        request_sha256=_bare_digest(request_file),
        orchestrator_commit=orchestrator_commit,
        exception_lake_commit=lake_commit,
        owner_packet_ref=str(owner_packet),
        owner_packet_sha256=_bare_digest(owner_packet),
        owner_packet_status="blocked_pending_owner_review",
        lake_review_packet_ref=str(lake_packet),
        lake_review_packet_sha256=_bare_digest(lake_packet),
        lake_review_packet_status="blocked_pending_exception_lake_owner_review",
        lake_validation_report_ref=str(validation_report),
        lake_validation_report_sha256=_bare_digest(validation_report),
        lake_validation_status="passed_candidate_packet_validation",
        generated_at=now_iso(),
    )
    write_json(
        proof_root / CROSS_REPO_CONTRACT_PROOF_REPORT_FILENAME, report.model_dump(mode="json")
    )
    (proof_root / CROSS_REPO_CONTRACT_PROOF_NOTES_FILENAME).write_text(
        render_cross_repo_contract_proof(report), encoding="utf-8"
    )
    return report, proof_root
