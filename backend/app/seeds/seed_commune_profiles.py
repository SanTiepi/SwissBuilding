"""
BatiConnect - Commune Profiles Seed
Idempotent seed with ~15 key Swiss communes (VD/GE focus).

Usage:
    python -m app.seeds.seed_commune_profiles
"""

import asyncio
import uuid

from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.commune_profile import CommuneProfile

# Stable UUIDs for idempotent upserts
_NS = uuid.UUID("c0000e00-0000-4000-a000-000000000001")

COMMUNES = [
    {
        "id": uuid.uuid5(_NS, "5586-lausanne"),
        "commune_number": 5586,
        "name": "Lausanne",
        "canton": "VD",
        "population": 146372,
        "population_year": 2023,
        "tax_multiplier": 1.545,
        "median_income": 58000,
        "homeowner_rate_pct": 17.2,
        "vacancy_rate_pct": 0.38,
        "unemployment_rate_pct": 4.8,
        "population_growth_pct": 1.2,
        "dominant_age_group": "mixed",
        "financial_health": "good",
    },
    {
        "id": uuid.uuid5(_NS, "5585-pully"),
        "commune_number": 5585,
        "name": "Pully",
        "canton": "VD",
        "population": 18945,
        "population_year": 2023,
        "tax_multiplier": 1.365,
        "median_income": 72000,
        "homeowner_rate_pct": 26.5,
        "vacancy_rate_pct": 0.42,
        "unemployment_rate_pct": 3.2,
        "population_growth_pct": 0.8,
        "dominant_age_group": "mixed",
        "financial_health": "excellent",
    },
    {
        "id": uuid.uuid5(_NS, "5890-montreux"),
        "commune_number": 5890,
        "name": "Montreux",
        "canton": "VD",
        "population": 26792,
        "population_year": 2023,
        "tax_multiplier": 1.515,
        "median_income": 55000,
        "homeowner_rate_pct": 22.0,
        "vacancy_rate_pct": 0.55,
        "dominant_age_group": "aging",
        "financial_health": "good",
    },
    {
        "id": uuid.uuid5(_NS, "5889-vevey"),
        "commune_number": 5889,
        "name": "Vevey",
        "canton": "VD",
        "population": 20070,
        "population_year": 2023,
        "tax_multiplier": 1.600,
        "median_income": 48000,
        "homeowner_rate_pct": 18.0,
        "vacancy_rate_pct": 0.60,
        "dominant_age_group": "mixed",
        "financial_health": "average",
    },
    {
        "id": uuid.uuid5(_NS, "5561-nyon"),
        "commune_number": 5561,
        "name": "Nyon",
        "canton": "VD",
        "population": 22068,
        "population_year": 2023,
        "tax_multiplier": 1.395,
        "median_income": 68000,
        "homeowner_rate_pct": 24.0,
        "vacancy_rate_pct": 0.35,
        "dominant_age_group": "young",
        "financial_health": "excellent",
    },
    {
        "id": uuid.uuid5(_NS, "5518-morges"),
        "commune_number": 5518,
        "name": "Morges",
        "canton": "VD",
        "population": 16497,
        "population_year": 2023,
        "tax_multiplier": 1.420,
        "median_income": 65000,
        "homeowner_rate_pct": 23.0,
        "vacancy_rate_pct": 0.40,
        "dominant_age_group": "mixed",
        "financial_health": "good",
    },
    {
        "id": uuid.uuid5(_NS, "5938-yverdon"),
        "commune_number": 5938,
        "name": "Yverdon-les-Bains",
        "canton": "VD",
        "population": 31184,
        "population_year": 2023,
        "tax_multiplier": 1.585,
        "median_income": 52000,
        "homeowner_rate_pct": 19.0,
        "vacancy_rate_pct": 0.72,
        "dominant_age_group": "mixed",
        "financial_health": "average",
    },
    {
        "id": uuid.uuid5(_NS, "6621-geneve"),
        "commune_number": 6621,
        "name": "Genève",
        "canton": "GE",
        "population": 205164,
        "population_year": 2023,
        "tax_multiplier": 0.4405,
        "median_income": 62000,
        "homeowner_rate_pct": 15.8,
        "vacancy_rate_pct": 0.45,
        "unemployment_rate_pct": 5.2,
        "population_growth_pct": 0.9,
        "dominant_age_group": "mixed",
        "financial_health": "good",
    },
    {
        "id": uuid.uuid5(_NS, "6630-carouge"),
        "commune_number": 6630,
        "name": "Carouge",
        "canton": "GE",
        "population": 22946,
        "population_year": 2023,
        "tax_multiplier": 0.4300,
        "median_income": 58000,
        "homeowner_rate_pct": 16.5,
        "vacancy_rate_pct": 0.40,
        "dominant_age_group": "mixed",
        "financial_health": "good",
    },
    {
        "id": uuid.uuid5(_NS, "6628-lancy"),
        "commune_number": 6628,
        "name": "Lancy",
        "canton": "GE",
        "population": 33948,
        "population_year": 2023,
        "tax_multiplier": 0.4380,
        "median_income": 55000,
        "homeowner_rate_pct": 14.0,
        "vacancy_rate_pct": 0.48,
        "dominant_age_group": "young",
        "financial_health": "good",
    },
    {
        "id": uuid.uuid5(_NS, "351-bern"),
        "commune_number": 351,
        "name": "Bern",
        "canton": "BE",
        "population": 134794,
        "population_year": 2023,
        "tax_multiplier": 1.540,
        "median_income": 60000,
        "homeowner_rate_pct": 20.0,
        "vacancy_rate_pct": 0.50,
        "unemployment_rate_pct": 3.5,
        "population_growth_pct": 0.6,
        "dominant_age_group": "mixed",
        "financial_health": "good",
    },
    {
        "id": uuid.uuid5(_NS, "261-zurich"),
        "commune_number": 261,
        "name": "Zürich",
        "canton": "ZH",
        "population": 443037,
        "population_year": 2023,
        "tax_multiplier": 1.190,
        "median_income": 68000,
        "homeowner_rate_pct": 19.5,
        "vacancy_rate_pct": 0.30,
        "unemployment_rate_pct": 2.8,
        "population_growth_pct": 1.0,
        "dominant_age_group": "mixed",
        "financial_health": "excellent",
    },
    {
        "id": uuid.uuid5(_NS, "2701-basel"),
        "commune_number": 2701,
        "name": "Basel",
        "canton": "BS",
        "population": 177654,
        "population_year": 2023,
        "tax_multiplier": 1.000,
        "median_income": 58000,
        "homeowner_rate_pct": 18.0,
        "vacancy_rate_pct": 0.42,
        "unemployment_rate_pct": 3.8,
        "population_growth_pct": 0.5,
        "dominant_age_group": "mixed",
        "financial_health": "good",
    },
    {
        "id": uuid.uuid5(_NS, "6266-sion"),
        "commune_number": 6266,
        "name": "Sion",
        "canton": "VS",
        "population": 35060,
        "population_year": 2023,
        "tax_multiplier": 1.300,
        "median_income": 56000,
        "homeowner_rate_pct": 30.0,
        "vacancy_rate_pct": 0.80,
        "dominant_age_group": "mixed",
        "financial_health": "average",
    },
    {
        "id": uuid.uuid5(_NS, "2196-fribourg"),
        "commune_number": 2196,
        "name": "Fribourg",
        "canton": "FR",
        "population": 42265,
        "population_year": 2023,
        "tax_multiplier": 1.360,
        "median_income": 52000,
        "homeowner_rate_pct": 21.0,
        "vacancy_rate_pct": 0.65,
        "unemployment_rate_pct": 4.0,
        "population_growth_pct": 0.7,
        "dominant_age_group": "young",
        "financial_health": "good",
    },
]


async def seed_commune_profiles() -> int:
    """Upsert commune profiles. Returns count of inserted/updated records."""
    async with AsyncSessionLocal() as db:
        count = 0
        for data in COMMUNES:
            row = await db.execute(
                select(CommuneProfile).where(CommuneProfile.commune_number == data["commune_number"])
            )
            existing = row.scalar_one_or_none()
            if existing is None:
                db.add(CommuneProfile(**data))
                count += 1
            else:
                for k, v in data.items():
                    if k != "id":
                        setattr(existing, k, v)
                count += 1
        await db.commit()
    return count


if __name__ == "__main__":
    result = asyncio.run(seed_commune_profiles())
    print(f"Seeded {result} commune profiles.")
