#!/usr/bin/env python3
"""Run a binary readiness gate for a wave brief bundle."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_HUB_FILES = [
    "backend/app/api/router.py",
    "backend/app/models/__init__.py",
    "backend/app/schemas/__init__.py",
    "frontend/src/i18n/en.ts",
    "frontend/src/i18n/fr.ts",
    "frontend/src/i18n/de.ts",
    "frontend/src/i18n/it.ts",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate wave briefs and scope disjointness with a binary PASS/FAIL verdict.",
    )
    parser.add_argument("--wave-id", required=True, help="Wave identifier, e.g. W76.")
    parser.add_argument(
        "--brief",
        action="append",
        default=[],
        help="Wave brief path (repeatable).",
    )
    parser.add_argument(
        "--allow-hub",
        action="append",
        default=[],
        help="Additional hub/shared path allowed for this gate run (repeatable).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output JSON path (default: tmp/wave_gates/<wave-id>.json).",
    )
    parser.add_argument(
        "--expect-three",
        action="store_true",
        help="Fail fast if number of briefs is not exactly 3.",
    )
    return parser.parse_args()


def run(command: list[str]) -> tuple[int, str, str]:
    proc = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode, proc.stdout, proc.stderr


def main() -> int:
    args = parse_args()
    if not args.brief:
        print("[error] At least one --brief must be provided.")
        return 2
    if args.expect_three and len(args.brief) != 3:
        print(f"[error] --expect-three enabled, got {len(args.brief)} brief(s).")
        return 2

    wave_id = args.wave_id.upper()
    output = args.output or (REPO_ROOT / "tmp" / "wave_gates" / f"{wave_id.lower()}.json")
    output.parent.mkdir(parents=True, exist_ok=True)

    lint_json = output.with_name(f"{wave_id.lower()}_brief_lint.json")
    overlap_json = output.with_name(f"{wave_id.lower()}_overlap.json")

    lint_cmd = [
        sys.executable,
        "scripts/brief_lint.py",
        "--strict-diff",
        *args.brief,
        "--json-out",
        str(lint_json),
    ]
    lint_rc, lint_out, lint_err = run(lint_cmd)

    allow = list(dict.fromkeys(DEFAULT_HUB_FILES + args.allow_hub))
    overlap_cmd = [sys.executable, "scripts/wave_overlap_guard.py", *args.brief]
    for path in allow:
        overlap_cmd.extend(["--allow-shared", path, "--allow-hub", path])
    overlap_cmd.extend(["--json-out", str(overlap_json)])
    overlap_rc, overlap_out, overlap_err = run(overlap_cmd)

    verdict = "PASS" if lint_rc == 0 and overlap_rc == 0 else "FAIL"
    payload = {
        "wave_id": wave_id,
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "briefs": args.brief,
        "verdict": verdict,
        "checks": {
            "brief_lint": {
                "status": "PASS" if lint_rc == 0 else "FAIL",
                "exit_code": lint_rc,
                "report": str(lint_json),
            },
            "overlap_guard": {
                "status": "PASS" if overlap_rc == 0 else "FAIL",
                "exit_code": overlap_rc,
                "report": str(overlap_json),
            },
        },
    }
    output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[gate] wave={wave_id} verdict={verdict}")
    print(f"[gate] report={output}")
    print(f"[gate] brief_lint={payload['checks']['brief_lint']['status']}")
    print(f"[gate] overlap_guard={payload['checks']['overlap_guard']['status']}")

    # Keep command outputs available for quick diagnosis.
    if verdict == "FAIL":
        if lint_out.strip():
            print("--- brief_lint stdout ---")
            print(lint_out.strip())
        if lint_err.strip():
            print("--- brief_lint stderr ---")
            print(lint_err.strip())
        if overlap_out.strip():
            print("--- overlap_guard stdout ---")
            print(overlap_out.strip())
        if overlap_err.strip():
            print("--- overlap_guard stderr ---")
            print(overlap_err.strip())

    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
