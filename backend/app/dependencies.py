"""
SwissBuildingOS - Authentication & RBAC Dependencies

Provides JWT-based authentication and role-based access control.
All route handlers use get_current_user and require_permission as dependencies.
"""

import uuid
from collections.abc import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Role-based permission matrix
# ---------------------------------------------------------------------------
PERMISSIONS: dict[str, dict[str, list[str]]] = {
    "admin": {
        "buildings": ["create", "read", "update", "delete", "list"],
        "campaigns": ["create", "read", "update", "delete", "list"],
        "diagnostics": ["create", "read", "update", "delete", "list", "validate"],
        "samples": ["create", "read", "update", "delete", "list"],
        "documents": ["create", "read", "delete", "list"],
        "events": ["create", "read", "list"],
        "risk_analysis": ["read", "execute"],
        "pollutant_map": ["read"],
        "users": ["create", "read", "update", "delete", "list"],
        "audit_logs": ["read", "list"],
        "actions": ["create", "read", "update", "delete", "list"],
        "organizations": ["create", "read", "update", "delete", "list"],
        "invitations": ["create", "read", "update", "delete", "list"],
        "assignments": ["create", "read", "delete", "list"],
        "notifications": ["read", "update", "list"],
        "exports": ["create", "read", "list"],
        "zones": ["create", "read", "update", "delete", "list"],
        "elements": ["create", "read", "update", "delete", "list"],
        "materials": ["create", "read", "update", "delete", "list"],
        "interventions": ["create", "read", "update", "delete", "list"],
        "leases": ["create", "read", "update", "list"],
        "contracts": ["create", "read", "update", "list"],
        "ownership": ["create", "read", "update", "list"],
        "obligations": ["create", "read", "update", "delete", "list"],
        "plans": ["create", "read", "update", "delete", "list"],
        "evidence": ["create", "read", "list"],
        "jurisdictions": ["create", "read", "update", "delete", "list"],
        "simulations": ["create", "read", "update", "delete", "list"],
        "data_quality": ["create", "read", "update", "delete", "list"],
        "change_signals": ["create", "read", "update", "delete", "list"],
        "readiness": ["create", "read", "update", "delete", "list"],
        "trust_scores": ["create", "read", "update", "delete", "list"],
        "unknowns": ["create", "read", "update", "delete", "list"],
        "post_works": ["create", "read", "update", "delete", "list"],
        "compliance_artefacts": ["create", "read", "update", "delete", "list"],
        "evidence_packs": ["create", "read", "update", "delete", "list"],
        "building_snapshots": ["create", "read", "update", "delete", "list"],
    },
    "owner": {
        "buildings": ["read", "update", "list"],
        "campaigns": ["create", "read", "update", "delete", "list"],
        "diagnostics": ["read", "list"],
        "samples": ["read", "list"],
        "documents": ["create", "read", "list"],
        "events": ["read", "list"],
        "risk_analysis": ["read"],
        "pollutant_map": ["read"],
        "users": ["read"],
        "actions": ["read", "list"],
        "organizations": ["read"],
        "assignments": ["read", "list"],
        "notifications": ["read", "update", "list"],
        "exports": ["create", "read", "list"],
        "zones": ["read", "list"],
        "elements": ["read", "list"],
        "materials": ["read", "list"],
        "interventions": ["create", "read", "update", "list"],
        "leases": ["create", "read", "update", "list"],
        "contracts": ["create", "read", "update", "list"],
        "ownership": ["read", "list"],
        "obligations": ["create", "read", "update", "list"],
        "plans": ["create", "read", "list"],
        "evidence": ["read", "list"],
        "jurisdictions": ["read", "list"],
        "simulations": ["create", "read", "list"],
        "data_quality": ["read", "list"],
        "change_signals": ["read", "list"],
        "readiness": ["read", "list"],
        "trust_scores": ["create", "read", "list"],
        "unknowns": ["create", "read", "list"],
        "post_works": ["create", "read", "list"],
        "compliance_artefacts": ["create", "read", "list"],
        "evidence_packs": ["create", "read", "list"],
        "building_snapshots": ["read", "create", "list"],
    },
    "diagnostician": {
        "buildings": ["read", "list"],
        "campaigns": ["read", "list"],
        "diagnostics": ["create", "read", "update", "list"],
        "samples": ["create", "read", "update", "delete", "list"],
        "documents": ["create", "read", "list"],
        "events": ["create", "read", "list"],
        "risk_analysis": ["read", "execute"],
        "pollutant_map": ["read"],
        "users": ["read"],
        "actions": ["create", "read", "update", "list"],
        "organizations": ["read"],
        "assignments": ["read", "list"],
        "notifications": ["read", "update", "list"],
        "exports": ["create", "read", "list"],
        "zones": ["create", "read", "list"],
        "elements": ["create", "read", "list"],
        "materials": ["create", "read", "list"],
        "interventions": ["create", "read", "list"],
        "leases": ["read", "list"],
        "contracts": ["read", "list"],
        "ownership": ["read", "list"],
        "obligations": ["read", "list"],
        "plans": ["create", "read", "list"],
        "evidence": ["create", "read", "list"],
        "jurisdictions": ["read", "list"],
        "simulations": ["create", "read", "list"],
        "data_quality": ["create", "read", "list"],
        "change_signals": ["read", "list"],
        "readiness": ["read", "list"],
        "trust_scores": ["create", "read", "list"],
        "unknowns": ["create", "read", "list"],
        "post_works": ["create", "read", "list"],
        "compliance_artefacts": ["create", "read", "list"],
        "evidence_packs": ["create", "read", "list"],
        "building_snapshots": ["read", "create", "list"],
    },
    "architect": {
        "buildings": ["read", "list"],
        "campaigns": ["read", "list"],
        "diagnostics": ["read", "list"],
        "samples": ["read", "list"],
        "documents": ["read", "list"],
        "events": ["read", "list"],
        "risk_analysis": ["read", "execute"],
        "pollutant_map": ["read"],
        "users": ["read"],
        "actions": ["read", "list"],
        "organizations": ["read"],
        "assignments": ["read", "list"],
        "notifications": ["read", "update", "list"],
        "exports": ["read", "list"],
        "zones": ["read", "list"],
        "elements": ["read", "list"],
        "materials": ["read", "list"],
        "interventions": ["read", "list"],
        "leases": ["read", "list"],
        "contracts": ["read", "list"],
        "ownership": ["read", "list"],
        "obligations": ["read", "list"],
        "plans": ["create", "read", "list"],
        "evidence": ["read", "list"],
        "jurisdictions": ["read", "list"],
        "simulations": ["read", "list"],
        "data_quality": ["read", "list"],
        "change_signals": ["read", "list"],
        "readiness": ["read", "list"],
        "trust_scores": ["read", "list"],
        "unknowns": ["read", "list"],
        "post_works": ["read", "list"],
        "compliance_artefacts": ["read", "list"],
        "evidence_packs": ["read", "list"],
        "building_snapshots": ["read", "list"],
    },
    "authority": {
        "buildings": ["read", "list"],
        "campaigns": ["read", "list"],
        "diagnostics": ["read", "list", "validate"],
        "samples": ["read", "list"],
        "documents": ["read", "list"],
        "events": ["read", "list"],
        "risk_analysis": ["read"],
        "pollutant_map": ["read"],
        "users": ["read"],
        "audit_logs": ["read", "list"],
        "actions": ["read", "list"],
        "organizations": ["read"],
        "assignments": ["read", "list"],
        "notifications": ["read", "update", "list"],
        "exports": ["read", "list"],
        "zones": ["read", "list"],
        "elements": ["read", "list"],
        "materials": ["read", "list"],
        "interventions": ["read", "list"],
        "leases": ["read", "list"],
        "contracts": ["read", "list"],
        "ownership": ["read", "list"],
        "obligations": ["read", "list"],
        "plans": ["read", "list"],
        "evidence": ["read", "list"],
        "jurisdictions": ["read", "list"],
        "simulations": ["read", "list"],
        "data_quality": ["read", "list"],
        "change_signals": ["read", "list"],
        "readiness": ["read", "list"],
        "trust_scores": ["read", "list"],
        "unknowns": ["read", "list"],
        "post_works": ["read", "list"],
        "compliance_artefacts": ["read", "list", "update"],
        "evidence_packs": ["read", "list"],
        "building_snapshots": ["read", "list"],
    },
    "contractor": {
        "buildings": ["read", "list"],
        "campaigns": ["read", "list"],
        "diagnostics": ["read", "list"],
        "samples": ["read", "list"],
        "documents": ["read", "list"],
        "events": ["read", "list"],
        "risk_analysis": ["read"],
        "pollutant_map": ["read"],
        "actions": ["read", "list"],
        "assignments": ["read", "list"],
        "notifications": ["read", "update", "list"],
        "exports": ["read", "list"],
        "zones": ["read", "list"],
        "elements": ["read", "list"],
        "materials": ["read", "list"],
        "interventions": ["create", "read", "list"],
        "leases": ["read", "list"],
        "contracts": ["read", "list"],
        "obligations": ["read", "list"],
        "plans": ["read", "list"],
        "evidence": ["read", "list"],
        "jurisdictions": ["read", "list"],
        "simulations": ["read", "list"],
        "data_quality": ["read", "list"],
        "change_signals": ["read", "list"],
        "readiness": ["read", "list"],
        "trust_scores": ["read", "list"],
        "unknowns": ["read", "list"],
        "post_works": ["read", "list"],
        "compliance_artefacts": ["read", "list"],
        "evidence_packs": ["read", "list"],
        "building_snapshots": ["read", "list"],
    },
}


def _has_permission(role: str, resource: str, action: str) -> bool:
    """Check whether a role grants the given action on the given resource."""
    role_perms = PERMISSIONS.get(role)
    if role_perms is None:
        return False
    resource_actions = role_perms.get(resource)
    if resource_actions is None:
        return False
    return action in resource_actions


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
    db: AsyncSession = Depends(get_db),
):
    """
    Decode the JWT bearer token and return the corresponding User ORM object.

    The token payload must contain:
      - sub: the user id (UUID as string)
      - role: the user role

    Raises 401 if the token is invalid or the user does not exist.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Jeton d'authentification invalide ou expire.",
        headers={"WWW-Authenticate": "Bearer"},
    )

    if credentials is None:
        raise credentials_exception

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
        user_id_str: str | None = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_uuid = uuid.UUID(user_id_str)
    except (JWTError, ValueError, AttributeError):
        raise credentials_exception from None

    # Lazy import to avoid circular dependency (models imports database)
    from app.models.user import User

    result = await db.execute(select(User).where(User.id == user_uuid))
    user = result.scalar_one_or_none()

    if user is None:
        raise credentials_exception

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Ce compte utilisateur est desactive.",
        )

    return user


def require_permission(resource: str, action: str) -> Callable:
    """
    Return a FastAPI dependency that verifies the current user's role
    grants the requested action on the specified resource.

    Usage in a route::

        @router.get("/buildings")
        async def list_buildings(
            user=Depends(require_permission("buildings", "list")),
        ):
            ...
    """

    async def _permission_checker(
        current_user=Depends(get_current_user),
    ):
        if not _has_permission(current_user.role, resource, action):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"Permission refusee: role '{current_user.role}' ne peut pas effectuer '{action}' sur '{resource}'."
                ),
            )
        return current_user

    return _permission_checker
