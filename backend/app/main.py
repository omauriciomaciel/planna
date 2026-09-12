import json
import logging
import re
import time
import uuid
from datetime import UTC, datetime

from fastapi import FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.auth import router as auth_router
from app.config import settings
from app.database import DbSession
from app.finance import router as finance_router
from app.insights import router as insights_router
from app.invoices import router as invoices_router
from app.operations import router as operations_router
from app.schemas import HealthRead
from app.security import SAFE_METHODS, csrf_origin_allowed, session_cookie_name
from app.wealth import router as wealth_router

REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


def route_name(request: Request) -> str:
    route = request.scope.get("route")
    return getattr(route, "path", "<unmatched>")


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "event": record.getMessage(),
        }
        if details := getattr(record, "details", None):
            payload.update(details)
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


handler = logging.StreamHandler()
handler.setFormatter(JsonFormatter())
logging.basicConfig(level=settings.log_level, handlers=[handler], force=True)
logging.getLogger("uvicorn.access").disabled = True
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Planna API",
    version="0.1.0",
    docs_url=None if settings.app_env == "production" else "/docs",
    redoc_url=None if settings.app_env == "production" else "/redoc",
    openapi_url=None if settings.app_env == "production" else "/openapi.json",
)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.trusted_hosts)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PATCH", "DELETE"],
    allow_headers=["Content-Type", "X-Metrics-Token", "X-Request-ID"],
    expose_headers=["Server-Timing", "X-Request-ID"],
)


@app.middleware("http")
async def harden_and_observe(request: Request, call_next):
    started = time.perf_counter()
    supplied_request_id = request.headers.get("X-Request-ID", "")
    request_id = (
        supplied_request_id if REQUEST_ID.fullmatch(supplied_request_id) else uuid.uuid4().hex
    )
    if (
        request.method not in SAFE_METHODS
        and session_cookie_name() in request.cookies
        and not csrf_origin_allowed(request.headers.get("Origin"))
    ):
        response = JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={"detail": "Origem da solicitação não permitida"},
        )
    else:
        try:
            response = await call_next(request)
        except Exception as exc:  # noqa: BLE001 — limite HTTP precisa ocultar falhas inesperadas.
            logger.error(
                "request.failed",
                extra={
                    "details": {
                        "request_id": request_id,
                        "method": request.method,
                        "path": route_name(request),
                        "error_type": type(exc).__name__,
                        "duration_ms": round((time.perf_counter() - started) * 1000, 2),
                    }
                },
            )
            response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={"detail": "Erro interno"},
            )

    duration_ms = round((time.perf_counter() - started) * 1000, 2)
    response.headers["Cache-Control"] = "private, no-store"
    response.headers["Server-Timing"] = f"app;dur={duration_ms}"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request.completed",
        extra={
            "details": {
                "request_id": request_id,
                "method": request.method,
                "path": route_name(request),
                "status": response.status_code,
                "duration_ms": duration_ms,
            }
        },
    )
    return response


app.include_router(auth_router)
app.include_router(finance_router)
app.include_router(invoices_router)
app.include_router(wealth_router)
app.include_router(insights_router)
app.include_router(operations_router)


@app.get("/health", tags=["operation"])
def health() -> HealthRead:
    return HealthRead(status="ok")


@app.get("/ready", tags=["operation"])
async def ready(db: DbSession) -> HealthRead:
    try:
        await db.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Banco de dados indisponível",
        ) from exc
    return HealthRead(status="ready")
