#!/usr/bin/env python3
"""Run and evaluate the Safe-to-Start external gate checks."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = REPO_ROOT / "tmp" / "safe_to_start_gate_result.json"
DEFAULT_LOG_DIR = REPO_ROOT / "tmp" / "safe_to_start_gate_logs"

BACKEND_DIR = REPO_ROOT / "backend"
FRONTEND_DIR = REPO_ROOT / "frontend"

REQUIRED_SCREENSHOTS = [
    "real-audit-dashboard-desktop.png",
    "real-audit-dashboard-mobile.png",
    "real-audit-building-detail-desktop.png",
    "real-audit-building-detail-mobile.png",
]


@dataclass
class CheckResult:
    check_id: str
    requirement: str
    status: str
    exit_code: int | None
    duration_seconds: float | None
    evidence: list[str]
    notes: list[str]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate the external gate #1 (safe-to-start dossier).",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute command checks (G1-G3). Without this flag, they are reported as skipped.",
    )
    parser.add_argument(
        "--run-screenshot-audit",
        action="store_true",
        help="Run Playwright screenshot audit before validating screenshot evidence.",
    )
    parser.add_argument(
        "--allow-missing-screenshots",
        action="store_true",
        help="Do not fail G4 when required screenshot artifacts are missing.",
    )
    parser.add_argument(
        "--allow-incomplete-exit0",
        action="store_true",
        help="Return exit code 0 when verdict is INCOMPLETE (useful for planning mode).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help=f"Path to write the gate result JSON (default: {DEFAULT_OUTPUT}).",
    )
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=DEFAULT_LOG_DIR,
        help=f"Directory for command logs (default: {DEFAULT_LOG_DIR}).",
    )
    return parser.parse_args()


def run_command(command: list[str], cwd: Path, log_path: Path) -> tuple[int, float]:
    start = time.perf_counter()
    try:
        completed = subprocess.run(
            command,
            cwd=cwd,
            capture_output=True,
            text=True,
            check=False,
        )
        rc = completed.returncode
        stdout = completed.stdout
        stderr = completed.stderr
    except FileNotFoundError as exc:
        rc = 127
        stdout = ""
        stderr = str(exc)
    duration = time.perf_counter() - start

    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_path.write_text(
        "\n".join(
            [
                f"$ {' '.join(command)}",
                f"# cwd: {cwd}",
                "",
                "=== STDOUT ===",
                stdout.rstrip(),
                "",
                "=== STDERR ===",
                stderr.rstrip(),
                "",
                f"=== EXIT CODE: {rc} ===",
                f"=== DURATION_SECONDS: {duration:.3f} ===",
                "",
            ]
        ),
        encoding="utf-8",
    )

    return rc, duration


def evaluate_docs_claim_discipline() -> tuple[bool, list[str]]:
    notes: list[str] = []
    onepager = REPO_ROOT / "docs" / "market" / "safe-to-start-demo-onepager.md"
    runbook = REPO_ROOT / "docs" / "safe-to-start-gate-runbook.md"

    ok = True
    if not onepager.exists():
        return False, [f"Missing file: {onepager}"]
    if not runbook.exists():
        return False, [f"Missing file: {runbook}"]

    onepager_text = onepager.read_text(encoding="utf-8").lower()
    runbook_text = runbook.read_text(encoding="utf-8").lower()

    if "no automatic legal-compliance guarantee" not in onepager_text:
        ok = False
        notes.append("One-pager missing explicit no-legal-guarantee boundary.")
    if "not `legal guarantee`" not in runbook_text:
        ok = False
        notes.append("Runbook missing explicit claim-discipline phrase.")

    if ok:
        notes.append("Claim-discipline checks found in runbook and one-pager.")
    return ok, notes


def evaluate_screenshots(allow_missing: bool, command_checks_executed: bool) -> tuple[str, list[str], list[str]]:
    evidence: list[str] = []
    notes: list[str] = []
    screenshots_dir = FRONTEND_DIR / "test-results"

    missing: list[str] = []
    for filename in REQUIRED_SCREENSHOTS:
        path = screenshots_dir / filename
        if path.exists():
            evidence.append(str(path.relative_to(REPO_ROOT)))
        else:
            missing.append(filename)

    if missing:
        notes.append(f"Missing required screenshots: {', '.join(missing)}")
        if not command_checks_executed:
            notes.append("Screenshot check is non-blocking in plan mode.")
            return "skipped", evidence, notes
        if allow_missing:
            notes.append("Missing screenshots allowed by --allow-missing-screenshots.")
            return "skipped", evidence, notes
        return "failed", evidence, notes

    notes.append("Required desktop/mobile screenshot evidence is present.")
    return "passed", evidence, notes


def finalize_verdict(results: list[CheckResult]) -> str:
    statuses = {result.status for result in results}
    if "failed" in statuses:
        return "FAIL"
    if "skipped" in statuses:
        return "INCOMPLETE"
    return "PASS"


def main() -> int:
    args = parse_args()
    results: list[CheckResult] = []

    g1_cmd = ["python", "-m", "app.seeds.seed_verify"]
    g2_cmd = ["npm", "run", "test:e2e:real:preflight"]
    g3_cmd = ["npm", "run", "test:e2e:real"]
    screenshot_cmd = ["npx", "playwright", "test", "-c", "playwright.real.config.ts", "screenshot-audit.spec.ts"]

    args.log_dir.mkdir(parents=True, exist_ok=True)

    def command_check(
        check_id: str,
        requirement: str,
        command: list[str],
        cwd: Path,
    ) -> CheckResult:
        if not args.run:
            return CheckResult(
                check_id=check_id,
                requirement=requirement,
                status="skipped",
                exit_code=None,
                duration_seconds=None,
                evidence=[],
                notes=[f"Planned command: {' '.join(command)} (cwd={cwd})"],
            )

        log_path = args.log_dir / f"{check_id.lower()}.log"
        rc, duration = run_command(command, cwd=cwd, log_path=log_path)
        return CheckResult(
            check_id=check_id,
            requirement=requirement,
            status="passed" if rc == 0 else "failed",
            exit_code=rc,
            duration_seconds=duration,
            evidence=[str(log_path.relative_to(REPO_ROOT))],
            notes=[],
        )

    results.append(
        command_check(
            "G1",
            "Seeded scenario exists and passes threshold checks",
            g1_cmd,
            BACKEND_DIR,
        )
    )
    results.append(
        command_check(
            "G2",
            "Real environment targeting is correct before test run",
            g2_cmd,
            FRONTEND_DIR,
        )
    )
    results.append(
        command_check(
            "G3",
            "Real e2e suite passes against SwissBuilding backend",
            g3_cmd,
            FRONTEND_DIR,
        )
    )

    if args.run and args.run_screenshot_audit:
        log_path = args.log_dir / "g4_screenshot_audit.log"
        run_command(screenshot_cmd, cwd=FRONTEND_DIR, log_path=log_path)

    g4_status, g4_evidence, g4_notes = evaluate_screenshots(
        allow_missing=args.allow_missing_screenshots,
        command_checks_executed=args.run,
    )
    results.append(
        CheckResult(
            check_id="G4",
            requirement="UI progression raw -> complete is visible on the same building chain",
            status=g4_status,
            exit_code=None,
            duration_seconds=None,
            evidence=g4_evidence,
            notes=g4_notes,
        )
    )

    g5_ok, g5_notes = evaluate_docs_claim_discipline()
    results.append(
        CheckResult(
            check_id="G5",
            requirement="Safe-to-start positioning remains claim-disciplined",
            status="passed" if g5_ok else "failed",
            exit_code=None,
            duration_seconds=None,
            evidence=[
                "docs/safe-to-start-gate-runbook.md",
                "docs/market/safe-to-start-demo-onepager.md",
            ],
            notes=g5_notes,
        )
    )

    verdict = finalize_verdict(results)
    summary = {
        "total": len(results),
        "passed": sum(result.status == "passed" for result in results),
        "failed": sum(result.status == "failed" for result in results),
        "skipped": sum(result.status == "skipped" for result in results),
    }

    payload = {
        "gate": "safe-to-start dossier",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "generated_on": str(date.today()),
        "mode": "run" if args.run else "plan",
        "verdict": verdict,
        "summary": summary,
        "checks": [asdict(result) for result in results],
    }

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    print(f"[gate] verdict={verdict} (passed={summary['passed']} failed={summary['failed']} skipped={summary['skipped']})")
    print(f"[gate] report={args.output}")
    for result in results:
        print(f"[{result.status}] {result.check_id} {result.requirement}")
        for note in result.notes:
            print(f"  - {note}")

    if verdict == "PASS":
        return 0
    if verdict == "INCOMPLETE" and args.allow_incomplete_exit0:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
