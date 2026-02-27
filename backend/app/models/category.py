import enum
import uuid
from decimal import Decimal

from sqlalchemy import Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CategoryType(str, enum.Enum):
    income = "income"
    expense = "expense"


class CategoryClassification(str, enum.Enum):
    essential = "essential"
    non_essential = "non_essential"


class Category(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "categories"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    emoji: Mapped[str | None] = mapped_column(String(10), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    category_type: Mapped[CategoryType | None] = mapped_column(
        Enum(CategoryType, name="categorytype"), nullable=True
    )
    classification: Mapped[CategoryClassification | None] = mapped_column(
        Enum(CategoryClassification, name="categoryclassification"), nullable=True
    )
    budget: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    user = relationship("User", back_populates="categories")
