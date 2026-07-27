"""Regenerate and freeze the driver-stratified synthetic corpus (DT4).

Byte-identical regeneration from the pinned seed; run after any deliberate
generator or contract change, then commit the refreshed artifacts.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from lawfirm_os_intake.stratified_corpus_generator import freeze_stratified_corpus  # noqa: E402


def main() -> int:
    manifest = freeze_stratified_corpus(REPO_ROOT)
    print(
        f"froze stratified corpus {manifest.corpus_id}: {manifest.case_count} matters "
        f"({manifest.train_count} train / {manifest.holdout_count} holdout)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
