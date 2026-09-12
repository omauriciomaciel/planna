import secrets
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException, Query, status
from sqlalchemy import func, select

from app.config import settings
from app.database import DbSession
from app.models import AIRun, PluggyItem
from app.schemas import OperationsMetricsRead

router = APIRouter(prefix="/operations", tags=["operation"])


def require_metrics_token(
    token: Annotated[str | None, Header(alias="X-Metrics-Token")] = None,
) -> None:
    expected = settings.metrics_token
    if expected is None or token is None or not secrets.compare_digest(
        token, expected.get_secret_value()
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Não autorizado")


MetricsAccess = Annotated[None, Depends(require_metrics_token)]


@router.get("/metrics")
async def metrics(
    db: DbSession,
    _: MetricsAccess,
    days: Annotated[int, Query(ge=1, le=366)] = 30,
) -> OperationsMetricsRead:
    since = datetime.now(UTC) - timedelta(days=days)
    sync_items, sync_errors, last_sync_at = (
        await db.execute(
            select(
                func.count(PluggyItem.id),
                func.count(PluggyItem.id).filter(PluggyItem.error.is_not(None)),
                func.max(PluggyItem.last_synced_at),
            )
        )
    ).one()
    ai_runs, prompt_tokens, completion_tokens, cost = (
        await db.execute(
            select(
                func.count(AIRun.id),
                func.coalesce(func.sum(AIRun.prompt_tokens), 0),
                func.coalesce(func.sum(AIRun.completion_tokens), 0),
                func.coalesce(func.sum(AIRun.cost_estimate), 0),
            ).where(AIRun.created_at >= since)
        )
    ).one()
    return OperationsMetricsRead(
        period_days=days,
        sync_items=sync_items,
        sync_errors=sync_errors,
        last_sync_at=last_sync_at,
        ai_runs=ai_runs,
        ai_prompt_tokens=prompt_tokens,
        ai_completion_tokens=completion_tokens,
        ai_cost_estimate=Decimal(cost),
    )
