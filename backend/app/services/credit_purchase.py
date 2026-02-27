import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.credit_purchase import CreditPurchase
from app.repositories.credit_purchase import CreditPurchaseRepository
from app.schemas.credit_purchase import CreditPurchaseResponse


def to_credit_purchase_response(p: CreditPurchase) -> CreditPurchaseResponse:
    return CreditPurchaseResponse(
        id=str(p.id),
        purchase_date=p.purchase_date,
        credit_card_id=str(p.credit_card_id) if p.credit_card_id else None,
        merchant=p.merchant,
        category_id=str(p.category_id) if p.category_id else None,
        total_amount=p.total_amount,
        installment_amount=p.installment_amount,
        current_installment=p.current_installment,
        total_installments=p.total_installments,
        due_date=p.due_date,
        credit_card_name=p.credit_card.name if p.credit_card else None,
        category_name=p.category.name if p.category else None,
    )


class CreditPurchaseService:
    def __init__(self, repo: CreditPurchaseRepository):
        self.repo = repo

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        credit_card_id: str | None = None,
    ) -> list[CreditPurchaseResponse]:
        purchases = await self.repo.list_for_user(user_id, skip, limit, credit_card_id)
        return [to_credit_purchase_response(p) for p in purchases]

    async def create(
        self, user_id: uuid.UUID, data: dict
    ) -> CreditPurchaseResponse:
        purchase = CreditPurchase(
            user_id=user_id,
            purchase_date=data["purchase_date"],
            credit_card_id=(
                uuid.UUID(data["credit_card_id"]) if data.get("credit_card_id") else None
            ),
            merchant=data["merchant"],
            category_id=uuid.UUID(data["category_id"]) if data.get("category_id") else None,
            total_amount=data["total_amount"],
            installment_amount=data["installment_amount"],
            current_installment=data["current_installment"],
            total_installments=data["total_installments"],
            due_date=data.get("due_date"),
        )
        self.repo.db.add(purchase)
        await self.repo.commit()
        await self.repo.refresh(purchase, ["credit_card", "category"])
        return to_credit_purchase_response(purchase)

    async def get(
        self, purchase_id: uuid.UUID, user_id: uuid.UUID
    ) -> CreditPurchaseResponse | None:
        p = await self.repo.get_with_relations(purchase_id, user_id)
        if not p:
            return None
        return to_credit_purchase_response(p)

    async def update(
        self, purchase_id: uuid.UUID, user_id: uuid.UUID, update_data: dict
    ) -> CreditPurchaseResponse | None:
        p = await self.repo.get_with_relations(purchase_id, user_id)
        if not p:
            return None

        for field, value in update_data.items():
            if field in ("credit_card_id", "category_id") and value:
                value = uuid.UUID(value)
            setattr(p, field, value)

        await self.repo.commit()
        await self.repo.refresh(p, ["credit_card", "category"])
        return to_credit_purchase_response(p)

    async def delete(
        self, purchase_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        p = await self.repo.get_by_id_and_user(purchase_id, user_id)
        if not p:
            return False
        await self.repo.delete(p)
        return True


def get_credit_purchase_repository(
    db: AsyncSession = Depends(get_db),
) -> CreditPurchaseRepository:
    return CreditPurchaseRepository(db)


def get_credit_purchase_service(
    repo: CreditPurchaseRepository = Depends(get_credit_purchase_repository),
) -> CreditPurchaseService:
    return CreditPurchaseService(repo)
