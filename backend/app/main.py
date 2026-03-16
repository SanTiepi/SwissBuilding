from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from prometheus_fastapi_instrumentator import Instrumentator
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api.router import api_router
from app.config import settings
from app.limiter import limiter
from app.logging_config import get_logger, setup_logging
from app.middleware.audit_middleware import AuditMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup/shutdown tasks."""
    # Startup: initialize resources
    setup_logging()
    logger = get_logger("swissbuildingos")
    logger.info("application_startup", service="swissbuildingos")
    yield
    # Shutdown: cleanup resources
    logger.info("application_shutdown", service="swissbuildingos")


app = FastAPI(
    title="SwissBuildingOS",
    description="Swiss National Building Intelligence Platform",
    version="1.0.0",
    lifespan=lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(AuditMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1")


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    """Catch ValueError from non-JSON-compliant values (NaN, Infinity)."""
    return JSONResponse(
        status_code=422,
        content={"detail": str(exc)},
    )


Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "service": "swissbuildingos"}
