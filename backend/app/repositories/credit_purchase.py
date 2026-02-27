import uuid
from datetime import date

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.credit_purchase import CreditPurchase
from app.repositories.base import BaseRepository


class CreditPurchaseRepository(BaseRepository[CreditPurchase]):
    def __init__(self, db: AsyncSession):
        super().__init__(CreditPurchase, db)

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        credit_card_id: str | None = None,
    ) -> list[CreditPurchase]:
        query = (
            select(CreditPurchase)
            .where(CreditPurchase.user_id == user_id)
            .options(
                selectinload(CreditPurchase.credit_card),
                selectinload(CreditPurchase.category),
            )
            .order_by(CreditPurchase.purchase_date.desc())
            .offset(skip)
            .limit(limit)
        )
        if credit_card_id:
            query = query.where(
                CreditPurchase.credit_card_id == uuid.UUID(credit_card_id)
            )

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_with_relations(
        self, purchase_id: uuid.UUID, user_id: uuid.UUID
    ) -> CreditPurchase | None:
        result = await self.db.execute(
            select(CreditPurchase)
            .where(
                CreditPurchase.id == purchase_id, CreditPurchase.user_id == user_id
            )
            .options(
                selectinload(CreditPurchase.credit_card),
                selectinload(CreditPurchase.category),
            )
        )
        return result.scalar_one_or_none()

    async def bulk_create(
        self,
        user_id: uuid.UUID,
        parsed: list[dict],
        credit_card_id: uuid.UUID | None = None,
    ) -> int:
        count = 0
        for item in parsed:
            purchase = CreditPurchase(
                user_id=user_id,
                purchase_date=item["purchase_date"],
                credit_card_id=credit_card_id,
                merchant=item["merchant"],
                total_amount=item["total_amount"],
                installment_amount=item["installment_amount"],
                current_installment=item["current_installment"],
                total_installments=item["total_installments"],
            )
            self.db.add(purchase)
            count += 1
        await self.db.commit()
        return count

    async def get_month_with_categories(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> list[tuple[CreditPurchase, str | None]]:
        result = await self.db.execute(
            select(CreditPurchase, Category.name.label("category_name"))
            .outerjoin(Category, CreditPurchase.category_id == Category.id)
            .where(
                CreditPurchase.user_id == user_id,
                extract("year", CreditPurchase.due_date) == year,
                extract("month", CreditPurchase.due_date) == month,
            )
        )
        return result.all()

    async def get_monthly_totals_by_card(
        self, user_id: uuid.UUID, start: date, end: date
    ) -> list:
        """Sum installment_amount grouped by (year, month, card_name)."""
        result = await self.db.execute(
            select(
                extract("year", CreditPurchase.due_date).label("yr"),
                extract("month", CreditPurchase.due_date).label("mo"),
                CreditCard.name.label("card_name"),
                func.sum(CreditPurchase.installment_amount).label("total"),
            )
            .outerjoin(
                CreditCard, CreditPurchase.credit_card_id == CreditCard.id
            )
            .where(
                CreditPurchase.user_id == user_id,
                CreditPurchase.due_date >= start,
                CreditPurchase.due_date < end,
            )
            .group_by("yr", "mo", CreditCard.name)
            .order_by("yr", "mo")
        )
        return result.all()

    async def get_month_total(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> float:
        """Total installment_amount for a given month."""
        result = await self.db.execute(
            select(func.coalesce(
                func.sum(CreditPurchase.installment_amount), 0
            )).where(
                CreditPurchase.user_id == user_id,
                extract("year", CreditPurchase.due_date) == year,
                extract("month", CreditPurchase.due_date) == month,
            )
        )
        return float(result.scalar_one())

    async def get_categorized_descriptions(
        self, user_id: uuid.UUID
    ) -> list[tuple[str, str]]:
        result = await self.db.execute(
            select(CreditPurchase.merchant, Category.name)
            .join(Category, CreditPurchase.category_id == Category.id)
            .where(
                CreditPurchase.user_id == user_id,
                CreditPurchase.category_id.isnot(None),
            )
        )
        return result.all()
