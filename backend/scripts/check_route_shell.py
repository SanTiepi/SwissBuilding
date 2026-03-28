#!/usr/bin/env python3
"""Route-shell drift guard. Validates that frontend routes conform to 5-hub doctrine.

Reads frontend/src/App.tsx, extracts all route definitions, classifies each route,
and validates against the 5-hub doctrine (Today, Buildings, Cases, Finance, Portfolio Command).

Exit code 0 = pass, 1 = fail.
"""

import json
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

# The 5 canonical hubs
HUBS = {"today", "buildings", "cases", "finance", "portfolio-command"}

# Contextual routes scoped under a hub entity (building sub-pages, case rooms, etc.)
CONTEXTUAL_PREFIXES = [
    "buildings/:id",
    "buildings/:buildingId",
    "cases/:caseId",
    "diagnostics/:id",
    "indispensability-export/:buildingId",
]

# Public / auth routes (no layout, no hub)
AUTH_ROUTES = {"login", "shared/:token", "intake"}

# Admin routes (operator-only, not user-facing hubs)
ADMIN_PREFIX = "admin/"

# Marketplace routes (bounded specialist surface)
MARKETPLACE_PREFIX = "marketplace/"

# Known bounded specialists: standalone pages that serve a specific function
# but don't qualify as hubs. Each must be explicitly listed.
BOUNDED_SPECIALISTS = {
    "campaigns",
    "comparison",
    "risk-simulator",
    "map",
    "exports",
    "authority-packs",
    "settings",
    "address-preview",
    "demo-path",
    "pilot-scorecard",
    "indispensability",
    "rules-studio",
}

# Absorbed routes: formerly bounded specialists, now redirect to canonical workspaces.
# Kept as routes for bookmark preservation but no longer standalone pages.
ABSORBED_REDIRECTS = {
    "dashboard",        # -> /today
    "control-tower",    # -> /today
    "portfolio",        # -> /portfolio-command
    "portfolio-triage", # -> /portfolio-command
    "actions",          # -> /today
    "documents",        # -> /today
}

# Catch-all / redirect routes to skip
SKIP_ROUTES = {"*", "/", ""}


def extract_routes(app_tsx_content: str) -> list[dict]:
    """Extract path=... from <Route path=... /> components."""
    pattern = re.compile(r'<Route\s[^>]*path="([^"]+)"')
    routes = []
    for match in pattern.finditer(app_tsx_content):
        raw_path = match.group(1).strip("/")
        routes.append({"path": raw_path, "raw": match.group(1)})
    return routes


def classify_route(path: str) -> str:
    """Classify a route path into a category.

    Returns one of: hub, contextual, bounded, absorbed, auth, admin, marketplace, redirect, unknown
    """
    if path in SKIP_ROUTES:
        return "redirect"

    if path in AUTH_ROUTES:
        return "auth"

    if path in HUBS:
        return "hub"

    if path.startswith(ADMIN_PREFIX):
        return "admin"

    if path.startswith(MARKETPLACE_PREFIX):
        return "marketplace"

    # Check contextual (sub-pages of entities)
    for prefix in CONTEXTUAL_PREFIXES:
        if path == prefix or path.startswith(prefix + "/"):
            return "contextual"

    if path in BOUNDED_SPECIALISTS:
        return "bounded"

    if path in ABSORBED_REDIRECTS:
        return "absorbed"

    return "unknown"


def check_drift(routes: list[dict]) -> dict:
    """Run the drift check and return structured results."""
    classified = []
    hubs_found = set()
    unknown_routes = []
    warnings = []

    for route in routes:
        category = classify_route(route["path"])
        entry = {"path": route["raw"], "normalized": route["path"], "category": category}
        classified.append(entry)

        if category == "hub":
            hubs_found.add(route["path"])
        elif category == "unknown":
            unknown_routes.append(route["path"])

    # Check all 5 hubs are present
    missing_hubs = HUBS - hubs_found
    if missing_hubs:
        warnings.append(f"Missing hubs: {sorted(missing_hubs)}")

    # Unknown routes = potential drift
    if unknown_routes:
        warnings.append(
            f"{len(unknown_routes)} unclassified top-level route(s): {unknown_routes}. "
            "Each must belong to a hub, be a bounded specialist, or be contextual."
        )

    passed = len(unknown_routes) == 0 and len(missing_hubs) == 0

    # Summary by category
    summary = {}
    for entry in classified:
        cat = entry["category"]
        summary[cat] = summary.get(cat, 0) + 1

    return {
        "check": "route_shell_drift",
        "pass": passed,
        "hubs_expected": sorted(HUBS),
        "hubs_found": sorted(hubs_found),
        "missing_hubs": sorted(missing_hubs),
        "unknown_routes": unknown_routes,
        "warnings": warnings,
        "summary": summary,
        "routes": classified,
    }


def main() -> int:
    app_tsx = REPO_ROOT / "frontend" / "src" / "App.tsx"
    if not app_tsx.exists():
        print(json.dumps({"check": "route_shell_drift", "pass": False, "error": f"File not found: {app_tsx}"}))
        return 1

    content = app_tsx.read_text(encoding="utf-8")
    routes = extract_routes(content)
    result = check_drift(routes)

    print(json.dumps(result, indent=2))
    return 0 if result["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
