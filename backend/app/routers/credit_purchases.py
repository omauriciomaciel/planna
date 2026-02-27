import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.credit_purchase import CreditPurchase
from app.models.user import User
from app.schemas.credit_purchase import (
    CreditPurchaseCreate,
    CreditPurchaseResponse,
    CreditPurchaseUpdate,
)

router = APIRouter(prefix="/credit-purchases", tags=["credit-purchases"])


def _to_response(p: CreditPurchase) -> CreditPurchaseResponse:
    return CreditPurchaseResponse(
        id=str(p.id),
        purchase_date=p.purchase_date,
        credit_card_id=str(p.credit_card_id) if p.credit_card_id else None,
        merchant=p.merchant,
        category_id=str(p.category_id) if p.category_id else None,
        total_amount=p.total_amount,
        installment_amount=p.installment_amount,
        current_installment=p.current_installment,
        total_installments=p.total_installments,
        due_date=p.due_date,
        credit_card_name=p.credit_card.name if p.credit_card else None,
        category_name=p.category.name if p.category else None,
    )


@router.get("", response_model=list[CreditPurchaseResponse])
async def list_purchases(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    credit_card_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    query = (
        select(CreditPurchase)
        .where(CreditPurchase.user_id == user.id)
        .options(
            selectinload(CreditPurchase.credit_card),
            selectinload(CreditPurchase.category),
        )
        .order_by(CreditPurchase.purchase_date.desc())
        .offset(skip)
        .limit(limit)
    )
    if credit_card_id:
        query = query.where(CreditPurchase.credit_card_id == uuid.UUID(credit_card_id))

    result = await db.execute(query)
    return [_to_response(p) for p in result.scalars().all()]


@router.post("", response_model=CreditPurchaseResponse, status_code=201)
async def create_purchase(
    data: CreditPurchaseCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    purchase = CreditPurchase(
        user_id=user.id,
        purchase_date=data.purchase_date,
        credit_card_id=uuid.UUID(data.credit_card_id) if data.credit_card_id else None,
        merchant=data.merchant,
        category_id=uuid.UUID(data.category_id) if data.category_id else None,
        total_amount=data.total_amount,
        installment_amount=data.installment_amount,
        current_installment=data.current_installment,
        total_installments=data.total_installments,
        due_date=data.due_date,
    )
    db.add(purchase)
    await db.commit()
    await db.refresh(purchase, attribute_names=["credit_card", "category"])
    return _to_response(purchase)


@router.get("/{purchase_id}", response_model=CreditPurchaseResponse)
async def get_purchase(
    purchase_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreditPurchase)
        .where(CreditPurchase.id == uuid.UUID(purchase_id), CreditPurchase.user_id == user.id)
        .options(
            selectinload(CreditPurchase.credit_card),
            selectinload(CreditPurchase.category),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Purchase not found")
    return _to_response(p)


@router.put("/{purchase_id}", response_model=CreditPurchaseResponse)
async def update_purchase(
    purchase_id: str,
    data: CreditPurchaseUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreditPurchase)
        .where(CreditPurchase.id == uuid.UUID(purchase_id), CreditPurchase.user_id == user.id)
        .options(
            selectinload(CreditPurchase.credit_card),
            selectinload(CreditPurchase.category),
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Purchase not found")

    update_data = data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field in ("credit_card_id", "category_id") and value:
            value = uuid.UUID(value)
        setattr(p, field, value)

    await db.commit()
    await db.refresh(p, attribute_names=["credit_card", "category"])
    return _to_response(p)


@router.delete("/{purchase_id}", status_code=204)
async def delete_purchase(
    purchase_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreditPurchase).where(
            CreditPurchase.id == uuid.UUID(purchase_id), CreditPurchase.user_id == user.id
        )
    )
    p = result.scalar_one_or_none()
    if not p:
        raise HTTPException(status_code=404, detail="Purchase not found")
    await db.delete(p)
    await db.commit()
