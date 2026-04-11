#!/usr/bin/env python3
"""Check that every model, service, and API module is classified in the canonical registry.

Usage:
    cd backend
    python scripts/check_canonical_registry.py

Outputs JSON with pass/fail per category and lists of unclassified items.
Exit code 0 = all classified, 1 = drift detected.
"""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

# Ensure backend root is on path
backend_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(backend_root))

from app.canonical_registry import (  # noqa: E402
    ALLOWED_TIERS,
    CANONICAL_API_MODULES,
    CANONICAL_MODELS,
    CANONICAL_SERVICES,
)


def get_registered_models() -> set[str]:
    """Extract all model class names from models/__init__.__all__ by parsing source AST.

    Does NOT import the module (avoids needing DB/env config).
    """
    init_path = backend_root / "app" / "models" / "__init__.py"
    source = init_path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "__all__" and isinstance(node.value, ast.List):
                    return {
                        elt.value
                        for elt in node.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    }
    # Fallback: regex
    match = re.search(r"__all__\s*=\s*\[(.*?)\]", source, re.DOTALL)
    if match:
        return set(re.findall(r'"([^"]+)"', match.group(1)))
    return set()


def get_registered_api_modules() -> set[str]:
    """Extract all API module names imported in api/router.py by scanning source."""
    router_path = backend_root / "app" / "api" / "router.py"
    modules: set[str] = set()
    in_import_block = False
    for line in router_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        # Detect "from app.api import (" block
        if stripped.startswith("from app.api import"):
            in_import_block = "(" in stripped
            # Grab inline imports after "import"
            after = stripped.split("import", 1)[1].strip().strip("(").strip(")")
            for token in after.split(","):
                token = token.strip()
                if token and not token.startswith("#"):
                    modules.add(token)
            continue
        if in_import_block:
            if ")" in stripped:
                in_import_block = False
                before_paren = stripped.split(")")[0]
                for token in before_paren.split(","):
                    token = token.strip()
                    if token and not token.startswith("#"):
                        modules.add(token)
            else:
                for token in stripped.split(","):
                    token = token.strip().rstrip(",")
                    if token and not token.startswith("#"):
                        modules.add(token)
    # Exclude 'router' itself if accidentally captured
    modules.discard("router")
    return modules


def get_service_file_stems() -> set[str]:
    """List all .py file stems in services/ (excluding __init__ and __pycache__)."""
    services_dir = backend_root / "app" / "services"
    stems: set[str] = set()
    for f in services_dir.glob("*.py"):
        if f.stem.startswith("__"):
            continue
        stems.add(f.stem)
    return stems


def validate_tiers(registry: dict[str, str], name: str) -> list[str]:
    """Check that all tier values in a registry are valid."""
    bad = []
    for key, tier in registry.items():
        if tier not in ALLOWED_TIERS:
            bad.append(f"{name}[{key!r}] has invalid tier {tier!r}")
    return bad


def main() -> None:
    results: dict[str, dict] = {}
    all_pass = True

    # --- Models ---
    registered_models = get_registered_models()
    classified_models = set(CANONICAL_MODELS.keys())
    unclassified_models = sorted(registered_models - classified_models)
    phantom_models = sorted(classified_models - registered_models)
    tier_errors_models = validate_tiers(CANONICAL_MODELS, "CANONICAL_MODELS")

    models_pass = len(unclassified_models) == 0 and len(tier_errors_models) == 0
    if not models_pass:
        all_pass = False

    results["models"] = {
        "pass": models_pass,
        "total_registered": len(registered_models),
        "total_classified": len(classified_models),
        "unclassified": unclassified_models,
        "phantom_entries": phantom_models,
        "tier_errors": tier_errors_models,
    }

    # --- Services ---
    service_stems = get_service_file_stems()
    classified_services = set(CANONICAL_SERVICES.keys())
    unclassified_services = sorted(service_stems - classified_services)
    phantom_services = sorted(classified_services - service_stems)
    tier_errors_services = validate_tiers(CANONICAL_SERVICES, "CANONICAL_SERVICES")

    services_pass = len(unclassified_services) == 0 and len(tier_errors_services) == 0
    if not services_pass:
        all_pass = False

    results["services"] = {
        "pass": services_pass,
        "total_registered": len(service_stems),
        "total_classified": len(classified_services),
        "unclassified": unclassified_services,
        "phantom_entries": phantom_services,
        "tier_errors": tier_errors_services,
    }

    # --- API modules ---
    api_modules = get_registered_api_modules()
    classified_apis = set(CANONICAL_API_MODULES.keys())
    unclassified_apis = sorted(api_modules - classified_apis)
    phantom_apis = sorted(classified_apis - api_modules)
    tier_errors_apis = validate_tiers(CANONICAL_API_MODULES, "CANONICAL_API_MODULES")

    apis_pass = len(unclassified_apis) == 0 and len(tier_errors_apis) == 0
    if not apis_pass:
        all_pass = False

    results["api_modules"] = {
        "pass": apis_pass,
        "total_registered": len(api_modules),
        "total_classified": len(classified_apis),
        "unclassified": unclassified_apis,
        "phantom_entries": phantom_apis,
        "tier_errors": tier_errors_apis,
    }

    # --- Summary ---
    results["overall_pass"] = all_pass

    # --- Tier distribution ---
    for category_name, registry in [
        ("models", CANONICAL_MODELS),
        ("services", CANONICAL_SERVICES),
        ("api_modules", CANONICAL_API_MODULES),
    ]:
        dist: dict[str, int] = {}
        for tier in registry.values():
            dist[tier] = dist.get(tier, 0) + 1
        results[category_name]["tier_distribution"] = dict(sorted(dist.items()))

    # --- Output ---
    output = json.dumps(results, indent=2)
    print(output)

    if not all_pass:
        print("\n** DRIFT DETECTED ** -- unclassified items found", file=sys.stderr)
        sys.exit(1)
    else:
        print("\nAll models, services, and API modules are classified.", file=sys.stderr)
        sys.exit(0)


if __name__ == "__main__":
    main()
