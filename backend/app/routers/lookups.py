import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.account import Account
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.user import User
from app.schemas.common import (
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    NamedItemCreate,
    NamedItemResponse,
)

router = APIRouter(tags=["lookups"])


# --- Accounts ---

@router.get("/accounts", response_model=list[NamedItemResponse])
async def list_accounts(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Account).where(Account.user_id == user.id).order_by(Account.name)
    )
    return [NamedItemResponse(id=str(a.id), name=a.name) for a in result.scalars().all()]


@router.post("/accounts", response_model=NamedItemResponse, status_code=201)
async def create_account(
    data: NamedItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = Account(user_id=user.id, name=data.name)
    db.add(account)
    await db.commit()
    await db.refresh(account)
    return NamedItemResponse(id=str(account.id), name=account.name)


@router.delete("/accounts/{account_id}", status_code=204)
async def delete_account(
    account_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Account).where(Account.id == uuid.UUID(account_id), Account.user_id == user.id)
    )
    account = result.scalar_one_or_none()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    await db.delete(account)
    await db.commit()


# --- Credit Cards ---

@router.get("/credit-cards", response_model=list[NamedItemResponse])
async def list_credit_cards(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CreditCard).where(CreditCard.user_id == user.id).order_by(CreditCard.name)
    )
    return [NamedItemResponse(id=str(c.id), name=c.name) for c in result.scalars().all()]


@router.post("/credit-cards", response_model=NamedItemResponse, status_code=201)
async def create_credit_card(
    data: NamedItemCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    card = CreditCard(user_id=user.id, name=data.name)
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return NamedItemResponse(id=str(card.id), name=card.name)


@router.delete("/credit-cards/{card_id}", status_code=204)
async def delete_credit_card(
    card_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(CreditCard).where(
            CreditCard.id == uuid.UUID(card_id), CreditCard.user_id == user.id
        )
    )
    card = result.scalar_one_or_none()
    if not card:
        raise HTTPException(status_code=404, detail="Credit card not found")
    await db.delete(card)
    await db.commit()


# --- Categories ---

@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Category)
        .where(Category.user_id == user.id)
        .order_by(Category.sort_order, Category.name)
    )
    return [
        CategoryResponse(id=str(c.id), name=c.name, emoji=c.emoji, sort_order=c.sort_order)
        for c in result.scalars().all()
    ]


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    cat = Category(user_id=user.id, name=data.name, emoji=data.emoji)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return CategoryResponse(
        id=str(cat.id), name=cat.name, emoji=cat.emoji, sort_order=cat.sort_order
    )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category).where(
            Category.id == uuid.UUID(category_id), Category.user_id == user.id
        )
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(cat, field, value)

    await db.commit()
    await db.refresh(cat)
    return CategoryResponse(
        id=str(cat.id), name=cat.name, emoji=cat.emoji, sort_order=cat.sort_order
    )


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Category).where(
            Category.id == uuid.UUID(category_id), Category.user_id == user.id
        )
    )
    cat = result.scalar_one_or_none()
    if not cat:
        raise HTTPException(status_code=404, detail="Category not found")
    await db.delete(cat)
    await db.commit()
