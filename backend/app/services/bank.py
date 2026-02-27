from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.bank import Bank
from app.repositories.bank import BankRepository


class BankService:
    def __init__(self, repo: BankRepository):
        self.repo = repo

    async def list_all(self) -> list[Bank]:
        return await self.repo.list_all()


def get_bank_repository(db: AsyncSession = Depends(get_db)) -> BankRepository:
    return BankRepository(db)


def get_bank_service(
    repo: BankRepository = Depends(get_bank_repository),
) -> BankService:
    return BankService(repo)
