import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.transaction import Transaction, TransactionStatus, TransactionType
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)

router = APIRouter(prefix="/transactions", tags=["transactions"])


def _to_response(t: Transaction) -> TransactionResponse:
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


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    type: str | None = None,
    status: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(Transaction)
        .where(Transaction.user_id == user.id)
        .options(selectinload(Transaction.account), selectinload(Transaction.category))
        .order_by(Transaction.date.desc())
        .offset(skip)
        .limit(limit)
    )
    if type:
        query = query.where(Transaction.type == TransactionType(type))
    if status:
        query = query.where(Transaction.status == TransactionStatus(status))

    result = await db.execute(query)
    return [_to_response(t) for t in result.scalars().all()]


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    data: TransactionCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    transaction = Transaction(
        user_id=user.id,
        date=data.date,
        due_date=data.due_date,
        description=data.description,
        account_id=uuid.UUID(data.account_id) if data.account_id else None,
        category_id=uuid.UUID(data.category_id) if data.category_id else None,
        type=TransactionType(data.type),
        amount=data.amount,
        status=TransactionStatus(data.status),
    )
    db.add(transaction)
    await db.commit()
    await db.refresh(transaction, attribute_names=["account", "category"])
    return _to_response(transaction)


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == uuid.UUID(transaction_id), Transaction.user_id == user.id)
        .options(selectinload(Transaction.account), selectinload(Transaction.category))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return _to_response(t)


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction)
        .where(Transaction.id == uuid.UUID(transaction_id), Transaction.user_id == user.id)
        .options(selectinload(Transaction.account), selectinload(Transaction.category))
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field == "type" and value:
            value = TransactionType(value)
        elif field == "status" and value:
            value = TransactionStatus(value)
        elif field in ("account_id", "category_id") and value:
            value = uuid.UUID(value)
        setattr(t, field, value)

    await db.commit()
    await db.refresh(t, attribute_names=["account", "category"])
    return _to_response(t)


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Transaction).where(
            Transaction.id == uuid.UUID(transaction_id), Transaction.user_id == user.id
        )
    )
    t = result.scalar_one_or_none()
    if not t:
        raise HTTPException(status_code=404, detail="Transaction not found")
    await db.delete(t)
    await db.commit()
