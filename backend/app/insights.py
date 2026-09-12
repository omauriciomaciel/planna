import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from decimal import Decimal
from itertools import pairwise
from typing import Literal

import httpx
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from sqlalchemy import case, delete, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentAuth
from app.config import settings
from app.database import DbSession
from app.models import (
    Account,
    AIRun,
    Category,
    HouseholdMember,
    Insight,
    Invoice,
    Liability,
    Transaction,
    User,
)
from app.schemas import InsightActionRead, InsightRead

router = APIRouter(prefix="/insights", tags=["insights"])
Severity = Literal["info", "warning", "critical"]


@dataclass
class MonthSummary:
    month: date
    income: Decimal = Decimal(0)
    expense: Decimal = Decimal(0)
    categories: dict[str, Decimal] = field(default_factory=dict)


@dataclass(frozen=True)
class ExpensePoint:
    date: datetime
    amount: Decimal
    category: str


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


class InsightGenerationError(RuntimeError):
    pass


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


def calculate_signals(
    months: list[MonthSummary],
    expenses: list[ExpensePoint],
    cash_balance: Decimal,
    monthly_debt_payments: Decimal = Decimal(0),
) -> list[Signal]:
    if not months:
        return []

    signals: list[Signal] = []
    latest = months[-1]
    period = latest.month.strftime("%Y-%m")

    category_outliers: list[tuple[str, Decimal, Decimal]] = []
    for category, current in latest.categories.items():
        history = [month.categories.get(category, Decimal(0)) for month in months[:-1]]
        if sum(value > 0 for value in history) < 3:
            continue
        mean = _average(history)
        deviation = (_average([(value - mean) ** 2 for value in history])).sqrt()
        threshold = max(mean + 2 * deviation, mean * Decimal("1.5"))
        if current > threshold:
            category_outliers.append((category, current, mean))

    for index, (category, current, mean) in enumerate(
        sorted(category_outliers, key=lambda item: item[1] - item[2], reverse=True)[:3]
    ):
        excess = current - mean
        signals.append(
            Signal(
                signal_id=f"category-outlier-{index}",
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
            )
        )

    historical_expenses = [point.amount for point in expenses if _month(point.date.date()) < latest.month]
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
        for index, point in enumerate(current_outliers):
            signals.append(
                Signal(
                    signal_id=f"transaction-outlier-{index}",
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
                )
            )

    if len(months) >= 4:
        recent_income = [month.income for month in months[-4:]]
        if all(recent_income) and all(
            previous > current for previous, current in pairwise(recent_income)
        ):
            loss = recent_income[0] - recent_income[-1]
            signals.append(
                Signal(
                    signal_id="income-decline",
                    type="income_decline",
                    severity="warning",
                    ref_period=f"{months[-4].month:%Y-%m}–{period}",
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
                )
            )

    if len(months) >= 6:
        previous = months[-6:-3]
        recent = months[-3:]
        previous_income = _average([month.income for month in previous])
        previous_expense = _average([month.expense for month in previous])
        recent_income = _average([month.income for month in recent])
        recent_expense = _average([month.expense for month in recent])
        expense_growth = _growth(recent_expense, previous_expense)
        income_growth = _growth(recent_income, previous_income)
        if previous_expense and previous_income and expense_growth > income_growth and expense_growth > 0:
            avoidable = max(Decimal(0), recent_expense - previous_expense)
            signals.append(
                Signal(
                    signal_id="cost-growth",
                    type="cost_growth",
                    severity="warning",
                    ref_period=f"{recent[0].month:%Y-%m}–{period}",
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
                )
            )

    efficiency = [
        (month, (month.income - month.expense) / month.income)
        for month in months
        if month.income > 0
    ]
    if len(efficiency) >= 2:
        best_month, best_rate = max(efficiency, key=lambda item: item[1])
        worst_month, worst_rate = min(efficiency, key=lambda item: item[1])
        improvement = max(
            Decimal(0),
            (best_rate - worst_rate) * latest.income if latest.income else Decimal(0),
        )
        signals.append(
            Signal(
                signal_id="efficiency-ranking",
                type="efficiency",
                severity="info",
                ref_period=f"{months[0].month:%Y-%m}–{period}",
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
            )
        )

    # ponytail: parcelas podem sobrepor despesas bancárias; vincule-as às transações se houver falso alerta.
    recent_net = (
        _average([month.income - month.expense for month in months[-3:]])
        - monthly_debt_payments
    )
    crossing_month = next(
        (
            offset
            for offset in range(4)
            if cash_balance + recent_net * offset < 0
        ),
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
            )
        )

    priority = {"critical": 0, "warning": 1, "info": 2}
    return sorted(signals, key=lambda signal: priority[signal.severity])


async def _financial_data(
    db: AsyncSession, household_id: uuid.UUID
) -> tuple[list[MonthSummary], list[ExpensePoint], Decimal, Decimal]:
    latest = _shift_month(_month(datetime.now(UTC).date()), -1)
    months = [MonthSummary(_shift_month(latest, offset)) for offset in range(-11, 1)]
    by_month = {month.month: month for month in months}
    start = datetime(months[0].month.year, months[0].month.month, 1, tzinfo=UTC)
    end = datetime(_shift_month(latest, 1).year, _shift_month(latest, 1).month, 1, tzinfo=UTC)
    rows = (
        await db.execute(
            select(Transaction.date, Transaction.amount, Transaction.type, Category.name)
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
    expenses: list[ExpensePoint] = []
    for transaction_date, raw_amount, transaction_type, category in rows:
        month = by_month.get(_month(transaction_date.date()))
        if month is None:
            continue
        amount = abs(Decimal(raw_amount))
        if transaction_type == "credit":
            month.income += amount
        else:
            name = category or "Sem categoria"
            month.expense += amount
            month.categories[name] = month.categories.get(name, Decimal(0)) + amount
            expenses.append(ExpensePoint(transaction_date, amount, name))

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
    if not signals or settings.openai_api_key is None or not allow_external_ai:
        return [Narrative.model_validate(signal.model_dump(exclude={"evidence"})) for signal in signals], 0, 0, "deterministic"

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
        async with httpx.AsyncClient(timeout=30) as client:
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
            Narrative.model_validate(signal.model_dump(exclude={"evidence"}))
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
    except (httpx.HTTPError, KeyError, StopIteration, TypeError, ValueError, ValidationError) as exc:
        raise InsightGenerationError("A geração de insights pela OpenAI falhou") from exc


def _read(row: Insight) -> InsightRead:
    return InsightRead(
        id=row.id,
        type=row.type,
        severity=row.severity,
        ref_period=row.ref_period,
        title=row.title,
        body=row.body,
        actions=[
            InsightActionRead.model_validate(action)
            for action in row.payload.get("actions", [])
        ],
        model=row.model,
        generated_at=row.generated_at,
    )


async def _cached(db: AsyncSession, household_id: uuid.UUID) -> list[Insight]:
    priority = case((Insight.severity == "critical", 0), (Insight.severity == "warning", 1), else_=2)
    return list(
        (
            await db.scalars(
                select(Insight)
                .where(Insight.household_id == household_id, Insight.dismissed_at.is_(None))
                .order_by(priority, Insight.generated_at.desc())
            )
        ).all()
    )


async def refresh_insights(db: AsyncSession, household_id: uuid.UUID) -> list[Insight]:
    months, expenses, cash_balance, monthly_debt_payments = await _financial_data(
        db, household_id
    )
    signals = calculate_signals(months, expenses, cash_balance, monthly_debt_payments)
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
        signals, allow_external_ai=not missing_consent
    )
    signal_by_id = {signal.signal_id: signal for signal in signals}

    await db.execute(delete(Insight).where(Insight.household_id == household_id))
    rows: list[Insight] = []
    for narrative in narratives:
        signal = signal_by_id[narrative.signal_id]
        row = Insight(
            household_id=household_id,
            type=signal.type,
            severity=signal.severity,
            ref_period=signal.ref_period,
            title=narrative.title,
            body=narrative.body,
            payload={
                "signal_id": signal.signal_id,
                "actions": [action.model_dump(mode="json") for action in narrative.actions],
                "evidence": json.loads(json.dumps(signal.evidence, default=str)),
            },
            model=model,
        )
        db.add(row)
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


@router.get("")
async def list_insights(auth: CurrentAuth, db: DbSession) -> list[InsightRead]:
    rows = await _cached(db, auth.household.id)
    current_month = _month(datetime.now(UTC).date())
    last_run = await db.scalar(
        select(func.max(AIRun.created_at)).where(
            AIRun.household_id == auth.household.id,
            AIRun.purpose == "financial_insights",
        )
    )
    latest_generation = rows[0].generated_at if rows else last_run
    stale = latest_generation is None or _month(latest_generation.date()) < current_month
    if stale:
        try:
            rows = await refresh_insights(db, auth.household.id)
        except InsightGenerationError:
            if not rows:
                raise HTTPException(status_code=503, detail="Não foi possível gerar os insights")
    return [_read(row) for row in rows]


@router.post("/refresh")
async def refresh(auth: CurrentAuth, db: DbSession) -> list[InsightRead]:
    try:
        rows = await refresh_insights(db, auth.household.id)
    except InsightGenerationError as exc:
        raise HTTPException(status_code=503, detail="Não foi possível gerar os insights") from exc
    return [_read(row) for row in rows]
