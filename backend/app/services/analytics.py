import uuid
from datetime import date, timedelta
from decimal import Decimal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.transaction import TransactionType
from app.repositories.credit_purchase import CreditPurchaseRepository
from app.repositories.transaction import TransactionRepository
from app.repositories.user_settings import UserSettingsRepository

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
    transaction_repo: TransactionRepository,
    credit_purchase_repo: CreditPurchaseRepository,
    user_id: uuid.UUID,
    year: int,
    month: int,
) -> tuple[Decimal, Decimal, dict[str, Decimal]]:
    rows = await transaction_repo.get_month_with_categories(user_id, year, month)

    income = Decimal("0")
    expenses = Decimal("0")
    category_totals: dict[str, Decimal] = {}

    for tx, cat_name in rows:
        if tx.type == TransactionType.INCOME:
            income += tx.amount
        else:
            expenses += tx.amount
            label = cat_name or "Sem categoria"
            category_totals[label] = category_totals.get(label, Decimal("0")) + tx.amount

    cp_rows = await credit_purchase_repo.get_month_with_categories(user_id, year, month)
    for cp, cat_name in cp_rows:
        expenses += cp.installment_amount
        label = cat_name or "Sem categoria"
        category_totals[label] = category_totals.get(label, Decimal("0")) + cp.installment_amount

    return income, expenses, category_totals


class AnalyticsService:
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        credit_purchase_repo: CreditPurchaseRepository,
        settings_repo: UserSettingsRepository,
    ):
        self.transaction_repo = transaction_repo
        self.credit_purchase_repo = credit_purchase_repo
        self.settings_repo = settings_repo

    async def get_sankey_data(
        self,
        user_id: uuid.UUID,
        year: int,
        month: int,
    ) -> dict:
        settings = await self.settings_repo.get_for_user(user_id)
        ignore_invoice_payment = settings.ignore_invoice_payment

        rows = await self.transaction_repo.get_month_with_categories(user_id, year, month)

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

        cp_rows = await self.credit_purchase_repo.get_month_with_categories(user_id, year, month)
        for cp, cat_name in cp_rows:
            label = cat_name or "Sem categoria"
            categories[label] = categories.get(label, Decimal("0")) + cp.installment_amount

        return {
            "income": float(income_total),
            "categories": {k: float(v) for k, v in categories.items()},
        }

    async def get_monthly_closing(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> dict:
        income, expenses, category_totals = await _compute_month_totals(
            self.transaction_repo, self.credit_purchase_repo, user_id, year, month
        )

        prev_month = month - 1 if month > 1 else 12
        prev_year = year if month > 1 else year - 1
        prev_income, prev_expenses, _ = await _compute_month_totals(
            self.transaction_repo, self.credit_purchase_repo, user_id, prev_year, prev_month
        )

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
        self, user_id: uuid.UUID, year: int, month: int, n: int = 6
    ) -> list[dict]:
        result = []
        for i in range(n - 1, -1, -1):
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1

            income, expenses, _ = await _compute_month_totals(
                self.transaction_repo, self.credit_purchase_repo, user_id, y, m
            )
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

    async def get_credit_analytics(
        self, user_id: uuid.UUID, year: int, month: int, n: int = 6
    ) -> dict:
        """Credit-specific analytics: spending by card, monthly history, commitment."""
        # Build month range for the last N months
        months = []
        for i in range(n - 1, -1, -1):
            m = month - i
            y = year
            while m <= 0:
                m += 12
                y -= 1
            months.append((y, m))

        first_y, first_m = months[0]
        start = date(first_y, first_m, 1)
        # End: first day of month after last
        last_y, last_m = months[-1]
        if last_m == 12:
            end = date(last_y + 1, 1, 1)
        else:
            end = date(last_y, last_m + 1, 1)

        # Credit totals by card by month
        card_rows = await self.credit_purchase_repo.get_monthly_totals_by_card(
            user_id, start, end
        )

        # Build per-month data
        history = []
        for y, m in months:
            label = f"{MONTH_ABBR[m - 1]}/{str(y)[2:]}"

            # Credit total for this month
            credit_total = Decimal("0")
            cards_breakdown: dict[str, float] = {}
            for row in card_rows:
                if int(row.yr) == y and int(row.mo) == m:
                    amt = float(row.total)
                    card_name = row.card_name or "Sem cartão"
                    cards_breakdown[card_name] = amt
                    credit_total += row.total

            # Income for commitment calculation
            tx_rows = await self.transaction_repo.get_month_with_categories(
                user_id, y, m
            )
            income = Decimal("0")
            expenses = Decimal("0")
            for tx, _ in tx_rows:
                if tx.type == TransactionType.INCOME:
                    income += tx.amount
                else:
                    expenses += tx.amount

            total_expenses = expenses + credit_total
            commitment = (
                float(total_expenses / income) if income > 0 else 0.0
            )

            history.append({
                "month": m,
                "year": y,
                "label": label,
                "credit_total": float(credit_total),
                "income": float(income),
                "expenses": float(expenses),
                "balance": float(income - total_expenses),
                "commitment": commitment,
                "cards": cards_breakdown,
            })

        # Current month summary
        current = history[-1] if history else None

        # Unique card names across all months for consistent chart series
        all_cards = sorted({
            card_name
            for item in history
            for card_name in item["cards"]
        })

        return {
            "history": history,
            "cards": all_cards,
            "current_month": current,
        }

    async def detect_outliers(
        self, user_id: uuid.UUID, year: int, month: int
    ) -> list[dict]:
        target = date(year, month, 1)
        start = date(year - 1, month, 1)

        rows = await self.transaction_repo.get_expense_category_monthly(
            user_id, start, target + timedelta(days=31)
        )

        cat_monthly: dict[str, list[float]] = {}
        cat_current: dict[str, float] = {}

        for row in rows:
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


def get_transaction_repository(
    db: AsyncSession = Depends(get_db),
) -> TransactionRepository:
    return TransactionRepository(db)


def get_credit_purchase_repository(
    db: AsyncSession = Depends(get_db),
) -> CreditPurchaseRepository:
    return CreditPurchaseRepository(db)


def get_user_settings_repository(
    db: AsyncSession = Depends(get_db),
) -> UserSettingsRepository:
    return UserSettingsRepository(db)


def get_analytics_service(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    credit_purchase_repo: CreditPurchaseRepository = Depends(get_credit_purchase_repository),
    settings_repo: UserSettingsRepository = Depends(get_user_settings_repository),
) -> AnalyticsService:
    return AnalyticsService(transaction_repo, credit_purchase_repo, settings_repo)
