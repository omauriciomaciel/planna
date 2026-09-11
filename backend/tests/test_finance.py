import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.finance import decode_cursor, encode_cursor, variation
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
