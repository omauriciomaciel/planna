from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models.user import User
from app.schemas.common import BankResponse
from app.services.bank import BankService, get_bank_service

router = APIRouter(tags=["banks"])


@router.get("/banks", response_model=list[BankResponse])
async def list_banks(
    _: User = Depends(get_current_user),
    service: BankService = Depends(get_bank_service),
):
    return await service.list_all()
