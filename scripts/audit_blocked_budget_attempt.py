from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawfirm_os_intake.blocked_budget_audit import (  # noqa: E402
    run_blocked_budget_attempt_audit,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run and audit a synthetic non-confirmed budget attempt."
    )
    parser.add_argument("--preflight-packet", required=True)
    parser.add_argument("--confirmation-template", required=True)
    parser.add_argument("--practice-profile", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    _, out_dir = run_blocked_budget_attempt_audit(
        preflight_packet_path=args.preflight_packet,
        confirmation_template_path=args.confirmation_template,
        practice_profile_path=args.practice_profile,
        out_dir=args.out_dir,
    )
    print(out_dir / "blocked_budget_attempt_audit_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
