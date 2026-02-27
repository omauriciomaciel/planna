from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank import Bank


class BankRepository:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_all(self) -> list[Bank]:
        result = await self.db.execute(
            select(Bank).order_by(Bank.code.nullslast(), Bank.name)
        )
        return list(result.scalars().all())
