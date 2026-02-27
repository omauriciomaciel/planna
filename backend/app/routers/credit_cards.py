import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user
from app.models.user import User
from app.schemas.common import CreditCardCreate, CreditCardResponse
from app.services.credit_card import CreditCardService, get_credit_card_service

router = APIRouter(tags=["credit-cards"])


@router.get("/credit-cards", response_model=list[CreditCardResponse])
async def list_credit_cards(
    user: User = Depends(get_current_user),
    service: CreditCardService = Depends(get_credit_card_service),
):
    return await service.list_for_user(user.id)


@router.post("/credit-cards", response_model=CreditCardResponse, status_code=201)
async def create_credit_card(
    data: CreditCardCreate,
    user: User = Depends(get_current_user),
    service: CreditCardService = Depends(get_credit_card_service),
):
    return await service.create(
        user_id=user.id,
        name=data.name,
        account_id=data.account_id,
        due_day=data.due_day,
        closing_day=data.closing_day,
        limit=data.limit,
    )


@router.delete("/credit-cards/{card_id}", status_code=204)
async def delete_credit_card(
    card_id: str,
    user: User = Depends(get_current_user),
    service: CreditCardService = Depends(get_credit_card_service),
):
    deleted = await service.delete(uuid.UUID(card_id), user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credit card not found")
