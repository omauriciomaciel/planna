import datetime
from decimal import Decimal

from pydantic import BaseModel


class TransactionCreate(BaseModel):
    date: datetime.date
    due_date: datetime.date | None = None
    description: str
    account_id: str | None = None
    category_id: str | None = None
    type: str  # "income" or "expense"
    amount: Decimal
    status: str = "unpaid"  # "paid" or "unpaid"


class TransactionUpdate(BaseModel):
    date: datetime.date | None = None
    due_date: datetime.date | None = None
    description: str | None = None
    account_id: str | None = None
    category_id: str | None = None
    type: str | None = None
    amount: Decimal | None = None
    status: str | None = None


class TransactionResponse(BaseModel):
    id: str
    date: datetime.date
    due_date: datetime.date | None
    description: str
    account_id: str | None
    category_id: str | None
    type: str
    amount: Decimal
    status: str
    account_name: str | None = None
    category_name: str | None = None

    model_config = {"from_attributes": True}
