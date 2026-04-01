#!/usr/bin/env python3
"""Pre-commit quality gate. Runs fast repo health checks.
Exit 0 = safe to commit. Exit 1 = issues found.

Usage:
    python scripts/pre_commit_check.py          # full check
    python scripts/pre_commit_check.py --fast   # route + compatibility only
    python scripts/pre_commit_check.py --json   # full check + JSON report to stdout
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent
BACKEND_DIR = SCRIPTS_DIR.parent

FAST_CHECKS = [
    ("Route shell", "check_route_shell.py"),
    ("Compatibility", "check_compatibility.py"),
]

FULL_CHECKS = [
    *FAST_CHECKS,
    ("File sizes", "check_file_sizes.py"),
    ("API registry", "check_api_registry.py"),
    ("Canonical registry", "check_canonical_registry.py"),
]


def run_single(name: str, script: str) -> dict:
    """Run one check script, return structured result."""
    script_path = SCRIPTS_DIR / script
    if not script_path.exists():
        return {"name": name, "pass": False, "elapsed_ms": 0, "error": f"Not found: {script_path}"}

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(BACKEND_DIR),
        )
        elapsed = int((time.time() - start) * 1000)

        # Parse JSON output to get pass/fail
        try:
            data = json.loads(result.stdout)
            passed = data.get("pass", data.get("overall_pass", False))
        except (json.JSONDecodeError, ValueError):
            passed = result.returncode == 0

        return {"name": name, "pass": passed, "elapsed_ms": elapsed}
    except subprocess.TimeoutExpired:
        elapsed = int((time.time() - start) * 1000)
        return {"name": name, "pass": False, "elapsed_ms": elapsed, "error": "Timeout (30s)"}
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return {"name": name, "pass": False, "elapsed_ms": elapsed, "error": str(e)}


def main() -> int:
    fast = "--fast" in sys.argv
    json_mode = "--json" in sys.argv
    checks = FAST_CHECKS if fast else FULL_CHECKS

    mode_label = "fast" if fast else "full"
    if not json_mode:
        print(f"  Pre-commit check ({mode_label})")
        print(f"  {'=' * 40}")

    results = []
    for name, script in checks:
        entry = run_single(name, script)
        results.append(entry)
        if not json_mode:
            status = "PASS" if entry["pass"] else "FAIL"
            symbol = "[+]" if entry["pass"] else "[X]"
            print(f"  {symbol} {name}: {status} ({entry['elapsed_ms']}ms)")

    all_pass = all(r["pass"] for r in results)
    total_ms = sum(r["elapsed_ms"] for r in results)

    report = {
        "check": "pre_commit",
        "pass": all_pass,
        "mode": mode_label,
        "checks_passed": sum(1 for r in results if r["pass"]),
        "checks_total": len(results),
        "total_ms": total_ms,
        "results": results,
    }

    if json_mode:
        print(json.dumps(report, indent=2))
    else:
        print(f"  {'=' * 40}")
        passed_count = report["checks_passed"]
        print(f"  {passed_count}/{len(results)} passed ({total_ms}ms)")
        if all_pass:
            print("  All checks passed.")
        else:
            print("  SOME CHECKS FAILED.")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
