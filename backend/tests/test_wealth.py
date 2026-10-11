from decimal import Decimal

from app.routers.wealth import financial_rates, investment_values, loan_values


def test_wealth_calculations_and_pluggy_mapping() -> None:
    assert financial_rates(
        Decimal(500000),
        Decimal(100000),
        Decimal(10000),
        Decimal(7500),
        Decimal(2500),
    ) == (0.2, 0.25, 0.25)
    assert financial_rates(Decimal(0), Decimal(10), Decimal(0), Decimal(0), Decimal(0)) == (
        None,
        None,
        None,
    )

    investment = investment_values(
        {
            "name": "Previdência",
            "subtype": "RETIREMENT",
            "balance": 1359.39,
            "date": "2026-09-11T12:00:00.000Z",
        }
    )
    assert investment["type"] == "pension"
    assert investment["current_value"] == Decimal("1359.39")
    assert investment_values({"balance": -1})["current_value"] == 0

    loan = loan_values(
        {
            "productName": "Crédito imobiliário",
            "type": "FINANCIAMENTO_IMOBILIARIO",
            "contractAmount": 500000,
            "CET": 0.12,
            "firstInstalmentDueDate": "2026-10-08T00:00:00.000Z",
            "payments": {"contractOutstandingBalance": 420000},
        }
    )
    assert loan["type"] == "financing"
    assert loan["current_balance"] == Decimal(420000)
    assert loan["due_day"] == 8
    assert loan_values({"payments": {"contractOutstandingBalance": -1}})["current_balance"] == 0
