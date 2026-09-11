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
    account_id: uuid.UUID
    account_name: str
    member_id: uuid.UUID
    member_name: str
    installment_current: int | None
    installment_total: int | None


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
