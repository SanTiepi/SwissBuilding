from __future__ import annotations

import subprocess
import sys
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]

GROUPS = {
    "wedge": [
        "tests/test_auth.py",
        "tests/test_buildings.py",
        "tests/test_diagnostics.py",
        "tests/test_readiness.py",
        "tests/test_dossier.py",
        "tests/test_authority_packs.py",
        "tests/test_seed_verify.py",
    ],
    "operating": [
        "tests/test_passport_service.py",
        "tests/test_time_machine.py",
        "tests/test_post_works.py",
        "tests/test_transaction_readiness.py",
        "tests/test_change_signals.py",
    ],
    "portfolio": [
        "tests/test_portfolio.py",
        "tests/test_portfolio_summary.py",
        "tests/test_portfolio_risk_trends.py",
        "tests/test_campaigns.py",
    ],
    "full_chain": [
        "tests/test_seed_authority_demo.py",
        "tests/test_avt_apt_transition.py",
    ],
}

DEFAULT_GROUPS = ["wedge", "operating", "full_chain"]


def main(argv: list[str]) -> int:
    if len(argv) > 1 and argv[1] in {"--list", "-l"}:
        print("Available confidence groups:")
        for group_name, tests in GROUPS.items():
            print(f"- {group_name}")
            for test_path in tests:
                print(f"  - {test_path}")
        return 0

    selected_groups = argv[1:] or DEFAULT_GROUPS
    unknown = [group for group in selected_groups if group not in GROUPS]
    if unknown:
        print(f"Unknown confidence group(s): {', '.join(unknown)}", file=sys.stderr)
        print(f"Available groups: {', '.join(sorted(GROUPS))}", file=sys.stderr)
        return 2

    seen: set[str] = set()
    test_paths: list[str] = []
    for group in selected_groups:
        for path in GROUPS[group]:
            if path not in seen:
                seen.add(path)
                test_paths.append(path)

    cmd = [sys.executable, "-m", "pytest", "-q", *test_paths]
    print("Running confidence suite groups:", ", ".join(selected_groups))
    print("Tests:")
    for path in test_paths:
        print(f"- {path}")
    print("")
    return subprocess.call(cmd, cwd=BACKEND_ROOT)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
