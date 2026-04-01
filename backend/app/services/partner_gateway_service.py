"""BatiConnect — Partner Gateway service.

Governed partner access: every external partner interaction is bounded by
a PartnerExchangeContract. This service validates access, checks trust levels,
runs conformance on submissions, and records exchange events for audit.

No open mutable access -- read-first with controlled submission.
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.exchange_contract import PartnerExchangeContract, PartnerExchangeEvent

logger = logging.getLogger(__name__)


async def validate_partner_access(
    db: AsyncSession,
    partner_org_id: UUID,
    operation: str,
    endpoint: str | None = None,
) -> dict:
    """Check if a partner is allowed to perform an operation.

    Walks the active contracts for the partner and checks:
    1. An active contract exists
    2. The contract has not expired
    3. The operation is in allowed_operations
    4. The endpoint is in allowed_endpoints (if specified on contract)
    5. The partner meets the minimum trust level

    Returns: {allowed: bool, reason: str, contract_id: UUID | None}
    """
    today = date.today()

    result = await db.execute(
        select(PartnerExchangeContract).where(
            and_(
                PartnerExchangeContract.partner_org_id == partner_org_id,
                PartnerExchangeContract.status == "active",
            )
        )
    )
    contracts = list(result.scalars().all())

    if not contracts:
        return {"allowed": False, "reason": "No active exchange contract found", "contract_id": None}

    # Filter by date validity
    valid_contracts = [c for c in contracts if c.start_date <= today and (c.end_date is None or c.end_date >= today)]
    if not valid_contracts:
        return {"allowed": False, "reason": "All contracts expired or not yet effective", "contract_id": None}

    # Find a contract that allows the requested operation
    for contract in valid_contracts:
        ops = contract.allowed_operations or []
        if operation not in ops:
            continue

        # Check endpoint whitelist if defined on contract
        if endpoint and contract.allowed_endpoints and endpoint not in contract.allowed_endpoints:
            continue

        # Check trust level
        trust_ok = await _check_trust_level(db, partner_org_id, contract.minimum_trust_level)
        if not trust_ok:
            # Record denied access
            await record_exchange_event(
                db,
                contract.id,
                "access_denied",
                {
                    "operation": operation,
                    "endpoint": endpoint,
                    "reason": "trust_level_insufficient",
                    "required": contract.minimum_trust_level,
                },
            )
            return {
                "allowed": False,
                "reason": f"Partner trust level below minimum '{contract.minimum_trust_level}'",
                "contract_id": contract.id,
            }

        # Access granted -- record it
        await record_exchange_event(
            db,
            contract.id,
            "access_granted",
            {"operation": operation, "endpoint": endpoint},
        )
        return {"allowed": True, "reason": "Access granted", "contract_id": contract.id}

    return {
        "allowed": False,
        "reason": f"No contract allows operation '{operation}'" + (f" on endpoint '{endpoint}'" if endpoint else ""),
        "contract_id": None,
    }


async def get_active_contracts(
    db: AsyncSession,
    our_org_id: UUID | None = None,
    partner_org_id: UUID | None = None,
) -> list[PartnerExchangeContract]:
    """List active exchange contracts with optional org filters."""
    stmt = select(PartnerExchangeContract).where(
        PartnerExchangeContract.status == "active",
    )
    if our_org_id:
        stmt = stmt.where(PartnerExchangeContract.our_org_id == our_org_id)
    if partner_org_id:
        stmt = stmt.where(PartnerExchangeContract.partner_org_id == partner_org_id)
    stmt = stmt.order_by(PartnerExchangeContract.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_contracts(
    db: AsyncSession,
    our_org_id: UUID | None = None,
    partner_org_id: UUID | None = None,
    status_filter: str | None = None,
) -> list[PartnerExchangeContract]:
    """List exchange contracts with optional filters (any status)."""
    stmt = select(PartnerExchangeContract)
    if our_org_id:
        stmt = stmt.where(PartnerExchangeContract.our_org_id == our_org_id)
    if partner_org_id:
        stmt = stmt.where(PartnerExchangeContract.partner_org_id == partner_org_id)
    if status_filter:
        stmt = stmt.where(PartnerExchangeContract.status == status_filter)
    stmt = stmt.order_by(PartnerExchangeContract.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_contract(db: AsyncSession, contract_id: UUID) -> PartnerExchangeContract | None:
    """Get a single contract by ID."""
    result = await db.execute(select(PartnerExchangeContract).where(PartnerExchangeContract.id == contract_id))
    return result.scalar_one_or_none()


async def create_contract(
    db: AsyncSession,
    data: dict,
) -> PartnerExchangeContract:
    """Create a new partner exchange contract."""
    contract = PartnerExchangeContract(**data)
    db.add(contract)
    await db.flush()
    await db.refresh(contract)

    # Record creation event
    await record_exchange_event(
        db,
        contract.id,
        "contract_created",
        {
            "contract_type": contract.contract_type,
            "partner_org_id": str(contract.partner_org_id),
            "status": contract.status,
        },
    )
    return contract


async def update_contract(
    db: AsyncSession,
    contract_id: UUID,
    updates: dict,
) -> PartnerExchangeContract | None:
    """Update an existing contract. Returns None if not found."""
    contract = await get_contract(db, contract_id)
    if contract is None:
        return None

    old_status = contract.status
    for key, value in updates.items():
        if hasattr(contract, key) and value is not None:
            setattr(contract, key, value)

    contract.updated_at = datetime.now(UTC)
    await db.flush()
    await db.refresh(contract)

    # Record status change if applicable
    if "status" in updates and updates["status"] != old_status:
        await record_exchange_event(
            db,
            contract.id,
            "status_changed",
            {"old_status": old_status, "new_status": contract.status},
        )

    return contract


async def validate_submission(
    db: AsyncSession,
    partner_org_id: UUID,
    submission_type: str,
    submission_data: dict,
) -> dict:
    """Validate a partner submission against their contract + conformance profile.

    1. Finds an active contract for the partner that allows the submission operation
    2. Checks trust level
    3. If a conformance profile is linked, runs conformance check
    4. Records the exchange event

    Returns: {valid: bool, issues: [...], conformance_result: {...}, contract_id: UUID | None}
    """
    # Map submission_type to operation
    operation = f"submit_{submission_type}"

    access = await validate_partner_access(db, partner_org_id, operation)
    if not access["allowed"]:
        return {
            "valid": False,
            "issues": [{"check": "access", "message": access["reason"], "severity": "error"}],
            "conformance_result": None,
            "contract_id": access.get("contract_id"),
        }

    contract_id = access["contract_id"]
    contract = await get_contract(db, contract_id)
    if contract is None:
        return {
            "valid": False,
            "issues": [{"check": "contract", "message": "Contract not found", "severity": "error"}],
            "conformance_result": None,
            "contract_id": None,
        }

    issues: list[dict] = []
    conformance_result = None

    # Check data_sharing_scope constraints
    scope = contract.data_sharing_scope
    if scope == "none":
        issues.append(
            {
                "check": "data_sharing_scope",
                "message": "Contract does not allow data sharing",
                "severity": "error",
            }
        )

    # Run conformance check if profile is linked and a building_id is provided
    if contract.conformance_profile_id and submission_data.get("building_id"):
        try:
            from app.services.conformance_service import run_conformance_check

            check = await run_conformance_check(
                db,
                building_id=submission_data["building_id"],
                profile_name=None,
                target_type="exchange",
                target_id=contract_id,
                checked_by_id=None,
            )
            conformance_result = {
                "result": check.result,
                "score": check.score,
                "passed": len(check.checks_passed or []),
                "failed": len(check.checks_failed or []),
                "warnings": len(check.checks_warning or []),
            }
            if check.result == "fail":
                issues.append(
                    {
                        "check": "conformance",
                        "message": f"Conformance check failed (score: {check.score:.0%})",
                        "severity": "error",
                    }
                )
        except Exception as e:
            logger.warning("Conformance check failed for contract %s: %s", contract_id, e)
            issues.append(
                {
                    "check": "conformance",
                    "message": f"Conformance check error: {e}",
                    "severity": "warning",
                }
            )

    valid = not any(i["severity"] == "error" for i in issues)

    # Record the submission event
    event_type = "submission_validated" if valid else "submission_rejected"
    await record_exchange_event(
        db,
        contract_id,
        event_type,
        {
            "submission_type": submission_type,
            "valid": valid,
            "issue_count": len(issues),
        },
    )

    return {
        "valid": valid,
        "issues": issues,
        "conformance_result": conformance_result,
        "contract_id": contract_id,
    }


async def record_exchange_event(
    db: AsyncSession,
    contract_id: UUID,
    event_type: str,
    detail: dict | None = None,
) -> PartnerExchangeEvent:
    """Record an exchange event for audit trail."""
    event = PartnerExchangeEvent(
        contract_id=contract_id,
        event_type=event_type,
        detail=detail,
        recorded_at=datetime.now(UTC),
    )
    db.add(event)
    await db.flush()
    return event


async def get_exchange_history(
    db: AsyncSession,
    contract_id: UUID,
    limit: int = 50,
) -> list[PartnerExchangeEvent]:
    """Get exchange event history for a contract."""
    result = await db.execute(
        select(PartnerExchangeEvent)
        .where(PartnerExchangeEvent.contract_id == contract_id)
        .order_by(PartnerExchangeEvent.recorded_at.desc())
        .limit(limit)
    )
    return list(result.scalars().all())


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


TRUST_LEVEL_ORDER = {"unknown": 0, "weak": 1, "adequate": 2, "strong": 3}


async def _check_trust_level(
    db: AsyncSession,
    partner_org_id: UUID,
    minimum_level: str,
) -> bool:
    """Check if partner's trust level meets the minimum requirement.

    Returns True if:
    - minimum_level is 'unknown' (no requirement)
    - partner has a trust profile with level >= minimum
    - partner has no trust profile and minimum is 'unknown'
    """
    min_rank = TRUST_LEVEL_ORDER.get(minimum_level, 0)
    if min_rank == 0:
        return True  # No trust requirement

    try:
        from app.services.partner_trust_service import get_profile

        profile = await get_profile(db, partner_org_id)
        if profile is None:
            return False  # No profile and trust is required

        actual_rank = TRUST_LEVEL_ORDER.get(profile.overall_trust_level, 0)
        return actual_rank >= min_rank
    except Exception:
        logger.warning("Could not check trust level for partner %s", partner_org_id)
        return False
