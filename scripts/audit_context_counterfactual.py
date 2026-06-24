from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from lawfirm_os_intake.context_counterfactual_audit import (  # noqa: E402
    run_context_counterfactual_audit,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run a synthetic same-source, different-profile counterfactual audit."
    )
    parser.add_argument("--input", required=True)
    parser.add_argument("--baseline-profile", required=True)
    parser.add_argument("--comparison-profile", required=True)
    parser.add_argument("--out-dir", required=True)
    args = parser.parse_args()

    _, out_dir = run_context_counterfactual_audit(
        input_path=args.input,
        baseline_profile_path=args.baseline_profile,
        comparison_profile_path=args.comparison_profile,
        out_dir=args.out_dir,
    )
    print(out_dir / "context_counterfactual_audit_report.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
