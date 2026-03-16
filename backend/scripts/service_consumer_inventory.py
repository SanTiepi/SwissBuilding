from __future__ import annotations

import ast
import json
import re
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_ROOT = REPO_ROOT / "backend"
FRONTEND_ROOT = REPO_ROOT / "frontend"
SERVICE_DIR = BACKEND_ROOT / "app" / "services"
SEARCH_ROOTS = [BACKEND_ROOT / "app", BACKEND_ROOT / "tests"]
MARKDOWN_OUTPUT = REPO_ROOT / "docs" / "service-consumer-map.md"
JSON_OUTPUT = REPO_ROOT / "docs" / "service-consumer-map.json"
PRUNING_OUTPUT = REPO_ROOT / "docs" / "service-consumer-pruning-candidates.md"


@dataclass(frozen=True)
class FileConsumer:
    path: str
    kind: str


def list_services() -> list[str]:
    return sorted(path.stem for path in SERVICE_DIR.glob("*.py") if path.name != "__init__.py")


def classify_consumer(path: Path) -> str:
    relative = path.relative_to(BACKEND_ROOT).as_posix()
    if relative.startswith("app/api/"):
        return "api"
    if relative.startswith("app/services/"):
        return "service"
    if relative.startswith("app/seeds/"):
        return "seed"
    if relative.startswith("app/importers/"):
        return "importer"
    if relative.startswith("app/ml/"):
        return "ml"
    if relative.startswith("tests/"):
        return "test"
    return "other"


def extract_service_imports(path: Path, service_names: set[str]) -> set[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, SyntaxError):
        return set()

    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module == "app.services":
                for alias in node.names:
                    if alias.name in service_names:
                        found.add(alias.name)
            elif module.startswith("app.services."):
                service_name = module.removeprefix("app.services.").split(".", 1)[0]
                if service_name in service_names:
                    found.add(service_name)
        elif isinstance(node, ast.Import):
            for alias in node.names:
                name = alias.name
                if name.startswith("app.services."):
                    service_name = name.removeprefix("app.services.").split(".", 1)[0]
                    if service_name in service_names:
                        found.add(service_name)
    return found


# Maps frontend API file basenames to corresponding backend service names.
# Only includes non-obvious mappings; obvious ones are handled by heuristic matching.
FRONTEND_API_TO_SERVICE: dict[str, list[str]] = {
    "completeness": ["completeness_engine"],
    "complianceSummary": ["compliance_engine"],
    "complianceArtefacts": ["compliance_artefact_service"],
    "contradictions": ["contradiction_detector"],
    "changeSignals": ["change_signal_generator"],
    "trustScores": ["trust_score_calculator"],
    "unknowns": ["unknown_generator"],
    "passport": ["passport_service"],
    "simulator": ["intervention_simulator"],
    "savedSimulations": ["intervention_simulator"],
    "risk": ["risk_engine"],
    "auditLogs": ["audit_service"],
    "postWorks": ["post_works_service"],
    "readiness": ["readiness_reasoner", "readiness_action_generator"],
    "snapshots": ["time_machine_service"],
    "planHeatmap": ["plan_heatmap_service"],
    "evidenceSummary": ["evidence_chain_service", "evidence_graph_service"],
    "evidencePacks": ["evidence_chain_service"],
    "dossier": ["dossier_service", "dossier_completion_agent"],
    "remediationSummary": ["remediation_cost_service"],
    "quality": ["quality_service", "quality_assurance_service"],
    "sharedLinks": ["shared_link_service"],
}


def _snake_to_service(camel: str) -> str:
    """Convert camelCase frontend filename to snake_case service name guess."""
    s1 = re.sub(r"([A-Z])", r"_\1", camel).lower().lstrip("_")
    return s1


def scan_frontend_consumers(service_names: set[str]) -> dict[str, list[str]]:
    """Scan frontend/src/api/ files and map them to backend services."""
    ui_consumers: dict[str, list[str]] = defaultdict(list)
    api_dir = FRONTEND_ROOT / "src" / "api"
    if not api_dir.exists():
        return ui_consumers

    for api_file in sorted(api_dir.glob("*.ts")):
        basename = api_file.stem
        if basename in ("client", "index"):
            continue
        rel_path = f"frontend/src/api/{api_file.name}"

        # Check explicit mapping first
        if basename in FRONTEND_API_TO_SERVICE:
            for svc in FRONTEND_API_TO_SERVICE[basename]:
                if svc in service_names:
                    ui_consumers[svc].append(rel_path)
            continue

        # Heuristic: try converting camelCase to snake_case + _service suffix
        snake = _snake_to_service(basename)
        candidates = [
            f"{snake}_service",
            snake,
            f"{snake}_engine",
        ]
        matched = False
        for candidate in candidates:
            if candidate in service_names:
                ui_consumers[candidate].append(rel_path)
                matched = True
        if not matched and snake.endswith("s"):
            singular = snake[:-1]
            for suffix in ("_service", "", "_engine"):
                candidate = f"{singular}{suffix}"
                if candidate in service_names:
                    ui_consumers[candidate].append(rel_path)

    return ui_consumers


def guess_context(service_name: str) -> str:
    explicit = {
        "passport_service": "building_memory",
        "time_machine_service": "building_memory",
        "decision_replay_service": "building_memory",
        "readiness_reasoner": "readiness",
        "readiness_action_generator": "readiness",
        "unknown_generator": "trust_readiness",
        "trust_score_calculator": "trust_readiness",
        "change_signal_generator": "readiness",
        "post_works_service": "post_works",
        "avt_apt_transition": "post_works",
        "dossier_service": "evidence_dossier",
        "dossier_completion_agent": "evidence_dossier",
        "authority_pack_service": "evidence_dossier",
        "evidence_chain_service": "evidence",
        "evidence_graph_service": "evidence",
        "search_service": "search",
        "bulk_operations_service": "orchestration",
        "workflow_orchestration_service": "orchestration",
    }
    if service_name in explicit:
        return explicit[service_name]

    token = service_name
    for suffix in ("_service", "_generator", "_planner", "_engine", "_simulator"):
        if token.endswith(suffix):
            token = token.removesuffix(suffix)
            break
    return token.split("_", 1)[0]


def classify_service(
    *,
    api_count: int,
    service_count: int,
    seed_count: int,
    importer_count: int,
    ml_count: int,
    test_count: int,
    ui_count: int,
    context_size: int,
) -> tuple[str, str]:
    non_test = api_count + service_count + seed_count + importer_count + ml_count
    total_production = non_test + ui_count

    if non_test == 0 and ui_count == 0 and test_count == 0:
        return ("zero_consumer", "No consumers at all (backend or frontend).")
    if non_test == 0 and ui_count == 0:
        return ("orphaned", "No non-test consumer detected (backend or frontend).")
    if (
        api_count == 0
        and seed_count == 0
        and importer_count == 0
        and ml_count == 0
        and service_count > 0
        and ui_count == 0
    ):
        return ("composed_helper", "Consumed internally by other services but not exposed directly.")
    if total_production == 1 and ui_count == 0:
        return ("single_consumer", "Only one non-test backend consumer.")
    if total_production == 1 and ui_count == 1 and non_test == 0:
        return ("ui_only", "Only consumed by frontend, no backend non-test consumer.")
    if api_count == 0 and non_test <= 1 and context_size >= 6:
        return ("duplicate_or_overlapping", "Low-consumption service in a saturated context cluster.")
    if api_count == 1 and service_count == 0 and seed_count == 0 and importer_count == 0 and ml_count == 0:
        thin_detail = f"Only 1 API route file, 0 internal service consumers. UI: {ui_count}."
        return ("thin_api_only", thin_detail)
    return ("core_domain", "Directly exposed by API, data pipeline, or multiple internal consumers.")


def _detect_duplicate_families(service_rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Detect context clusters with 3+ services where most have low consumption."""
    context_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in service_rows:
        context_groups[row["context_guess"]].append(row)

    families: list[dict[str, Any]] = []
    for context, members in sorted(context_groups.items()):
        if len(members) < 3:
            continue
        low_signal = [m for m in members if m["non_test_consumer_count"] <= 1]
        if len(low_signal) >= 2:
            families.append(
                {
                    "context": context,
                    "total_services": len(members),
                    "low_signal_count": len(low_signal),
                    "services": [m["service"] for m in members],
                    "low_signal_services": [m["service"] for m in low_signal],
                }
            )
    return families


def build_inventory() -> dict[str, Any]:
    services = list_services()
    service_names = set(services)
    consumers: dict[str, list[FileConsumer]] = {service: [] for service in services}

    for root in SEARCH_ROOTS:
        for path in root.rglob("*.py"):
            imported_services = extract_service_imports(path, service_names)
            if not imported_services:
                continue
            kind = classify_consumer(path)
            rel_path = path.relative_to(BACKEND_ROOT).as_posix()
            for service in imported_services:
                if path == SERVICE_DIR / f"{service}.py":
                    continue
                consumers[service].append(FileConsumer(path=rel_path, kind=kind))

    # Scan frontend UI consumers
    ui_consumer_map = scan_frontend_consumers(service_names)
    for service, ui_paths in ui_consumer_map.items():
        for ui_path in ui_paths:
            consumers[service].append(FileConsumer(path=ui_path, kind="ui"))

    context_counts = Counter(guess_context(service) for service in services)
    service_rows: list[dict[str, Any]] = []

    for service in services:
        grouped: dict[str, list[str]] = defaultdict(list)
        for consumer in sorted(consumers[service], key=lambda item: (item.kind, item.path)):
            grouped[consumer.kind].append(consumer.path)

        api_count = len(grouped["api"])
        service_count = len(grouped["service"])
        seed_count = len(grouped["seed"])
        importer_count = len(grouped["importer"])
        ml_count = len(grouped["ml"])
        test_count = len(grouped["test"])
        ui_count = len(grouped["ui"])
        classification, reason = classify_service(
            api_count=api_count,
            service_count=service_count,
            seed_count=seed_count,
            importer_count=importer_count,
            ml_count=ml_count,
            test_count=test_count,
            ui_count=ui_count,
            context_size=context_counts[guess_context(service)],
        )

        service_rows.append(
            {
                "service": service,
                "context_guess": guess_context(service),
                "classification": classification,
                "classification_reason": reason,
                "consumer_counts": {
                    "api": api_count,
                    "service": service_count,
                    "seed": seed_count,
                    "importer": importer_count,
                    "ml": ml_count,
                    "test": test_count,
                    "ui": ui_count,
                    "other": len(grouped["other"]),
                },
                "non_test_consumer_count": api_count
                + service_count
                + seed_count
                + importer_count
                + ml_count
                + len(grouped["other"]),
                "total_production_consumers": api_count
                + service_count
                + seed_count
                + importer_count
                + ml_count
                + ui_count
                + len(grouped["other"]),
                "consumers": grouped,
            }
        )

    duplicate_families = _detect_duplicate_families(service_rows)

    summary = {
        "generated_at_utc": datetime.now(UTC).isoformat(),
        "total_services": len(service_rows),
        "classification_counts": Counter(row["classification"] for row in service_rows),
        "context_counts": context_counts,
        "low_signal_context_counts": Counter(
            row["context_guess"] for row in service_rows if row["non_test_consumer_count"] <= 1
        ),
        "top_api_exposed": sorted(
            service_rows,
            key=lambda row: (
                row["consumer_counts"]["api"],
                row["non_test_consumer_count"],
            ),
            reverse=True,
        )[:15],
        "review_candidates": [
            row
            for row in service_rows
            if row["classification"]
            in {
                "zero_consumer",
                "orphaned",
                "legacy_candidate",
                "duplicate_or_overlapping",
                "single_consumer",
                "thin_api_only",
                "ui_only",
            }
        ],
        "duplicate_families": duplicate_families,
        "pruning_summary": {
            "zero_consumer": [r["service"] for r in service_rows if r["classification"] == "zero_consumer"],
            "orphaned": [r["service"] for r in service_rows if r["classification"] == "orphaned"],
            "single_consumer": [r["service"] for r in service_rows if r["classification"] == "single_consumer"],
            "thin_api_only": [r["service"] for r in service_rows if r["classification"] == "thin_api_only"],
            "ui_only": [r["service"] for r in service_rows if r["classification"] == "ui_only"],
        },
    }

    return {"summary": summary, "services": service_rows}


def write_json(inventory: dict[str, Any]) -> None:
    JSON_OUTPUT.write_text(json.dumps(inventory, indent=2, sort_keys=True), encoding="utf-8")


def write_markdown(inventory: dict[str, Any]) -> None:
    summary = inventory["summary"]
    rows = inventory["services"]

    lines: list[str] = []
    lines.append("# Service Consumer Map")
    lines.append("")
    lines.append("This inventory is generated by `backend/scripts/service_consumer_inventory.py`.")
    lines.append("")
    lines.append("Heuristic notes:")
    lines.append("- imports are scanned across backend app code, tests, and frontend API files")
    lines.append("- classifications are intentionally conservative")
    lines.append("- `thin_api_only` services have exactly 1 API route and 0 internal service consumers")
    lines.append("- `duplicate_or_overlapping` and `orphaned` are review starting points, not auto-delete orders")
    lines.append("- see `docs/service-consumer-pruning-candidates.md` for grouped pruning analysis")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Generated at: `{summary['generated_at_utc']}`")
    lines.append(f"- Total services: `{summary['total_services']}`")
    lines.append("")
    lines.append("### Classification counts")
    lines.append("")
    for classification, count in sorted(summary["classification_counts"].items()):
        lines.append(f"- `{classification}`: `{count}`")
    lines.append("")
    lines.append("### Largest context clusters")
    lines.append("")
    for context, count in sorted(summary["context_counts"].items(), key=lambda item: (-item[1], item[0]))[:12]:
        lines.append(f"- `{context}`: `{count}`")
    lines.append("")
    lines.append("### Contexts with the most low-signal services")
    lines.append("")
    for context, count in sorted(summary["low_signal_context_counts"].items(), key=lambda item: (-item[1], item[0]))[
        :12
    ]:
        lines.append(f"- `{context}`: `{count}` low-signal services")
    lines.append("")
    lines.append("### Top API-exposed services")
    lines.append("")
    lines.append("| Service | Context | API consumers | UI consumers | Total non-test consumers |")
    lines.append("| --- | --- | ---: | ---: | ---: |")
    for row in summary["top_api_exposed"]:
        lines.append(
            f"| `{row['service']}` | `{row['context_guess']}` | `{row['consumer_counts']['api']}` | `{row['consumer_counts']['ui']}` | `{row['non_test_consumer_count']}` |"
        )
    lines.append("")
    lines.append("### Review candidates")
    lines.append("")
    lines.append("| Service | Classification | Context | API | Service | UI | Seed/Imp/ML | Test | Reason |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |")
    for row in sorted(
        summary["review_candidates"],
        key=lambda item: (
            item["classification"],
            item["non_test_consumer_count"],
            item["service"],
        ),
    ):
        lines.append(
            "| `{service}` | `{classification}` | `{context}` | `{api}` | `{service_count}` | `{ui}` | `{pipeline}` | `{test}` | {reason} |".format(
                service=row["service"],
                classification=row["classification"],
                context=row["context_guess"],
                api=row["consumer_counts"]["api"],
                service_count=row["consumer_counts"]["service"],
                ui=row["consumer_counts"]["ui"],
                pipeline=row["consumer_counts"]["seed"]
                + row["consumer_counts"]["importer"]
                + row["consumer_counts"]["ml"],
                test=row["consumer_counts"]["test"],
                reason=row["classification_reason"],
            )
        )
    lines.append("")

    if summary["duplicate_families"]:
        lines.append("### Duplicate / Overlapping Service Families")
        lines.append("")
        for fam in summary["duplicate_families"]:
            lines.append(
                f"- **`{fam['context']}`** ({fam['total_services']} services, {fam['low_signal_count']} low-signal)"
            )
            for svc in fam["low_signal_services"]:
                lines.append(f"  - `{svc}`")
        lines.append("")

    lines.append("## Full Inventory")
    lines.append("")
    lines.append("| Service | Context | Classification | API | Service | Seed | Importer | ML | UI | Test |")
    lines.append("| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |")
    for row in sorted(rows, key=lambda item: (item["context_guess"], item["service"])):
        counts = row["consumer_counts"]
        lines.append(
            f"| `{row['service']}` | `{row['context_guess']}` | `{row['classification']}` | `{counts['api']}` | `{counts['service']}` | `{counts['seed']}` | `{counts['importer']}` | `{counts['ml']}` | `{counts['ui']}` | `{counts['test']}` |"
        )

    MARKDOWN_OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_pruning_report(inventory: dict[str, Any]) -> None:
    """Generate docs/service-consumer-pruning-candidates.md with grouped analysis."""
    summary = inventory["summary"]
    rows = inventory["services"]
    rows_by_name = {r["service"]: r for r in rows}

    lines: list[str] = []
    lines.append("# Service Consumer Pruning Candidates")
    lines.append("")
    lines.append("Generated by `backend/scripts/service_consumer_inventory.py`.")
    lines.append(f"Generated at: `{summary['generated_at_utc']}`")
    lines.append("")
    lines.append("This report groups services by pruning risk. **No services should be deleted**")
    lines.append("**without supervisor review** -- this is an audit artifact only.")
    lines.append("")

    # Counts overview
    pruning = summary["pruning_summary"]
    total = summary["total_services"]
    zero = len(pruning["zero_consumer"])
    orphaned = len(pruning["orphaned"])
    single = len(pruning["single_consumer"])
    thin = len(pruning["thin_api_only"])
    ui_only = len(pruning["ui_only"])

    lines.append("## Overview")
    lines.append("")
    lines.append(f"- Total services: **{total}**")
    lines.append(f"- Zero-consumer (no references at all): **{zero}**")
    lines.append(f"- Orphaned (test-only consumers): **{orphaned}**")
    lines.append(f"- Single non-test consumer: **{single}**")
    lines.append(f"- Thin API-only (1 route, 0 service consumers): **{thin}**")
    lines.append(f"- UI-only (frontend consumer, no backend non-test): **{ui_only}**")
    lines.append(f"- Core/helper (healthy): **{total - zero - orphaned - single - thin - ui_only}**")
    lines.append("")

    # --- TIER 1: Safe to prune (zero-consumer) ---
    lines.append("---")
    lines.append("")
    lines.append("## Tier 1: Safe to Prune (zero-consumer)")
    lines.append("")
    if pruning["zero_consumer"]:
        lines.append(
            "These services have **zero imports** anywhere in the codebase (no API, no service, no test, no UI)."
        )
        lines.append("They are dead code and safe to remove after confirming no dynamic imports.")
        lines.append("")
        lines.append("| Service | Context | Evidence |")
        lines.append("| --- | --- | --- |")
        for svc in sorted(pruning["zero_consumer"]):
            r = rows_by_name[svc]
            lines.append(f"| `{svc}` | `{r['context_guess']}` | 0 consumers across all search roots |")
    else:
        lines.append("No zero-consumer services found.")
    lines.append("")

    # --- TIER 2: Likely safe (orphaned = test-only) ---
    lines.append("## Tier 2: Likely Safe to Prune (test-only consumers)")
    lines.append("")
    if pruning["orphaned"]:
        lines.append("These services are only imported by test files. No API route, no other service, no UI.")
        lines.append("Pruning them also requires removing corresponding tests.")
        lines.append("")
        lines.append("| Service | Context | Test consumers | Evidence |")
        lines.append("| --- | --- | ---: | --- |")
        for svc in sorted(pruning["orphaned"]):
            r = rows_by_name[svc]
            test_paths = ", ".join(r["consumers"].get("test", [])[:3])
            lines.append(
                f"| `{svc}` | `{r['context_guess']}` | `{r['consumer_counts']['test']}` | Tests: {test_paths} |"
            )
    else:
        lines.append("No orphaned (test-only) services found.")
    lines.append("")

    # --- TIER 3: Needs manual review (thin-api-only) ---
    lines.append("## Tier 3: Needs Manual Review (thin API-only)")
    lines.append("")
    thin_services = [rows_by_name[s] for s in pruning["thin_api_only"]]
    if thin_services:
        lines.append("These services have exactly **1 API route** and **0 internal service consumers**.")
        lines.append("They work but have no internal reuse. Consider whether they justify a standalone service")
        lines.append("or could be inlined into the route handler / merged with a sibling service.")
        lines.append("")
        lines.append("| Service | Context | API file | UI | Test | Action |")
        lines.append("| --- | --- | --- | ---: | ---: | --- |")
        for r in sorted(thin_services, key=lambda x: x["context_guess"]):
            api_file = r["consumers"].get("api", ["?"])[0]
            lines.append(
                f"| `{r['service']}` | `{r['context_guess']}` | `{api_file}` | `{r['consumer_counts']['ui']}` | `{r['consumer_counts']['test']}` | Review if worth standalone service |"
            )
    else:
        lines.append("No thin API-only services found.")
    lines.append("")

    # --- TIER 3b: Single consumer ---
    lines.append("## Tier 3b: Needs Manual Review (single non-test consumer)")
    lines.append("")
    single_services = [rows_by_name[s] for s in pruning["single_consumer"]]
    if single_services:
        lines.append("These services have exactly 1 non-test consumer and no UI consumer.")
        lines.append("They may be candidates for inlining into their sole consumer.")
        lines.append("")
        lines.append("| Service | Context | Consumer | Kind | Test | Action |")
        lines.append("| --- | --- | --- | --- | ---: | --- |")
        for r in sorted(single_services, key=lambda x: x["context_guess"]):
            # Find the single non-test consumer
            consumer_path = "?"
            consumer_kind = "?"
            for kind in ("api", "service", "seed", "importer", "ml", "other"):
                if r["consumers"].get(kind):
                    consumer_path = r["consumers"][kind][0]
                    consumer_kind = kind
                    break
            lines.append(
                f"| `{r['service']}` | `{r['context_guess']}` | `{consumer_path}` | `{consumer_kind}` | `{r['consumer_counts']['test']}` | Consider inlining |"
            )
    else:
        lines.append("No single-consumer services found.")
    lines.append("")

    # --- TIER 4: Duplicate families ---
    lines.append("## Tier 4: Duplicate / Overlapping Families (supervisor triage)")
    lines.append("")
    families = summary["duplicate_families"]
    if families:
        lines.append("Context clusters with 3+ services and 2+ low-signal members.")
        lines.append("These may contain conceptual overlap or premature service splits.")
        lines.append("")
        for fam in sorted(families, key=lambda f: -f["low_signal_count"]):
            lines.append(
                f"### `{fam['context']}` ({fam['total_services']} services, {fam['low_signal_count']} low-signal)"
            )
            lines.append("")
            lines.append("| Service | Low-signal? | Non-test consumers |")
            lines.append("| --- | --- | ---: |")
            for svc in sorted(fam["services"]):
                r = rows_by_name[svc]
                is_low = "yes" if svc in fam["low_signal_services"] else "no"
                lines.append(f"| `{svc}` | {is_low} | `{r['non_test_consumer_count']}` |")
            lines.append("")
            lines.append("**Suggested action**: Review whether low-signal members can be merged into the")
            lines.append("hub service or removed if functionality is not used.")
            lines.append("")
    else:
        lines.append("No duplicate families detected.")
    lines.append("")

    # --- Hub services ---
    lines.append("## Hub Services (high fan-in, do NOT prune)")
    lines.append("")
    lines.append("For reference, these services have the highest non-test consumer counts")
    lines.append("and should be treated as architectural anchors.")
    lines.append("")
    lines.append("| Service | Context | Non-test consumers | UI |")
    lines.append("| --- | --- | ---: | ---: |")
    hub_rows = sorted(rows, key=lambda r: -r["non_test_consumer_count"])[:10]
    for r in hub_rows:
        lines.append(
            f"| `{r['service']}` | `{r['context_guess']}` | `{r['non_test_consumer_count']}` | `{r['consumer_counts']['ui']}` |"
        )
    lines.append("")

    PRUNING_OUTPUT.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    inventory = build_inventory()
    write_json(inventory)
    write_markdown(inventory)
    write_pruning_report(inventory)
    print(f"Wrote {JSON_OUTPUT.relative_to(REPO_ROOT)}")
    print(f"Wrote {MARKDOWN_OUTPUT.relative_to(REPO_ROOT)}")
    print(f"Wrote {PRUNING_OUTPUT.relative_to(REPO_ROOT)}")

    # Print summary counts for validation
    summary = inventory["summary"]
    counts = summary["classification_counts"]
    print()
    print("=== Validation Summary ===")
    print(f"total_services: {summary['total_services']}")
    for cls in sorted(counts):
        print(f"  {cls}: {counts[cls]}")
    pruning = summary["pruning_summary"]
    print(f"zero_consumer: {len(pruning['zero_consumer'])}")
    print(f"orphaned (test-only): {len(pruning['orphaned'])}")
    print(f"single_consumer: {len(pruning['single_consumer'])}")
    print(f"thin_api_only: {len(pruning['thin_api_only'])}")
    print(f"ui_only: {len(pruning['ui_only'])}")


if __name__ == "__main__":
    main()
