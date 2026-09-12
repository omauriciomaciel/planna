import uuid
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, EmailStr, Field


class MagicLinkRequest(BaseModel):
    email: EmailStr


class Message(BaseModel):
    message: str


class MemberRead(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    role: str


class HouseholdRead(BaseModel):
    id: uuid.UUID
    name: str
    members: list[MemberRead] = Field(default_factory=list)


class MeRead(BaseModel):
    id: uuid.UUID
    name: str
    email: EmailStr
    household: HouseholdRead


class HealthRead(BaseModel):
    status: str


class PluggyConnectTokenRead(BaseModel):
    access_token: str = Field(serialization_alias="accessToken")


class PluggyItemCreate(BaseModel):
    item_id: uuid.UUID


class SyncRequest(BaseModel):
    item_id: uuid.UUID | None = None


class SyncRead(BaseModel):
    items: int
    accounts: int
    transactions: int


class AccountRead(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    member_name: str
    institution_name: str
    name: str
    type: str
    subtype: str | None
    number_masked: str | None
    balance: Decimal
    currency: str
    credit_limit: Decimal | None
    last_synced_at: datetime | None


class CategoryCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    kind: str = Field(pattern="^(expense|income)$")


class CategoryRead(BaseModel):
    id: uuid.UUID
    name: str
    kind: str
    is_system: bool


class TransactionCategoryUpdate(BaseModel):
    category_id: uuid.UUID | None


class TransactionRead(BaseModel):
    id: uuid.UUID
    date: datetime
    description: str
    merchant_name: str | None
    amount: Decimal
    type: str
    status: str
    source: str
    category_id: uuid.UUID | None
    category_name: str | None
    account_id: uuid.UUID | None
    account_name: str
    member_id: uuid.UUID
    member_name: str
    installment_current: int | None
    installment_total: int | None
    invoice_id: uuid.UUID | None
    invoice_items: list["InvoiceItemRead"] = Field(default_factory=list)


class TransactionPage(BaseModel):
    items: list[TransactionRead]
    next_cursor: str | None


class KpiRead(BaseModel):
    value: Decimal
    variation: float | None


class KpisRead(BaseModel):
    income: KpiRead
    expense: KpiRead
    balance: KpiRead
    net_worth: KpiRead
    date_from: date
    date_to: date


class TrendRead(BaseModel):
    month: date
    income: Decimal
    expense: Decimal
    balance: Decimal


class CategoryExpenseRead(BaseModel):
    category_id: uuid.UUID | None
    category: str
    amount: Decimal


class InvoiceIngestRequest(BaseModel):
    url: str = Field(min_length=44, max_length=4096)


class InvoiceResolveRequest(BaseModel):
    transaction_id: uuid.UUID | None = None


class InvoiceItemRead(BaseModel):
    id: uuid.UUID
    description: str
    product_code: str | None
    quantity: Decimal
    unit: str | None
    unit_price: Decimal
    total_price: Decimal
    category_id: uuid.UUID | None


class InvoiceRead(BaseModel):
    id: uuid.UUID
    access_key: str
    number: str | None
    series: str | None
    issue_datetime: datetime
    total_amount: Decimal
    merchant_cnpj: str | None
    merchant_name: str
    payment_method_raw: str | None
    payment_status: str
    matched_transaction_id: uuid.UUID | None
    match_confidence: Decimal
    needs_review: bool
    items: list[InvoiceItemRead] = Field(default_factory=list)


class InvoiceIngestRead(BaseModel):
    invoice: InvoiceRead
    created: bool


class AssetCreate(BaseModel):
    member_id: uuid.UUID | None = None
    type: str = Field(pattern="^(cash|investment|real_estate|pension)$")
    name: str = Field(min_length=1, max_length=160)
    current_value: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    valued_at: datetime | None = None


class AssetUpdate(BaseModel):
    member_id: uuid.UUID | None = None
    type: str | None = Field(default=None, pattern="^(cash|investment|real_estate|pension)$")
    name: str | None = Field(default=None, min_length=1, max_length=160)
    current_value: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    valued_at: datetime | None = None


class AssetRead(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    member_name: str
    type: str
    name: str
    current_value: Decimal
    source: str
    valued_at: datetime


class LiabilityCreate(BaseModel):
    member_id: uuid.UUID | None = None
    type: str = Field(pattern="^(financing|credit_card|loan)$")
    name: str = Field(min_length=1, max_length=160)
    current_balance: Decimal = Field(ge=0, max_digits=18, decimal_places=2)
    original_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    interest_rate: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=4)
    monthly_payment: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    due_day: int | None = Field(default=None, ge=1, le=31)


class LiabilityUpdate(BaseModel):
    member_id: uuid.UUID | None = None
    type: str | None = Field(default=None, pattern="^(financing|credit_card|loan)$")
    name: str | None = Field(default=None, min_length=1, max_length=160)
    current_balance: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    original_amount: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    interest_rate: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=4)
    monthly_payment: Decimal | None = Field(default=None, ge=0, max_digits=18, decimal_places=2)
    due_day: int | None = Field(default=None, ge=1, le=31)


class LiabilityRead(BaseModel):
    id: uuid.UUID
    member_id: uuid.UUID
    member_name: str
    type: str
    name: str
    current_balance: Decimal
    original_amount: Decimal | None
    interest_rate: Decimal | None
    monthly_payment: Decimal | None
    due_day: int | None
    source: str


class WealthAssetRead(BaseModel):
    id: str
    member_id: uuid.UUID
    member_name: str
    type: str
    name: str
    value: Decimal
    source: str
    valued_at: datetime | None
    editable: bool


class WealthLiabilityRead(BaseModel):
    id: str
    member_id: uuid.UUID
    member_name: str
    type: str
    name: str
    balance: Decimal
    monthly_payment: Decimal | None
    source: str
    editable: bool


class AllocationRead(BaseModel):
    type: str
    value: Decimal


class NetWorthRead(BaseModel):
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal
    debt_ratio: float | None
    income_commitment: float | None
    savings_rate: float | None
    monthly_income: Decimal
    monthly_expense: Decimal
    monthly_debt_payments: Decimal
    assets: list[WealthAssetRead]
    liabilities: list[WealthLiabilityRead]
    allocation: list[AllocationRead]


class NetWorthHistoryRead(BaseModel):
    month: date
    total_assets: Decimal
    total_liabilities: Decimal
    net_worth: Decimal


class ValueHistoryRead(BaseModel):
    recorded_at: datetime
    value: Decimal


class InsightActionRead(BaseModel):
    description: str
    estimated_impact: Decimal | None


class InsightRead(BaseModel):
    id: uuid.UUID
    type: str
    severity: str
    ref_period: str
    title: str
    body: str
    actions: list[InsightActionRead] = Field(default_factory=list)
    model: str
    generated_at: datetime
