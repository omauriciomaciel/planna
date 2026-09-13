import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import pairwise
from typing import Literal

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentAuth
from app.config import settings
from app.database import DbSession, SessionLocal
from app.models import (
    Account,
    AIRun,
    Category,
    HouseholdMember,
    Insight,
    Invoice,
    Liability,
    PluggyItem,
    Transaction,
    User,
)
from app.schemas import InsightActionRead, InsightRead, Message

router = APIRouter(prefix="/insights", tags=["insights"])
Severity = Literal["info", "warning", "critical"]
GROCERY_TERMS = ("mercado", "supermercado", "atacadao", "mercearia", "hipermercado")


@dataclass
class MonthSummary:
    month: date
    income: Decimal = Decimal(0)
    expense: Decimal = Decimal(0)
    salary: Decimal = Decimal(0)
    other_income: Decimal = Decimal(0)
    benefits: Decimal = Decimal(0)
    voucher_expense: Decimal = Decimal(0)
    categories: dict[str, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class ExpensePoint:
    date: datetime
    amount: Decimal
    category: str
    label: str = "Despesa"
    source: str = "pluggy"
    transaction_id: uuid.UUID | None = None


@dataclass
class TransactionFact:
    id: uuid.UUID
    date: datetime
    amount: Decimal
    transaction_type: str
    description: str
    merchant: str | None
    category: str
    source: str
    account_type: str | None
    economic_type: str = ""
    confidence: float = 0


class ActionDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    description: str = Field(min_length=1, max_length=240)
    estimated_impact: float | None = Field(ge=0)


class Signal(BaseModel):
    signal_id: str
    type: str
    severity: Severity
    ref_period: str
    title: str
    body: str
    actions: list[ActionDraft]
    evidence: dict
    confidence: float = Field(default=0.9, ge=0, le=1)
    evidence_summary: list[str] = Field(default_factory=list)


class Narrative(BaseModel):
    model_config = ConfigDict(extra="forbid")

    signal_id: str
    type: str
    severity: Severity
    ref_period: str
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=1000)
    actions: list[ActionDraft] = Field(max_length=3)


class NarrativeBundle(BaseModel):
    model_config = ConfigDict(extra="forbid")

    insights: list[Narrative]


def _month(value: date) -> date:
    return value.replace(day=1)


def _shift_month(value: date, offset: int) -> date:
    absolute = value.year * 12 + value.month - 1 + offset
    return date(absolute // 12, absolute % 12 + 1, 1)


def _brl(value: Decimal) -> str:
    return f"R$ {value:,.2f}".replace(",", "_").replace(".", ",").replace("_", ".")


def _average(values: list[Decimal]) -> Decimal:
    return sum(values, Decimal(0)) / len(values)


def _growth(current: Decimal, previous: Decimal) -> Decimal:
    return (current - previous) / previous if previous else Decimal(0)


def _normalized(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", " ", value).strip()


def _stable_id(prefix: str, value: str) -> str:
    return f"{prefix}-{hashlib.sha256(value.encode()).hexdigest()[:12]}"


def _economic_type(
    transaction_type: str,
    description: str,
    category: str,
    source: str,
    account_type: str | None,
) -> tuple[str, float]:
    text = _normalized(f"{description} {category}")
    normalized_category = _normalized(category)
    if source == "voucher" and transaction_type == "debit":
        return "voucher_expense", 1
    if normalized_category in {"transfer", "transfers", "same person transfer"} or any(
        term in text
        for term in (
            "transferencia entre contas",
            "mesma titularidade",
            "same person transfer",
            "own account transfer",
            "internal transfer",
        )
    ):
        return "transfer", 0.95
    if (
        transaction_type == "debit"
        and account_type != "credit"
        and any(
            term in text
            for term in (
                "pagamento fatura",
                "pagto fatura",
                "fatura cartao",
                "credit card payment",
            )
        )
    ):
        return "card_payment", 0.95
    if transaction_type == "credit" and any(
        term in text
        for term in ("estorno", "reembolso", "refund", "reversal", "chargeback", "cashback")
    ):
        return "refund", 0.95
    if transaction_type == "credit" and any(
        term in text
        for term in ("salario", "folha de pagamento", "provento", "holerite", "salary", "payroll")
    ):
        return "salary", 0.98
    if transaction_type == "credit" and any(
        term in text for term in ("vale alimentacao", "vale refeicao", "alelo", "sodexo", "ticket")
    ):
        return "benefit", 0.95
    if transaction_type == "debit" and any(
        term in text for term in ("aplicacao", "investimento", "aporte", "investment")
    ):
        return "investment", 0.9
    return ("other_income", 0.45) if transaction_type == "credit" else ("expense", 0.8)


def _mark_recurring_salary(facts: list[TransactionFact]) -> None:
    candidates: dict[str, list[TransactionFact]] = {}
    for fact in facts:
        if fact.economic_type != "other_income":
            continue
        key = _normalized(fact.merchant or fact.description)
        if key:
            candidates.setdefault(key, []).append(fact)
    for group in candidates.values():
        if len({_month(fact.date.date()) for fact in group}) < 3:
            continue
        amounts = [fact.amount for fact in group]
        days = [fact.date.day for fact in group]
        if (
            min(amounts) > 0
            and max(amounts) / min(amounts) <= Decimal("1.35")
            and max(days) - min(days) <= 10
        ):
            for fact in group:
                fact.economic_type, fact.confidence = "salary", 0.82


def calculate_signals(
    months: list[MonthSummary],
    expenses: list[ExpensePoint],
    cash_balance: Decimal,
    monthly_debt_payments: Decimal = Decimal(0),
    *,
    current_month_partial: bool = False,
) -> list[Signal]:
    if not months:
        return []

    signals: list[Signal] = []
    latest = months[-1]
    period = latest.month.strftime("%Y-%m")
    trend_months = months[:-1] if current_month_partial and len(months) > 1 else months
    trend_latest = trend_months[-1]
    trend_period = trend_latest.month.strftime("%Y-%m")

    category_outliers: list[tuple[str, Decimal, Decimal]] = []
    for category, current in latest.categories.items():
        normalized_category = _normalized(category)
        if normalized_category in {"sem categoria", "uncategorized"} or any(
            term in normalized_category for term in GROCERY_TERMS
        ):
            continue
        history = [month.categories.get(category, Decimal(0)) for month in months[:-1]]
        if sum(value > 0 for value in history) < 3:
            continue
        mean = _average(history)
        deviation = (_average([(value - mean) ** 2 for value in history])).sqrt()
        threshold = max(mean + 2 * deviation, mean * Decimal("1.5"))
        if current > threshold:
            category_outliers.append((category, current, mean))

    for category, current, mean in sorted(
        category_outliers, key=lambda item: item[1] - item[2], reverse=True
    )[:3]:
        excess = current - mean
        signals.append(
            Signal(
                signal_id=_stable_id("category-outlier", category),
                type="category_outlier",
                severity="warning",
                ref_period=period,
                title=f"{category} saiu do padrão",
                body=(
                    f"A categoria fechou em {_brl(current)}, {_brl(excess)} acima da média "
                    "dos meses anteriores."
                ),
                actions=[
                    ActionDraft(
                        description=f"Trazer {category} de volta à média histórica",
                        estimated_impact=excess,
                    )
                ],
                evidence={"category": category, "amount": current, "historical_average": mean},
                evidence_summary=[
                    f"{category}: {_brl(current)} no período",
                    f"Média histórica: {_brl(mean)}",
                ],
            )
        )

    historical_expenses = [
        point.amount for point in expenses if _month(point.date.date()) < latest.month
    ]
    if len(historical_expenses) >= 5:
        mean = _average(historical_expenses)
        deviation = (_average([(value - mean) ** 2 for value in historical_expenses])).sqrt()
        threshold = max(mean + 2 * deviation, mean * 2)
        current_outliers = sorted(
            (
                point
                for point in expenses
                if _month(point.date.date()) == latest.month and point.amount > threshold
            ),
            key=lambda point: point.amount,
            reverse=True,
        )[:3]
        for point in current_outliers:
            signals.append(
                Signal(
                    signal_id=_stable_id(
                        "transaction-outlier",
                        str(
                            point.transaction_id
                            or f"{point.date.isoformat()}-{point.amount}-{point.label}"
                        ),
                    ),
                    type="transaction_outlier",
                    severity="warning",
                    ref_period=period,
                    title="Uma compra merece atenção",
                    body=(
                        f"Uma despesa de {_brl(point.amount)} em {point.category} ficou acima "
                        f"do padrão de {_brl(mean)} por transação."
                    ),
                    actions=[
                        ActionDraft(
                            description="Confirmar se a compra foi pontual ou tende a se repetir",
                            estimated_impact=None,
                        )
                    ],
                    evidence={
                        "date": point.date.date().isoformat(),
                        "category": point.category,
                        "amount": point.amount,
                        "historical_average": mean,
                    },
                    evidence_summary=[
                        f"{point.label}: {_brl(point.amount)} em {point.date:%d/%m/%Y}",
                        f"Média por transação: {_brl(mean)}",
                    ],
                )
            )

    if latest.salary or latest.other_income or latest.benefits:
        parts = []
        if latest.salary:
            parts.append(f"{_brl(latest.salary)} de salário")
        if latest.benefits:
            parts.append(f"{_brl(latest.benefits)} de benefícios")
        if latest.other_income:
            parts.append(f"{_brl(latest.other_income)} de outras entradas")
        signals.append(
            Signal(
                signal_id="income-composition",
                type="income_composition",
                severity="info",
                ref_period=period,
                title="De onde vieram as entradas do mês",
                body="Foram identificados " + ", ".join(parts) + ".",
                actions=[],
                evidence={
                    "salary": latest.salary,
                    "benefits": latest.benefits,
                    "other_income": latest.other_income,
                },
                confidence=0.82 if latest.salary else 0.65,
                evidence_summary=parts,
            )
        )

    if latest.voucher_expense:
        signals.append(
            Signal(
                signal_id="voucher-usage",
                type="voucher_usage",
                severity="info",
                ref_period=period,
                title="Vale-alimentação separado do caixa bancário",
                body=(
                    f"Foram consumidos {_brl(latest.voucher_expense)} via vale. Esse valor entra "
                    "na leitura de consumo, mas não como saída da conta bancária."
                ),
                actions=[],
                evidence={"voucher_expense": latest.voucher_expense},
                confidence=1,
                evidence_summary=[f"Compras conciliadas como vale: {_brl(latest.voucher_expense)}"],
            )
        )

    grocery_by_month: dict[date, Decimal] = {}
    for point in expenses:
        if any(term in _normalized(f"{point.category} {point.label}") for term in GROCERY_TERMS):
            month = _month(point.date.date())
            grocery_by_month[month] = grocery_by_month.get(month, Decimal(0)) + point.amount
    grocery_history = [value for month, value in grocery_by_month.items() if month < latest.month]
    grocery_current = grocery_by_month.get(latest.month, Decimal(0))
    if grocery_current and len(grocery_history) >= 2:
        grocery_average = _average(grocery_history)
        if grocery_current > grocery_average * Decimal("1.1"):
            excess = grocery_current - grocery_average
            signals.append(
                Signal(
                    signal_id="grocery-opportunity",
                    type="grocery_opportunity",
                    severity="warning",
                    ref_period=period,
                    title="O mercado passou da média recente",
                    body=(
                        f"As compras de mercado somam {_brl(grocery_current)}, {_brl(excess)} "
                        "acima da média dos meses com compras identificadas."
                    ),
                    actions=[
                        ActionDraft(
                            description="Usar a média recente como teto para as próximas compras",
                            estimated_impact=excess,
                        )
                    ],
                    evidence={"amount": grocery_current, "historical_average": grocery_average},
                    confidence=0.85,
                    evidence_summary=[
                        f"Mercado no período: {_brl(grocery_current)}",
                        f"Média dos meses anteriores: {_brl(grocery_average)}",
                    ],
                )
            )

    recurring: dict[str, list[ExpensePoint]] = {}
    for point in expenses:
        key = _normalized(point.label)
        if key and key != "despesa" and not any(term in key for term in GROCERY_TERMS):
            recurring.setdefault(key, []).append(point)
    recurring_groups = [
        group
        for group in recurring.values()
        if len({_month(point.date.date()) for point in group}) >= 3
        and max(_month(point.date.date()) for point in group) >= _shift_month(latest.month, -1)
    ]
    for group in sorted(
        recurring_groups, key=lambda points: sum(p.amount for p in points), reverse=True
    )[:2]:
        label = group[0].label
        monthly = {
            month: sum(
                (point.amount for point in group if _month(point.date.date()) == month), Decimal(0)
            )
            for month in {_month(point.date.date()) for point in group}
        }
        average = _average(list(monthly.values()))
        signals.append(
            Signal(
                signal_id=_stable_id("recurring-expense", _normalized(label)),
                type="recurring_expense",
                severity="info",
                ref_period=f"{min(monthly):%Y-%m}–{max(monthly):%Y-%m}",
                title=f"{label} aparece de forma recorrente",
                body=f"O gasto apareceu em {len(monthly)} meses, com média mensal de {_brl(average)}.",
                actions=[
                    ActionDraft(
                        description="Confirmar se esse gasto ainda é necessário",
                        estimated_impact=average,
                    )
                ],
                evidence={"months": len(monthly), "monthly_average": average},
                confidence=0.78,
                evidence_summary=[
                    f"Ocorrência em {len(monthly)} meses",
                    f"Média mensal: {_brl(average)}",
                ],
            )
        )

    if len(trend_months) >= 4:
        recent_income = [month.income for month in trend_months[-4:]]
        if all(recent_income) and all(
            previous > current for previous, current in pairwise(recent_income)
        ):
            loss = recent_income[0] - recent_income[-1]
            signals.append(
                Signal(
                    signal_id="income-decline",
                    type="income_decline",
                    severity="warning",
                    ref_period=f"{trend_months[-4].month:%Y-%m}–{trend_period}",
                    title="A receita caiu por três meses seguidos",
                    body=(
                        f"A entrada mensal recuou de {_brl(recent_income[0])} para "
                        f"{_brl(recent_income[-1])} no período."
                    ),
                    actions=[
                        ActionDraft(
                            description="Revisar as fontes de renda antes de assumir novos compromissos",
                            estimated_impact=loss,
                        )
                    ],
                    evidence={"monthly_income": recent_income, "total_decline": loss},
                    evidence_summary=[
                        f"Receita no início: {_brl(recent_income[0])}",
                        f"Receita no fim: {_brl(recent_income[-1])}",
                    ],
                )
            )

    if len(trend_months) >= 6:
        previous = trend_months[-6:-3]
        recent = trend_months[-3:]
        previous_income = _average([month.income for month in previous])
        previous_expense = _average([month.expense for month in previous])
        recent_income = _average([month.income for month in recent])
        recent_expense = _average([month.expense for month in recent])
        expense_growth = _growth(recent_expense, previous_expense)
        income_growth = _growth(recent_income, previous_income)
        if (
            previous_expense
            and previous_income
            and expense_growth > income_growth
            and expense_growth > 0
        ):
            avoidable = max(Decimal(0), recent_expense - previous_expense)
            signals.append(
                Signal(
                    signal_id="cost-growth",
                    type="cost_growth",
                    severity="warning",
                    ref_period=f"{recent[0].month:%Y-%m}–{trend_period}",
                    title="Os custos avançaram mais que a receita",
                    body=(
                        f"As despesas médias cresceram {expense_growth:.1%}, enquanto a receita "
                        f"variou {income_growth:.1%} entre os dois trimestres."
                    ),
                    actions=[
                        ActionDraft(
                            description="Reduzir o gasto mensal ao nível do trimestre anterior",
                            estimated_impact=avoidable,
                        )
                    ],
                    evidence={
                        "expense_growth": expense_growth,
                        "income_growth": income_growth,
                        "recent_monthly_expense": recent_expense,
                        "previous_monthly_expense": previous_expense,
                    },
                    evidence_summary=[
                        f"Média anterior de despesas: {_brl(previous_expense)}",
                        f"Média recente de despesas: {_brl(recent_expense)}",
                    ],
                )
            )

    efficiency = [
        (month, (month.income - month.expense) / month.income)
        for month in trend_months
        if month.income > 0
    ]
    if len(efficiency) >= 2:
        best_month, best_rate = max(efficiency, key=lambda item: item[1])
        worst_month, worst_rate = min(efficiency, key=lambda item: item[1])
        improvement = max(
            Decimal(0),
            (best_rate - worst_rate) * trend_latest.income if trend_latest.income else Decimal(0),
        )
        signals.append(
            Signal(
                signal_id="efficiency-ranking",
                type="efficiency",
                severity="info",
                ref_period=f"{trend_months[0].month:%Y-%m}–{trend_period}",
                title=f"{best_month.month:%m/%Y} foi o mês mais eficiente",
                body=(
                    f"A taxa de poupança variou de {worst_rate:.1%} em "
                    f"{worst_month.month:%m/%Y} para {best_rate:.1%} em "
                    f"{best_month.month:%m/%Y}."
                ),
                actions=[
                    ActionDraft(
                        description="Repetir os limites de gasto do mês mais eficiente",
                        estimated_impact=improvement,
                    )
                ],
                evidence={
                    "best_month": best_month.month.isoformat(),
                    "best_savings_rate": best_rate,
                    "worst_month": worst_month.month.isoformat(),
                    "worst_savings_rate": worst_rate,
                },
                evidence_summary=[
                    f"Melhor taxa de poupança: {best_rate:.1%} em {best_month.month:%m/%Y}",
                    f"Menor taxa de poupança: {worst_rate:.1%} em {worst_month.month:%m/%Y}",
                ],
            )
        )

    # ponytail: parcelas podem sobrepor despesas bancárias; vincule-as às transações se houver falso alerta.
    recent_net = (
        _average([month.income - month.expense for month in trend_months[-3:]])
        - monthly_debt_payments
    )
    crossing_month = next(
        (offset for offset in range(4) if cash_balance + recent_net * offset < 0),
        None,
    )
    if crossing_month is not None:
        already_negative = crossing_month == 0
        needed = abs(cash_balance) if already_negative else max(Decimal(0), -recent_net)
        signals.append(
            Signal(
                signal_id="cash-flow-risk",
                type="cash_flow_risk",
                severity="critical",
                ref_period=period,
                title="O saldo disponível está negativo"
                if already_negative
                else "O saldo pode cruzar zero",
                body=f"O saldo disponível está em {_brl(cash_balance)}."
                if already_negative
                else (
                    f"Mantido o ritmo médio dos últimos três meses, o saldo disponível de "
                    f"{_brl(cash_balance)} fica negativo em até {crossing_month} "
                    f"{'mês' if crossing_month == 1 else 'meses'}."
                ),
                actions=[
                    ActionDraft(
                        description="Cobrir o saldo negativo e preservar uma margem de segurança"
                        if already_negative
                        else "Equilibrar o fluxo mensal antes do próximo ciclo",
                        estimated_impact=needed,
                    )
                ],
                evidence={
                    "cash_balance": cash_balance,
                    "average_monthly_net": recent_net,
                    "monthly_debt_payments": monthly_debt_payments,
                    "crossing_month": crossing_month,
                },
                evidence_summary=[
                    f"Saldo disponível: {_brl(cash_balance)}",
                    f"Resultado mensal médio após parcelas: {_brl(recent_net)}",
                ],
            )
        )

    priority = {"critical": 0, "warning": 1, "info": 2}
    return sorted(signals, key=lambda signal: priority[signal.severity])


async def _financial_data(
    db: AsyncSession, household_id: uuid.UUID
) -> tuple[list[MonthSummary], list[ExpensePoint], Decimal, Decimal]:
    latest = _month(datetime.now(UTC).date())
    months = [MonthSummary(_shift_month(latest, offset)) for offset in range(-11, 1)]
    by_month = {month.month: month for month in months}
    start = datetime(months[0].month.year, months[0].month.month, 1, tzinfo=UTC)
    end = datetime(_shift_month(latest, 1).year, _shift_month(latest, 1).month, 1, tzinfo=UTC)
    rows = (
        await db.execute(
            select(
                Transaction.id,
                Transaction.date,
                Transaction.amount,
                Transaction.type,
                Transaction.description,
                Transaction.merchant_name,
                Transaction.source,
                Category.name,
                Account.type,
            )
            .outerjoin(Account, Account.id == Transaction.account_id)
            .outerjoin(Invoice, Invoice.id == Transaction.source_invoice_id)
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(
                or_(Account.household_id == household_id, Invoice.household_id == household_id),
                Transaction.status == "posted",
                Transaction.date >= start,
                Transaction.date < end,
            )
        )
    ).all()
    facts: list[TransactionFact] = []
    for (
        transaction_id,
        transaction_date,
        raw_amount,
        transaction_type,
        description,
        merchant,
        source,
        category,
        account_type,
    ) in rows:
        economic_type, confidence = _economic_type(
            transaction_type,
            f"{description} {merchant or ''}",
            category or "",
            source,
            account_type,
        )
        facts.append(
            TransactionFact(
                id=transaction_id,
                date=transaction_date,
                amount=abs(Decimal(raw_amount)),
                transaction_type=transaction_type,
                description=description,
                merchant=merchant,
                category=category or "Sem categoria",
                source=source,
                account_type=account_type,
                economic_type=economic_type,
                confidence=confidence,
            )
        )
    _mark_recurring_salary(facts)
    expenses: list[ExpensePoint] = []
    for fact in facts:
        month = by_month.get(_month(fact.date.date()))
        if month is None:
            continue
        if fact.economic_type in {"salary", "other_income", "benefit"}:
            month.income += fact.amount
            if fact.economic_type == "salary":
                month.salary += fact.amount
            elif fact.economic_type == "benefit":
                month.benefits += fact.amount
            else:
                month.other_income += fact.amount
        elif fact.economic_type in {"expense", "voucher_expense"}:
            if fact.economic_type == "expense":
                month.expense += fact.amount
            else:
                month.voucher_expense += fact.amount
            month.categories[fact.category] = (
                month.categories.get(fact.category, Decimal(0)) + fact.amount
            )
            expenses.append(
                ExpensePoint(
                    fact.date,
                    fact.amount,
                    fact.category,
                    fact.merchant or fact.description,
                    fact.source,
                    fact.id,
                )
            )

    cash_balance = await db.scalar(
        select(func.coalesce(func.sum(Account.balance), 0)).where(
            Account.household_id == household_id, Account.type == "bank"
        )
    )
    monthly_debt_payments = await db.scalar(
        select(func.coalesce(func.sum(Liability.monthly_payment), 0)).where(
            Liability.household_id == household_id
        )
    )
    return (
        months,
        expenses,
        Decimal(cash_balance or 0),
        Decimal(monthly_debt_payments or 0),
    )


async def _narrate(
    signals: list[Signal], *, allow_external_ai: bool = True
) -> tuple[list[Narrative], int, int, str]:
    fallback = [
        Narrative.model_validate(
            signal.model_dump(exclude={"evidence", "confidence", "evidence_summary"})
        )
        for signal in signals
    ]
    if not signals or settings.openai_api_key is None or not allow_external_ai:
        return fallback, 0, 0, "deterministic"

    payload = {
        "model": settings.openai_model,
        "instructions": (
            "Você é um planejador financeiro doméstico. Reescreva e priorize os sinais em "
            "português claro, direto e sem alarmismo. Use somente os fatos e valores recebidos. "
            "Preserve signal_id, type, severity e ref_period. Dê no máximo três ações por sinal."
        ),
        "input": json.dumps(
            [signal.model_dump(mode="json") for signal in signals],
            ensure_ascii=False,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "financial_insights",
                "strict": True,
                "schema": NarrativeBundle.model_json_schema(),
            }
        },
        "store": False,
    }
    try:
        async with httpx.AsyncClient(timeout=None) as client:
            response = await client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
            response.raise_for_status()
        result = response.json()
        text = next(
            content["text"]
            for output in result.get("output", [])
            if output.get("type") == "message"
            for content in output.get("content", [])
            if content.get("type") == "output_text"
        )
        narratives = NarrativeBundle.model_validate_json(text).insights
        known = {signal.signal_id: signal for signal in signals}
        ordered: list[Narrative] = []
        seen: set[str] = set()
        for narrative in narratives:
            signal = known.get(narrative.signal_id)
            if signal is None or narrative.signal_id in seen:
                continue
            ordered.append(
                narrative.model_copy(
                    update={
                        "type": signal.type,
                        "severity": signal.severity,
                        "ref_period": signal.ref_period,
                    }
                )
            )
            seen.add(narrative.signal_id)
        ordered.extend(
            Narrative.model_validate(
                signal.model_dump(exclude={"evidence", "confidence", "evidence_summary"})
            )
            for signal in signals
            if signal.signal_id not in seen
        )
        usage = result.get("usage") or {}
        return (
            ordered,
            int(usage.get("input_tokens") or 0),
            int(usage.get("output_tokens") or 0),
            str(result.get("model") or settings.openai_model),
        )
    except (
        httpx.HTTPError,
        KeyError,
        StopIteration,
        TypeError,
        ValueError,
        ValidationError,
    ):
        return fallback, 0, 0, "deterministic"


def _read(row: Insight) -> InsightRead:
    return InsightRead(
        id=row.id,
        type=row.type,
        severity=row.severity,
        ref_period=row.ref_period,
        title=row.title,
        body=row.body,
        actions=[
            InsightActionRead.model_validate(action) for action in row.payload.get("actions", [])
        ],
        confidence=float(row.payload.get("confidence", 0.9)),
        evidence=list(row.payload.get("evidence_summary", [])),
        model=row.model,
        generated_at=row.generated_at,
    )


async def _cached(db: AsyncSession, household_id: uuid.UUID) -> list[Insight]:
    priority = case(
        (Insight.severity == "critical", 0), (Insight.severity == "warning", 1), else_=2
    )
    return list(
        (
            await db.scalars(
                select(Insight)
                .where(Insight.household_id == household_id, Insight.dismissed_at.is_(None))
                .order_by(priority, Insight.generated_at.desc())
            )
        ).all()
    )


async def refresh_insights(
    db: AsyncSession,
    household_id: uuid.UUID,
    *,
    allow_external_ai: bool = True,
    pending_ai: bool = False,
) -> list[Insight]:
    months, expenses, cash_balance, monthly_debt_payments = await _financial_data(db, household_id)
    signals = calculate_signals(
        months,
        expenses,
        cash_balance,
        monthly_debt_payments,
        current_month_partial=True,
    )
    await db.commit()
    missing_consent = await db.scalar(
        select(func.count())
        .select_from(HouseholdMember)
        .join(User, User.id == HouseholdMember.user_id)
        .where(
            HouseholdMember.household_id == household_id,
            User.ai_consent_at.is_(None),
        )
    )
    narratives, prompt_tokens, completion_tokens, model = await _narrate(
        signals, allow_external_ai=allow_external_ai and not missing_consent
    )
    signal_by_id = {signal.signal_id: signal for signal in signals}

    existing = list(
        (await db.scalars(select(Insight).where(Insight.household_id == household_id))).all()
    )
    existing_by_signal = {
        row.payload.get("signal_id"): row for row in existing if row.payload.get("signal_id")
    }
    current_signal_ids = set(signal_by_id)
    for old_row in existing:
        if (
            old_row.payload.get("signal_id") not in current_signal_ids
            and old_row.dismissed_at is None
        ):
            await db.delete(old_row)

    rows: list[Insight] = []
    for narrative in narratives:
        signal = signal_by_id[narrative.signal_id]
        row = existing_by_signal.get(signal.signal_id)
        if row is None:
            row = Insight(household_id=household_id)
            db.add(row)
        row.type = signal.type
        row.severity = signal.severity
        row.ref_period = signal.ref_period
        row.title = narrative.title
        row.body = narrative.body
        row.payload = {
            "signal_id": signal.signal_id,
            "actions": [action.model_dump(mode="json") for action in narrative.actions],
            "evidence": json.loads(json.dumps(signal.evidence, default=str)),
            "confidence": signal.confidence,
            "evidence_summary": signal.evidence_summary,
        }
        row.model = "pending-ai" if pending_ai else model
        row.generated_at = datetime.now(UTC)
        if row.dismissed_at is None:
            rows.append(row)

    million = Decimal(1_000_000)
    cost = (
        Decimal(prompt_tokens) * settings.openai_input_cost_per_million
        + Decimal(completion_tokens) * settings.openai_output_cost_per_million
    ) / million
    db.add(
        AIRun(
            household_id=household_id,
            purpose="financial_insights",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cost_estimate=cost,
        )
    )
    await db.commit()
    return rows


async def _ai_allowed(db: AsyncSession, household_id: uuid.UUID) -> bool:
    if settings.openai_api_key is None:
        return False
    missing_consent = await db.scalar(
        select(func.count())
        .select_from(HouseholdMember)
        .join(User, User.id == HouseholdMember.user_id)
        .where(
            HouseholdMember.household_id == household_id,
            User.ai_consent_at.is_(None),
        )
    )
    return not missing_consent


async def _enrich_insights_background(household_id: uuid.UUID) -> None:
    async with SessionLocal() as task_db:
        await refresh_insights(task_db, household_id, allow_external_ai=True)


@router.get("")
async def list_insights(
    auth: CurrentAuth, db: DbSession, background_tasks: BackgroundTasks
) -> list[InsightRead]:
    rows = await _cached(db, auth.household.id)
    current_month = _month(datetime.now(UTC).date())
    last_run = await db.scalar(
        select(func.max(AIRun.created_at)).where(
            AIRun.household_id == auth.household.id,
            AIRun.purpose == "financial_insights",
        )
    )
    latest_generation = rows[0].generated_at if rows else last_run
    last_sync = await db.scalar(
        select(func.max(PluggyItem.last_synced_at)).where(
            PluggyItem.household_id == auth.household.id
        )
    )
    last_invoice = await db.scalar(
        select(func.max(Invoice.created_at)).where(Invoice.household_id == auth.household.id)
    )
    latest_source = max((value for value in (last_sync, last_invoice) if value), default=None)
    stale = (
        latest_generation is None
        or _month(latest_generation.date()) < current_month
        or (latest_source is not None and latest_source > latest_generation)
    )
    if stale:
        ai_allowed = await _ai_allowed(db, auth.household.id)
        rows = await refresh_insights(
            db,
            auth.household.id,
            allow_external_ai=False,
            pending_ai=ai_allowed,
        )
        if ai_allowed:
            background_tasks.add_task(_enrich_insights_background, auth.household.id)
    return [_read(row) for row in rows]


@router.post("/refresh")
async def refresh(
    auth: CurrentAuth, db: DbSession, background_tasks: BackgroundTasks
) -> list[InsightRead]:
    ai_allowed = await _ai_allowed(db, auth.household.id)
    rows = await refresh_insights(
        db,
        auth.household.id,
        allow_external_ai=False,
        pending_ai=ai_allowed,
    )
    if ai_allowed:
        background_tasks.add_task(_enrich_insights_background, auth.household.id)
    return [_read(row) for row in rows]


@router.post("/{insight_id}/dismiss")
async def dismiss_insight(insight_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> Message:
    row = await db.scalar(
        select(Insight).where(
            Insight.id == insight_id,
            Insight.household_id == auth.household.id,
        )
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Insight não encontrado")
    row.dismissed_at = datetime.now(UTC)
    await db.commit()
    return Message(message="Insight ocultado")
