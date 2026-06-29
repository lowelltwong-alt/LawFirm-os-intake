from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawfirm_os_intake.starter_audit import (  # noqa: E402
    build_starter_release_audit_report,
    enforce_starter_release_audit,
)
from lawfirm_os_intake.util import write_json  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Audit a generated starter demo against release invariants."
    )
    parser.add_argument("--demo-dir", required=True)
    parser.add_argument("--repo-root", default=str(ROOT))
    parser.add_argument("--out")
    args = parser.parse_args()

    demo_dir = Path(args.demo_dir)
    out = Path(args.out) if args.out else demo_dir / "budget" / "starter_release_audit_report.json"
    report = build_starter_release_audit_report(
        repo_root=args.repo_root,
        demo_dir=demo_dir,
    )
    write_json(out, report.model_dump(mode="json"))
    enforce_starter_release_audit(report)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
