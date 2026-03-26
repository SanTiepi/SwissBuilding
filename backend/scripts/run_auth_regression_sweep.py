from __future__ import annotations

import argparse
import re
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
TESTS_ROOT = BACKEND_ROOT / "tests"

TEST_DEF_RE = re.compile(
    r"^\s*(?:async\s+def|def)\s+(test_[A-Za-z0-9_]+)\s*\(",
    re.MULTILINE,
)
ASSERT_403_RE = re.compile(r"assert\s+.+?status_code\s*==\s*403\b")

UNAUTH_NAME_TOKENS = (
    "unauth",
    "unauthorized",
    "without_auth",
    "without_token",
    "requires_auth",
    "requires_login",
    "no_auth",
    "no_token",
    "missing_auth",
    "missing_token",
)

UNAUTH_BODY_TOKENS = (
    "unauthenticated",
    "unauthorized",
    "without auth",
    "without token",
    "requires auth",
    "missing auth",
    "missing token",
    "no auth",
    "no token",
)

FORBIDDEN_TOKENS = (
    "forbidden",
    "wrong_role",
    "insufficient",
    "inactive",
    "disabled",
    "permission",
    "denied",
    "different_user",
    "other_user",
    "cross_tenant",
    "cross_org",
)

AUTH_USAGE_TOKENS = (
    "headers=",
    "_headers(",
    "authorization",
    "www-authenticate",
)


@dataclass(frozen=True)
class TestBlock:
    path: Path
    name: str
    start_line: int
    end_line: int
    lines: list[str]

    @property
    def body(self) -> str:
        return "".join(self.lines)


@dataclass(frozen=True)
class Finding:
    path: Path
    test_name: str
    line_no: int
    score: int
    reasons: tuple[str, ...]
    line_text: str


def _display_path(path: Path) -> str:
    try:
        return path.relative_to(BACKEND_ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def _iter_test_blocks(path: Path) -> list[TestBlock]:
    content = path.read_text(encoding="utf-8").splitlines(keepends=True)
    matches = list(TEST_DEF_RE.finditer("".join(content)))
    if not matches:
        return []

    blocks: list[TestBlock] = []
    line_offsets: list[int] = []
    running = 0
    for line in content:
        line_offsets.append(running)
        running += len(line)

    def offset_to_line(offset: int) -> int:
        low = 0
        high = len(line_offsets) - 1
        while low <= high:
            mid = (low + high) // 2
            if line_offsets[mid] <= offset:
                low = mid + 1
            else:
                high = mid - 1
        return high + 1

    text = "".join(content)
    spans: list[tuple[str, int, int]] = []
    for match in matches:
        name = match.group(1)
        start_offset = match.start()
        spans.append((name, start_offset, match.end()))

    for index, (name, start_offset, _) in enumerate(spans):
        end_offset = spans[index + 1][1] if index + 1 < len(spans) else len(text)
        start_line = offset_to_line(start_offset)
        end_line = offset_to_line(end_offset)
        blocks.append(
            TestBlock(
                path=path,
                name=name,
                start_line=start_line,
                end_line=end_line,
                lines=content[start_line - 1 : end_line - 1],
            )
        )
    return blocks


def _classify_block(block: TestBlock) -> tuple[int, list[str]]:
    score = 0
    reasons: list[str] = []
    name_lower = block.name.lower()
    body_lower = block.body.lower()

    if any(token in name_lower for token in UNAUTH_NAME_TOKENS):
        score += 4
        reasons.append("unauth token in test name")
    if any(token in body_lower for token in UNAUTH_BODY_TOKENS):
        score += 2
        reasons.append("unauth token in body/docstring")
    if not any(token in body_lower for token in AUTH_USAGE_TOKENS):
        score += 2
        reasons.append("no explicit auth headers in body")
    if any(token in name_lower or token in body_lower for token in FORBIDDEN_TOKENS):
        score -= 5
        reasons.append("forbidden/permission token present")

    return score, reasons


def _scan_paths(paths: list[Path]) -> list[Finding]:
    findings: list[Finding] = []
    for path in paths:
        for block in _iter_test_blocks(path):
            score, reasons = _classify_block(block)
            if score < 3:
                continue
            for index, line in enumerate(block.lines, start=block.start_line):
                if ASSERT_403_RE.search(line):
                    findings.append(
                        Finding(
                            path=path,
                            test_name=block.name,
                            line_no=index,
                            score=score,
                            reasons=tuple(reasons),
                            line_text=line.rstrip(),
                        )
                    )
    return findings


def _candidate_paths(user_paths: list[str]) -> list[Path]:
    if user_paths:
        candidates = [BACKEND_ROOT / raw for raw in user_paths]
    else:
        candidates = sorted(TESTS_ROOT.glob("test_*.py"))
    return [path for path in candidates if path.exists() and path.is_file()]


def _rewrite(findings: list[Finding]) -> int:
    by_path: dict[Path, list[Finding]] = {}
    for finding in findings:
        by_path.setdefault(finding.path, []).append(finding)

    changed_files = 0
    for path, path_findings in by_path.items():
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        changed = False
        for finding in path_findings:
            index = finding.line_no - 1
            if index >= len(lines):
                continue
            updated = re.sub(
                r"(status_code\s*==\s*)403\b",
                r"\g<1>401",
                lines[index],
                count=1,
            )
            if updated != lines[index]:
                lines[index] = updated
                changed = True
        if changed:
            path.write_text("".join(lines), encoding="utf-8")
            changed_files += 1
    return changed_files


def _run_pytest(files: list[str]) -> int:
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=line", *files]
    print("Running:")
    print(" ".join(cmd))
    print("")
    return subprocess.call(cmd, cwd=BACKEND_ROOT)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Scan backend tests for likely unauthenticated 403 assertions."
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="scan",
        choices=["scan", "rewrite", "pytest"],
    )
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--files-only", action="store_true")
    args = parser.parse_args(argv[1:])

    findings = _scan_paths(_candidate_paths(args.paths))
    if not findings:
        print("No likely unauthenticated 403 assertions found.")
        return 0

    unique_files = sorted({_display_path(finding.path) for finding in findings})

    if args.mode == "rewrite":
        changed_files = _rewrite(findings)
        print(f"Rewrote {len(findings)} assertions across {changed_files} files.")
        return 0

    if args.mode == "pytest":
        return _run_pytest(unique_files)

    if args.files_only:
        for file_path in unique_files:
            print(file_path)
        return 0

    print(f"Found {len(findings)} likely unauthenticated 403 assertions.")
    print("")
    for finding in findings:
        reason_text = "; ".join(finding.reasons)
        print(
            f"{_display_path(finding.path)}:{finding.line_no} "
            f"{finding.test_name} [score={finding.score}] {reason_text}"
        )
        print(f"  {finding.line_text}")
    print("")
    print("Unique files:")
    for file_path in unique_files:
        print(f"- {file_path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
