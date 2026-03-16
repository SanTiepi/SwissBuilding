#!/usr/bin/env python3
"""Validate lead control-plane hygiene across key repo docs."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


REQUIRED_FILES = [
    Path("ORCHESTRATOR.md"),
    Path("MEMORY.md"),
    Path("docs/lead-master-plan.md"),
    Path("docs/lead-parallel-operating-model.md"),
    Path("docs/lead-ongoing-backlog.md"),
    Path("docs/projects/README.md"),
]

REQUIRED_ORCHESTRATOR_HEADINGS = [
    "## Core Invariants (AGENTS Sync)",
    "## Lead Feed",
    "## Next 10 Actions",
    "## Validation Gates",
    "## Decision Log",
]

REQUIRED_DOC_HEADINGS = {
    Path("docs/lead-master-plan.md"): [
        "## Strategy Guardrails (AGENTS Sync)",
    ],
    Path("docs/lead-parallel-operating-model.md"): [
        "## Non-Negotiable Invariants",
    ],
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check whether lead control-plane files are present and coherent."
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if Next 10 Actions does not contain exactly 10 numbered items.",
    )
    return parser.parse_args()


def extract_section(content: str, heading: str) -> str:
    pattern = rf"(?ms)^{re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, content)
    return match.group(1) if match else ""


def count_numbered_items(markdown_section: str) -> int:
    list_count = len(re.findall(r"(?m)^\s*\d+\.\s", markdown_section))
    table_count = len(re.findall(r"(?m)^\|\s*\d+\s*\|", markdown_section))
    return max(list_count, table_count)


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    problems: list[str] = []
    notes: list[str] = []

    for rel_path in REQUIRED_FILES:
        abs_path = repo_root / rel_path
        if not abs_path.exists():
            problems.append(f"Missing required file: {rel_path}")
            continue
        required_headings = REQUIRED_DOC_HEADINGS.get(rel_path, [])
        if required_headings:
            content = abs_path.read_text(encoding="utf-8")
            for heading in required_headings:
                if heading not in content:
                    problems.append(f"Missing required heading in {rel_path}: {heading}")

    orchestrator_path = repo_root / "ORCHESTRATOR.md"
    if orchestrator_path.exists():
        orchestrator_content = orchestrator_path.read_text(encoding="utf-8")
        for heading in REQUIRED_ORCHESTRATOR_HEADINGS:
            if heading not in orchestrator_content:
                problems.append(f"Missing ORCHESTRATOR heading: {heading}")

        next_ten_section = extract_section(orchestrator_content, "## Next 10 Actions")
        next_ten_count = count_numbered_items(next_ten_section)
        notes.append(f"Next 10 Actions items detected: {next_ten_count}")
        if next_ten_count == 0:
            problems.append("Next 10 Actions has no numbered items.")
        elif args.strict and next_ten_count != 10:
            problems.append(
                "Next 10 Actions must contain exactly 10 numbered items in strict mode."
            )

    for note in notes:
        print(f"[note] {note}")

    if problems:
        for problem in problems:
            print(f"[error] {problem}")
        return 1

    print("[ok] lead control-plane check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
