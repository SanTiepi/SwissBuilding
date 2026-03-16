#!/usr/bin/env python3
"""Lint Claude briefs against the canonical brief template."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

FULL_REQUIRED_HEADINGS = [
    "## Mission",
    "## Agent usage",
    "## Scope",
    "## Target files",
    "## Non-negotiable constraints",
    "## Validation",
    "## Exit criteria",
    "## Non-goals",
    "## Deliverables",
]

COMPACT_REQUIRED_HEADINGS = [
    "## Task",
    "## Agent usage",
    "## Scope",
    "## Target files",
    "## Hard constraints",
    "## Validate loop",
    "## Exit",
]


@dataclass
class LintResult:
    file: str
    ok: bool
    issues: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Lint one or more brief markdown files.",
    )
    parser.add_argument(
        "files",
        nargs="*",
        help="Brief files to lint.",
    )
    parser.add_argument(
        "--glob",
        action="append",
        default=[],
        help="Additional glob(s), e.g. --glob 'docs/projects/*.md'.",
    )
    parser.add_argument(
        "--json-out",
        type=Path,
        help="Optional JSON report output path.",
    )
    parser.add_argument(
        "--strict-diff",
        action="store_true",
        help="Require explicit target-file paths and diff-friendly constraints.",
    )
    return parser.parse_args()


def gather_files(args: argparse.Namespace) -> list[Path]:
    candidates: list[Path] = []
    for raw in args.files:
        path = (REPO_ROOT / raw).resolve() if not Path(raw).is_absolute() else Path(raw)
        if path.exists() and path.is_file():
            candidates.append(path)
    for pattern in args.glob:
        candidates.extend(sorted(REPO_ROOT.glob(pattern)))
    # Keep unique, stable order.
    unique: dict[str, Path] = {}
    for path in candidates:
        unique[str(path.resolve())] = path.resolve()
    return list(unique.values())


def extract_section(content: str, heading: str) -> str:
    pattern = rf"(?ms)^{re.escape(heading)}\n(.*?)(?=^## |\Z)"
    match = re.search(pattern, content)
    return match.group(1).strip() if match else ""


def detect_heading_mode(content: str) -> tuple[str, list[str]]:
    full_missing = [heading for heading in FULL_REQUIRED_HEADINGS if heading not in content]
    if not full_missing:
        return "full", []

    compact_missing = [heading for heading in COMPACT_REQUIRED_HEADINGS if heading not in content]
    if not compact_missing:
        return "compact", []

    # Pick the closer template to report useful missing headings.
    if len(compact_missing) < len(full_missing):
        return "compact", compact_missing
    return "full", full_missing


def has_nonempty_bullets(section: str) -> bool:
    for line in section.splitlines():
        stripped = line.strip()
        if stripped.startswith("- "):
            value = stripped[2:].strip()
            if value and value != ":":
                return True
    return False


def extract_path_like_tokens(section: str) -> list[str]:
    tokens: list[str] = []
    for inline in re.findall(r"`([^`\n]+)`", section):
        candidate = inline.strip()
        if "/" in candidate and "." in Path(candidate).name:
            tokens.append(candidate)
    for line in section.splitlines():
        for token in re.findall(r"[A-Za-z0-9_.\-\/]+", line):
            if "/" in token and "." in Path(token).name:
                tokens.append(token)
    # Deduplicate preserving order.
    seen: set[str] = set()
    ordered: list[str] = []
    for token in tokens:
        key = token.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(token)
    return ordered


def lint_brief(path: Path, strict_diff: bool) -> LintResult:
    content = path.read_text(encoding="utf-8")
    issues: list[str] = []

    mode, missing_headings = detect_heading_mode(content)
    required_headings = FULL_REQUIRED_HEADINGS if mode == "full" else COMPACT_REQUIRED_HEADINGS

    for heading in missing_headings:
        issues.append(f"Missing heading: {heading}")

    heading_map = {
        "mission": "## Mission" if mode == "full" else "## Task",
        "validation": "## Validation" if mode == "full" else "## Validate loop",
        "constraints": "## Non-negotiable constraints" if mode == "full" else "## Hard constraints",
    }

    for heading in required_headings:
        if heading not in content:
            continue
        section = extract_section(content, heading)
        if not section:
            issues.append(f"Empty section: {heading}")
        elif not has_nonempty_bullets(section):
            issues.append(f"No filled bullet items: {heading}")

    mission = extract_section(content, heading_map["mission"]).lower()
    if mission and "visible consumer window" not in mission:
        issues.append("Mission section should include visible consumer window.")

    agent_usage = extract_section(content, "## Agent usage").lower()
    if agent_usage:
        has_agent_phrase = "tu peux utiliser tes agents" in agent_usage
        has_no_agent_phrase = "aucun agent n'est necessaire" in agent_usage
        if not (has_agent_phrase or has_no_agent_phrase):
            issues.append(
                "Agent usage section must include explicit agent line "
                "('Tu peux utiliser tes agents...' or 'Aucun agent n'est necessaire...')."
            )

    target_files = extract_section(content, "## Target files").lower()
    for keyword in ("primary file", "change mode", "do-not-touch"):
        if target_files and keyword not in target_files:
            issues.append(f"Target files section should include keyword: {keyword}")

    if strict_diff:
        target_section = extract_section(content, "## Target files")
        paths = extract_path_like_tokens(target_section)
        if not paths:
            issues.append("Strict diff mode: target files section must contain explicit file paths.")
        if any("*" in path for path in paths):
            issues.append("Strict diff mode: wildcard paths are not allowed in target files.")
        lower_target = target_section.lower()
        if "do-not-touch" not in lower_target:
            issues.append("Strict diff mode: do-not-touch line is required.")
        if "change mode" not in lower_target or "`new`" not in lower_target or "`modify`" not in lower_target:
            issues.append("Strict diff mode: explicit new/modify change mode markers are required.")

    validation = extract_section(content, heading_map["validation"]).lower()
    if validation and "command" not in validation and "run -> fix -> rerun" not in validation:
        issues.append("Validation section should include explicit commands.")
    if validation and "`" not in validation:
        issues.append("Validation section should include at least one command/code block marker.")
    if mode == "compact" and strict_diff and validation and "rerun" not in validation:
        issues.append(
            "Compact strict mode: validate loop section should include rerun-until-clean wording."
        )

    return LintResult(
        file=str(path.relative_to(REPO_ROOT)),
        ok=not issues,
        issues=issues,
    )


def main() -> int:
    args = parse_args()
    files = gather_files(args)
    if not files:
        print("[error] No brief files found. Pass file paths or --glob.")
        return 2

    results = [lint_brief(path, strict_diff=args.strict_diff) for path in files]

    for result in results:
        status = "ok" if result.ok else "error"
        print(f"[{status}] {result.file}")
        for issue in result.issues:
            print(f"  - {issue}")

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(
            json.dumps([asdict(result) for result in results], indent=2),
            encoding="utf-8",
        )
        print(f"[report] {args.json_out}")

    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
