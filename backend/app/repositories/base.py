import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


class BaseRepository[T]:
    def __init__(self, model: type[T], db: AsyncSession):
        self.model = model
        self.db = db

    async def get_by_id(self, entity_id: uuid.UUID) -> T | None:
        result = await self.db.execute(
            select(self.model).where(self.model.id == entity_id)
        )
        return result.scalar_one_or_none()

    async def get_by_id_and_user(
        self, entity_id: uuid.UUID, user_id: uuid.UUID
    ) -> T | None:
        result = await self.db.execute(
            select(self.model).where(
                self.model.id == entity_id, self.model.user_id == user_id
            )
        )
        return result.scalar_one_or_none()

    async def create(self, entity: T) -> T:
        self.db.add(entity)
        await self.db.commit()
        await self.db.refresh(entity)
        return entity

    async def delete(self, entity: T) -> None:
        await self.db.delete(entity)
        await self.db.commit()

    async def commit(self) -> None:
        await self.db.commit()

    async def refresh(self, entity: T, attribute_names: list[str] | None = None) -> None:
        if attribute_names:
            await self.db.refresh(entity, attribute_names=attribute_names)
        else:
            await self.db.refresh(entity)
