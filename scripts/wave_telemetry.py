#!/usr/bin/env python3
"""Update ORCHESTRATOR wave counters and append wave debrief notes."""

from __future__ import annotations

import argparse
import re
from datetime import date
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_FILE = REPO_ROOT / "ORCHESTRATOR.md"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Apply wave telemetry updates (counters + debrief) to ORCHESTRATOR.md.",
    )
    parser.add_argument("--wave-id", required=True, help="Wave identifier, e.g. W72.")
    parser.add_argument("--clear", required=True, help="Debrief clear line.")
    parser.add_argument("--fuzzy", required=True, help="Debrief fuzzy line.")
    parser.add_argument("--missing", required=True, help="Debrief missing line.")
    parser.add_argument(
        "--rework",
        action="store_true",
        help="Increment rework_count by 1.",
    )
    parser.add_argument(
        "--blocked",
        action="store_true",
        help="Increment blocked_count by 1.",
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=DEFAULT_FILE,
        help=f"ORCHESTRATOR file path (default: {DEFAULT_FILE}).",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Write changes. Without this flag, run in preview mode.",
    )
    return parser.parse_args()


def update_counter_line(content: str, key: str, delta: int = 0, replacement: str | None = None) -> str:
    pattern = rf"(?m)^- {re.escape(key)}:\s*`([^`]+)`(?:\s*\(([^)]*)\))?\s*$"
    match = re.search(pattern, content)
    if not match:
        raise ValueError(f"Counter line not found: {key}")

    current_raw = match.group(1)
    note = match.group(2)

    if replacement is not None:
        new_raw = replacement
    else:
        new_raw = str(int(current_raw) + delta)

    new_line = f"- {key}: `{new_raw}`"
    if note:
        new_line += f" ({note})"
    return content[: match.start()] + new_line + content[match.end() :]


def update_waves_line(content: str, wave_id: str) -> str:
    pattern = r"(?m)^- waves_completed:\s*`([^`]+)`(?:\s*\(([^)]*)\))?\s*$"
    match = re.search(pattern, content)
    if not match:
        raise ValueError("Counter line not found: waves_completed")

    current = int(match.group(1))
    note = match.group(2) or ""
    new_count = current + 1
    if wave_id and wave_id.lower() not in note.lower():
        note = f"{note}; +{wave_id}".strip("; ").strip()

    new_line = f"- waves_completed: `{new_count}`"
    if note:
        new_line += f" ({note})"

    return content[: match.start()] + new_line + content[match.end() :]


def append_debrief_to_decision_log(content: str, wave_id: str, clear: str, fuzzy: str, missing: str) -> str:
    marker = "## Decision Log"
    index = content.find(marker)
    if index < 0:
        raise ValueError("Heading not found: ## Decision Log")

    insert_at = index + len(marker)
    entry = (
        "\n\n"
        f"- wave debrief `{wave_id}` ({date.today()}):\n"
        f"  - clear: {clear}\n"
        f"  - fuzzy: {fuzzy}\n"
        f"  - missing: {missing}\n"
    )
    return content[:insert_at] + entry + content[insert_at:]


def main() -> int:
    args = parse_args()
    if not args.file.exists():
        print(f"[error] file not found: {args.file}")
        return 1

    original = args.file.read_text(encoding="utf-8")
    updated = original

    try:
        updated = update_waves_line(updated, args.wave_id)
        updated = update_counter_line(updated, "rework_count", delta=1 if args.rework else 0)
        updated = update_counter_line(updated, "blocked_count", delta=1 if args.blocked else 0)
        updated = update_counter_line(updated, "last_updated", replacement=str(date.today()))
        updated = append_debrief_to_decision_log(
            updated,
            wave_id=args.wave_id,
            clear=args.clear,
            fuzzy=args.fuzzy,
            missing=args.missing,
        )
    except ValueError as exc:
        print(f"[error] {exc}")
        return 1

    if not args.apply:
        print("[preview] telemetry update prepared. Re-run with --apply to write.")
        print(f"[preview] file={args.file}")
        return 0

    args.file.write_text(updated, encoding="utf-8")
    print(f"[ok] telemetry updated in {args.file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

