import uuid
from decimal import Decimal

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.account import Account
from app.models.bank import Bank
from app.models.transaction import Transaction
from app.repositories.base import BaseRepository


class AccountRepository(BaseRepository[Account]):
    def __init__(self, db: AsyncSession):
        super().__init__(Account, db)

    async def list_for_user(self, user_id: uuid.UUID) -> list[Account]:
        result = await self.db.execute(
            select(Account)
            .where(Account.user_id == user_id)
            .options(selectinload(Account.bank))
            .join(Bank, Account.bank_ispb == Bank.ispb, isouter=True)
            .order_by(Bank.full_name)
        )
        return list(result.scalars().all())

    async def get_balance_sums(
        self, user_id: uuid.UUID
    ) -> dict[uuid.UUID, tuple[Decimal, Decimal]]:
        income_expr = func.sum(
            case((Transaction.type == "income", Transaction.amount), else_=0)
        ).label("income_sum")
        expense_expr = func.sum(
            case((Transaction.type == "expense", Transaction.amount), else_=0)
        ).label("expense_sum")
        result = await self.db.execute(
            select(Transaction.account_id, income_expr, expense_expr)
            .where(Transaction.user_id == user_id, Transaction.account_id.is_not(None))
            .group_by(Transaction.account_id)
        )
        return {
            row.account_id: (row.income_sum, row.expense_sum) for row in result
        }

    async def get_account_balance(
        self, user_id: uuid.UUID, account_id: uuid.UUID
    ) -> tuple[Decimal, Decimal]:
        income_expr = func.sum(
            case((Transaction.type == "income", Transaction.amount), else_=0)
        ).label("income_sum")
        expense_expr = func.sum(
            case((Transaction.type == "expense", Transaction.amount), else_=0)
        ).label("expense_sum")
        result = await self.db.execute(
            select(income_expr, expense_expr).where(
                Transaction.user_id == user_id, Transaction.account_id == account_id
            )
        )
        row = result.one()
        return (Decimal(row.income_sum or 0), Decimal(row.expense_sum or 0))
