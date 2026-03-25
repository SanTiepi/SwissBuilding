"""SwissRules Watch — idempotent seed.

Run: python -m app.seeds.seed_swiss_rules_watch

Seeds:
- 5 RuleSources (vd_camac, suva_asbestos, bafu_oled, bag_radon, minergie)
- 2 RuleChangeEvents (1 reviewed, 1 unreviewed)
- 2 CommunalAdapterProfiles (Lausanne VD active, Meyrin GE draft)
- 2 CommunalRuleOverrides (Lausanne heritage, Meyrin stricter threshold)
"""

import asyncio
import uuid
from datetime import UTC, date, datetime, timedelta

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.communal_adapter import CommunalAdapterProfile
from app.models.communal_override import CommunalRuleOverride
from app.models.rule_change_event import RuleChangeEvent
from app.models.swiss_rules_source import RuleSource
from app.models.user import User


async def seed():
    async with AsyncSessionLocal() as db:
        # ---- Idempotency: skip if sources already exist ----
        existing = await db.execute(select(RuleSource).limit(1))
        if existing.scalar_one_or_none():
            print("SwissRules Watch seed: already seeded, skipping.")
            return

        now = datetime.now(UTC)

        # ---- 1. RuleSources ----
        sources = []
        for code, name, url, tier, checked_days_ago in [
            (
                "vd_camac",
                "Canton de Vaud - CAMAC (permis de construire)",
                "https://www.vd.ch/themes/territoire-et-construction/constructions",
                "daily",
                1,
            ),
            (
                "suva_asbestos",
                "SUVA - Amiante dans le batiment",
                "https://www.suva.ch/fr-ch/prevention/themes-specialises/amiante",
                "weekly",
                5,
            ),
            (
                "bafu_oled",
                "OFEV/BAFU - OLED dechets de chantier",
                "https://www.bafu.admin.ch/bafu/fr/home/themes/dechets.html",
                "weekly",
                12,
            ),
            (
                "bag_radon",
                "OFSP/BAG - Radon (ORaP)",
                "https://www.bag.admin.ch/bag/fr/home/gesund-leben/umwelt-und-gesundheit/strahlung-radioaktivitaet-schall/radon.html",
                "monthly",
                25,
            ),
            (
                "minergie",
                "Minergie - Standards energetiques",
                "https://www.minergie.ch",
                "quarterly",
                60,
            ),
        ]:
            checked_at = now - timedelta(days=checked_days_ago)
            s = RuleSource(
                id=uuid.uuid4(),
                source_code=code,
                source_name=name,
                source_url=url,
                watch_tier=tier,
                last_checked_at=checked_at,
                freshness_state="current" if checked_days_ago <= 7 else "aging",
                is_active=True,
            )
            db.add(s)
            sources.append(s)
        await db.flush()

        # ---- 2. RuleChangeEvents ----
        # Find admin user for reviewed_by
        admin_result = await db.execute(select(User).where(User.email == "admin@swissbuildingos.ch"))
        admin = admin_result.scalar_one_or_none()

        evt1 = RuleChangeEvent(
            id=uuid.uuid4(),
            source_id=sources[0].id,  # vd_camac
            event_type="portal_change",
            title="Nouveau formulaire CAMAC pour declarations amiante",
            description="Le canton de Vaud a mis a jour le formulaire de declaration amiante sur le portail CAMAC.",
            impact_summary="Formulaire de declaration mis a jour, verifier compatibilite export",
            detected_at=now - timedelta(days=3),
            reviewed=True,
            reviewed_by_user_id=admin.id if admin else None,
            reviewed_at=now - timedelta(days=2),
            review_notes="Formulaire verifie, pas d'impact sur les donnees existantes.",
            affects_buildings=False,
        )
        evt2 = RuleChangeEvent(
            id=uuid.uuid4(),
            source_id=sources[1].id,  # suva_asbestos
            event_type="amended_rule",
            title="SUVA: mise a jour seuils intervention amiante friable",
            description="La SUVA a publie une mise a jour des seuils d'intervention pour l'amiante friable dans les revetements de sol.",
            impact_summary="Seuils potentiellement modifies pour materiaux de sol — evaluer impact sur risk_engine",
            detected_at=now - timedelta(days=1),
            reviewed=False,
            affects_buildings=True,
        )
        db.add_all([evt1, evt2])

        # Update source change_types_detected
        sources[0].change_types_detected = ["portal_change"]
        sources[0].last_changed_at = now - timedelta(days=3)
        sources[1].change_types_detected = ["amended_rule"]
        sources[1].last_changed_at = now - timedelta(days=1)

        # ---- 3. CommunalAdapterProfiles ----
        adapter_lau = CommunalAdapterProfile(
            id=uuid.uuid4(),
            commune_code="5586",  # OFS code Lausanne
            commune_name="Lausanne",
            canton_code="VD",
            adapter_status="active",
            supports_procedure_projection=True,
            supports_rule_projection=True,
            fallback_mode="canton_default",
            source_ids=[str(sources[0].id)],
            notes="Pilote — integration CAMAC Vaud active",
        )
        adapter_mey = CommunalAdapterProfile(
            id=uuid.uuid4(),
            commune_code="6630",  # OFS code Meyrin
            commune_name="Meyrin",
            canton_code="GE",
            adapter_status="draft",
            supports_procedure_projection=False,
            supports_rule_projection=False,
            fallback_mode="manual_review",
            notes="Draft — en attente de validation regles communales GE",
        )
        db.add_all([adapter_lau, adapter_mey])
        await db.flush()

        # ---- 4. CommunalRuleOverrides ----
        ovr_lau = CommunalRuleOverride(
            id=uuid.uuid4(),
            commune_code="5586",
            canton_code="VD",
            override_type="heritage_constraint",
            rule_reference="RPGA Lausanne Art. 45",
            impact_summary="Batiments classes patrimoine: diagnostic amiante obligatoire avant tout travaux, meme mineurs",
            review_required=True,
            confidence_level="review_required",
            source_id=sources[0].id,
            effective_from=date(2020, 1, 1),
            is_active=True,
        )
        ovr_mey = CommunalRuleOverride(
            id=uuid.uuid4(),
            commune_code="6630",
            canton_code="GE",
            override_type="stricter_threshold",
            rule_reference="REI Meyrin 2023",
            impact_summary="Seuil PCB abaisse a 30 mg/kg (vs 50 mg/kg federal) pour batiments scolaires",
            review_required=True,
            confidence_level="auto_with_notice",
            effective_from=date(2023, 6, 1),
            is_active=True,
        )
        db.add_all([ovr_lau, ovr_mey])

        await db.commit()
        print("SwissRules Watch seed complete:")
        print(f"  Sources: {len(sources)}")
        print("  Change events: 2 (1 reviewed, 1 unreviewed)")
        print("  Commune adapters: 2 (Lausanne active, Meyrin draft)")
        print("  Commune overrides: 2")


if __name__ == "__main__":
    asyncio.run(seed())
