from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from .models import ContractStateCheck, ContractStateDependency, ContractStateReport
from .util import new_id, now_iso


REQUIRED_REPOS = {
    "LawFirm-os-semantic-substrate": "control",
    "LawFirm-os-orchestrator": "execution",
    "LawFirm-os-exceptions-lake-runtime": "evidence",
    "LawFirm-os-legal-knowledge-runtime": "legal_knowledge_runtime",
    "LawFirm-os-skills-registry": "skills_registry",
}
REVIEWED_LOCK_STATUS = "reviewed_seed_lock"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _check(check_id: str, ok: bool, message: str, evidence_refs: list[str]) -> ContractStateCheck:
    return ContractStateCheck(
        check_id=check_id,
        status="passed" if ok else "failed",
        message=message,
        evidence_refs=evidence_refs,
    )


def _read_json_dict(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing {path.name}")
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid JSON {path.name}: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.name} must contain a JSON object")
        return None
    return payload


def _read_yaml_dict(path: Path, errors: list[str]) -> dict[str, Any] | None:
    if not path.is_file():
        errors.append(f"missing {path.name}")
        return None
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    except Exception as exc:
        errors.append(f"invalid YAML {path.name}: {exc}")
        return None
    if not isinstance(payload, dict):
        errors.append(f"{path.name} must contain a YAML mapping")
        return None
    return payload


def _lock_repos(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    repos = payload.get("repos") if payload else None
    if not isinstance(repos, list):
        return {}
    result = {}
    for item in repos:
        if isinstance(item, dict) and isinstance(item.get("repo"), str):
            result[item["repo"]] = item
    return result


def _topology_repos(payload: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    repos = payload.get("repos") if payload else None
    if isinstance(repos, dict):
        return {name: value for name, value in repos.items() if isinstance(value, dict)}
    if isinstance(repos, list):
        return {
            item["repo"]: item
            for item in repos
            if isinstance(item, dict) and isinstance(item.get("repo"), str)
        }
    return {}


def _valid_sha(value: Any) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 40
        and all(character in "0123456789abcdef" for character in value)
    )


def _dependencies(
    lock_repos: dict[str, dict[str, Any]],
    topology_repos: dict[str, dict[str, Any]],
) -> list[ContractStateDependency]:
    dependencies = []
    for repo in sorted(REQUIRED_REPOS):
        locked = lock_repos.get(repo, {})
        topology = topology_repos.get(repo, {})
        topology_matches = (
            bool(locked)
            and bool(topology)
            and locked.get("sha") == topology.get("sha")
            and locked.get("authority_plane") == topology.get("authority_plane")
            and locked.get("remote") == topology.get("remote")
        )
        verified = (
            bool(locked)
            and locked.get("ref_type") == "git_sha"
            and _valid_sha(locked.get("sha"))
            and locked.get("authority_plane") == REQUIRED_REPOS[repo]
            and topology_matches
        )
        dependencies.append(
            ContractStateDependency(
                repo=repo,
                remote=locked.get("remote"),
                branch=locked.get("branch"),
                ref_type=locked.get("ref_type"),
                sha=locked.get("sha"),
                authority_plane=locked.get("authority_plane"),
                local_folder=locked.get("local_folder"),
                topology_sha=topology.get("sha"),
                topology_authority_plane=topology.get("authority_plane"),
                topology_matches_lock=topology_matches,
                status="verified" if verified else "invalid",
            )
        )
    return dependencies


def build_contract_state_report(
    run_id: str,
    repo_root: str | Path | None = None,
) -> ContractStateReport:
    root = Path(repo_root) if repo_root else _repo_root()
    lockfile = root / "contracts.lock.json"
    topology_lock = root / "repo_topology.lock.yaml"
    evidence_refs = [str(lockfile), str(topology_lock)]
    errors: list[str] = []

    lock_payload = _read_json_dict(lockfile, errors)
    topology_payload = _read_yaml_dict(topology_lock, errors)
    locked_repos = _lock_repos(lock_payload)
    topology = _topology_repos(topology_payload)
    dependencies = _dependencies(locked_repos, topology)

    required_repos_present = set(REQUIRED_REPOS).issubset(locked_repos)
    immutable_sha_pins = required_repos_present and all(
        locked_repos[repo].get("ref_type") == "git_sha"
        and _valid_sha(locked_repos[repo].get("sha"))
        for repo in REQUIRED_REPOS
    )
    authority_planes_match = required_repos_present and all(
        locked_repos[repo].get("authority_plane") == plane for repo, plane in REQUIRED_REPOS.items()
    )
    topology_matches_lock = bool(topology) and all(
        dependency.topology_matches_lock for dependency in dependencies
    )
    non_authority_rule = lock_payload.get("non_authority_rule") if lock_payload else None
    non_authority_rule_present = (
        isinstance(non_authority_rule, str)
        and "does not create canonical" in non_authority_rule.casefold()
    )
    lock_status = lock_payload.get("status") if lock_payload else None
    topology_status = topology_payload.get("status") if topology_payload else None

    checks = [
        _check(
            "contract_lockfile_present",
            lock_payload is not None,
            "contracts.lock.json is present and parseable.",
            [str(lockfile)],
        ),
        _check(
            "topology_lock_present",
            topology_payload is not None,
            "repo_topology.lock.yaml is present and parseable.",
            [str(topology_lock)],
        ),
        _check(
            "reviewed_seed_lock_status",
            lock_status == REVIEWED_LOCK_STATUS and topology_status == REVIEWED_LOCK_STATUS,
            "Both lock files declare reviewed_seed_lock status.",
            evidence_refs,
        ),
        _check(
            "required_governing_repos_present",
            required_repos_present,
            "All five governing LawFirm OS repos are listed in the contract lock.",
            [str(lockfile)],
        ),
        _check(
            "immutable_git_sha_pins",
            immutable_sha_pins,
            "All governing repos are pinned by 40-character git SHAs.",
            [str(lockfile)],
        ),
        _check(
            "authority_planes_match",
            authority_planes_match,
            "Locked authority planes match the intake authority map.",
            [str(lockfile)],
        ),
        _check(
            "topology_matches_contract_lock",
            topology_matches_lock,
            "The topology lock matches contract lock SHAs, remotes, and authority planes.",
            evidence_refs,
        ),
        _check(
            "intake_non_authority_rule_present",
            non_authority_rule_present,
            "The lock preserves intake's non-authority rule.",
            [str(lockfile)],
        ),
    ]
    status = (
        "passed" if not errors and all(check.status == "passed" for check in checks) else "failed"
    )
    return ContractStateReport(
        contract_state_report_id=new_id("contractstate"),
        run_id=run_id,
        status=status,
        lock_status=lock_status if isinstance(lock_status, str) else None,
        lockfile_ref=str(lockfile),
        topology_lock_ref=str(topology_lock),
        dependencies=dependencies,
        checks=checks,
        errors=errors,
        generated_at=now_iso(),
    )


def enforce_contract_state(report: ContractStateReport) -> None:
    if report.status == "passed":
        return
    failed = [check.check_id for check in report.checks if check.status == "failed"]
    detail = ", ".join(failed + report.errors)
    raise ValueError(f"contract state gate failed: {detail}")
