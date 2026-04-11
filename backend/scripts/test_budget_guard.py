#!/usr/bin/env python3
"""Test budget guard. Ensures test counts don't regress below known baselines.

Tracks the number of tests in backend and frontend suites. Alerts if the count
drops below the established baseline (tests were deleted without replacement).

Exit code 0 = pass, 1 = fail.

Note: This guard does NOT run the tests — it counts test functions/cases.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
BASELINE_PATH = REPO_ROOT / "backend" / "scripts" / "baselines" / "test_budget_baseline.json"

# Current known baselines (from MEMORY.md + validation commands)
EXPECTED_BASELINES = {
    "backend_tests": 4563,
    "frontend_unit_tests": 299,
    "frontend_e2e_mock_tests": 185,
}

# Tolerance: allow this much drop before failing (accounts for test refactoring)
DROP_TOLERANCE = 5


def count_backend_tests() -> int:
    """Count test functions in backend/tests/."""
    test_dir = REPO_ROOT / "backend" / "tests"
    if not test_dir.exists():
        return 0

    count = 0
    pattern = re.compile(r"^\s*(async\s+)?def\s+test_", re.MULTILINE)
    for py_file in test_dir.rglob("*.py"):
        try:
            content = py_file.read_text(encoding="utf-8", errors="ignore")
            count += len(pattern.findall(content))
        except OSError:
            continue
    return count


def count_frontend_unit_tests() -> int:
    """Count test cases in frontend vitest files."""
    test_patterns = [
        REPO_ROOT / "frontend" / "src",
    ]
    count = 0
    # Match it("...", test("...", it.each, test.each
    pattern = re.compile(r"""^\s*(?:it|test)\s*[\.(]""", re.MULTILINE)
    for base in test_patterns:
        if not base.exists():
            continue
        for ext in ("*.test.ts", "*.test.tsx", "*.spec.ts", "*.spec.tsx"):
            for f in base.rglob(ext):
                try:
                    content = f.read_text(encoding="utf-8", errors="ignore")
                    count += len(pattern.findall(content))
                except OSError:
                    continue
    return count


def count_frontend_e2e_tests() -> int:
    """Count test cases in frontend e2e mock files."""
    e2e_dir = REPO_ROOT / "frontend" / "e2e"
    if not e2e_dir.exists():
        return 0

    count = 0
    pattern = re.compile(r"""^\s*(?:it|test)\s*[\.(]""", re.MULTILINE)
    for f in e2e_dir.rglob("*.spec.ts"):
        try:
            content = f.read_text(encoding="utf-8", errors="ignore")
            count += len(pattern.findall(content))
        except OSError:
            continue
    return count


def load_baseline() -> dict | None:
    """Load previous baseline if it exists."""
    if BASELINE_PATH.exists():
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return None


def save_baseline(current: dict[str, int]) -> None:
    """Save current counts as baseline."""
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    current = {
        "backend_tests": count_backend_tests(),
        "frontend_unit_tests": count_frontend_unit_tests(),
        "frontend_e2e_mock_tests": count_frontend_e2e_tests(),
    }

    baseline = load_baseline()
    reference = baseline if baseline else EXPECTED_BASELINES

    warnings = []
    regressions = []

    for key, count in current.items():
        ref = reference.get(key, 0)
        if ref > 0 and count < ref - DROP_TOLERANCE:
            drop = ref - count
            regressions.append(
                {
                    "suite": key,
                    "baseline": ref,
                    "current": count,
                    "dropped": drop,
                }
            )
            warnings.append(f"{key}: dropped from {ref} to {count} (-{drop} tests)")

    # Save current as new baseline (ratchet up, never down)
    new_baseline = {}
    for key in current:
        ref = reference.get(key, 0)
        new_baseline[key] = max(current[key], ref)
    save_baseline(new_baseline)

    passed = len(regressions) == 0

    result = {
        "check": "test_budget_guard",
        "pass": passed,
        "current_counts": current,
        "baseline_used": "stored" if baseline else "expected",
        "regressions": regressions,
        "warnings": warnings,
    }

    print(json.dumps(result, indent=2))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
