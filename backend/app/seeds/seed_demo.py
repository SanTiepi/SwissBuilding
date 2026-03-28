"""
SwissBuildingOS - Demo Seed Orchestrator

Seeds the local demo dataset, then optionally enriches it with public Vaud
building data for realistic UI and workflow testing.

Usage:
    python -m app.seeds.seed_demo --commune Lausanne --limit 150
    python -m app.seeds.seed_demo --municipality-ofs 5586 --limit 200 --output-json ../tmp/vaud-lausanne-200.json
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from app.database import AsyncSessionLocal
from app.importers.vaud_public import apply_records, harvest_vd_buildings, write_output_json
from app.seeds.seed_data import seed
from app.seeds.seed_demo_enrich import enrich_demo_buildings
from app.seeds.seed_demo_prospect import seed_prospect_demo
from app.seeds.seed_demo_workspace import seed_demo_workspace
from app.seeds.seed_form_templates import seed_form_templates
from app.seeds.seed_procedure_templates import seed_procedure_templates
from app.seeds.seed_source_registry import seed_source_registry


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Seed demo data, then optionally import public Vaud buildings.",
    )
    parser.add_argument("--skip-vaud", action="store_true", help="Only run the synthetic demo seed.")
    parser.add_argument(
        "--skip-enrich", action="store_true", help="Skip demo enrichment (diagnostics/samples/docs on Vaud buildings)."
    )
    parser.add_argument("--dry-run-vaud", action="store_true", help="Harvest Vaud data without applying it to the DB.")
    parser.add_argument("--commune", type=str, help="Vaud commune name filter, e.g. Lausanne.")
    parser.add_argument("--municipality-ofs", type=int, help="Vaud municipality OFS code.")
    parser.add_argument("--postal-code", type=str, help="Vaud postal code filter.")
    parser.add_argument("--limit", type=int, default=150, help="Maximum number of Vaud buildings to import.")
    parser.add_argument("--concurrency", type=int, default=8, help="Concurrent source requests for Vaud import.")
    parser.add_argument(
        "--created-by-email",
        type=str,
        default="admin@swissbuildingos.ch",
        help="User email used as creator for imported Vaud buildings.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        help="Optional path to write normalized Vaud records before DB apply.",
    )
    return parser.parse_args()


def _has_vd_filter(args: argparse.Namespace) -> bool:
    return any([args.commune, args.municipality_ofs is not None, args.postal_code])


async def _seed_workspace() -> dict:
    async with AsyncSessionLocal() as db:
        return await seed_demo_workspace(db)


async def main() -> None:
    args = parse_args()

    await seed()
    workspace_stats = await _seed_workspace()
    print(
        "[SEED-DEMO] Demo workspace: "
        f"building={workspace_stats['building_address']}, "
        f"contacts={workspace_stats['contacts_count']}, "
        f"leases={workspace_stats['leases_count']}, "
        f"contracts={workspace_stats['contracts_count']}"
    )

    # Seed form templates (idempotent)
    async with AsyncSessionLocal() as db:
        form_count = await seed_form_templates(db)
        await db.commit()
    if form_count:
        print(f"[SEED-DEMO] Form templates: {form_count} created")

    # Seed source registry (idempotent)
    async with AsyncSessionLocal() as db:
        source_count = await seed_source_registry(db)
        await db.commit()
    if source_count:
        print(f"[SEED-DEMO] Source registry: {source_count} sources registered")

    # Seed procedure templates (idempotent)
    async with AsyncSessionLocal() as db:
        proc_count = await seed_procedure_templates(db)
        await db.commit()
    if proc_count:
        print(f"[SEED-DEMO] Procedure templates: {proc_count} created")

    if args.skip_vaud:
        print("[SEED-DEMO] Synthetic demo seed completed. Vaud import skipped.")
        return

    if not _has_vd_filter(args):
        raise SystemExit(
            "Missing Vaud filter. Pass --commune, --municipality-ofs, or --postal-code, "
            "or use --skip-vaud to run only the synthetic demo seed."
        )

    records, stats = await harvest_vd_buildings(
        commune=args.commune,
        municipality_ofs=args.municipality_ofs,
        postal_code=args.postal_code,
        limit=args.limit,
        concurrency=args.concurrency,
    )

    print(
        "[SEED-DEMO] Vaud harvest summary: "
        f"normalized={stats['normalized']}, unique_egids={stats['unique_egids']}, "
        f"address_records={stats['address_records']}, skipped={stats['skipped']}."
    )

    if args.output_json:
        write_output_json(records, args.output_json)
        print(f"[SEED-DEMO] Wrote normalized Vaud JSON to {args.output_json}")

    if not records:
        print("[SEED-DEMO] No Vaud buildings matched the provided filter.")
        return

    if args.dry_run_vaud:
        print("[SEED-DEMO] Dry-run Vaud mode enabled. No Vaud buildings were applied to the DB.")
        return

    created, updated, unchanged = await apply_records(
        records,
        created_by_email=args.created_by_email,
    )
    print(f"[SEED-DEMO] Vaud import applied: created={created}, updated={updated}, unchanged={unchanged}")

    # Step 3: enrich buildings with demo diagnostics/samples/documents
    if not args.skip_enrich:
        enrich_stats = await enrich_demo_buildings()
        print(
            "[SEED-DEMO] Demo enrichment: "
            f"diagnostics={enrich_stats['diagnostics']}, "
            f"samples={enrich_stats['samples']}, "
            f"documents={enrich_stats['documents']}, "
            f"events={enrich_stats['events']}"
        )

    # Step 4: prospect demo scenario (requires VD buildings)
    async with AsyncSessionLocal() as db:
        prospect_result = await seed_prospect_demo(db)
    print(f"[SEED-DEMO] Prospect demo: status={prospect_result.get('status')}")
    if prospect_result.get("status") == "completed":
        print(f"  building: {prospect_result.get('building_address')}")


if __name__ == "__main__":
    asyncio.run(main())
