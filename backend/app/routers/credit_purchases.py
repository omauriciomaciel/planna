import uuid

from fastapi import APIRouter, Depends, HTTPException, Query

from app.deps import get_current_user
from app.models.user import User
from app.schemas.credit_purchase import (
    CreditPurchaseCreate,
    CreditPurchaseResponse,
    CreditPurchaseUpdate,
)
from app.services.credit_purchase import CreditPurchaseService, get_credit_purchase_service

router = APIRouter(prefix="/credit-purchases", tags=["credit-purchases"])


@router.get("", response_model=list[CreditPurchaseResponse])
async def list_purchases(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    credit_card_id: str | None = None,
    user: User = Depends(get_current_user),
    service: CreditPurchaseService = Depends(get_credit_purchase_service),
):
    return await service.list_for_user(user.id, skip, limit, credit_card_id)


@router.post("", response_model=CreditPurchaseResponse, status_code=201)
async def create_purchase(
    data: CreditPurchaseCreate,
    user: User = Depends(get_current_user),
    service: CreditPurchaseService = Depends(get_credit_purchase_service),
):
    return await service.create(user.id, data.model_dump())


@router.get("/{purchase_id}", response_model=CreditPurchaseResponse)
async def get_purchase(
    purchase_id: str,
    user: User = Depends(get_current_user),
    service: CreditPurchaseService = Depends(get_credit_purchase_service),
):
    result = await service.get(uuid.UUID(purchase_id), user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return result


@router.put("/{purchase_id}", response_model=CreditPurchaseResponse)
async def update_purchase(
    purchase_id: str,
    data: CreditPurchaseUpdate,
    user: User = Depends(get_current_user),
    service: CreditPurchaseService = Depends(get_credit_purchase_service),
):
    result = await service.update(
        uuid.UUID(purchase_id), user.id, data.model_dump(exclude_unset=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return result


@router.delete("/{purchase_id}", status_code=204)
async def delete_purchase(
    purchase_id: str,
    user: User = Depends(get_current_user),
    service: CreditPurchaseService = Depends(get_credit_purchase_service),
):
    deleted = await service.delete(uuid.UUID(purchase_id), user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Purchase not found")
