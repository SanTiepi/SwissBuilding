"""Audit trail middleware — logs significant API operations."""

import time

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.database import AsyncSessionLocal
from app.logging_config import get_logger
from app.models.audit_log import AuditLog

logger = get_logger("audit_middleware")


class AuditMiddleware(BaseHTTPMiddleware):
    """Logs write operations (POST, PUT, PATCH, DELETE) to the audit trail.

    Uses a dedicated database session so that audit logging never interferes
    with the request's own transaction.  Failures are logged but never block
    the response.
    """

    AUDIT_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
    SKIP_PATHS = {
        "/health",
        "/docs",
        "/redoc",
        "/openapi.json",
        "/metrics",
        "/api/v1/auth/login",
        "/api/v1/auth/register",
    }

    async def dispatch(self, request: Request, call_next):
        if request.method not in self.AUDIT_METHODS:
            return await call_next(request)

        if request.url.path in self.SKIP_PATHS:
            return await call_next(request)

        start = time.time()
        response = await call_next(request)
        duration_ms = round((time.time() - start) * 1000, 1)

        # Fire-and-forget audit logging — never block the response
        try:
            # Extract user id from request state if auth middleware set it
            user_id = None
            if hasattr(request.state, "user_id"):
                user_id = request.state.user_id

            # Derive entity_type from the URL path
            path_parts = [p for p in request.url.path.split("/") if p]
            entity_type = None
            if len(path_parts) >= 3:
                # e.g. /api/v1/buildings -> entity_type = "buildings"
                entity_type = path_parts[2] if path_parts[0] == "api" else path_parts[0]

            # Map HTTP method to action name
            method_action_map = {
                "POST": "create",
                "PUT": "update",
                "PATCH": "update",
                "DELETE": "delete",
            }
            action = method_action_map.get(request.method, request.method.lower())

            client_ip = request.client.host if request.client else None

            async with AsyncSessionLocal() as session:
                audit_entry = AuditLog(
                    user_id=user_id,
                    action=f"api_{action}",
                    entity_type=entity_type,
                    entity_id=None,
                    details={
                        "path": request.url.path,
                        "method": request.method,
                        "status_code": response.status_code,
                        "duration_ms": duration_ms,
                    },
                    ip_address=client_ip,
                )
                session.add(audit_entry)
                await session.commit()
        except Exception:
            logger.warning(
                "audit_middleware_error",
                path=request.url.path,
                method=request.method,
                exc_info=True,
            )

        return response
