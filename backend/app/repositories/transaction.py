import uuid
from datetime import date

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.category import Category
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.repositories.base import BaseRepository


class TransactionRepository(BaseRepository[Transaction]):
    def __init__(self, db: AsyncSession):
        super().__init__(Transaction, db)

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        type: str | None = None,
        status: str | None = None,
    ) -> list[Transaction]:
        query = (
            select(Transaction)
            .where(Transaction.user_id == user_id)
            .options(
                selectinload(Transaction.account).selectinload(Account.bank),
                selectinload(Transaction.category),
            )
            .order_by(Transaction.date.desc())
            .offset(skip)
            .limit(limit)
        )
        if type:
            query = query.where(Transaction.type == TransactionType(type))
        if status:
            query = query.where(Transaction.status == TransactionStatus(status))

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def get_with_relations(
        self, transaction_id: uuid.UUID, user_id: uuid.UUID
    ) -> Transaction | None:
        result = await self.db.execute(
            select(Transaction)
            .where(Transaction.id == transaction_id, Transaction.user_id == user_id)
            .options(
                selectinload(Transaction.account).selectinload(Account.bank),
                selectinload(Transaction.category),
            )
        )
        return result.scalar_one_or_none()

    async def bulk_create(
        self,
        user_id: uuid.UUID,
        parsed: list[dict],
        account_id: uuid.UUID | None = None,
    ) -> int:
        count = 0
        for item in parsed:
            tx = Transaction(
                user_id=user_id,
                date=item["date"],
                due_date=item.get("due_date"),
                description=item["description"],
                account_id=account_id,
                type=item["type"],
                amount=item["amount"],
                status=item["status"],
            )
            self.db.add(tx)
            count += 1
        await self.db.commit()
        return count

    async def get_month_with_categories(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> list[tuple[Transaction, str | None]]:
        result = await self.db.execute(
            select(Transaction, Category.name.label("category_name"))
            .outerjoin(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                extract("year", Transaction.date) == year,
                extract("month", Transaction.date) == month,
            )
        )
        return result.all()

    async def get_expense_category_monthly(
        self, user_id: uuid.UUID, start: date, end: date
    ) -> list:
        result = await self.db.execute(
            select(
                Category.name,
                extract("year", Transaction.date).label("yr"),
                extract("month", Transaction.date).label("mo"),
                func.sum(Transaction.amount).label("total"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.type == TransactionType.EXPENSE,
                Transaction.date >= start,
                Transaction.date < end,
            )
            .group_by(Category.name, "yr", "mo")
        )
        return result.all()

    async def get_categorized_descriptions(
        self, user_id: uuid.UUID
    ) -> list[tuple[str, str]]:
        result = await self.db.execute(
            select(Transaction.description, Category.name)
            .join(Category, Transaction.category_id == Category.id)
            .where(Transaction.user_id == user_id, Transaction.category_id.isnot(None))
        )
        return result.all()
