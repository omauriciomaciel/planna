import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.credit_card import CreditCard
from app.repositories.credit_card import CreditCardRepository


class CreditCardService:
    def __init__(self, repo: CreditCardRepository):
        self.repo = repo

    async def list_for_user(self, user_id: uuid.UUID) -> list[CreditCard]:
        return await self.repo.list_for_user(user_id)

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        account_id: str | None = None,
        due_day: int | None = None,
        closing_day: int | None = None,
        limit: float | None = None,
    ) -> CreditCard:
        card = CreditCard(
            user_id=user_id,
            name=name,
            account_id=uuid.UUID(account_id) if account_id else None,
            due_day=due_day,
            closing_day=closing_day,
            limit=limit,
        )
        return await self.repo.create(card)

    async def delete(self, card_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        card = await self.repo.get_by_id_and_user(card_id, user_id)
        if not card:
            return False
        await self.repo.delete(card)
        return True


def get_credit_card_repository(
    db: AsyncSession = Depends(get_db),
) -> CreditCardRepository:
    return CreditCardRepository(db)


def get_credit_card_service(
    repo: CreditCardRepository = Depends(get_credit_card_repository),
) -> CreditCardService:
    return CreditCardService(repo)
