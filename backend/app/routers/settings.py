from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import User
from app.schemas.common import UserSettingsResponse, UserSettingsUpdate
from app.services.user_settings import UserSettingsService, get_user_settings_service

router = APIRouter(prefix="/settings", tags=["settings"])


@router.get("", response_model=UserSettingsResponse)
async def get_settings(
    user: User = Depends(get_current_user),
    service: UserSettingsService = Depends(get_user_settings_service),
):
    return await service.get_for_user(user.id)


@router.put("", response_model=UserSettingsResponse)
async def update_settings(
    data: UserSettingsUpdate,
    user: User = Depends(get_current_user),
    service: UserSettingsService = Depends(get_user_settings_service),
):
    return await service.update(user.id, data.model_dump(exclude_unset=True))
