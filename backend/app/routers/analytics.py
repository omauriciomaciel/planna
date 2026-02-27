from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.models.user_settings import UserSettings
from app.services.analytics import (
    detect_outliers,
    get_monthly_closing,
    get_monthly_history,
    get_sankey_data,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sankey")
async def sankey(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    settings_result = await db.execute(
        select(UserSettings).where(UserSettings.user_id == user.id)
    )
    settings = settings_result.scalar_one()

    data = await get_sankey_data(db, user.id, year, month, settings.ignore_invoice_payment)
    return data


@router.get("/monthly-closing")
async def monthly_closing(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_monthly_closing(db, user.id, year, month)


@router.get("/history")
async def history(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    n: int = Query(default=6, ge=2, le=24),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await get_monthly_history(db, user.id, year, month, n)


@router.get("/outliers")
async def outliers(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    return await detect_outliers(db, user.id, year, month)
