import uuid

from sqlalchemy import ForeignKey, String
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

    user = relationship("User", back_populates="accounts")
    bank = relationship("Bank", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

    @property
    def name(self) -> str:
        return self.bank.full_name if self.bank else ""
