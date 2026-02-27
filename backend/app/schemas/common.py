import uuid

from pydantic import BaseModel


class NamedItemCreate(BaseModel):
    name: str


class NamedItemUpdate(BaseModel):
    name: str | None = None


class NamedItemResponse(BaseModel):
    id: str
    name: str

    model_config = {"from_attributes": True}


class CategoryCreate(BaseModel):
    name: str
    emoji: str | None = None


class CategoryUpdate(BaseModel):
    name: str | None = None
    emoji: str | None = None
    sort_order: int | None = None


class CategoryResponse(BaseModel):
    id: str
    name: str
    emoji: str | None
    sort_order: int

    model_config = {"from_attributes": True}


class BankResponse(BaseModel):
    ispb: str
    code: int | None
    name: str
    full_name: str

    model_config = {"from_attributes": True}


class AccountCreate(BaseModel):
    bank_ispb: str


class AccountResponse(BaseModel):
    id: uuid.UUID
    name: str
    bank_ispb: str | None
    bank: BankResponse | None

    model_config = {"from_attributes": True}


class UserSettingsUpdate(BaseModel):
    auto_categorize: bool | None = None
    notify_due_expenses: bool | None = None
    due_days_ahead: int | None = None
    notify_abnormal_expenses: bool | None = None
    notify_overdue_expenses: bool | None = None
    notify_monthly_closing: bool | None = None
    ignore_invoice_payment: bool | None = None


class UserSettingsResponse(BaseModel):
    auto_categorize: bool
    notify_due_expenses: bool
    due_days_ahead: int
    notify_abnormal_expenses: bool
    notify_overdue_expenses: bool
    notify_monthly_closing: bool
    ignore_invoice_payment: bool

    model_config = {"from_attributes": True}
