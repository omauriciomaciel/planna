from datetime import UTC, date, datetime
from decimal import Decimal

from app.insights import ExpensePoint, MonthSummary, NarrativeBundle, calculate_signals


def test_calculate_signals_covers_phase_four_rules() -> None:
    incomes = [10000] * 8 + [10000, 9000, 8000, 7000]
    expenses = [4000] * 9 + [9000, 10000, 11000]
    months = []
    for index, (income, expense) in enumerate(zip(incomes, expenses), start=1):
        months.append(
            MonthSummary(
                month=date(2025 + index // 13, (index - 1) % 12 + 1, 1),
                income=Decimal(income),
                expense=Decimal(expense),
                categories={"Mercado": Decimal(8000 if index == 12 else 1000)},
            )
        )
    points = [
        ExpensePoint(datetime(2025, month, 10, tzinfo=UTC), Decimal(100), "Mercado")
        for month in range(1, 12)
    ]
    points.append(ExpensePoint(datetime(2025, 12, 10, tzinfo=UTC), Decimal(3000), "Mercado"))

    types = {signal.type for signal in calculate_signals(months, points, Decimal(1000))}

    assert {
        "category_outlier",
        "transaction_outlier",
        "income_decline",
        "cost_growth",
        "efficiency",
        "cash_flow_risk",
    } <= types
    schema = NarrativeBundle.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["Narrative"]["additionalProperties"] is False
    assert schema["$defs"]["ActionDraft"]["additionalProperties"] is False
