import uuid

from sqlalchemy import Boolean, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class UserSettings(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "user_settings"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    auto_categorize: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_due_expenses: Mapped[bool] = mapped_column(Boolean, default=True)
    due_days_ahead: Mapped[int] = mapped_column(Integer, default=3)
    notify_abnormal_expenses: Mapped[bool] = mapped_column(Boolean, default=False)
    notify_overdue_expenses: Mapped[bool] = mapped_column(Boolean, default=True)
    notify_monthly_closing: Mapped[bool] = mapped_column(Boolean, default=True)
    ignore_invoice_payment: Mapped[bool] = mapped_column(Boolean, default=False)

    user = relationship("User", back_populates="settings")
