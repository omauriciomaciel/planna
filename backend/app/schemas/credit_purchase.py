import datetime
from decimal import Decimal

from pydantic import BaseModel


class CreditPurchaseCreate(BaseModel):
    purchase_date: datetime.date
    credit_card_id: str | None = None
    merchant: str
    category_id: str | None = None
    total_amount: Decimal
    installment_amount: Decimal
    current_installment: int = 1
    total_installments: int = 1
    due_date: datetime.date | None = None


class CreditPurchaseUpdate(BaseModel):
    purchase_date: datetime.date | None = None
    credit_card_id: str | None = None
    merchant: str | None = None
    category_id: str | None = None
    total_amount: Decimal | None = None
    installment_amount: Decimal | None = None
    current_installment: int | None = None
    total_installments: int | None = None
    due_date: datetime.date | None = None


class CreditPurchaseResponse(BaseModel):
    id: str
    purchase_date: datetime.date
    credit_card_id: str | None
    merchant: str
    category_id: str | None
    total_amount: Decimal
    installment_amount: Decimal
    current_installment: int
    total_installments: int
    due_date: datetime.date | None
    credit_card_name: str | None = None
    category_name: str | None = None

    model_config = {"from_attributes": True}
