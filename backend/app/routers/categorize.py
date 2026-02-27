from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.ml.categorizer import predict_category, train_and_save
from app.models.user import User

router = APIRouter(prefix="/categorize", tags=["categorize"])


class CategorizeRequest(BaseModel):
    description: str


class CategorizeResponse(BaseModel):
    category: str | None


@router.post("", response_model=CategorizeResponse)
async def categorize(
    data: CategorizeRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    category = await predict_category(db, user.id, data.description)
    return CategorizeResponse(category=category)


@router.post("/train")
async def train(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    success = await train_and_save(db, user.id)
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Not enough categorized data to train (minimum 10 entries needed)",
        )
    return {"status": "trained"}
