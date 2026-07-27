"""Fail when a tracked file reintroduces a local absolute path.

Publication guard for the D-1 "accept history, fix forward" decision
(2026-07-26): history retains old absolute-path strings, so this check is the
floor that keeps HEAD clean going forward. It scans tracked text files for
Windows/POSIX user-home paths and OneDrive desktop layouts.

Environment indirection is the sanctioned alternative (`${DAD_HUB}`,
`$env:DAD_HUB`, `~/.dad/hub.json`); see DIGITAL_ASSET_DIRECTORY_HANDOFF.md.

Usage:
    python scripts/check_no_local_paths.py
Exit codes: 0 clean, 1 findings, 2 execution problem (fail closed).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

PATTERNS = (
    re.compile(r"[A-Za-z]:[\\/]Users[\\/]"),
    re.compile(r"(?<![\w.])/(?:home|Users)/[A-Za-z0-9._-]+/"),
    re.compile(r"OneDrive[\\/]Desktop"),
)

TEXT_SUFFIXES = {
    ".md",
    ".txt",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".toml",
    ".cfg",
    ".ini",
    ".py",
    ".ps1",
    ".sh",
    ".csv",
    ".rs",
    ".ts",
    ".tsx",
    ".js",
    ".html",
}

# The guard documents the patterns it forbids; never self-flag. The remediation
# TRACE records legitimately discuss the old paths in fenced code as history.
EXEMPT = {Path("scripts/check_no_local_paths.py")}


def main() -> int:
    try:
        proc = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "-z"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        print(f"EXECUTION ERROR (failing closed): {exc}")
        return 2

    findings: list[str] = []
    for rel in (p for p in proc.stdout.split("\0") if p):
        rel_path = Path(rel)
        if rel_path in EXEMPT or rel_path.suffix.lower() not in TEXT_SUFFIXES:
            continue
        try:
            text = (ROOT / rel_path).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for pattern in PATTERNS:
            match = pattern.search(text)
            if match:
                line = text.count("\n", 0, match.start()) + 1
                findings.append(f"{rel}:{line}: {match.group(0)}")
                break

    if findings:
        print("LOCAL ABSOLUTE PATH CHECK FAILED")
        for finding in findings:
            print(f"- {finding}")
        print(
            "Use ${DAD_HUB} / $env:DAD_HUB / ~/.dad/hub.json indirection or a "
            "generic placeholder instead of a machine-specific path."
        )
        return 1
    print("local absolute path check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
