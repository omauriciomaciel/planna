from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.deps import get_current_user
from app.models.user import User
from app.services.categorizer import CategorizerService, get_categorizer_service

router = APIRouter(prefix="/categorize", tags=["categorize"])


class CategorizeRequest(BaseModel):
    description: str


class CategorizeResponse(BaseModel):
    category: str | None


@router.post("", response_model=CategorizeResponse)
async def categorize(
    data: CategorizeRequest,
    user: User = Depends(get_current_user),
    service: CategorizerService = Depends(get_categorizer_service),
):
    category = await service.predict_category(user.id, data.description)
    return CategorizeResponse(category=category)


@router.post("/train")
async def train(
    user: User = Depends(get_current_user),
    service: CategorizerService = Depends(get_categorizer_service),
):
    success = await service.train_and_save(user.id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Not enough categorized data to train (minimum 10 entries needed)",
        )
    return {"status": "trained"}
