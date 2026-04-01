#!/usr/bin/env python3
"""Master repo health check. Runs all architecture fitness functions.

Executes each guard script, collects results, and outputs an aggregate report.
Exit code 0 = all checks pass, 1 = at least one failure.
"""

import json
import subprocess
import sys
import time
from pathlib import Path

SCRIPTS_DIR = Path(__file__).resolve().parent

CHECKS = [
    ("Route shell drift", "check_route_shell.py"),
    ("File size guard", "check_file_sizes.py"),
    ("Compatibility surface", "check_compatibility.py"),
    ("API registry", "check_api_registry.py"),
    ("Test budget", "test_budget_guard.py"),
]


def run_check(name: str, script: str) -> dict:
    """Run a single check script and capture its result."""
    script_path = SCRIPTS_DIR / script
    if not script_path.exists():
        return {
            "name": name,
            "script": script,
            "pass": False,
            "error": f"Script not found: {script_path}",
            "duration_ms": 0,
        }

    start = time.time()
    try:
        result = subprocess.run(
            [sys.executable, str(script_path)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(SCRIPTS_DIR.parent),
        )
        duration_ms = int((time.time() - start) * 1000)

        try:
            output = json.loads(result.stdout)
        except (json.JSONDecodeError, ValueError):
            output = {"raw_stdout": result.stdout[:500]}

        return {
            "name": name,
            "script": script,
            "pass": result.returncode == 0,
            "exit_code": result.returncode,
            "duration_ms": duration_ms,
            "result": output,
            "stderr": result.stderr[:200] if result.stderr else None,
        }
    except subprocess.TimeoutExpired:
        duration_ms = int((time.time() - start) * 1000)
        return {
            "name": name,
            "script": script,
            "pass": False,
            "error": "Timeout (60s)",
            "duration_ms": duration_ms,
        }
    except Exception as e:
        duration_ms = int((time.time() - start) * 1000)
        return {
            "name": name,
            "script": script,
            "pass": False,
            "error": str(e),
            "duration_ms": duration_ms,
        }


def main() -> int:
    results = []
    all_pass = True

    print("=" * 60)
    print("  BatiConnect Architecture Fitness Functions")
    print("=" * 60)

    for name, script in CHECKS:
        check_result = run_check(name, script)
        results.append(check_result)

        status = "PASS" if check_result["pass"] else "FAIL"
        symbol = "[+]" if check_result["pass"] else "[X]"
        print(f"  {symbol} {name}: {status} ({check_result['duration_ms']}ms)")

        if not check_result["pass"]:
            all_pass = False
            # Print warnings if available
            inner = check_result.get("result", {})
            for w in inner.get("warnings", [])[:3]:
                print(f"      ! {w}")

    print("=" * 60)
    total_ms = sum(r["duration_ms"] for r in results)
    passed_count = sum(1 for r in results if r["pass"])
    print(f"  Result: {passed_count}/{len(results)} checks passed ({total_ms}ms total)")
    print("=" * 60)

    # Also output machine-readable JSON
    aggregate = {
        "check": "repo_health",
        "pass": all_pass,
        "checks_passed": passed_count,
        "checks_total": len(results),
        "total_duration_ms": total_ms,
        "results": results,
    }

    # Write JSON to file for CI consumption
    json_path = SCRIPTS_DIR / "repo_health_report.json"
    json_path.write_text(json.dumps(aggregate, indent=2), encoding="utf-8")
    print(f"\n  JSON report: {json_path}")

    return 0 if all_pass else 1


if __name__ == "__main__":
    sys.exit(main())
