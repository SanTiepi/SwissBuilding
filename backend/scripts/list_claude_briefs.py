from __future__ import annotations

import argparse
import re
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BRIEF_KIT = REPO_ROOT / "docs" / "projects" / "claude-wave-brief-kit-2026-03-25.md"
BRIEF_RE = re.compile(r"^## Brief (\d+) - (.+)$", re.MULTILINE)


@dataclass(frozen=True)
class Brief:
    brief_id: int
    title: str


def _load_briefs() -> list[Brief]:
    text = BRIEF_KIT.read_text(encoding="utf-8")
    return [Brief(int(match.group(1)), match.group(2).strip()) for match in BRIEF_RE.finditer(text)]


def main() -> int:
    parser = argparse.ArgumentParser(description="List and filter Claude wave briefs.")
    parser.add_argument("--contains", type=str, default=None, help="Filter by title substring.")
    parser.add_argument("--ids", nargs="*", type=int, default=None, help="Filter by brief ids.")
    parser.add_argument("--markdown", action="store_true", help="Render as markdown bullet list.")
    args = parser.parse_args()

    briefs = _load_briefs()
    if args.ids:
        wanted = set(args.ids)
        briefs = [brief for brief in briefs if brief.brief_id in wanted]
    if args.contains:
        needle = args.contains.lower()
        briefs = [brief for brief in briefs if needle in brief.title.lower()]

    if args.markdown:
        for brief in briefs:
            print(f"- Brief {brief.brief_id}: {brief.title}")
        return 0

    for brief in briefs:
        print(f"{brief.brief_id:02d} | {brief.title}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
