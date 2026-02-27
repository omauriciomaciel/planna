import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user
from app.models.user import User
from app.schemas.common import AccountCreate, AccountResponse, AccountUpdate
from app.services.account import AccountService, get_account_service

router = APIRouter(tags=["accounts"])


@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
):
    return await service.list_for_user(user.id)


@router.post("/accounts", response_model=AccountResponse, status_code=201)
async def create_account(
    data: AccountCreate,
    user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
):
    return await service.create(user.id, data.bank_ispb, data.initial_balance)


@router.patch("/accounts/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: str,
    data: AccountUpdate,
    user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
):
    result = await service.update(uuid.UUID(account_id), user.id, data.initial_balance)
    if not result:
        raise HTTPException(status_code=404, detail="Account not found")
    return result


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: str,
    user: User = Depends(get_current_user),
    service: AccountService = Depends(get_account_service),
):
    deleted = await service.delete(uuid.UUID(account_id), user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Account not found")
