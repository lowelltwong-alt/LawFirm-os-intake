from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys
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

    forbidden = list(ROOT.rglob("__pycache__")) + list(ROOT.rglob("*.egg-info"))
    if forbidden:
        fail("generated cache/package metadata is present")

    print("repository validation passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
