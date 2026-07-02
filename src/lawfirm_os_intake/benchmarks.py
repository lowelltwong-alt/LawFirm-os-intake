from __future__ import annotations

from .models import BenchmarkSnapshotManifest, BudgetProposal


def validate_benchmark_snapshot(payload: dict) -> BenchmarkSnapshotManifest:
    manifest = BenchmarkSnapshotManifest.model_validate(payload)
    seen = {cell.benchmark_cell_id for cell in manifest.cells}
    if len(seen) != len(manifest.cells):
        raise ValueError("benchmark snapshot contains duplicate benchmark_cell_id values")
    for cell in manifest.cells:
        if not cell.page_sha256.startswith("sha256:"):
            raise ValueError(f"benchmark cell {cell.benchmark_cell_id} is missing sha256 hash")
    return manifest


def replay_budget_benchmark_refs(
    budget: BudgetProposal,
    manifest: BenchmarkSnapshotManifest,
) -> list[str]:
    available = {cell.benchmark_cell_id for cell in manifest.cells}
    missing: list[str] = []
    for line in budget.lines:
        if line.estimate_basis != "benchmark_cell":
            continue
        for ref in line.estimate_basis_refs:
            if ref not in available:
                missing.append(ref)
    return sorted(set(missing))
