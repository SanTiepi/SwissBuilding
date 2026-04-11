#!/usr/bin/env python3
"""Compatibility surface guard. Ensures legacy/frozen surfaces don't grow new semantics.

Tracks line counts for files marked as "compatibility" (frozen API surfaces that exist
for backward compat but shouldn't gain new features). Alerts if they grow beyond baseline.

Exit code 0 = pass, 1 = fail.
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# Files that are frozen as compatibility surfaces.
# They should not gain new endpoints, fields, or logic.
COMPATIBILITY_FILES = [
    "backend/app/models/change_signal.py",
    "backend/app/schemas/change_signal.py",
    "backend/app/api/change_signals.py",
    "backend/app/services/change_signal_generator.py",
    "frontend/src/api/changeSignals.ts",
    "frontend/src/pages/ChangeSignals.tsx",
    "frontend/src/components/ChangeSignalsFeed.tsx",
]

# Growth tolerance: allow this many lines of growth before flagging (for minor fixes)
GROWTH_TOLERANCE = 5

BASELINE_PATH = REPO_ROOT / "backend" / "scripts" / "baselines" / "compatibility_baseline.json"


def count_lines(filepath: Path) -> int:
    """Count lines in a file."""
    try:
        return sum(1 for _ in filepath.open("r", encoding="utf-8", errors="ignore"))
    except OSError:
        return -1


def load_baseline() -> dict | None:
    """Load previous baseline if it exists."""
    if BASELINE_PATH.exists():
        return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return None


def save_baseline(current: dict[str, int]) -> None:
    """Save current line counts as baseline."""
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(current, indent=2, sort_keys=True), encoding="utf-8")


def main() -> int:
    baseline = load_baseline()
    current = {}
    warnings = []
    growth_violations = []
    missing_files = []

    for rel_path in COMPATIBILITY_FILES:
        filepath = REPO_ROOT / rel_path
        lines = count_lines(filepath)

        if lines < 0:
            missing_files.append(rel_path)
            continue

        current[rel_path] = lines

        if baseline and rel_path in baseline:
            prev = baseline[rel_path]
            growth = lines - prev
            if growth > GROWTH_TOLERANCE:
                growth_violations.append(
                    {
                        "file": rel_path,
                        "previous": prev,
                        "current": lines,
                        "growth": growth,
                    }
                )
                warnings.append(
                    f"{rel_path}: grew by {growth} lines ({prev} -> {lines}). "
                    f"Compatibility surfaces should not gain new semantics."
                )

    # First run: establish baseline, always pass
    is_first_run = baseline is None

    # Save current as baseline
    save_baseline(current)

    passed = len(growth_violations) == 0

    result = {
        "check": "compatibility_surface_guard",
        "pass": passed,
        "first_run": is_first_run,
        "tracked_files": len(COMPATIBILITY_FILES),
        "missing_files": missing_files,
        "growth_violations": growth_violations,
        "warnings": warnings,
        "current_sizes": current,
    }

    if is_first_run:
        result["pass"] = True
        result["info"] = "First run — baseline established. Future runs will detect growth."

    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
