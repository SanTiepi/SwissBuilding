#!/usr/bin/env python3
"""Detect overlapping task scopes before launching a multi-agent wave."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

HUB_FILES = {
    "backend/app/api/router.py",
    "backend/app/models/__init__.py",
    "backend/app/schemas/__init__.py",
    "backend/app/seeds/seed_data.py",
    "frontend/src/i18n/en.ts",
    "frontend/src/i18n/fr.ts",
    "frontend/src/i18n/de.ts",
    "frontend/src/i18n/it.ts",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check that brief scopes are disjoint and avoid hub-file contention.",
    )
    parser.add_argument(
        "briefs",
        nargs="+",
        help="Brief markdown files to compare.",
    )
    parser.add_argument(
        "--allow-shared",
        action="append",
        default=[],
        help="Path allowed to overlap across briefs (repeatable).",
    )
    parser.add_argument(
        "--allow-hub",
        action="append",
        default=[],
        help="Hub file allowed for this run (repeatable).",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional JSON report path.",
    )
    return parser.parse_args()


def normalize_path(value: str) -> str:
    return value.strip().strip("`").replace("\\", "/").lower()


def is_candidate_path(value: str) -> bool:
    if not value:
        return False
    if any(ch.isspace() for ch in value):
        return False
    if "&&" in value or "||" in value or ";" in value:
        return False
    if value.startswith("http://") or value.startswith("https://"):
        return False
    if "/" not in value:
        return False
    return "." in Path(value).name


def extract_paths(markdown: str) -> set[str]:
    paths: set[str] = set()

    # Inline code fragments.
    for match in re.findall(r"`([^`\n]+)`", markdown):
        candidate = normalize_path(match)
        if is_candidate_path(candidate):
            paths.add(candidate)

    # Bare path-like tokens in bullet lines.
    for line in markdown.splitlines():
        if not line.strip().startswith("- "):
            continue
        for token in re.findall(r"[A-Za-z0-9_.\-\/]+", line):
            candidate = normalize_path(token)
            if is_candidate_path(candidate):
                paths.add(candidate)

    return paths


def main() -> int:
    args = parse_args()
    allow_shared = {normalize_path(path) for path in args.allow_shared}
    allow_hub = {normalize_path(path) for path in args.allow_hub}

    brief_to_paths: dict[str, set[str]] = {}
    for raw in args.briefs:
        path = (REPO_ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
        if not path.exists():
            print(f"[error] brief does not exist: {raw}")
            return 2
        content = path.read_text(encoding="utf-8")
        brief_to_paths[str(path.relative_to(REPO_ROOT))] = extract_paths(content)

    owners: dict[str, list[str]] = defaultdict(list)
    for brief, paths in brief_to_paths.items():
        for path in paths:
            owners[path].append(brief)

    overlaps = {
        path: sorted(briefs)
        for path, briefs in owners.items()
        if len(set(briefs)) > 1 and path not in allow_shared
    }

    hub_touches = {
        brief: sorted(path for path in paths if path in HUB_FILES and path not in allow_hub)
        for brief, paths in brief_to_paths.items()
    }
    hub_touches = {brief: paths for brief, paths in hub_touches.items() if paths}

    for brief, paths in sorted(brief_to_paths.items()):
        print(f"[brief] {brief}")
        print(f"  paths_detected={len(paths)}")
        for path in sorted(paths):
            print(f"  - {path}")

    if overlaps:
        print("[error] overlapping target paths detected:")
        for path, briefs in sorted(overlaps.items()):
            print(f"  - {path}: {', '.join(briefs)}")

    if hub_touches:
        print("[error] hub-file touches detected (reserved to supervisor merge by default):")
        for brief, paths in sorted(hub_touches.items()):
            print(f"  - {brief}: {', '.join(paths)}")

    payload = {
        "briefs": {brief: sorted(paths) for brief, paths in brief_to_paths.items()},
        "overlaps": overlaps,
        "hub_touches": hub_touches,
        "ok": not overlaps and not hub_touches,
    }
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        print(f"[report] {args.json_out}")

    if overlaps or hub_touches:
        return 1
    print("[ok] wave scopes are disjoint and hub-safe.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
