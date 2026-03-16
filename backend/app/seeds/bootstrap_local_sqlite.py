"""
Bootstrap a fully seeded local SQLite database for SwissBuilding preview.

Usage:
    python -m app.seeds.bootstrap_local_sqlite
    python -m app.seeds.bootstrap_local_sqlite --db-path ./local_preview.db --reset
"""

from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path

from sqlalchemy import MetaData, String
from sqlalchemy.ext.asyncio import create_async_engine


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bootstrap local SQLite DB and seed demo data.")
    parser.add_argument("--db-path", default="./local_preview.db", help="SQLite database file path.")
    parser.add_argument("--reset", action="store_true", help="Delete DB file before creating schema and seeding.")
    return parser.parse_args()


def _set_local_env(database_url: str) -> None:
    os.environ["DATABASE_URL"] = database_url
    os.environ.setdefault("JWT_SECRET_KEY", "dev-secret-key-change-in-production-abc123")
    os.environ.setdefault("CLAMAV_ENABLED", "false")
    os.environ.setdefault("OCRMYPDF_ENABLED", "false")
    os.environ.setdefault("MEILISEARCH_ENABLED", "false")


def _build_sqlite_metadata(base_metadata: MetaData) -> MetaData:
    from geoalchemy2 import Geometry

    meta = MetaData()
    for table in base_metadata.sorted_tables:
        new_table = table.to_metadata(meta)
        for col in new_table.columns:
            if isinstance(table.columns[col.name].type, Geometry):
                col.type = String()
                col.nullable = True
        for idx in tuple(new_table.indexes):
            if "postgresql_using" in idx.dialect_kwargs:
                new_table.indexes.discard(idx)
    return meta


async def main() -> None:
    args = parse_args()
    db_file = Path(args.db_path).resolve()
    db_file.parent.mkdir(parents=True, exist_ok=True)

    if args.reset and db_file.exists():
        db_file.unlink()

    sqlite_url = f"sqlite+aiosqlite:///{db_file.as_posix()}"
    _set_local_env(sqlite_url)

    # Import after env setup so app.database picks SQLite settings.
    import app.models  # noqa: F401
    from app.database import Base
    from app.seeds.seed_data import seed

    sqlite_meta = _build_sqlite_metadata(Base.metadata)
    engine = create_async_engine(sqlite_url, connect_args={"check_same_thread": False})
    async with engine.begin() as conn:
        await conn.run_sync(sqlite_meta.create_all)
    await engine.dispose()

    await seed()
    print(f"[BOOTSTRAP-SQLITE] Ready: {db_file}")


if __name__ == "__main__":
    asyncio.run(main())
