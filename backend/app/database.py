"""
SwissBuildingOS - Database Configuration

Async SQLAlchemy engine, session factory, and base model.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import declarative_base

from app.config import settings

_engine_kwargs: dict = {"echo": False}

if settings.DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

    # Keep a single shared connection only for in-memory SQLite.
    # File-backed SQLite is used for local preview / real E2E and needs
    # independent connections to avoid cross-request transaction bleed.
    if ":memory:" in settings.DATABASE_URL:
        from sqlalchemy.pool import StaticPool

        _engine_kwargs["poolclass"] = StaticPool
else:
    _engine_kwargs.update(
        {
            "pool_size": 20,
            "max_overflow": 10,
            "pool_pre_ping": True,
            "pool_recycle": 300,
        }
    )

engine = create_async_engine(settings.DATABASE_URL, **_engine_kwargs)

if settings.DATABASE_URL.startswith("sqlite"):

    @event.listens_for(engine.sync_engine, "connect")
    def _register_sqlite_spatial_stubs(dbapi_conn, _):  # pragma: no cover - registration hook
        # Local/dev SQLite fallback for PostGIS-dependent columns/functions.
        def _noop(*args):
            return None

        def _identity(x):
            return x

        dbapi_conn.create_function("ST_AsText", 1, lambda x: str(x) if x else None)
        dbapi_conn.create_function("ST_GeomFromText", 2, lambda wkt, srid: wkt)
        dbapi_conn.create_function("ST_AsGeoJSON", 1, lambda x: '{"type":"Point","coordinates":[0,0]}')
        dbapi_conn.create_function("GeomFromEWKT", 1, _identity)
        dbapi_conn.create_function("AsEWKB", 1, _identity)
        dbapi_conn.create_function("ST_GeomFromEWKT", 1, _identity)
        dbapi_conn.create_function("RecoverGeometryColumn", -1, _noop)
        dbapi_conn.create_function("CheckSpatialMetaData", 0, lambda: 1)
        dbapi_conn.create_function("AddGeometryColumn", -1, _noop)
        dbapi_conn.create_function("DiscardGeometryColumn", -1, _noop)


AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

Base = declarative_base()


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Dependency that provides an async database session."""
    session = AsyncSessionLocal()
    try:
        yield session
    finally:
        await session.close()
