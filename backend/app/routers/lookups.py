import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.deps import get_current_user
from app.models.account import Account
from app.models.bank import Bank
from app.models.category import Category
from app.models.credit_card import CreditCard
from app.models.user import User
from app.schemas.common import (
    AccountCreate,
    AccountResponse,
    BankResponse,
    CategoryCreate,
    CategoryResponse,
    CategoryUpdate,
    CreditCardCreate,
    CreditCardResponse,
)

router = APIRouter(tags=["lookups"])


# --- Banks ---

@router.get("/banks", response_model=list[BankResponse])
async def list_banks(
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Bank).order_by(Bank.code.nullslast(), Bank.name))
    return result.scalars().all()


# --- Accounts ---

@router.get("/accounts", response_model=list[AccountResponse])
async def list_accounts(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(Account)
        .where(Account.user_id == user.id)
        .options(selectinload(Account.bank))
        .join(Bank, Account.bank_ispb == Bank.ispb, isouter=True)
        .order_by(Bank.full_name)
    )
    return result.scalars().all()


@router.post("/accounts", response_model=AccountResponse, status_code=201)
async def create_account(
    data: AccountCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    account = Account(user_id=user.id, bank_ispb=data.bank_ispb)
    db.add(account)
    await db.commit()
    await db.refresh(account, ["bank"])
    return account


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

@router.get("/credit-cards", response_model=list[CreditCardResponse])
async def list_credit_cards(
    user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(CreditCard).where(CreditCard.user_id == user.id).order_by(CreditCard.name)
    )
    return result.scalars().all()


@router.post("/credit-cards", response_model=CreditCardResponse, status_code=201)
async def create_credit_card(
    data: CreditCardCreate,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    card = CreditCard(
        user_id=user.id,
        name=data.name,
        account_id=uuid.UUID(data.account_id) if data.account_id else None,
        due_day=data.due_day,
        closing_day=data.closing_day,
        limit=data.limit,
    )
    db.add(card)
    await db.commit()
    await db.refresh(card)
    return card


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
