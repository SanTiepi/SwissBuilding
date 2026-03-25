"""BatiConnect — Exchange contract and publication service."""

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_contract import ExchangeContractVersion
from app.models.import_receipt import PassportImportReceipt
from app.models.passport_publication import PassportPublication


async def list_contracts(
    db: AsyncSession,
    *,
    audience_filter: str | None = None,
) -> list[ExchangeContractVersion]:
    query = select(ExchangeContractVersion).order_by(ExchangeContractVersion.contract_code)
    if audience_filter:
        query = query.where(ExchangeContractVersion.audience_type == audience_filter)
    result = await db.execute(query)
    return list(result.scalars().all())


async def get_active_contract(db: AsyncSession, contract_code: str) -> ExchangeContractVersion | None:
    result = await db.execute(
        select(ExchangeContractVersion)
        .where(
            ExchangeContractVersion.contract_code == contract_code,
            ExchangeContractVersion.status == "active",
        )
        .order_by(ExchangeContractVersion.version.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def publish_passport(
    db: AsyncSession,
    building_id: UUID,
    data: dict,
    *,
    published_by_org_id: UUID | None = None,
    published_by_user_id: UUID | None = None,
) -> PassportPublication:
    pub = PassportPublication(
        building_id=building_id,
        published_by_org_id=published_by_org_id,
        published_by_user_id=published_by_user_id,
        **data,
    )
    db.add(pub)
    await db.flush()
    await db.refresh(pub)

    # Custody tracking: create version + created/published events
    try:
        from app.services.artifact_custody_service import create_version, record_custody_event

        version = await create_version(
            db,
            artifact_type="passport_publication",
            artifact_id=pub.id,
            content_hash=pub.content_hash if hasattr(pub, "content_hash") else None,
            user_id=published_by_user_id,
        )
        await record_custody_event(db, version.id, {"event_type": "created", "actor_type": "system"})
        await record_custody_event(
            db, version.id, {"event_type": "published", "actor_type": "user", "actor_id": published_by_user_id}
        )
    except Exception:
        pass  # Non-fatal: custody tracking should not break publication

    return pub


async def record_import(db: AsyncSession, data: dict) -> PassportImportReceipt:
    receipt = PassportImportReceipt(**data)
    db.add(receipt)
    await db.flush()
    await db.refresh(receipt)
    return receipt


async def get_publications(db: AsyncSession, building_id: UUID) -> list[PassportPublication]:
    result = await db.execute(
        select(PassportPublication)
        .where(PassportPublication.building_id == building_id)
        .order_by(PassportPublication.published_at.desc())
    )
    return list(result.scalars().all())


async def get_imports(db: AsyncSession, building_id: UUID) -> list[PassportImportReceipt]:
    result = await db.execute(
        select(PassportImportReceipt)
        .where(PassportImportReceipt.building_id == building_id)
        .order_by(PassportImportReceipt.imported_at.desc())
    )
    return list(result.scalars().all())
