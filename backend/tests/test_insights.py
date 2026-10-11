import asyncio
from datetime import UTC, date, datetime
from decimal import Decimal

import httpx
from pydantic import SecretStr

from app.routers.insights import (
    ActionDraft,
    ExpensePoint,
    MonthSummary,
    NarrativeBundle,
    Signal,
    _economic_type,
    _narrate,
    calculate_signals,
    settings,
)


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
                categories={
                    "Mercado": Decimal(8000 if index == 12 else 1000),
                    "Lazer": Decimal(4000 if index == 12 else 500),
                },
            )
        )
    points = [
        ExpensePoint(datetime(2025, month, 10, tzinfo=UTC), Decimal(100), "Mercado")
        for month in range(1, 12)
    ]
    points.append(ExpensePoint(datetime(2025, 12, 10, tzinfo=UTC), Decimal(3000), "Mercado"))
    months[-1].salary = Decimal(7000)
    months[-1].voucher_expense = Decimal(500)
    points.extend(
        ExpensePoint(
            datetime(2025, month, 5, tzinfo=UTC),
            Decimal(80),
            "Assinaturas",
            "Streaming",
        )
        for month in (9, 10, 11)
    )

    types = {signal.type for signal in calculate_signals(months, points, Decimal(1000))}

    assert {
        "category_outlier",
        "transaction_outlier",
        "income_decline",
        "cost_growth",
        "efficiency",
        "cash_flow_risk",
        "income_composition",
        "voucher_usage",
        "grocery_opportunity",
        "recurring_expense",
    } <= types
    schema = NarrativeBundle.model_json_schema()
    assert schema["additionalProperties"] is False
    assert schema["$defs"]["Narrative"]["additionalProperties"] is False
    assert schema["$defs"]["ActionDraft"]["additionalProperties"] is False


def test_economic_classification_avoids_double_counting() -> None:
    assert _economic_type("credit", "PIX mesma titularidade", "", "pluggy", "bank")[0] == "transfer"
    assert _economic_type("debit", "Pagamento fatura", "", "pluggy", "bank")[0] == "card_payment"
    assert _economic_type("credit", "Estorno compra", "", "pluggy", "bank")[0] == "refund"
    assert _economic_type("debit", "Compra", "", "voucher", None)[0] == "voucher_expense"
    assert _economic_type("credit", "Folha de pagamento", "", "pluggy", "bank")[0] == "salary"
    assert (
        _economic_type("debit", "PIX enviado", "Same person transfer", "pluggy", "bank")[0]
        == "transfer"
    )
    assert (
        _economic_type("debit", "itau", "Credit card payment", "pluggy", "bank")[0]
        == "card_payment"
    )


def test_narration_timeout_falls_back_to_local(monkeypatch) -> None:
    class TimeoutClient:
        def __init__(self, **_kwargs) -> None:
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            pass

        async def post(self, *_args, **_kwargs):
            raise httpx.TimeoutException("timeout")

    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test"))
    monkeypatch.setattr(httpx, "AsyncClient", TimeoutClient)
    signal = Signal(
        signal_id="test",
        type="test",
        severity="info",
        ref_period="2026-09",
        title="Teste",
        body="Teste",
        actions=[ActionDraft(description="Revisar", estimated_impact=None)],
        evidence={},
    )

    narratives, _, _, model = asyncio.run(_narrate([signal]))

    assert narratives[0].signal_id == "test"
    assert model == "deterministic"


def test_narration_consumes_merged_signals(monkeypatch) -> None:
    class Response:
        def raise_for_status(self) -> None:
            pass

        def json(self) -> dict:
            text = NarrativeBundle(
                insights=[
                    {
                        "signal_id": "cost",
                        "type": "cost_growth",
                        "severity": "warning",
                        "ref_period": "2026-09",
                        "title": "Custos concentrados",
                        "body": "Mercado explica a alta.",
                        "actions": [],
                        "merged_signal_ids": ["market"],
                    }
                ]
            ).model_dump_json()
            return {
                "output": [{"type": "message", "content": [{"type": "output_text", "text": text}]}]
            }

    class Client:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            pass

        async def post(self, *_args, **_kwargs):
            return Response()

    monkeypatch.setattr(settings, "openai_api_key", SecretStr("test"))
    monkeypatch.setattr(httpx, "AsyncClient", lambda **_kwargs: Client())
    signals = [
        Signal(
            signal_id="cost",
            type="cost_growth",
            severity="warning",
            ref_period="2026-09",
            title="Custos",
            body="Alta",
            actions=[],
            evidence={},
        ),
        Signal(
            signal_id="market",
            type="category_outlier",
            severity="warning",
            ref_period="2026-09",
            title="Mercado",
            body="Alta",
            actions=[],
            evidence={},
        ),
    ]
    narratives, *_ = asyncio.run(_narrate(signals))
    assert [item.signal_id for item in narratives] == ["cost"]
    assert narratives[0].merged_signal_ids == ["market"]
