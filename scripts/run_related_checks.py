from __future__ import annotations

import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class FrontendSurface:
    name: str
    patterns: tuple[str, ...]


@dataclass(frozen=True)
class BackendGroup:
    name: str
    patterns: tuple[str, ...]


FRONTEND_SURFACES = (
    FrontendSurface(
        "trust",
        (
            "passport",
            "trust",
            "contradiction",
            "evidence",
            "unknown",
            "change_signal",
        ),
    ),
    FrontendSurface(
        "readiness",
        (
            "readiness",
            "completeness",
            "requalification",
            "safe_to",
            "post_works",
            "postworks",
        ),
    ),
    FrontendSurface(
        "timeline",
        (
            "timeline",
            "time_machine",
            "snapshot",
            "activity",
            "building_detail",
        ),
    ),
    FrontendSurface(
        "portfolio",
        (
            "portfolio",
            "quality",
            "heatmap",
            "comparison",
            "campaign",
        ),
    ),
    FrontendSurface(
        "dossier",
        (
            "dossier",
            "export",
            "transfer_package",
            "authority_pack",
        ),
    ),
    FrontendSurface(
        "shell",
        (
            "header",
            "sidebar",
            "notification",
            "command_palette",
            "settings",
            "login",
            "navigation",
        ),
    ),
)

BACKEND_GROUPS = (
    BackendGroup(
        "wedge",
        (
            "auth",
            "building",
            "diagnostic",
            "readiness",
            "dossier",
            "authority_pack",
            "seed_verify",
            "compliance",
            "regulatory",
        ),
    ),
    BackendGroup(
        "operating",
        (
            "passport",
            "time_machine",
            "post_works",
            "transaction",
            "change_signal",
            "trust",
            "unknown",
            "snapshot",
        ),
    ),
    BackendGroup(
        "portfolio",
        (
            "portfolio",
            "campaign",
            "simulation",
            "risk_trend",
        ),
    ),
    BackendGroup(
        "full_chain",
        (
            "avt_apt",
            "authority_demo",
            "full_chain",
        ),
    ),
)


def normalize_target(raw: str) -> str:
    return raw.replace("\\", "/").lower()


def infer_frontend_surfaces(targets: list[str]) -> list[str]:
    matches: list[str] = []
    for target in targets:
        normalized = normalize_target(target)
        if not normalized.startswith("frontend/"):
            continue
        for surface in FRONTEND_SURFACES:
            if any(pattern in normalized for pattern in surface.patterns):
                matches.append(surface.name)
    return sorted(set(matches))


def infer_backend_groups(targets: list[str]) -> list[str]:
    matches: list[str] = []
    for target in targets:
        normalized = normalize_target(target)
        if not normalized.startswith("backend/"):
            continue
        for group in BACKEND_GROUPS:
            if any(pattern in normalized for pattern in group.patterns):
                matches.append(group.name)
    return sorted(set(matches))


def requires_real_e2e_preflight(targets: list[str]) -> bool:
    for target in targets:
        normalized = normalize_target(target)
        if normalized.startswith("frontend/e2e-real/"):
            return True
        if normalized == "frontend/playwright.real.config.ts":
            return True
        if normalized == "frontend/scripts/e2e_real_preflight.mjs":
            return True
    return False


def run_command(command: list[str], cwd: Path) -> int:
    print(f"$ {' '.join(command)}")
    return subprocess.call(" ".join(command), cwd=cwd, shell=True)


def print_usage() -> int:
    print("Usage:")
    print("  python scripts/run_related_checks.py --list")
    print("  python scripts/run_related_checks.py [--run] [--with-e2e] <file> [<file> ...]")
    print("")
    print("Examples:")
    print("  python scripts/run_related_checks.py frontend/src/components/PassportCard.tsx")
    print("  python scripts/run_related_checks.py --run frontend/src/pages/ReadinessWallet.tsx")
    print("  python scripts/run_related_checks.py --run --with-e2e frontend/src/components/NotificationBell.tsx")
    print("  python scripts/run_related_checks.py backend/app/services/passport_service.py")
    return 0


def print_catalog() -> int:
    print("Frontend surfaces:")
    for surface in FRONTEND_SURFACES:
        print(f"- {surface.name}: {', '.join(surface.patterns)}")
    print("")
    print("Backend confidence groups:")
    for group in BACKEND_GROUPS:
        print(f"- {group.name}: {', '.join(group.patterns)}")
    return 0


def main(argv: list[str]) -> int:
    if len(argv) == 1:
        return print_usage()

    if "--list" in argv:
        return print_catalog()

    run = "--run" in argv
    with_e2e = "--with-e2e" in argv
    targets = [arg for arg in argv[1:] if not arg.startswith("--")]

    if not targets:
        return print_usage()

    frontend_surfaces = infer_frontend_surfaces(targets)
    backend_groups = infer_backend_groups(targets)
    real_e2e_preflight = requires_real_e2e_preflight(targets)

    if not frontend_surfaces and not backend_groups and not real_e2e_preflight:
        print("No related checks inferred from the provided targets.")
        print("Tip: pass repo-relative paths under frontend/ or backend/.")
        return 2

    if real_e2e_preflight:
        print("Frontend real-e2e preflight: required")
        if run:
            status = run_command(["npm", "run", "test:e2e:real:preflight"], REPO_ROOT / "frontend")
            if status != 0:
                return status
        else:
            print("Suggested command: cd frontend && npm run test:e2e:real:preflight")
        print("")

    if frontend_surfaces:
        print("Frontend related surfaces:")
        for surface in frontend_surfaces:
            print(f"- {surface}")
        if run:
            command = ["npm", "run", "test:surface", "--", *frontend_surfaces]
            if with_e2e:
                command.append("--with-e2e")
            status = run_command(command, REPO_ROOT / "frontend")
            if status != 0:
                return status
        else:
            suffix = " --with-e2e" if with_e2e else ""
            print(f"Suggested command: cd frontend && npm run test:surface -- {' '.join(frontend_surfaces)}{suffix}")
        print("")

    if backend_groups:
        print("Backend related confidence groups:")
        for group in backend_groups:
            print(f"- {group}")
        if run:
            status = run_command(
                [sys.executable, "scripts/run_confidence_suite.py", *backend_groups],
                REPO_ROOT / "backend",
            )
            if status != 0:
                return status
        else:
            print(
                "Suggested command: cd backend && "
                f"{sys.executable} scripts/run_confidence_suite.py {' '.join(backend_groups)}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
