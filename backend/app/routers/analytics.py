from datetime import date

from fastapi import APIRouter, Depends, Query

from app.deps import get_current_user
from app.models.user import User
from app.services.analytics import AnalyticsService, get_analytics_service

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/sankey")
async def sankey(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_sankey_data(user.id, year, month)


@router.get("/monthly-closing")
async def monthly_closing(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_monthly_closing(user.id, year, month)


@router.get("/history")
async def history(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    n: int = Query(default=6, ge=2, le=24),
    user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_monthly_history(user.id, year, month, n)


@router.get("/credit")
async def credit_analytics(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    n: int = Query(default=6, ge=2, le=24),
    user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.get_credit_analytics(user.id, year, month, n)


@router.get("/outliers")
async def outliers(
    year: int = Query(default_factory=lambda: date.today().year),
    month: int = Query(default_factory=lambda: date.today().month),
    user: User = Depends(get_current_user),
    service: AnalyticsService = Depends(get_analytics_service),
):
    return await service.detect_outliers(user.id, year, month)
