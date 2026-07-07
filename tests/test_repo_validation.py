import importlib.util
import json
import yaml


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


def test_repo_validation_detects_public_catalog_ingestion_drift(tmp_path, repo_root):
    validate_repo = _load_validate_repo(repo_root)
    (tmp_path / "config").mkdir()
    (tmp_path / "examples/public").mkdir(parents=True)
    policy = yaml.safe_load((repo_root / "config/data_policy.yaml").read_text(encoding="utf-8"))
    catalog = yaml.safe_load(
        (repo_root / "examples/public/catalog.yaml").read_text(encoding="utf-8")
    )
    catalog["sources"][0]["direct_runtime_ingestion"] = True
    (tmp_path / "config/data_policy.yaml").write_text(
        yaml.safe_dump(policy, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_path / "examples/public/catalog.yaml").write_text(
        yaml.safe_dump(catalog, sort_keys=False),
        encoding="utf-8",
    )
    (tmp_path / "examples/public/README.md").write_text(
        "Planning-only public metadata catalog.\n",
        encoding="utf-8",
    )

    assert validate_repo.public_data_boundary_failures(tmp_path) == [
        "catalog_source_allows_direct_runtime_ingestion"
    ]


def test_repo_validation_minimal_rust_ladder_gate_passes_without_runtime_imports(repo_root):
    validate_repo = _load_validate_repo(repo_root)

    assert validate_repo._minimal_rust_tool_ladder_failures(repo_root) == []


def test_repo_validation_minimal_rust_ladder_gate_blocks_replacement_flag(tmp_path, repo_root):
    validate_repo = _load_validate_repo(repo_root)
    (tmp_path / "config").mkdir()
    policy = json.loads(
        (repo_root / "config/rust-ingestion-transition-policy.json").read_text(encoding="utf-8")
    )
    ladder = json.loads((repo_root / "config/rust-tool-ladder.json").read_text(encoding="utf-8"))
    ladder["rust_replacement_allowed"] = True

    (tmp_path / "config/rust-ingestion-transition-policy.json").write_text(
        json.dumps(policy, indent=2),
        encoding="utf-8",
    )
    (tmp_path / "config/rust-tool-ladder.json").write_text(
        json.dumps(ladder, indent=2),
        encoding="utf-8",
    )

    assert (
        "Rust tool ladder rust_replacement_allowed must be False"
        in validate_repo._minimal_rust_tool_ladder_failures(tmp_path)
    )
