import importlib.util


def _load_validate_repo(repo_root):
    script = repo_root / "scripts/validate_repo.py"
    spec = importlib.util.spec_from_file_location("validate_repo", script)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_front_door_file_refs_are_current(repo_root):
    validate_repo = _load_validate_repo(repo_root)

    assert validate_repo.missing_front_door_file_refs(repo_root) == []


def test_front_door_file_ref_validation_detects_missing_paths(tmp_path, repo_root):
    validate_repo = _load_validate_repo(repo_root)
    (tmp_path / "README.md").write_text(
        "# Local Front Door\n\n## Start here\n\n1. `docs/missing-boundary.md`\n",
        encoding="utf-8",
    )

    assert validate_repo.missing_front_door_file_refs(tmp_path) == [
        "README.md -> docs/missing-boundary.md"
    ]
