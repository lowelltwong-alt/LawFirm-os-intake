"""Regenerate the frozen LW1 synthetic corpus + manifest (deterministic).

Usage: ``python scripts/generate_synthetic_corpus.py``. The in-repo corpus is
frozen at N=52 (P10); larger corpora are reproducible from the same parameters
into a scratch/output dir and are not committed.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.dont_write_bytecode = True
sys.path.insert(0, str(ROOT / "src"))

from lawfirm_os_intake.synthetic_corpus_generator import freeze_corpus  # noqa: E402


def main() -> int:
    manifest = freeze_corpus(ROOT)
    print(
        f"froze corpus {manifest.corpus_id}: {manifest.case_count} cases "
        f"({manifest.train_count} train / {manifest.holdout_count} holdout)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
