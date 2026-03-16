#!/usr/bin/env python3
"""Guard test-suite growth against runaway broadness."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from test_inventory import analyze_file, iter_test_files, summarize


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = REPO_ROOT / "docs" / "test-budget-guard.json"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check repo test-size growth against a budget baseline.")
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Path to budget config JSON (default: docs/test-budget-guard.json).",
    )
    parser.add_argument(
        "--write-current",
        action="store_true",
        help="Write docs/test-inventory.{md,json} before checking budget.",
    )
    parser.add_argument(
        "--refresh-baseline",
        action="store_true",
        help="Refresh baseline counts with current inventory and exit.",
    )
    return parser.parse_args()


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, data: dict[str, Any]) -> None:
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def get_current_summary() -> dict[str, Any]:
    stats = [analyze_file(path, layer) for path, layer in iter_test_files()]
    return summarize(stats)


def extract_flag_counts(summary: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    flagged = summary.get("flagged", [])
    if not isinstance(flagged, list):
        return counts
    for row in flagged:
        for flag in row.get("flags", []):
            counts[flag] = counts.get(flag, 0) + 1
    return counts


def print_baseline_and_current(
    baseline: dict[str, Any], current: dict[str, Any], baseline_flags: dict[str, int], current_flags: dict[str, int]
) -> None:
    print(
        "[budget] totals "
        f"files={current.get('total_files')} "
        f"tests={current.get('total_tests')} "
        f"flagged={current.get('flagged_count')}"
    )
    print(
        "[budget] baseline "
        f"files={baseline.get('total_files')} "
        f"tests={baseline.get('total_tests')} "
        f"flagged={baseline.get('flagged_count')}"
    )

    baseline_by_layer = baseline.get("by_layer", {})
    current_by_layer = current.get("by_layer", {})
    if isinstance(current_by_layer, dict):
        for layer, bucket in current_by_layer.items():
            flagged = bucket.get("flagged", 0)
            base_flagged = baseline_by_layer.get(layer, {}).get("flagged", 0)
            print(f"[budget] layer={layer} flagged={flagged} (baseline={base_flagged})")

    if current_flags:
        print("[budget] flags", json.dumps(current_flags, sort_keys=True))
    if baseline_flags:
        print("[budget] baseline_flags", json.dumps(baseline_flags, sort_keys=True))


def check_budget(config: dict[str, Any], current: dict[str, Any]) -> list[str]:
    violations: list[str] = []
    baseline = config.get("baseline", {})
    limits = config.get("limits", {})
    if not isinstance(baseline, dict) or not isinstance(limits, dict):
        return ["Invalid budget config: missing baseline/limits objects."]

    checks = [
        ("total_files", "max_total_files_growth"),
        ("total_tests", "max_total_tests_growth"),
        ("flagged_count", "max_flagged_growth"),
    ]
    for metric_key, limit_key in checks:
        base = int(baseline.get(metric_key, 0))
        current_value = int(current.get(metric_key, 0))
        growth = current_value - base
        max_growth = int(limits.get(limit_key, 0))
        if growth > max_growth:
            violations.append(
                f"{metric_key} growth {growth} exceeds {limit_key}={max_growth} "
                f"(baseline={base}, current={current_value})"
            )

    baseline_by_layer = baseline.get("by_layer", {})
    current_by_layer = current.get("by_layer", {})
    layer_limits = limits.get("max_flagged_by_layer_growth", {})
    if isinstance(baseline_by_layer, dict) and isinstance(current_by_layer, dict) and isinstance(layer_limits, dict):
        for layer, max_growth in layer_limits.items():
            base = int(baseline_by_layer.get(layer, {}).get("flagged", 0))
            current_value = int(current_by_layer.get(layer, {}).get("flagged", 0))
            growth = current_value - base
            if growth > int(max_growth):
                violations.append(
                    f"{layer}.flagged growth {growth} exceeds max_flagged_by_layer_growth={max_growth} "
                    f"(baseline={base}, current={current_value})"
                )

    baseline_flag_counts = baseline.get("flag_counts", {})
    current_flag_counts = extract_flag_counts(current)
    flag_growth_limits = limits.get("max_flag_growth", {})
    if isinstance(baseline_flag_counts, dict) and isinstance(flag_growth_limits, dict):
        for flag, max_growth in flag_growth_limits.items():
            base = int(baseline_flag_counts.get(flag, 0))
            current_value = int(current_flag_counts.get(flag, 0))
            growth = current_value - base
            if growth > int(max_growth):
                violations.append(
                    f"flag '{flag}' growth {growth} exceeds max_flag_growth={max_growth} "
                    f"(baseline={base}, current={current_value})"
                )

    return violations


def refresh_baseline(config_path: Path, config: dict[str, Any], current: dict[str, Any]) -> None:
    config["baseline"] = {
        "total_files": int(current.get("total_files", 0)),
        "total_tests": int(current.get("total_tests", 0)),
        "flagged_count": int(current.get("flagged_count", 0)),
        "by_layer": current.get("by_layer", {}),
        "flag_counts": extract_flag_counts(current),
        "captured_at": datetime.now(UTC).isoformat(),
    }
    config.setdefault("meta", {})
    config["meta"]["updated_at"] = datetime.now(UTC).isoformat()
    write_json(config_path, config)
    print(f"[ok] refreshed baseline in {config_path.relative_to(REPO_ROOT)}")


def maybe_write_inventory(summary: dict[str, Any]) -> None:
    from test_inventory import OUTPUT_JSON, OUTPUT_MD, render_markdown

    OUTPUT_MD.write_text(render_markdown(summary), encoding="utf-8")
    OUTPUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    print(f"[write] {OUTPUT_MD.relative_to(REPO_ROOT)}")
    print(f"[write] {OUTPUT_JSON.relative_to(REPO_ROOT)}")


def main() -> int:
    args = parse_args()
    config_path = args.config if args.config.is_absolute() else REPO_ROOT / args.config
    if not config_path.exists():
        print(f"[error] budget config not found: {config_path}")
        return 1

    config = load_json(config_path)
    current = get_current_summary()

    if args.write_current:
        maybe_write_inventory(current)

    baseline = config.get("baseline", {})
    baseline_flags = baseline.get("flag_counts", {}) if isinstance(baseline, dict) else {}
    current_flags = extract_flag_counts(current)
    print_baseline_and_current(baseline, current, baseline_flags, current_flags)

    if args.refresh_baseline:
        refresh_baseline(config_path, config, current)
        return 0

    violations = check_budget(config, current)
    if violations:
        for violation in violations:
            print(f"[error] {violation}")
        return 1

    print("[ok] test budget guard passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

