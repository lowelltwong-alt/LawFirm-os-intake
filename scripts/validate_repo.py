from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys
import yaml

ROOT = Path(__file__).resolve().parents[1]
REQUIRED = [
    "README.md",
    "AI_WORK_START_HERE.md",
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


def fail(message: str) -> None:
    raise SystemExit(f"repository validation failed: {message}")


def main() -> int:
    for rel in REQUIRED:
        if not (ROOT / rel).is_file():
            fail(f"missing required file: {rel}")

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
