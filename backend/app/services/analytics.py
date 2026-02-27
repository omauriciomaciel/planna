import uuid
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.category import Category
from app.models.credit_purchase import CreditPurchase
from app.models.transaction import Transaction, TransactionType

MONTH_ABBR = ["jan", "fev", "mar", "abr", "mai", "jun",
              "jul", "ago", "set", "out", "nov", "dez"]


def calculate_iqr(values: list[float]) -> dict | None:
    """Calculate IQR statistics. Returns None if fewer than 4 values."""
    if len(values) < 4:
        return None

    sorted_vals = sorted(values)
    n = len(sorted_vals)

    q1_idx = n // 4
    q3_idx = (3 * n) // 4

    q1 = sorted_vals[q1_idx]
    q3 = sorted_vals[q3_idx]
    iqr = q3 - q1
    upper = q3 + 1.5 * iqr

    return {"q1": q1, "q3": q3, "iqr": iqr, "upper": upper}


async def _compute_month_totals(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
) -> tuple[Decimal, Decimal, dict[str, Decimal]]:
    """Compute income, expenses, and category totals for a given month."""
    result = await db.execute(
        select(Transaction, Category.name.label("category_name"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )
    )

    income = Decimal("0")
    expenses = Decimal("0")
    category_totals: dict[str, Decimal] = {}

    for tx, cat_name in result.all():
        if tx.type == TransactionType.INCOME:
            income += tx.amount
        else:
            expenses += tx.amount
            label = cat_name or "Sem categoria"
            category_totals[label] = category_totals.get(label, Decimal("0")) + tx.amount

    cp_result = await db.execute(
        select(CreditPurchase, Category.name.label("category_name"))
        .outerjoin(Category, CreditPurchase.category_id == Category.id)
        .where(
            CreditPurchase.user_id == user_id,
            extract("year", CreditPurchase.due_date) == year,
            extract("month", CreditPurchase.due_date) == month,
        )
    )
    for cp, cat_name in cp_result.all():
        expenses += cp.installment_amount
        label = cat_name or "Sem categoria"
        category_totals[label] = category_totals.get(label, Decimal("0")) + cp.installment_amount

    return income, expenses, category_totals


async def get_sankey_data(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
    ignore_invoice_payment: bool = False,
) -> dict:
    """Get income/expense data for Sankey chart."""
    result = await db.execute(
        select(Transaction, Category.name.label("category_name"))
        .outerjoin(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            extract("year", Transaction.date) == year,
            extract("month", Transaction.date) == month,
        )
    )
    rows = result.all()

    income_total = Decimal("0")
    categories: dict[str, Decimal] = {}

    for tx, cat_name in rows:
        if tx.type == TransactionType.INCOME:
            income_total += tx.amount
        else:
            label = cat_name or "Sem categoria"
            if ignore_invoice_payment and "Pagamento Fatura" in label:
                continue
            categories[label] = categories.get(label, Decimal("0")) + tx.amount

    cp_result = await db.execute(
        select(CreditPurchase, Category.name.label("category_name"))
        .outerjoin(Category, CreditPurchase.category_id == Category.id)
        .where(
            CreditPurchase.user_id == user_id,
            extract("year", CreditPurchase.due_date) == year,
            extract("month", CreditPurchase.due_date) == month,
        )
    )
    for cp, cat_name in cp_result.all():
        label = cat_name or "Sem categoria"
        categories[label] = categories.get(label, Decimal("0")) + cp.installment_amount

    return {
        "income": float(income_total),
        "categories": {k: float(v) for k, v in categories.items()},
    }


async def get_monthly_closing(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
) -> dict:
    """Calculate monthly closing summary with previous month comparison."""
    income, expenses, category_totals = await _compute_month_totals(db, user_id, year, month)

    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    prev_income, prev_expenses, _ = await _compute_month_totals(db, user_id, prev_year, prev_month)

    balance = income - expenses
    prev_balance = prev_income - prev_expenses
    commitment_rate = float(expenses / income) if income > 0 else 0.0

    top_categories = sorted(category_totals.items(), key=lambda x: x[1], reverse=True)[:5]
    total_exp = float(expenses)

    return {
        "income": float(income),
        "expenses": float(expenses),
        "balance": float(balance),
        "prev_income": float(prev_income),
        "prev_expenses": float(prev_expenses),
        "prev_balance": float(prev_balance),
        "commitment_rate": commitment_rate,
        "top_categories": [
            {
                "name": k,
                "amount": float(v),
                "pct": float(v) / total_exp if total_exp > 0 else 0.0,
            }
            for k, v in top_categories
        ],
    }


async def get_monthly_history(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
    n: int = 6,
) -> list[dict]:
    """Return last n months of income/expenses/balance ending at (year, month)."""
    result = []
    for i in range(n - 1, -1, -1):
        m = month - i
        y = year
        while m <= 0:
            m += 12
            y -= 1

        income, expenses, _ = await _compute_month_totals(db, user_id, y, m)
        balance = income - expenses
        label = f"{MONTH_ABBR[m - 1]}/{str(y)[2:]}"

        result.append({
            "month": m,
            "year": y,
            "label": label,
            "income": float(income),
            "expenses": float(expenses),
            "balance": float(balance),
        })

    return result


async def detect_outliers(
    db: AsyncSession,
    user_id: uuid.UUID,
    year: int,
    month: int,
) -> list[dict]:
    """Detect expense outliers by category using IQR method."""
    target = date(year, month, 1)
    start = date(year - 1, month, 1)

    result = await db.execute(
        select(
            Category.name,
            extract("year", Transaction.date).label("yr"),
            extract("month", Transaction.date).label("mo"),
            func.sum(Transaction.amount).label("total"),
        )
        .join(Category, Transaction.category_id == Category.id)
        .where(
            Transaction.user_id == user_id,
            Transaction.type == TransactionType.EXPENSE,
            Transaction.date >= start,
            Transaction.date < target + timedelta(days=31),
        )
        .group_by(Category.name, "yr", "mo")
    )

    cat_monthly: dict[str, list[float]] = {}
    cat_current: dict[str, float] = {}

    for row in result.all():
        cat_name = row[0]
        yr, mo, total = int(row[1]), int(row[2]), float(row[3])
        if cat_name not in cat_monthly:
            cat_monthly[cat_name] = []
        if yr == year and mo == month:
            cat_current[cat_name] = total
        cat_monthly[cat_name].append(total)

    outliers = []
    for cat_name, values in cat_monthly.items():
        stats = calculate_iqr(values)
        if not stats:
            continue
        current = cat_current.get(cat_name, 0)
        if current > stats["upper"]:
            outliers.append({
                "category": cat_name,
                "expected": stats["q3"],
                "upper_bound": stats["upper"],
                "actual": current,
            })

    return outliers
