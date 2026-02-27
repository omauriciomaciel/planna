import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories.user_settings import UserSettingsRepository
from app.schemas.common import UserSettingsResponse


class UserSettingsService:
    def __init__(self, repo: UserSettingsRepository):
        self.repo = repo

    async def get_for_user(self, user_id: uuid.UUID) -> UserSettingsResponse:
        settings = await self.repo.get_for_user(user_id)
        return UserSettingsResponse.model_validate(settings)

    async def update(
        self, user_id: uuid.UUID, update_data: dict
    ) -> UserSettingsResponse:
        settings = await self.repo.get_for_user(user_id)
        for field, value in update_data.items():
            setattr(settings, field, value)
        await self.repo.commit()
        await self.repo.refresh(settings)
        return UserSettingsResponse.model_validate(settings)


def get_user_settings_repository(
    db: AsyncSession = Depends(get_db),
) -> UserSettingsRepository:
    return UserSettingsRepository(db)


def get_user_settings_service(
    repo: UserSettingsRepository = Depends(get_user_settings_repository),
) -> UserSettingsService:
    return UserSettingsService(repo)
