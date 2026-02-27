import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.categorization_model import CategorizationModel
from app.repositories.base import BaseRepository


class CategorizationModelRepository(BaseRepository[CategorizationModel]):
    def __init__(self, db: AsyncSession):
        super().__init__(CategorizationModel, db)

    async def get_for_user(self, user_id: uuid.UUID) -> CategorizationModel | None:
        result = await self.db.execute(
            select(CategorizationModel).where(
                CategorizationModel.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def upsert(
        self,
        user_id: uuid.UUID,
        model_blob: bytes,
        label_mapping: dict[str, str],
    ) -> None:
        model = await self.get_for_user(user_id)
        if model:
            model.model_blob = model_blob
            model.label_mapping = label_mapping
        else:
            model = CategorizationModel(
                user_id=user_id,
                model_blob=model_blob,
                label_mapping=label_mapping,
            )
            self.db.add(model)
        await self.db.commit()
