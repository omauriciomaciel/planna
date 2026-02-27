import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.repositories.transaction import TransactionRepository
from app.schemas.transaction import TransactionResponse


def to_transaction_response(t: Transaction) -> TransactionResponse:
    return TransactionResponse(
        id=str(t.id),
        date=t.date,
        due_date=t.due_date,
        description=t.description,
        account_id=str(t.account_id) if t.account_id else None,
        category_id=str(t.category_id) if t.category_id else None,
        type=t.type.value,
        amount=t.amount,
        status=t.status.value,
        account_name=t.account.name if t.account else None,
        category_name=t.category.name if t.category else None,
    )


class TransactionService:
    def __init__(self, repo: TransactionRepository):
        self.repo = repo

    async def list_for_user(
        self,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 50,
        type: str | None = None,
        status: str | None = None,
    ) -> list[TransactionResponse]:
        transactions = await self.repo.list_for_user(user_id, skip, limit, type, status)
        return [to_transaction_response(t) for t in transactions]

    async def create(
        self, user_id: uuid.UUID, data: dict
    ) -> TransactionResponse:
        transaction = Transaction(
            user_id=user_id,
            date=data["date"],
            due_date=data.get("due_date"),
            description=data["description"],
            account_id=uuid.UUID(data["account_id"]) if data.get("account_id") else None,
            category_id=uuid.UUID(data["category_id"]) if data.get("category_id") else None,
            type=TransactionType(data["type"]),
            amount=data["amount"],
            status=TransactionStatus(data["status"]),
        )
        self.repo.db.add(transaction)
        await self.repo.commit()
        await self.repo.refresh(transaction, ["account", "category"])
        if transaction.account:
            await self.repo.refresh(transaction.account, ["bank"])
        return to_transaction_response(transaction)

    async def get(
        self, transaction_id: uuid.UUID, user_id: uuid.UUID
    ) -> TransactionResponse | None:
        t = await self.repo.get_with_relations(transaction_id, user_id)
        if not t:
            return None
        return to_transaction_response(t)

    async def update(
        self, transaction_id: uuid.UUID, user_id: uuid.UUID, update_data: dict
    ) -> TransactionResponse | None:
        t = await self.repo.get_with_relations(transaction_id, user_id)
        if not t:
            return None

        for field, value in update_data.items():
            if field == "type" and value:
                value = TransactionType(value)
            elif field == "status" and value:
                value = TransactionStatus(value)
            elif field in ("account_id", "category_id") and value:
                value = uuid.UUID(value)
            setattr(t, field, value)

        await self.repo.commit()
        await self.repo.refresh(t, ["account", "category"])
        if t.account:
            await self.repo.refresh(t.account, ["bank"])
        return to_transaction_response(t)

    async def delete(
        self, transaction_id: uuid.UUID, user_id: uuid.UUID
    ) -> bool:
        t = await self.repo.get_by_id_and_user(transaction_id, user_id)
        if not t:
            return False
        await self.repo.delete(t)
        return True


def get_transaction_repository(
    db: AsyncSession = Depends(get_db),
) -> TransactionRepository:
    return TransactionRepository(db)


def get_transaction_service(
    repo: TransactionRepository = Depends(get_transaction_repository),
) -> TransactionService:
    return TransactionService(repo)
