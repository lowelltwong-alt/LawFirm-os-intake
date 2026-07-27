"""The evaluation split must actually gate scoring, not merely describe itself.

The tests that matter here are the negative ones: a split audit that cannot fail
is not a control. Each contamination mode gets an explicit test that the audit
catches it.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from lawfirm_os_intake.evaluation_split import (
    build_split_assignment,
    enforce_evaluation_split_audit_report,
    run_evaluation_split_audit,
)
from lawfirm_os_intake.models import EvaluationSplitManifest

SPLIT_REF = "examples/synthetic/evaluation/intake-evaluation-split.json"


def _manifest(repo_root: Path) -> EvaluationSplitManifest:
    return EvaluationSplitManifest.model_validate(
        json.loads((repo_root / SPLIT_REF).read_text(encoding="utf-8"))
    )


def _write_manifest(path: Path, manifest: EvaluationSplitManifest) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(manifest.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def test_checked_in_split_passes_against_the_real_corpus(repo_root: Path, tmp_path: Path) -> None:
    report, out_dir = run_evaluation_split_audit(
        split_manifest_path=repo_root / SPLIT_REF,
        out_dir=tmp_path / "audit",
        repo_root=repo_root,
        generated_at="2026-07-27T00:00:00Z",
    )

    assert report.status == "passed", [c for c in report.checks if c.status == "failed"]
    assert report.holdout_count >= 1
    assert report.development_count >= 1
    enforce_evaluation_split_audit_report(report)

    persisted = json.loads(
        (out_dir / "evaluation_split_audit_report.json").read_text(encoding="utf-8")
    )
    assert persisted["status"] == "passed"
    assert persisted["external_writes_performed"] is False
    assert persisted["lake_write_performed"] is False
    assert persisted["candidate_only"] is True
    assert (out_dir / "evaluation_split_audit_report.md").is_file()


def test_edited_holdout_fixture_is_detected(repo_root: Path, tmp_path: Path) -> None:
    """THE contamination control: a holdout case edited after review breaks its
    digest, so numbers produced against the old content are no longer
    attributable to this split."""

    manifest = _manifest(repo_root)
    holdout = next(item for item in manifest.assignments if item.partition == "holdout")
    tampered = manifest.model_copy(
        update={
            "assignments": [
                item.model_copy(update={"fixture_digest": "sha256:" + "0" * 64})
                if item.fixture_ref == holdout.fixture_ref
                else item
                for item in manifest.assignments
            ]
        }
    )
    path = tmp_path / "tampered-split.json"
    _write_manifest(path, tampered)

    report, _ = run_evaluation_split_audit(
        split_manifest_path=path, out_dir=tmp_path / "audit", repo_root=repo_root
    )

    assert report.status == "failed"
    drift = next(c for c in report.checks if c.check_id == "pinned_fixture_digests_match_disk")
    assert drift.status == "failed"
    assert holdout.fixture_ref in drift.offending_refs
    with pytest.raises(ValueError, match="pinned_fixture_digests_match_disk"):
        enforce_evaluation_split_audit_report(report)


def test_missing_fixture_is_detected(repo_root: Path, tmp_path: Path) -> None:
    manifest = _manifest(repo_root)
    ghost = build_split_assignment(
        repo_root=repo_root,
        fixture_ref=manifest.assignments[0].fixture_ref,
        partition="development",
        rationale="placeholder",
    ).model_copy(update={"fixture_ref": "examples/synthetic/inbound/does-not-exist.json"})
    broken = manifest.model_copy(update={"assignments": [*manifest.assignments, ghost]})
    path = tmp_path / "missing-split.json"
    _write_manifest(path, broken)

    report, _ = run_evaluation_split_audit(
        split_manifest_path=path, out_dir=tmp_path / "audit", repo_root=repo_root
    )

    assert report.status == "failed"
    check = next(c for c in report.checks if c.check_id == "all_assigned_fixtures_exist")
    assert check.status == "failed"
    assert "examples/synthetic/inbound/does-not-exist.json" in check.offending_refs


def test_holdout_named_fixture_cannot_hide_in_development(repo_root: Path, tmp_path: Path) -> None:
    """A case authored as a holdout must not be quietly reassigned to
    development; the contradiction is surfaced rather than resolved."""

    manifest = _manifest(repo_root)
    holdout = next(item for item in manifest.assignments if item.partition == "holdout")
    misfiled = manifest.model_copy(
        update={
            "assignments": [
                item.model_copy(update={"partition": "development"})
                if item.fixture_ref == holdout.fixture_ref
                else item
                for item in manifest.assignments
            ]
        }
    )
    path = tmp_path / "misfiled-split.json"
    _write_manifest(path, misfiled)

    report, _ = run_evaluation_split_audit(
        split_manifest_path=path, out_dir=tmp_path / "audit", repo_root=repo_root
    )

    assert report.status == "failed"
    check = next(
        c for c in report.checks if c.check_id == "no_holdout_named_fixture_in_development"
    )
    assert check.status == "failed"
    assert holdout.fixture_ref in check.offending_refs


def test_split_with_no_holdout_is_rejected_at_the_model(repo_root: Path) -> None:
    """A partition with nothing reserved cannot gate scoring, so it is invalid
    at construction rather than merely failing an audit later."""

    payload = _manifest(repo_root).model_dump(mode="json")
    payload["assignments"] = [
        {**item, "partition": "development"} for item in payload["assignments"]
    ]
    with pytest.raises(ValueError, match="at least one holdout"):
        EvaluationSplitManifest.model_validate(payload)


def test_split_with_no_development_is_rejected_at_the_model(repo_root: Path) -> None:
    payload = _manifest(repo_root).model_dump(mode="json")
    payload["assignments"] = [{**item, "partition": "holdout"} for item in payload["assignments"]]
    with pytest.raises(ValueError, match="at least one development"):
        EvaluationSplitManifest.model_validate(payload)


def test_unreviewed_split_cannot_gate_scoring(repo_root: Path) -> None:
    manifest = _manifest(repo_root)
    with pytest.raises(ValueError, match="unreviewed split manifest"):
        EvaluationSplitManifest.model_validate(
            {**manifest.model_dump(mode="json"), "reviewed": False}
        )


def test_duplicate_fixture_assignment_is_rejected(repo_root: Path) -> None:
    manifest = _manifest(repo_root)
    payload = manifest.model_dump(mode="json")
    payload["assignments"] = [*payload["assignments"], payload["assignments"][0]]
    with pytest.raises(ValueError, match="may not appear twice"):
        EvaluationSplitManifest.model_validate(payload)
