#!/usr/bin/env python3
"""Inventory and sanity checks for backend API router wiring."""

from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ROUTER_PATH = REPO_ROOT / "backend" / "app" / "api" / "router.py"
API_DIR = REPO_ROOT / "backend" / "app" / "api"
OUTPUT_MD = REPO_ROOT / "docs" / "router-inventory.md"
OUTPUT_JSON = REPO_ROOT / "docs" / "router-inventory.json"

IMPORT_BLOCK_RE = re.compile(r"from app\.api import \((?P<body>.*?)\)\n\napi_router", re.DOTALL)
INCLUDE_RE = re.compile(
    r"api_router\.include_router\((?P<module>\w+)\.router,\s*prefix=\"(?P<prefix>[^\"]*)\",\s*tags=\[(?P<tags>[^\]]*)\]\)"
)


@dataclass
class IncludeEntry:
    module: str
    prefix: str
    tag: str
    line: int


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate backend router wiring inventory.")
    parser.add_argument("--write", action="store_true", help="Write markdown/json reports under docs/.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if import/include wiring is inconsistent.",
    )
    return parser.parse_args()


def read_router() -> str:
    return ROUTER_PATH.read_text(encoding="utf-8")


def parse_imported_modules(router_text: str) -> list[str]:
    match = IMPORT_BLOCK_RE.search(router_text)
    if not match:
        return []
    body = match.group("body")
    modules = [line.strip().rstrip(",") for line in body.splitlines() if line.strip()]
    return [module for module in modules if module and module != ")"]


def parse_include_entries(router_text: str) -> tuple[list[IncludeEntry], list[str]]:
    entries: list[IncludeEntry] = []
    malformed: list[str] = []
    lines = router_text.splitlines()
    for idx, line in enumerate(lines, start=1):
        if "api_router.include_router(" not in line:
            continue
        match = INCLUDE_RE.search(line)
        if not match:
            malformed.append(f"line {idx}: {line.strip()}")
            continue
        raw_tag = match.group("tags").strip()
        tag = raw_tag.strip().strip('"').strip("'")
        entries.append(
            IncludeEntry(
                module=match.group("module"),
                prefix=match.group("prefix"),
                tag=tag,
                line=idx,
            )
        )
    return entries, malformed


def api_module_files() -> list[str]:
    modules: list[str] = []
    for path in sorted(API_DIR.glob("*.py")):
        if path.name in {"__init__.py", "router.py"}:
            continue
        modules.append(path.stem)
    return modules


def find_duplicate_modules(entries: list[IncludeEntry]) -> list[str]:
    seen: set[str] = set()
    duplicates: list[str] = []
    for entry in entries:
        if entry.module in seen:
            duplicates.append(entry.module)
        seen.add(entry.module)
    return sorted(set(duplicates))


def find_tag_style_issues(entries: list[IncludeEntry]) -> list[str]:
    issues: list[str] = []
    for entry in entries:
        if "-" in entry.tag:
            issues.append(f"{entry.module}: tag '{entry.tag}' contains hyphen")
        if entry.tag and entry.tag[0].islower():
            issues.append(f"{entry.module}: tag '{entry.tag}' starts lowercase")
    return issues


def build_summary(router_text: str) -> dict[str, object]:
    imported = parse_imported_modules(router_text)
    includes, malformed = parse_include_entries(router_text)
    include_modules = [entry.module for entry in includes]
    module_files = api_module_files()

    imported_set = set(imported)
    include_set = set(include_modules)
    module_file_set = set(module_files)

    import_not_included = sorted(imported_set - include_set)
    included_not_imported = sorted(include_set - imported_set)
    duplicate_includes = find_duplicate_modules(includes)
    tag_style_issues = find_tag_style_issues(includes)

    module_files_not_imported = sorted(module_file_set - imported_set)
    imported_without_module_file = sorted(imported_set - module_file_set)

    return {
        "router_path": str(ROUTER_PATH.relative_to(REPO_ROOT)).replace("\\", "/"),
        "imported_modules_count": len(imported),
        "include_entries_count": len(includes),
        "included_unique_modules_count": len(include_set),
        "api_module_files_count": len(module_files),
        "import_not_included": import_not_included,
        "included_not_imported": included_not_imported,
        "duplicate_includes": duplicate_includes,
        "malformed_include_lines": malformed,
        "module_files_not_imported": module_files_not_imported,
        "imported_without_module_file": imported_without_module_file,
        "tag_style_issues": tag_style_issues,
        "empty_prefix_count": sum(1 for entry in includes if entry.prefix == ""),
        "non_empty_prefix_count": sum(1 for entry in includes if entry.prefix != ""),
        "entries": [asdict(entry) for entry in includes],
    }


def render_markdown(summary: dict[str, object]) -> str:
    lines = [
        "# Router Inventory",
        "",
        "Generated by `python scripts/router_inventory.py --write`.",
        "",
        f"- Router file: `{summary['router_path']}`",
        f"- Imported modules: `{summary['imported_modules_count']}`",
        f"- Include entries: `{summary['include_entries_count']}`",
        f"- Unique included modules: `{summary['included_unique_modules_count']}`",
        f"- API module files: `{summary['api_module_files_count']}`",
        f"- Empty prefixes: `{summary['empty_prefix_count']}`",
        f"- Non-empty prefixes: `{summary['non_empty_prefix_count']}`",
        "",
    ]

    def add_list(title: str, values: list[str]) -> None:
        lines.append(f"## {title}")
        lines.append("")
        if values:
            for value in values:
                lines.append(f"- `{value}`")
        else:
            lines.append("- _none_")
        lines.append("")

    add_list("Import Not Included", summary["import_not_included"])
    add_list("Included Not Imported", summary["included_not_imported"])
    add_list("Duplicate Includes", summary["duplicate_includes"])
    add_list("Malformed Include Lines", summary["malformed_include_lines"])
    add_list("Module Files Not Imported", summary["module_files_not_imported"])
    add_list("Imported Without Module File", summary["imported_without_module_file"])
    add_list("Tag Style Issues", summary["tag_style_issues"])

    lines.extend(
        [
            "## Include Entries",
            "",
            "| Module | Prefix | Tag | Line |",
            "| --- | --- | --- | ---: |",
        ]
    )
    for entry in summary["entries"]:
        lines.append(
            f"| `{entry['module']}` | `{entry['prefix']}` | `{entry['tag']}` | {entry['line']} |"
        )
    lines.append("")

    return "\n".join(lines)


def has_strict_violations(summary: dict[str, object]) -> bool:
    keys = [
        "import_not_included",
        "included_not_imported",
        "duplicate_includes",
        "malformed_include_lines",
    ]
    return any(summary[key] for key in keys)


def main() -> int:
    args = parse_args()
    router_text = read_router()
    summary = build_summary(router_text)

    print(
        json.dumps(
            {
                "imported_modules_count": summary["imported_modules_count"],
                "include_entries_count": summary["include_entries_count"],
                "included_unique_modules_count": summary["included_unique_modules_count"],
                "api_module_files_count": summary["api_module_files_count"],
                "strict_violations": bool(has_strict_violations(summary)),
            },
            indent=2,
        )
    )

    if args.write:
        OUTPUT_MD.write_text(render_markdown(summary), encoding="utf-8")
        OUTPUT_JSON.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"[write] {OUTPUT_MD.relative_to(REPO_ROOT)}")
        print(f"[write] {OUTPUT_JSON.relative_to(REPO_ROOT)}")

    if args.strict and has_strict_violations(summary):
        print("[error] strict router check failed due to wiring inconsistencies.")
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

