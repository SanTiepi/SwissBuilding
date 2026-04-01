"""One-command pilot-ready seed.

Usage:
    python -m app.seeds.seed_pilot_ready

Creates:
1. Base data (organizations, users, buildings, jurisdictions)
2. The prospect organization + users + 5-building portfolio
3. The G1 detailed scenario building (1 building with 4 blockers)
4. Form templates (Swiss regulatory forms)
5. Procedure templates (Swiss regulatory procedures)
6. Source registry (all known data sources)

Result: a complete, demo-ready, pilot-operable universe.
"""

from __future__ import annotations

import asyncio
import logging

logger = logging.getLogger(__name__)


async def seed_pilot_ready() -> None:
    """Run all pilot-relevant seeds in the correct order."""
    from app.database import AsyncSessionLocal

    # 1. Base data (organizations, users, buildings, jurisdictions)
    #    seed_data() manages its own session internally
    from app.seeds.seed_data import seed

    print("[PILOT-READY] 1/6 Seeding base data...")
    await seed()

    # 2. Prospect scenario (5 buildings, org, users)
    from app.seeds.seed_prospect_scenario import seed_prospect_scenario

    print("[PILOT-READY] 2/6 Seeding prospect scenario...")
    async with AsyncSessionLocal() as db:
        result = await seed_prospect_scenario(db)
        if result.get("status") != "already_seeded":
            await db.commit()

    # 3. G1 detailed scenario (1 building with 4 blockers)
    from app.seeds.seed_g1_scenario import seed_g1_scenario

    print("[PILOT-READY] 3/6 Seeding G1 scenario...")
    async with AsyncSessionLocal() as db:
        result = await seed_g1_scenario(db)
        if result.get("status") != "already_seeded":
            await db.commit()

    # 4. Form templates
    from app.seeds.seed_form_templates import seed_form_templates

    print("[PILOT-READY] 4/6 Seeding form templates...")
    async with AsyncSessionLocal() as db:
        count = await seed_form_templates(db)
        await db.commit()
        print(f"  -> {count} form templates")

    # 5. Procedure templates
    from app.seeds.seed_procedure_templates import seed_procedure_templates

    print("[PILOT-READY] 5/6 Seeding procedure templates...")
    async with AsyncSessionLocal() as db:
        count = await seed_procedure_templates(db)
        await db.commit()
        print(f"  -> {count} procedure templates")

    # 6. Source registry (manages its own session)
    from app.seeds.seed_source_registry import seed_source_registry

    print("[PILOT-READY] 6/6 Seeding source registry...")
    await seed_source_registry()

    print()
    print("[PILOT-READY] Seeding complete.")
    print("  Organization: Regie Pilote SA")
    print("  Users: marc.favre@regiepilote.ch / pilot123")
    print("         nathalie.blanc@regiepilote.ch / pilot123")
    print("  Buildings: 5 prospect + 1 G1 scenario")
    print("  Ready for demo and pilot operation.")


if __name__ == "__main__":
    asyncio.run(seed_pilot_ready())
