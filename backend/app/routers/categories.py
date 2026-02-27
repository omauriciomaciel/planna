import uuid

from fastapi import APIRouter, Depends, HTTPException

from app.deps import get_current_user
from app.models.user import User
from app.schemas.common import CategoryCreate, CategoryResponse, CategoryUpdate
from app.services.category import CategoryService, get_category_service

router = APIRouter(tags=["categories"])


@router.get("/categories", response_model=list[CategoryResponse])
async def list_categories(
    user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
):
    return await service.list_for_user(user.id)


@router.post("/categories", response_model=CategoryResponse, status_code=201)
async def create_category(
    data: CategoryCreate,
    user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
):
    return await service.create(
        user.id,
        name=data.name,
        emoji=data.emoji,
        category_type=data.category_type,
        classification=data.classification,
    )


@router.put("/categories/{category_id}", response_model=CategoryResponse)
async def update_category(
    category_id: str,
    data: CategoryUpdate,
    user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
):
    result = await service.update(
        uuid.UUID(category_id), user.id, data.model_dump(exclude_unset=True)
    )
    if not result:
        raise HTTPException(status_code=404, detail="Category not found")
    return result


@router.delete("/categories/{category_id}", status_code=204)
async def delete_category(
    category_id: str,
    user: User = Depends(get_current_user),
    service: CategoryService = Depends(get_category_service),
):
    deleted = await service.delete(uuid.UUID(category_id), user.id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Category not found")
