import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit_card import CreditCard
from app.repositories.base import BaseRepository


class CreditCardRepository(BaseRepository[CreditCard]):
    def __init__(self, db: AsyncSession):
        super().__init__(CreditCard, db)

    async def list_for_user(self, user_id: uuid.UUID) -> list[CreditCard]:
        result = await self.db.execute(
            select(CreditCard)
            .where(CreditCard.user_id == user_id)
            .order_by(CreditCard.name)
        )
        return list(result.scalars().all())
