import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VALIDATOR = ROOT / "scripts" / "validate_governance_dependency_map_mirror.py"


class GovernanceDependencyMapMirrorTests(unittest.TestCase):
    def run_validator(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, str(VALIDATOR), *args],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_mirror_validation_passes(self) -> None:
        result = self.run_validator("--mirror-updated", "true")
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_watched_change_requires_mirror_update(self) -> None:
        result = self.run_validator(
            "--changed-file",
            "GOVERNANCE_BOUNDARY.md",
            "--mirror-updated",
            "false",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mirror must be updated", result.stderr)

    def test_contract_topology_lock_change_requires_mirror_update(self) -> None:
        result = self.run_validator(
            "--changed-file",
            "repo_topology.lock.yaml",
            "--mirror-updated",
            "false",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mirror must be updated", result.stderr)

    def test_build_verification_change_requires_mirror_update(self) -> None:
        result = self.run_validator(
            "--changed-file",
            "BUILD_VERIFICATION.md",
            "--mirror-updated",
            "false",
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("mirror must be updated", result.stderr)

    def test_watched_change_passes_when_mirror_updates(self) -> None:
        result = self.run_validator(
            "--changed-file",
            "GOVERNANCE_BOUNDARY.md",
            "--changed-file",
            ".ai/control/governance-dependency-map-mirror.json",
            "--mirror-updated",
            "true",
        )
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
