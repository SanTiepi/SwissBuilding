#!/usr/bin/env python3
"""Build an evidence bundle from a Safe-to-Start gate run."""

from __future__ import annotations

import argparse
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_GATE_JSON = REPO_ROOT / "tmp" / "safe_to_start_gate_result.json"
DEFAULT_BUNDLE_ROOT = REPO_ROOT / "artifacts" / "gates" / "safe-to-start"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a timestamped proof bundle for external gate #1.",
    )
    parser.add_argument(
        "--gate-json",
        type=Path,
        default=DEFAULT_GATE_JSON,
        help=f"Gate report JSON path (default: {DEFAULT_GATE_JSON}).",
    )
    parser.add_argument(
        "--bundle-root",
        type=Path,
        default=DEFAULT_BUNDLE_ROOT,
        help=f"Root directory for bundles (default: {DEFAULT_BUNDLE_ROOT}).",
    )
    parser.add_argument(
        "--strict-pass",
        action="store_true",
        help="Fail if gate verdict is not PASS.",
    )
    return parser.parse_args()


def safe_copy(src: Path, dst: Path) -> bool:
    if not src.exists() or not src.is_file():
        return False
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)
    return True


def main() -> int:
    args = parse_args()
    if not args.gate_json.exists():
        print(f"[error] missing gate json: {args.gate_json}")
        return 1

    report = json.loads(args.gate_json.read_text(encoding="utf-8"))
    verdict = str(report.get("verdict", "UNKNOWN"))
    generated_at = datetime.now(timezone.utc)
    stamp = generated_at.strftime("%Y%m%dT%H%M%SZ")
    bundle_dir = args.bundle_root / stamp
    bundle_dir.mkdir(parents=True, exist_ok=True)

    copied: list[str] = []
    missing: list[str] = []

    gate_json_dst = bundle_dir / "gate_result.json"
    safe_copy(args.gate_json, gate_json_dst)
    copied.append(str(gate_json_dst.relative_to(REPO_ROOT)))

    # Copy evidence files referenced in check results.
    checks = report.get("checks", [])
    for check in checks:
        for evidence in check.get("evidence", []):
            src = (REPO_ROOT / evidence).resolve()
            dst = bundle_dir / "evidence" / evidence.replace("\\", "/")
            if safe_copy(src, dst):
                copied.append(str(dst.relative_to(REPO_ROOT)))
            else:
                missing.append(evidence)

    # Copy all real-audit screenshots as an operator-friendly add-on.
    screenshot_dir = REPO_ROOT / "frontend" / "test-results"
    for screenshot in screenshot_dir.glob("real-audit-*.png"):
        dst = bundle_dir / "screenshots" / screenshot.name
        if safe_copy(screenshot, dst):
            copied.append(str(dst.relative_to(REPO_ROOT)))

    summary_lines = [
        "# Safe-to-Start Gate Proof Bundle",
        "",
        f"- created_at_utc: `{generated_at.isoformat()}`",
        f"- gate_verdict: `{verdict}`",
        f"- source_report: `{args.gate_json}`",
        "",
        "## Included files",
    ]
    summary_lines.extend(f"- `{path}`" for path in sorted(set(copied)))
    summary_lines.extend(["", "## Missing referenced evidence"])
    if missing:
        summary_lines.extend(f"- `{path}`" for path in sorted(set(missing)))
    else:
        summary_lines.append("- none")
    summary_lines.append("")

    summary_md = bundle_dir / "SUMMARY.md"
    summary_md.write_text("\n".join(summary_lines), encoding="utf-8")
    copied.append(str(summary_md.relative_to(REPO_ROOT)))

    manifest = {
        "created_at_utc": generated_at.isoformat(),
        "gate_verdict": verdict,
        "source_report": str(args.gate_json),
        "bundle_dir": str(bundle_dir),
        "files": sorted(set(copied)),
        "missing_referenced_evidence": sorted(set(missing)),
    }
    manifest_path = bundle_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"[bundle] dir={bundle_dir}")
    print(f"[bundle] verdict={verdict}")
    print(f"[bundle] files={len(set(copied))}, missing_references={len(set(missing))}")

    if args.strict_pass and verdict != "PASS":
        print("[error] strict-pass enabled and gate verdict is not PASS.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
