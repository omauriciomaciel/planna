import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(120))
    privacy_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    privacy_version: Mapped[str | None] = mapped_column(String(16))
    ai_consent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    memberships: Mapped[list["HouseholdMember"]] = relationship(back_populates="user")


class Household(TimestampMixin, Base):
    __tablename__ = "households"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(120))

    members: Mapped[list["HouseholdMember"]] = relationship(back_populates="household")


class HouseholdMember(Base):
    __tablename__ = "household_members"
    __table_args__ = (
        UniqueConstraint("user_id"),
        CheckConstraint("role IN ('owner', 'member')", name="ck_household_member_role"),
    )

    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role: Mapped[str] = mapped_column(String(16))
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    household: Mapped[Household] = relationship(back_populates="members")
    user: Mapped[User] = relationship(back_populates="memberships")


class MagicLinkToken(TimestampMixin, Base):
    __tablename__ = "magic_link_tokens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    ip_request: Mapped[str | None] = mapped_column(String(45))


class Session(TimestampMixin, Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    cookie_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class PluggyItem(TimestampMixin, Base):
    __tablename__ = "pluggy_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    pluggy_item_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    connector_id: Mapped[str | None] = mapped_column(String(64))
    institution_name: Mapped[str] = mapped_column(String(160), default="Instituição")
    status: Mapped[str] = mapped_column(String(40), default="UPDATING")
    execution_status: Mapped[str | None] = mapped_column(String(80))
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error: Mapped[str | None] = mapped_column(String(500))


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (CheckConstraint("kind IN ('expense', 'income')", name="ck_category_kind"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(100))
    parent_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"))
    kind: Mapped[str] = mapped_column(String(16))
    color: Mapped[str | None] = mapped_column(String(32))
    icon: Mapped[str | None] = mapped_column(String(40))
    is_system: Mapped[bool] = mapped_column(Boolean, default=False)
    external_id: Mapped[str | None] = mapped_column(String(40), unique=True)


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        CheckConstraint("type IN ('bank', 'credit', 'investment')", name="ck_account_type"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    item_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("pluggy_items.id", ondelete="CASCADE"))
    pluggy_account_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    type: Mapped[str] = mapped_column(String(24))
    subtype: Mapped[str | None] = mapped_column(String(50))
    name: Mapped[str] = mapped_column(String(160))
    number_masked: Mapped[str | None] = mapped_column(String(80))
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="BRL")
    credit_limit: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    due_day: Mapped[int | None]


class AccountBalanceSnapshot(Base):
    __tablename__ = "account_balance_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class Invoice(TimestampMixin, Base):
    __tablename__ = "invoices"
    __table_args__ = (
        CheckConstraint(
            "payment_status IN ('reconciled', 'voucher')", name="ck_invoice_payment_status"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    access_key: Mapped[str] = mapped_column(String(44), unique=True)
    number: Mapped[str | None] = mapped_column(String(20))
    series: Mapped[str | None] = mapped_column(String(10))
    issue_datetime: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    gross_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    discount_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2), default=0)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    merchant_cnpj: Mapped[str | None] = mapped_column(String(14), index=True)
    merchant_name: Mapped[str] = mapped_column(String(200))
    merchant_address: Mapped[str | None] = mapped_column(String(500))
    source_url: Mapped[str] = mapped_column(String(4096))
    payment_method_raw: Mapped[str | None] = mapped_column(String(120))
    payment_status: Mapped[str] = mapped_column(String(16))
    matched_transaction_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("transactions.id", ondelete="SET NULL"), unique=True
    )
    match_confidence: Mapped[Decimal] = mapped_column(Numeric(3, 2))
    protocol: Mapped[str | None] = mapped_column(String(100))
    raw: Mapped[dict] = mapped_column(JSON)


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    invoice_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("invoices.id", ondelete="CASCADE"), index=True
    )
    description: Mapped[str] = mapped_column(String(500))
    product_code: Mapped[str | None] = mapped_column(String(80))
    ncm: Mapped[str | None] = mapped_column(String(16))
    quantity: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    unit: Mapped[str | None] = mapped_column(String(20))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(18, 4))
    total_price: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"), index=True)


class Transaction(TimestampMixin, Base):
    __tablename__ = "transactions"
    __table_args__ = (
        CheckConstraint("type IN ('debit', 'credit')", name="ck_transaction_type"),
        CheckConstraint("status IN ('posted', 'pending')", name="ck_transaction_status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    account_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("accounts.id", ondelete="CASCADE"), index=True
    )
    pluggy_transaction_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True)
    source_invoice_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey(
            "invoices.id",
            name="fk_transactions_source_invoice_id",
            ondelete="CASCADE",
            use_alter=True,
        ),
        unique=True,
    )
    date: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    description: Mapped[str] = mapped_column(String(500))
    merchant_name: Mapped[str | None] = mapped_column(String(200))
    merchant_cnpj: Mapped[str | None] = mapped_column(String(20))
    category_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("categories.id"), index=True)
    type: Mapped[str] = mapped_column(String(16))
    status: Mapped[str] = mapped_column(String(16))
    installment_current: Mapped[int | None]
    installment_total: Mapped[int | None]
    source: Mapped[str] = mapped_column(String(16), default="pluggy")
    raw: Mapped[dict] = mapped_column(JSON)


class Asset(TimestampMixin, Base):
    __tablename__ = "assets"
    __table_args__ = (
        CheckConstraint(
            "type IN ('cash', 'investment', 'real_estate', 'pension')",
            name="ck_asset_type",
        ),
        CheckConstraint("source IN ('manual', 'pluggy')", name="ck_asset_source"),
        CheckConstraint("current_value >= 0", name="ck_asset_current_value"),
        UniqueConstraint("source", "external_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(160))
    current_value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    source: Mapped[str] = mapped_column(String(16), default="manual")
    external_ref: Mapped[str | None] = mapped_column(String(100))
    valued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class Liability(TimestampMixin, Base):
    __tablename__ = "liabilities"
    __table_args__ = (
        CheckConstraint("type IN ('financing', 'credit_card', 'loan')", name="ck_liability_type"),
        CheckConstraint("source IN ('manual', 'pluggy')", name="ck_liability_source"),
        CheckConstraint("current_balance >= 0", name="ck_liability_current_balance"),
        CheckConstraint(
            "original_amount IS NULL OR original_amount >= 0",
            name="ck_liability_original_amount",
        ),
        CheckConstraint(
            "interest_rate IS NULL OR interest_rate >= 0", name="ck_liability_interest_rate"
        ),
        CheckConstraint(
            "monthly_payment IS NULL OR monthly_payment >= 0",
            name="ck_liability_monthly_payment",
        ),
        CheckConstraint("due_day IS NULL OR due_day BETWEEN 1 AND 31", name="ck_liability_due_day"),
        UniqueConstraint("source", "external_ref"),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    member_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    type: Mapped[str] = mapped_column(String(24))
    name: Mapped[str] = mapped_column(String(160))
    current_balance: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    original_amount: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    monthly_payment: Mapped[Decimal | None] = mapped_column(Numeric(18, 2))
    due_day: Mapped[int | None]
    source: Mapped[str] = mapped_column(String(16), default="manual")
    external_ref: Mapped[str | None] = mapped_column(String(100))


class AssetValueHistory(Base):
    __tablename__ = "asset_value_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("assets.id", ondelete="CASCADE"), index=True
    )
    value: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class LiabilityValueHistory(Base):
    __tablename__ = "liability_value_history"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    liability_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("liabilities.id", ondelete="CASCADE"), index=True
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class NetWorthSnapshot(TimestampMixin, Base):
    __tablename__ = "net_worth_snapshots"
    __table_args__ = (UniqueConstraint("household_id", "ref_month"),)

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    ref_month: Mapped[date] = mapped_column(index=True)
    total_assets: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    total_liabilities: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    net_worth: Mapped[Decimal] = mapped_column(Numeric(18, 2))
    debt_ratio: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))
    savings_rate: Mapped[Decimal | None] = mapped_column(Numeric(12, 6))


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (
        CheckConstraint(
            "severity IN ('info', 'warning', 'critical')", name="ck_insight_severity"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(40))
    severity: Mapped[str] = mapped_column(String(16))
    ref_period: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(160))
    body: Mapped[str] = mapped_column(String(1000))
    payload: Mapped[dict] = mapped_column(JSON)
    model: Mapped[str] = mapped_column(String(80))
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class AIRun(Base):
    __tablename__ = "ai_runs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    household_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("households.id", ondelete="CASCADE"), index=True
    )
    purpose: Mapped[str] = mapped_column(String(80))
    prompt_tokens: Mapped[int] = mapped_column(default=0)
    completion_tokens: Mapped[int] = mapped_column(default=0)
    cost_estimate: Mapped[Decimal] = mapped_column(Numeric(12, 6), default=0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
