import uuid

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.category import Category
from app.repositories.category import CategoryRepository
from app.schemas.common import CategoryResponse


def to_category_response(c: Category) -> CategoryResponse:
    return CategoryResponse(
        id=str(c.id),
        name=c.name,
        emoji=c.emoji,
        sort_order=c.sort_order,
        category_type=c.category_type,
        classification=c.classification,
    )


class CategoryService:
    def __init__(self, repo: CategoryRepository):
        self.repo = repo

    async def list_for_user(self, user_id: uuid.UUID) -> list[CategoryResponse]:
        categories = await self.repo.list_for_user(user_id)
        return [to_category_response(c) for c in categories]

    async def create(
        self,
        user_id: uuid.UUID,
        name: str,
        emoji: str | None = None,
        category_type: str | None = None,
        classification: str | None = None,
    ) -> CategoryResponse:
        cat = Category(
            user_id=user_id,
            name=name,
            emoji=emoji,
            category_type=category_type,
            classification=classification,
        )
        await self.repo.create(cat)
        return to_category_response(cat)

    async def update(
        self,
        category_id: uuid.UUID,
        user_id: uuid.UUID,
        update_data: dict,
    ) -> CategoryResponse | None:
        cat = await self.repo.get_by_id_and_user(category_id, user_id)
        if not cat:
            return None

        for field, value in update_data.items():
            setattr(cat, field, value)

        await self.repo.commit()
        await self.repo.refresh(cat)
        return to_category_response(cat)

    async def delete(self, category_id: uuid.UUID, user_id: uuid.UUID) -> bool:
        cat = await self.repo.get_by_id_and_user(category_id, user_id)
        if not cat:
            return False
        await self.repo.delete(cat)
        return True


def get_category_repository(
    db: AsyncSession = Depends(get_db),
) -> CategoryRepository:
    return CategoryRepository(db)


def get_category_service(
    repo: CategoryRepository = Depends(get_category_repository),
) -> CategoryService:
    return CategoryService(repo)
