import asyncio
import uuid
from datetime import UTC, date, datetime
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException

from app import finance
from app.finance import decode_cursor, encode_cursor, variation
from app.models import PluggyItem, Transaction
from app.pluggy import transaction_values


def test_finance_helpers_preserve_money_signs_and_cursor() -> None:
    debit = transaction_values(
        {
            "date": "2026-09-11T12:00:00.000Z",
            "amount": 12.34,
            "type": "DEBIT",
            "status": "POSTED",
            "description": "Mercado",
        }
    )
    credit = transaction_values(
        {
            "date": "2026-09-11T12:00:00.000Z",
            "amount": -50,
            "type": "CREDIT",
            "status": "PENDING",
        }
    )
    assert debit["amount"] == Decimal("-12.34")
    assert credit["amount"] == Decimal(50)
    assert credit["status"] == "pending"
    assert variation(Decimal(120), Decimal(100)) == 0.2
    assert variation(Decimal(10), Decimal(0)) is None

    timestamp = datetime(2026, 9, 11, 12, tzinfo=UTC)
    row_id = uuid.uuid4()
    assert decode_cursor(encode_cursor(timestamp, row_id)) == (timestamp, row_id)
    with pytest.raises(HTTPException):
        decode_cursor("não-é-um-cursor")


def test_installment_month_projection_handles_short_months() -> None:
    assert finance._add_months(date(2026, 1, 31), 1) == date(2026, 2, 28)
    assert finance._add_months(date(2026, 11, 30), 2) == date(2027, 1, 30)
    assert finance._bill_forecast_month(
        {"creditCardMetadata": {"billForecastDate": "2026-11-15T00:00:00Z"}},
        date(2026, 9, 1),
    ) == date(2026, 11, 1)


def test_transfer_matching_is_one_to_one_and_skips_ambiguous_pairs() -> None:
    rows = [
        SimpleNamespace(
            id=uuid.uuid4(),
            account_id="a",
            type="debit",
            amount=Decimal(-200),
            date=datetime(2026, 9, 1, 12, tzinfo=UTC),
            economic_type="expense",
        ),
        SimpleNamespace(
            id=uuid.uuid4(),
            account_id="b",
            type="credit",
            amount=Decimal(200),
            date=datetime(2026, 9, 1, 12, tzinfo=UTC),
            economic_type="other_income",
        ),
    ]
    assert finance._find_transfer_pairs(rows) == [(rows[0].id, rows[1].id)]
    rows.append(
        SimpleNamespace(
            id=uuid.uuid4(),
            account_id="c",
            type="credit",
            amount=Decimal(200),
            date=datetime(2026, 9, 1, 13, tzinfo=UTC),
            economic_type="other_income",
        )
    )
    assert finance._find_transfer_pairs(rows) == []


def test_sync_populates_transaction_before_category_query(monkeypatch: pytest.MonkeyPatch) -> None:
    item = PluggyItem(
        id=uuid.uuid4(),
        household_id=uuid.uuid4(),
        member_id=uuid.uuid4(),
        pluggy_item_id=str(uuid.uuid4()),
        institution_name="Banco",
        status="UPDATED",
    )

    class FakeDb:
        def __init__(self) -> None:
            self.calls = 0
            self.added: list[object] = []

        async def scalar(self, _query):
            self.calls += 1
            if self.calls == 4:
                transaction = next(row for row in self.added if isinstance(row, Transaction))
                assert transaction.date is not None
                assert transaction.amount is not None
            return item if self.calls == 1 else None

        def add(self, row: object) -> None:
            if getattr(row, "id", None) is None:
                row.id = uuid.uuid4()
            self.added.append(row)

        async def flush(self) -> None:
            pass

        async def commit(self) -> None:
            pass

    monkeypatch.setattr(finance.client, "item", AsyncMock(return_value={"id": item.pluggy_item_id}))
    monkeypatch.setattr(
        finance.client,
        "accounts",
        AsyncMock(return_value=[{"id": str(uuid.uuid4()), "name": "Conta", "balance": 10}]),
    )
    monkeypatch.setattr(
        finance.client,
        "transactions",
        AsyncMock(
            return_value=[
                {
                    "id": str(uuid.uuid4()),
                    "date": "2026-09-12T12:00:00Z",
                    "amount": 10,
                    "type": "DEBIT",
                    "categoryId": "food",
                    "category": "Alimentação",
                }
            ]
        ),
    )
    for name in (
        "sync_pluggy_wealth",
        "_match_transfer_pairs",
        "reconcile_unmatched_invoices",
        "record_snapshot",
    ):
        monkeypatch.setattr(finance, name, AsyncMock())

    asyncio.run(finance.sync_one(FakeDb(), item))
