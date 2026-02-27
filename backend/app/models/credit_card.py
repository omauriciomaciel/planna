import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class CreditCard(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "credit_cards"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    due_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    closing_day: Mapped[int | None] = mapped_column(Integer, nullable=True)
    limit: Mapped[Decimal | None] = mapped_column(Numeric(12, 2), nullable=True)

    user = relationship("User", back_populates="credit_cards")
    account = relationship("Account", back_populates="credit_cards")
    purchases = relationship("CreditPurchase", back_populates="credit_card")
