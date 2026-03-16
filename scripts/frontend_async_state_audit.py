#!/usr/bin/env python3
"""Audit frontend async surfaces for explicit query error handling."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


QUERY_HOOK_RE = re.compile(r"\buse(?:Query|InfiniteQuery|SuspenseQuery|Queries)\s*\(")
DESTRUCTURED_QUERY_RE = re.compile(
    r"const\s*\{(?P<destructured>.*?)\}\s*=\s*use(?:Query|InfiniteQuery|SuspenseQuery|Queries)\s*\(",
    re.DOTALL,
)
IS_ERROR_ALIAS_RE = re.compile(r"\bisError\s*:\s*([A-Za-z_][A-Za-z0-9_]*)")
HAS_IS_ERROR_RE = re.compile(r"\bisError\b")
ERROR_ALIAS_RE = re.compile(r"\berror\s*:\s*([A-Za-z_][A-Za-z0-9_]*)")
HAS_ERROR_RE = re.compile(r"\berror\b")
PROPERTY_ERROR_USAGE_RE = re.compile(r"\.\s*(?:isError|error)\b|status\s*===\s*['\"]error['\"]")


@dataclass
class SurfaceAudit:
    file: str
    query_count: int
    error_variables: list[str]
    has_property_error_usage: bool
    has_error_token: bool
    has_error_branch: bool
    status: str
    notes: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Audit async query error-state coverage.")
    parser.add_argument("--write", action="store_true", help="Write markdown/json reports under docs/.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any surface needs review or has missing error state.",
    )
    parser.add_argument(
        "--max-review",
        type=int,
        default=None,
        help="Maximum allowed count for review_error_path before failing.",
    )
    parser.add_argument(
        "--max-missing",
        type=int,
        default=None,
        help="Maximum allowed count for missing_error_state before failing.",
    )
    return parser.parse_args()


def scan_files(repo_root: Path) -> list[Path]:
    roots = [repo_root / "frontend" / "src" / "pages", repo_root / "frontend" / "src" / "components"]
    files: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        files.extend(sorted(root.rglob("*.tsx")))
    return files


def extract_error_variables(text: str) -> list[str]:
    variables: set[str] = set()
    for match in DESTRUCTURED_QUERY_RE.finditer(text):
        destructured = match.group("destructured")
        for alias in IS_ERROR_ALIAS_RE.findall(destructured):
            variables.add(alias.strip())
        if HAS_IS_ERROR_RE.search(destructured):
            variables.add("isError")

        for alias in ERROR_ALIAS_RE.findall(destructured):
            variables.add(alias.strip())
        if HAS_ERROR_RE.search(destructured):
            variables.add("error")
    return sorted(v for v in variables if v)


def has_conditional_usage(text: str, variable: str) -> bool:
    escaped = re.escape(variable)
    patterns = [
        rf"\bif\s*\([^)]*\b{escaped}\b",
        rf"\b{escaped}\b\s*\?",
        rf"\b{escaped}\b\s*&&",
        rf"\|\|\s*\b{escaped}\b",
    ]
    return any(re.search(pattern, text, re.MULTILINE | re.DOTALL) for pattern in patterns)


def audit_file(file_path: Path, repo_root: Path) -> SurfaceAudit | None:
    text = file_path.read_text(encoding="utf-8")
    query_count = len(QUERY_HOOK_RE.findall(text))
    if query_count == 0:
        return None

    error_variables = extract_error_variables(text)
    has_property_error_usage = bool(PROPERTY_ERROR_USAGE_RE.search(text))
    has_error_token = bool(error_variables) or has_property_error_usage
    has_error_branch = has_property_error_usage or any(
        has_conditional_usage(text, variable) for variable in error_variables
    )
    notes: list[str] = []

    if not has_error_token:
        status = "missing_error_state"
        notes.append("query hook detected but no explicit query error token was found.")
    elif not has_error_branch:
        status = "review_error_path"
        notes.append("error token exists but no explicit conditional branch was detected.")
    else:
        status = "explicit_error_state"

    return SurfaceAudit(
        file=str(file_path.relative_to(repo_root)).replace("\\", "/"),
        query_count=query_count,
        error_variables=error_variables,
        has_property_error_usage=has_property_error_usage,
        has_error_token=has_error_token,
        has_error_branch=has_error_branch,
        status=status,
        notes=notes,
    )


def render_markdown(audits: list[SurfaceAudit]) -> str:
    total = len(audits)
    explicit = sum(1 for a in audits if a.status == "explicit_error_state")
    review = sum(1 for a in audits if a.status == "review_error_path")
    missing = sum(1 for a in audits if a.status == "missing_error_state")

    lines = [
        "# Frontend Async State Audit",
        "",
        f"- Surfaces scanned: `{total}`",
        f"- Explicit error state: `{explicit}`",
        f"- Review needed: `{review}`",
        f"- Missing error state: `{missing}`",
        "",
        "## Review Targets",
        "",
        "| File | Queries | Error Vars | Status | Notes |",
        "|------|---------|------------|--------|-------|",
    ]

    targets = [a for a in audits if a.status != "explicit_error_state"]
    if targets:
        for item in sorted(targets, key=lambda x: (x.status, -x.query_count, x.file)):
            notes = "; ".join(item.notes) if item.notes else "-"
            error_vars = ", ".join(item.error_variables) if item.error_variables else "-"
            lines.append(f"| `{item.file}` | {item.query_count} | `{error_vars}` | `{item.status}` | {notes} |")
    else:
        lines.append("| _none_ | - | - | - | All query surfaces include explicit error handling patterns. |")

    lines.extend(
        [
            "",
            "## Raw Status",
            "",
            "| File | Queries | Error Vars | Property Usage | Status |",
            "|------|---------|------------|----------------|--------|",
        ]
    )
    for item in sorted(audits, key=lambda x: (-x.query_count, x.file)):
        error_vars = ", ".join(item.error_variables) if item.error_variables else "-"
        property_usage = "yes" if item.has_property_error_usage else "no"
        lines.append(f"| `{item.file}` | {item.query_count} | `{error_vars}` | `{property_usage}` | `{item.status}` |")

    lines.append("")
    return "\n".join(lines)


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parents[1]

    audits: list[SurfaceAudit] = []
    for file_path in scan_files(repo_root):
        result = audit_file(file_path, repo_root)
        if result:
            audits.append(result)

    summary = {
        "surfaces_scanned": len(audits),
        "explicit_error_state": sum(1 for a in audits if a.status == "explicit_error_state"),
        "review_error_path": sum(1 for a in audits if a.status == "review_error_path"),
        "missing_error_state": sum(1 for a in audits if a.status == "missing_error_state"),
    }

    print(json.dumps(summary, indent=2))

    if args.write:
        docs_dir = repo_root / "docs"
        docs_dir.mkdir(parents=True, exist_ok=True)
        (docs_dir / "frontend-async-state-audit.json").write_text(
            json.dumps(
                {
                    "summary": summary,
                    "items": [asdict(item) for item in audits],
                },
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        (docs_dir / "frontend-async-state-audit.md").write_text(
            render_markdown(audits),
            encoding="utf-8",
        )
        print("[write] docs/frontend-async-state-audit.json")
        print("[write] docs/frontend-async-state-audit.md")

    problems: list[str] = []
    if args.strict and (summary["review_error_path"] > 0 or summary["missing_error_state"] > 0):
        problems.append("strict mode requires zero review_error_path and zero missing_error_state.")
    if args.max_review is not None and summary["review_error_path"] > args.max_review:
        problems.append(
            f"review_error_path={summary['review_error_path']} exceeds max_review={args.max_review}."
        )
    if args.max_missing is not None and summary["missing_error_state"] > args.max_missing:
        problems.append(
            f"missing_error_state={summary['missing_error_state']} exceeds max_missing={args.max_missing}."
        )

    if problems:
        for problem in problems:
            print(f"[error] {problem}")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
