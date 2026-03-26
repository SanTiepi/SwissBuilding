from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from run_confidence_suite import DEFAULT_GROUPS, GROUPS


BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = BACKEND_ROOT.parent
TESTS_ROOT = BACKEND_ROOT / "tests"


def _run(cmd: list[str]) -> int:
    print("Running:")
    print(" ".join(cmd))
    print("")
    return subprocess.call(cmd, cwd=BACKEND_ROOT)


def _xdist_args(disabled: bool) -> list[str]:
    if disabled:
        return []
    try:
        import xdist.plugin  # noqa: F401
    except ImportError:
        return []
    return ["-n", "auto", "--dist", "loadfile"]


def _git_changed_backend_paths() -> list[Path]:
    cmd = ["git", "status", "--porcelain", "--untracked-files=all", "--", "backend"]
    result = subprocess.run(
        cmd,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    changed: list[Path] = []
    for raw_line in result.stdout.splitlines():
        line = raw_line.rstrip()
        if not line:
            continue
        path_text = line[3:]
        if " -> " in path_text:
            path_text = path_text.split(" -> ", 1)[1]
        changed.append(Path(path_text))
    return changed


def _pluralize(name: str) -> str:
    if name.endswith("y") and len(name) > 1 and name[-2] not in "aeiou":
        return f"{name[:-1]}ies"
    if name.endswith("s"):
        return name
    return f"{name}s"


def _name_variants(stem: str) -> set[str]:
    base = stem.lower()
    variants = {base, _pluralize(base)}
    suffixes = [
        "_service",
        "_services",
        "_schema",
        "_schemas",
        "_model",
        "_models",
        "_api",
        "_router",
        "_route",
    ]
    for suffix in suffixes:
        if base.endswith(suffix):
            trimmed = base[: -len(suffix)]
            if trimmed:
                variants.add(trimmed)
                variants.add(_pluralize(trimmed))
    return {value for value in variants if value}


def _infer_tests_from_paths(paths: list[Path]) -> list[str]:
    all_tests = sorted(TESTS_ROOT.glob("test_*.py"))
    selected: set[str] = set()
    for path in paths:
        if path.parts[:2] == ("backend", "tests") and path.name.startswith("test_"):
            selected.add(path.relative_to(BACKEND_ROOT).as_posix())
            continue
        if path.parts[:2] != ("backend", "app"):
            continue
        variants = _name_variants(path.stem)
        if not variants:
            continue
        for test_path in all_tests:
            test_name = test_path.stem.removeprefix("test_").lower()
            if any(
                test_name == variant
                or test_name.startswith(f"{variant}_")
                or test_name.endswith(f"_{variant}")
                for variant in variants
            ):
                selected.add(test_path.relative_to(BACKEND_ROOT).as_posix())
    return sorted(selected)


def _group_tests(group_names: list[str]) -> list[str]:
    tests: list[str] = []
    seen: set[str] = set()
    for group_name in group_names:
        for test_path in GROUPS[group_name]:
            if test_path not in seen:
                seen.add(test_path)
                tests.append(test_path)
    return tests


def _build_pytest_cmd(
    *,
    tests: list[str],
    no_parallel: bool,
    last_failed: bool = False,
    maxfail: int | None = None,
) -> list[str]:
    cmd = [sys.executable, "-m", "pytest", "-q", "--tb=line"]
    cmd.extend(_xdist_args(no_parallel))
    if last_failed:
        cmd.append("--lf")
    if maxfail is not None:
        cmd.append(f"--maxfail={maxfail}")
    cmd.extend(tests)
    return cmd


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Fast local backend test loop with changed/confidence/full modes."
    )
    parser.add_argument(
        "mode",
        nargs="?",
        default="changed",
        choices=["changed", "confidence", "last-failed", "full", "files"],
    )
    parser.add_argument("paths", nargs="*")
    parser.add_argument("--no-parallel", action="store_true")
    parser.add_argument("--maxfail", type=int, default=None)
    parser.add_argument("--list", action="store_true", dest="list_only")
    args = parser.parse_args(argv[1:])

    if args.mode == "confidence":
        tests = _group_tests(DEFAULT_GROUPS)
    elif args.mode == "full":
        tests = ["tests/"]
    elif args.mode == "last-failed":
        tests = ["tests/"]
    elif args.mode == "files":
        if not args.paths:
            print("No test paths provided for mode=files.", file=sys.stderr)
            return 2
        tests = args.paths
    else:
        changed = _git_changed_backend_paths()
        tests = _infer_tests_from_paths(changed)
        if not tests:
            tests = _group_tests(DEFAULT_GROUPS)
        if args.list_only:
            print("Changed backend paths:")
            for path in changed:
                print(f"- {path.as_posix()}")
            print("")
            print("Selected tests:")
            for test_path in tests:
                print(f"- {test_path}")
            return 0

    cmd = _build_pytest_cmd(
        tests=tests,
        no_parallel=args.no_parallel,
        last_failed=args.mode == "last-failed",
        maxfail=args.maxfail,
    )
    return _run(cmd)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
