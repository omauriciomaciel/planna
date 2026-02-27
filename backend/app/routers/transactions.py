import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user
from app.models.user import User
from app.schemas.transaction import (
    TransactionCreate,
    TransactionResponse,
    TransactionUpdate,
)
from app.services.transaction import TransactionService, get_transaction_service

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("", response_model=list[TransactionResponse])
async def list_transactions(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    type: str | None = None,
    status: str | None = None,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    return await service.list_for_user(user.id, skip, limit, type, status)


@router.post("", response_model=TransactionResponse, status_code=201)
async def create_transaction(
    data: TransactionCreate,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    return await service.create(user.id, data.model_dump())


@router.get("/{transaction_id}", response_model=TransactionResponse)
async def get_transaction(
    transaction_id: str,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    result = await service.get(uuid.UUID(transaction_id), user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return result


@router.put("/{transaction_id}", response_model=TransactionResponse)
async def update_transaction(
    transaction_id: str,
    data: TransactionUpdate,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    result = await service.update(
        uuid.UUID(transaction_id), user.id, data.model_dump(exclude_unset=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Transaction not found")
    return result


@router.delete("/{transaction_id}", status_code=204)
async def delete_transaction(
    transaction_id: str,
    user: User = Depends(get_current_user),
    service: TransactionService = Depends(get_transaction_service),
):
    deleted = await service.delete(uuid.UUID(transaction_id), user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Transaction not found")
