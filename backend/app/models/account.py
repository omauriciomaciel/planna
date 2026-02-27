import uuid
from decimal import Decimal

from sqlalchemy import ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Account(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "accounts"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    bank_ispb: Mapped[str | None] = mapped_column(
        String(8), ForeignKey("banks.ispb", ondelete="SET NULL"), nullable=True, index=True
    )
    initial_balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0, server_default="0")

    user = relationship("User", back_populates="accounts")
    bank = relationship("Bank", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")
    credit_cards = relationship("CreditCard", back_populates="account")

    @property
    def name(self) -> str:
        return self.bank.full_name if self.bank else ""
