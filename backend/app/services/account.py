import uuid
from decimal import Decimal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.account import Account
from app.repositories.account import AccountRepository
from app.schemas.common import AccountResponse


def build_account_response(
    acc: Account, income: Decimal, expense: Decimal
) -> AccountResponse:
    current_balance = acc.initial_balance + income - expense
    return AccountResponse(
        id=acc.id,
        name=acc.name,
        bank_ispb=acc.bank_ispb,
        bank=acc.bank,
        initial_balance=acc.initial_balance,
        current_balance=current_balance,
    )


class AccountService:
    def __init__(self, repo: AccountRepository):
        self.repo = repo

    async def list_for_user(self, user_id: uuid.UUID) -> list[AccountResponse]:
        accounts = await self.repo.list_for_user(user_id)
        sums = await self.repo.get_balance_sums(user_id)
        return [
            build_account_response(
                acc,
                Decimal(sums.get(acc.id, (0, 0))[0] or 0),
                Decimal(sums.get(acc.id, (0, 0))[1] or 0),
            )
            for acc in accounts
        ]

    async def create(
        self, user_id: uuid.UUID, bank_ispb: str, initial_balance: Decimal
    ) -> AccountResponse:
        account = Account(
            user_id=user_id, bank_ispb=bank_ispb, initial_balance=initial_balance
        )
        await self.repo.create(account)
        await self.repo.refresh(account, ["bank"])
        return build_account_response(account, Decimal("0"), Decimal("0"))

    async def update(
        self,
        account_id: uuid.UUID,
        user_id: uuid.UUID,
        initial_balance: Decimal,
    ) -> AccountResponse | None:
        account = await self.repo.get_by_id_and_user(account_id, user_id)
        if not account:
            return None

        account.initial_balance = initial_balance
        await self.repo.commit()
        await self.repo.refresh(account, ["bank"])

        income, expense = await self.repo.get_account_balance(user_id, account.id)
        return build_account_response(account, income, expense)

    async def delete(
        self, account_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        account = await self.repo.get_by_id_and_user(account_id, user_id)
        if not account:
            return False
        await self.repo.delete(account)
        return True


def get_account_repository(
    db: AsyncSession = Depends(get_db),
) -> AccountRepository:
    return AccountRepository(db)


def get_account_service(
    repo: AccountRepository = Depends(get_account_repository),
) -> AccountService:
    return AccountService(repo)
