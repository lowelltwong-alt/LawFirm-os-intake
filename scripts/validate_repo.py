from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))

from lawfirm_os_intake.public_data import validate_public_data_boundary  # noqa: E402

REQUIRED = [
    "README.md",
    "AI_WORK_START_HERE.md",
    "AI_TABLE_OF_CONTENTS.md",
    "AGENTS.md",
    "CLAUDE.md",
    "REPO_ROLE.md",
    "NON_GOALS.md",
    "MVP_BOUNDARY.md",
    "GOVERNANCE_BOUNDARY.md",
    "ROADMAP.md",
    "DEFINITION_OF_DONE.md",
    "PREMORTEM.md",
    "THREAT_MODEL.md",
    "repo_topology.yaml",
    "workflow/intake-to-budget.workflow.yaml",
]
FRONT_DOOR_REF_FILES = [
    "README.md",
    "AI_WORK_START_HERE.md",
    "AI_TABLE_OF_CONTENTS.md",
    "CLAUDE.md",
]
FRONT_DOOR_REF_SECTIONS = {
    "README.md": ["Start here"],
    "AI_WORK_START_HERE.md": ["Required reading order"],
}
FENCED_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
INLINE_CODE_RE = re.compile(r"`([^`\n]+)`")
DEFAULT_INTENSITY_SIGNOFF_PATH = Path("docs/governance/intensity_normalization_signoff.json")
RUST_TOOL_LADDER_REF = Path("config/rust-tool-ladder.json")
RUST_TOOL_LADDER_STAGES = [
    "s0_candidate",
    "s1_shadow",
    "s2_audit",
    "s3_cosign",
    "s4_authoritative",
]
RUST_TOOL_LADDER_AUTHORITY_FLAGS = {
    "rust_replacement_allowed": False,
    "no_connector_or_external_writes": True,
    "no_lake_or_sqlite_writes": True,
    "no_budget_or_matter_authority": True,
    "no_canonical_authority": True,
    "candidate_only": True,
}


def _looks_like_local_ref(value: str) -> bool:
    if not value or "://" in value or any(char.isspace() for char in value):
        return False
    if "*" in value:
        return False
    return value.endswith((".md", ".json", ".yaml", ".yml", "/")) or "/" in value


def _section_text(markdown: str, heading: str) -> str:
    pattern = re.compile(
        rf"^##\s+{re.escape(heading)}\s*$([\s\S]*?)(?=^##\s+|\Z)",
        re.MULTILINE,
    )
    match = pattern.search(markdown)
    return match.group(1) if match else ""


def front_door_file_refs(root: Path = ROOT) -> dict[str, list[str]]:
    refs: dict[str, list[str]] = {}
    for rel in FRONT_DOOR_REF_FILES:
        path = root / rel
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")
        sections = FRONT_DOOR_REF_SECTIONS.get(rel)
        if sections:
            text = "\n".join(_section_text(text, section) for section in sections)
        text = FENCED_BLOCK_RE.sub("", text)
        local_refs = sorted(
            {
                match.group(1).strip()
                for match in INLINE_CODE_RE.finditer(text)
                if _looks_like_local_ref(match.group(1).strip())
            }
        )
        refs[rel] = local_refs
    return refs


def missing_front_door_file_refs(root: Path = ROOT) -> list[str]:
    missing: list[str] = []
    for source, refs in front_door_file_refs(root).items():
        for ref in refs:
            if not (root / ref.rstrip("/")).exists():
                missing.append(f"{source} -> {ref}")
    return sorted(missing)


def public_data_boundary_failures(root: Path = ROOT) -> list[str]:
    ok, details = validate_public_data_boundary(root)
    return [] if ok else list(details.get("failures", []))


def _digest_json(value: object) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def intensity_signoff_gate_failures(root: Path = ROOT) -> list[str]:
    policy_path = root / "config" / "budget-driver-policy.yaml"
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    if not isinstance(policy, dict):
        return ["budget-driver-policy.yaml must be a mapping"]
    intensity_policy = policy.get("intensity_multiplier_policy", {})
    mode = (
        str(intensity_policy.get("normalization", "raw"))
        if isinstance(intensity_policy, dict)
        else "raw"
    )
    if mode == "raw":
        return []
    if mode != "baseline_relative":
        return [f"unsupported intensity normalization mode: {mode}"]

    signoff_path = root / DEFAULT_INTENSITY_SIGNOFF_PATH
    if not signoff_path.is_file():
        return [
            "baseline_relative intensity normalization requires approved signoff at "
            f"{DEFAULT_INTENSITY_SIGNOFF_PATH.as_posix()}"
        ]
    signoff = json.loads(signoff_path.read_text(encoding="utf-8"))
    if not isinstance(signoff, dict):
        return ["intensity normalization signoff must be a JSON object"]

    failures: list[str] = []
    if signoff.get("status") != "approved_for_baseline_relative":
        failures.append("intensity normalization signoff is not approved_for_baseline_relative")
    if not signoff.get("approved_by") or not signoff.get("approved_at"):
        failures.append("approved intensity normalization signoff requires approved_by/approved_at")
    if signoff.get("policy_id") != policy.get("policy_id", "unknown"):
        failures.append("intensity normalization signoff policy_id does not match active policy")
    if signoff.get("policy_sha256_after") != _digest_json(policy):
        failures.append(
            "intensity normalization signoff policy_sha256_after does not match active policy"
        )
    return failures


def _minimal_rust_tool_ladder_failures(root: Path = ROOT) -> list[str]:
    """Dependency-light gate for CI before editable dev dependencies are installed."""

    ladder_path = root / RUST_TOOL_LADDER_REF
    if not ladder_path.is_file():
        return [f"missing Rust tool ladder config: {RUST_TOOL_LADDER_REF.as_posix()}"]
    ladder = json.loads(ladder_path.read_text(encoding="utf-8"))
    if not isinstance(ladder, dict):
        return ["Rust tool ladder config must be a JSON object"]

    failures: list[str] = []
    if ladder.get("stage_order") != RUST_TOOL_LADDER_STAGES:
        failures.append("Rust tool ladder stage_order does not match required S0-S4 order")
    for field, expected in RUST_TOOL_LADDER_AUTHORITY_FLAGS.items():
        if ladder.get(field) is not expected:
            failures.append(f"Rust tool ladder {field} must be {expected!r}")

    policy_ref = ladder.get("rust_transition_policy_ref")
    policy: dict[str, object] = {}
    if isinstance(policy_ref, str) and policy_ref:
        policy_path = root / policy_ref
        if policy_path.is_file():
            policy = json.loads(policy_path.read_text(encoding="utf-8"))
        else:
            failures.append(f"Rust transition policy ref is missing: {policy_ref}")
    else:
        failures.append("Rust tool ladder must declare rust_transition_policy_ref")
    forbidden_scope = (
        set(policy.get("forbidden_rust_scope", [])) if isinstance(policy, dict) else set()
    )

    tools = ladder.get("tools")
    if not isinstance(tools, list) or not tools:
        return failures + ["Rust tool ladder must include at least one tool"]

    seen_tool_ids: set[str] = set()
    stage_index = {stage: index for index, stage in enumerate(RUST_TOOL_LADDER_STAGES)}
    for index, tool in enumerate(tools):
        if not isinstance(tool, dict):
            failures.append(f"Rust tool ladder tool[{index}] must be a JSON object")
            continue
        tool_id = str(tool.get("tool_id") or f"tool[{index}]")
        if tool_id in seen_tool_ids:
            failures.append(f"Rust tool ladder duplicate tool_id: {tool_id}")
        seen_tool_ids.add(tool_id)

        stage = str(tool.get("stage") or "")
        ceiling = str(tool.get("stage_ceiling") or "")
        if stage not in stage_index:
            failures.append(f"{tool_id}: invalid stage {stage!r}")
        if ceiling not in stage_index:
            failures.append(f"{tool_id}: invalid stage_ceiling {ceiling!r}")
        if (
            stage in stage_index
            and ceiling in stage_index
            and stage_index[stage] > stage_index[ceiling]
        ):
            failures.append(f"{tool_id}: stage exceeds stage_ceiling")

        scope_items = set(tool.get("scope_items", []))
        forbidden_hits = sorted(scope_items & forbidden_scope)
        if forbidden_hits:
            failures.append(f"{tool_id}: forbidden Rust scope items: {', '.join(forbidden_hits)}")

        gate_evidence = tool.get("gate_evidence", {})
        if not isinstance(gate_evidence, dict) or not gate_evidence.get(stage):
            failures.append(f"{tool_id}: missing gate_evidence for current stage {stage}")

        history = tool.get("history", [])
        if not isinstance(history, list) or not history:
            failures.append(f"{tool_id}: missing stage history")
        elif not isinstance(history[-1], dict) or history[-1].get("stage") != stage:
            failures.append(f"{tool_id}: latest history stage does not match current stage")

        for field in ("rust_replacement_allowed", "candidate_only", "non_authoritative"):
            expected = False if field == "rust_replacement_allowed" else True
            if tool.get(field) is not expected:
                failures.append(f"{tool_id}: {field} must be {expected!r}")
        if tool.get("rust_output_consumed_downstream") is True and stage not in {
            "s3_cosign",
            "s4_authoritative",
        }:
            failures.append(f"{tool_id}: Rust output cannot be consumed downstream before S3/S4")
    return failures


def rust_tool_ladder_failures(root: Path = ROOT) -> list[str]:
    try:
        from lawfirm_os_intake.rust_tool_ladder import (  # noqa: PLC0415
            RUST_TOOL_LADDER_REF as runtime_ladder_ref,
        )
        from lawfirm_os_intake.rust_tool_ladder import run_rust_tool_ladder_audit  # noqa: PLC0415
    except ModuleNotFoundError as exc:
        if exc.name == "pydantic":
            return _minimal_rust_tool_ladder_failures(root)
        raise

    with tempfile.TemporaryDirectory(prefix="intake-rust-ladder-") as temp_dir:
        report, _ = run_rust_tool_ladder_audit(
            ladder_path=root / runtime_ladder_ref,
            out_dir=Path(temp_dir),
            repo_root=root,
        )
    if report.status == "rust_tool_ladder_ready_for_review":
        return []
    return [
        f"{check.check_id}: {check.tool_id or 'ladder'}: {check.message}"
        for check in report.checks
        if check.status == "failed"
    ]


def fail(message: str) -> None:
    raise SystemExit(f"repository validation failed: {message}")


def main() -> int:
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(f"missing required file: {rel}")

    missing_front_door_refs = missing_front_door_file_refs(ROOT)
    if missing_front_door_refs:
        fail("broken front-door file refs: " + ", ".join(missing_front_door_refs))

    public_data_failures = public_data_boundary_failures(ROOT)
    if public_data_failures:
        fail("public data boundary failures: " + ", ".join(public_data_failures))

    intensity_failures = intensity_signoff_gate_failures(ROOT)
    if intensity_failures:
        fail("intensity normalization signoff gate failed: " + "; ".join(intensity_failures))

    ladder_failures = rust_tool_ladder_failures(ROOT)
    if ladder_failures:
        fail("rust tool ladder gate failed: " + "; ".join(ladder_failures))

    for path in ROOT.rglob("*.json"):
        try:
            json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            fail(f"invalid JSON {path.relative_to(ROOT)}: {exc}")

    for pattern in ("*.yaml", "*.yml"):
        for path in ROOT.rglob(pattern):
            try:
                yaml.safe_load(path.read_text(encoding="utf-8"))
            except Exception as exc:
                fail(f"invalid YAML {path.relative_to(ROOT)}: {exc}")

    registry = yaml.safe_load((ROOT / "prompts/registry.yaml").read_text(encoding="utf-8"))
    for entry in registry["prompts"]:
        path = ROOT / "prompts" / f"{entry['prompt_ref']}.md"
        actual = "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != entry["sha256"]:
            fail(f"prompt hash drift: {path.relative_to(ROOT)}")

    for path in (ROOT / "contracts/candidate").glob("*.json"):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("canonical") is not False:
            fail(f"candidate registry masquerades as canon: {path.relative_to(ROOT)}")

    # Generated artifacts are only a defect when git does not already ignore
    # them (i.e. when they could be committed). A fresh clone that follows the
    # README verbatim runs `pip install -e .` first, which unavoidably creates
    # src/*.egg-info; failing on ignored artifacts made the documented
    # quickstart fail on every clean checkout.
    forbidden = list(ROOT.rglob("__pycache__")) + list(ROOT.rglob("*.egg-info"))
    if forbidden:
        probe = subprocess.run(
            ["git", "-C", str(ROOT), "check-ignore", "--stdin"],
            input="\n".join(str(p.relative_to(ROOT)) for p in forbidden),
            capture_output=True,
            text=True,
        )
        ignored = set(probe.stdout.splitlines())
        not_ignored = [
            p for p in forbidden if str(p.relative_to(ROOT)) not in ignored
        ]
        if not_ignored:
            fail("generated cache/package metadata is present and not gitignored")

    print("repository validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
