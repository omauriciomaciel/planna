import base64
import binascii
import secrets
import uuid
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated, Any

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query, status
from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentAuth
from app.config import settings
from app.database import DbSession, SessionLocal
from app.models import (
    Account,
    AccountBalanceSnapshot,
    Category,
    HouseholdMember,
    PluggyItem,
    Transaction,
    User,
)
from app.pluggy import PluggyUnavailable, client, transaction_values
from app.schemas import (
    AccountRead,
    CategoryCreate,
    CategoryExpenseRead,
    CategoryRead,
    KpiRead,
    KpisRead,
    Message,
    PluggyConnectTokenRead,
    PluggyItemCreate,
    SyncRead,
    SyncRequest,
    TransactionCategoryUpdate,
    TransactionPage,
    TransactionRead,
    TrendRead,
)

router = APIRouter(tags=["finance"])


def variation(current: Decimal, previous: Decimal) -> float | None:
    return float((current - previous) / abs(previous)) if previous else None


def encode_cursor(value: datetime, row_id: uuid.UUID) -> str:
    return base64.urlsafe_b64encode(f"{value.isoformat()}|{row_id}".encode()).decode()


def decode_cursor(value: str) -> tuple[datetime, uuid.UUID]:
    try:
        raw_date, raw_id = base64.urlsafe_b64decode(value).decode().split("|", 1)
        cursor_date = datetime.fromisoformat(raw_date)
        if cursor_date.tzinfo is None:
            raise ValueError
        return cursor_date, uuid.UUID(raw_id)
    except (binascii.Error, ValueError, UnicodeDecodeError) as exc:
        raise HTTPException(status_code=400, detail="Cursor inválido") from exc


def date_bounds(date_from: date | None, date_to: date | None) -> tuple[date, date]:
    today = datetime.now(UTC).date()
    start = date_from or today.replace(day=1)
    end = date_to or today
    if start > end:
        raise HTTPException(status_code=422, detail="Período inválido")
    return start, end


async def _category(db: AsyncSession, data: dict[str, Any]) -> Category | None:
    external_id = data.get("categoryId")
    name = data.get("category")
    if not external_id and not name:
        return None
    kind = "expense" if str(data.get("type", "DEBIT")).upper() == "DEBIT" else "income"
    category = await db.scalar(
        select(Category).where(Category.external_id == str(external_id))
        if external_id
        else select(Category).where(
            Category.household_id.is_(None), Category.name == str(name), Category.kind == kind
        )
    )
    if category:
        return category
    category = Category(
        name=str(name or "Sem categoria")[:100],
        kind=kind,
        is_system=True,
        external_id=str(external_id) if external_id else None,
    )
    db.add(category)
    await db.flush()
    return category


async def _upsert_item(
    db: AsyncSession, item_data: dict[str, Any], household_id: uuid.UUID, member_id: uuid.UUID
) -> PluggyItem:
    external_id = str(item_data["id"])
    item = await db.scalar(select(PluggyItem).where(PluggyItem.pluggy_item_id == external_id))
    if item and item.household_id != household_id:
        raise HTTPException(status_code=403, detail="Conexão pertence a outro household")
    connector = item_data.get("connector") or {}
    if item is None:
        item = PluggyItem(
            household_id=household_id,
            member_id=member_id,
            pluggy_item_id=external_id,
        )
        db.add(item)
    item.connector_id = str(connector.get("id") or item_data.get("connectorId") or "") or None
    item.institution_name = str(connector.get("name") or item.institution_name or "Instituição")
    item.status = str(item_data.get("status") or "UPDATING")
    item.execution_status = item_data.get("executionStatus")
    error = item_data.get("error")
    item.error = str(error.get("message") if isinstance(error, dict) else error)[:500] if error else None
    await db.flush()
    return item


async def sync_one(db: AsyncSession, item: PluggyItem) -> SyncRead:
    item_data = await client.item(item.pluggy_item_id)
    await _upsert_item(db, item_data, item.household_id, item.member_id)
    account_count = transaction_count = 0
    for raw_account in await client.accounts(item.pluggy_item_id):
        external_id = str(raw_account["id"])
        account = await db.scalar(
            select(Account).where(Account.pluggy_account_id == external_id)
        )
        if account is None:
            account = Account(
                household_id=item.household_id,
                member_id=item.member_id,
                item_id=item.id,
                pluggy_account_id=external_id,
            )
            db.add(account)
        credit_data = raw_account.get("creditData") or {}
        raw_type = str(raw_account.get("type", "BANK")).lower()
        account.type = raw_type if raw_type in {"bank", "credit", "investment"} else "bank"
        account.subtype = raw_account.get("subtype")
        account.name = str(raw_account.get("marketingName") or raw_account.get("name") or "Conta")[:160]
        account.number_masked = raw_account.get("number")
        account.balance = Decimal(str(raw_account.get("balance") or 0))
        account.currency = str(raw_account.get("currencyCode") or "BRL")[:3]
        account.credit_limit = (
            Decimal(str(credit_data["creditLimit"])) if credit_data.get("creditLimit") is not None else None
        )
        due_date = credit_data.get("balanceDueDate")
        account.due_day = int(str(due_date)[-2:]) if due_date else None
        await db.flush()
        account_count += 1
        for raw_transaction in await client.transactions(external_id):
            external_transaction_id = str(raw_transaction["id"])
            transaction = await db.scalar(
                select(Transaction).where(
                    Transaction.pluggy_transaction_id == external_transaction_id
                )
            )
            if transaction is None:
                transaction = Transaction(
                    account_id=account.id,
                    pluggy_transaction_id=external_transaction_id,
                )
                db.add(transaction)
            category = await _category(db, raw_transaction)
            for field, value in transaction_values(raw_transaction).items():
                setattr(transaction, field, value)
            transaction.category_id = category.id if category else None
            transaction_count += 1
        db.add(AccountBalanceSnapshot(account_id=account.id, balance=account.balance))
    item.last_synced_at = datetime.now(UTC)
    await db.commit()
    return SyncRead(items=1, accounts=account_count, transactions=transaction_count)


async def _sync_webhook(payload: dict[str, Any]) -> None:
    # ponytail: in-process webhook work; use a durable queue when missed retries become observable.
    item_id = str(payload.get("itemId") or "")
    if not item_id:
        return
    async with SessionLocal() as db:
        item = await db.scalar(select(PluggyItem).where(PluggyItem.pluggy_item_id == item_id))
        if item is None:
            item_data = await client.item(item_id)
            try:
                member_id = uuid.UUID(str(item_data.get("clientUserId")))
            except ValueError:
                return
            household_id = await db.scalar(
                select(HouseholdMember.household_id).where(HouseholdMember.user_id == member_id)
            )
            if household_id is None:
                return
            item = await _upsert_item(db, item_data, household_id, member_id)
        if payload.get("event") in {"item/created", "item/updated", "transactions/created", "transactions/updated"}:
            await sync_one(db, item)


@router.post("/pluggy/connect-token")
async def connect_token(auth: CurrentAuth) -> PluggyConnectTokenRead:
    try:
        token = await client.create_connect_token(str(auth.user.id))
    except (PluggyUnavailable, httpx.HTTPError) as exc:
        raise HTTPException(status_code=503, detail="Pluggy indisponível") from exc
    return PluggyConnectTokenRead(access_token=token)


@router.post("/pluggy/items")
async def register_item(payload: PluggyItemCreate, auth: CurrentAuth, db: DbSession) -> SyncRead:
    try:
        item_data = await client.item(str(payload.item_id))
        linked_user = item_data.get("clientUserId")
        if linked_user and linked_user != str(auth.user.id):
            raise HTTPException(status_code=403, detail="Conexão pertence a outro membro")
        item = await _upsert_item(db, item_data, auth.household.id, auth.user.id)
        return await sync_one(db, item)
    except HTTPException:
        raise
    except (PluggyUnavailable, httpx.HTTPError) as exc:
        raise HTTPException(status_code=503, detail="Não foi possível sincronizar a conexão") from exc


@router.post("/pluggy/sync")
async def sync(payload: SyncRequest, auth: CurrentAuth, db: DbSession) -> SyncRead:
    query = select(PluggyItem).where(PluggyItem.household_id == auth.household.id)
    if payload.item_id:
        query = query.where(PluggyItem.id == payload.item_id)
    items = (await db.scalars(query)).all()
    total = SyncRead(items=0, accounts=0, transactions=0)
    try:
        for item in items:
            result = await sync_one(db, item)
            total.items += result.items
            total.accounts += result.accounts
            total.transactions += result.transactions
    except (PluggyUnavailable, httpx.HTTPError) as exc:
        raise HTTPException(status_code=503, detail="Pluggy indisponível") from exc
    return total


@router.post("/webhooks/pluggy", status_code=status.HTTP_202_ACCEPTED)
async def pluggy_webhook(
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
    token: Annotated[str | None, Query()] = None,
) -> Message:
    if not settings.pluggy_webhook_secret or not token or not secrets.compare_digest(
        token, settings.pluggy_webhook_secret
    ):
        raise HTTPException(status_code=401, detail="Webhook não autorizado")
    background_tasks.add_task(_sync_webhook, payload)
    return Message(message="Evento recebido")


@router.get("/accounts")
async def accounts(
    auth: CurrentAuth,
    db: DbSession,
    member_id: Annotated[uuid.UUID | None, Query()] = None,
) -> list[AccountRead]:
    query = (
        select(Account, User.name, PluggyItem.institution_name, PluggyItem.last_synced_at)
        .join(User, User.id == Account.member_id)
        .join(PluggyItem, PluggyItem.id == Account.item_id)
        .where(Account.household_id == auth.household.id)
        .order_by(Account.name)
    )
    if member_id:
        query = query.where(Account.member_id == member_id)
    return [
        AccountRead(
            id=account.id,
            member_id=account.member_id,
            member_name=member_name,
            institution_name=institution,
            name=account.name,
            type=account.type,
            subtype=account.subtype,
            number_masked=account.number_masked,
            balance=account.balance,
            currency=account.currency,
            credit_limit=account.credit_limit,
            last_synced_at=last_synced_at,
        )
        for account, member_name, institution, last_synced_at in (await db.execute(query)).all()
    ]


@router.get("/categories")
async def categories(auth: CurrentAuth, db: DbSession) -> list[CategoryRead]:
    rows = (
        await db.scalars(
            select(Category)
            .where(or_(Category.household_id.is_(None), Category.household_id == auth.household.id))
            .order_by(Category.name)
        )
    ).all()
    return [CategoryRead(id=row.id, name=row.name, kind=row.kind, is_system=row.is_system) for row in rows]


@router.post("/categories", status_code=status.HTTP_201_CREATED)
async def create_category(payload: CategoryCreate, auth: CurrentAuth, db: DbSession) -> CategoryRead:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status_code=422, detail="Nome da categoria é obrigatório")
    category = Category(
        household_id=auth.household.id,
        name=name,
        kind=payload.kind,
        is_system=False,
    )
    db.add(category)
    await db.commit()
    return CategoryRead(id=category.id, name=category.name, kind=category.kind, is_system=False)


def _transaction_query(household_id: uuid.UUID):
    return (
        select(Transaction, Account.name, Account.member_id, User.name, Category.name)
        .join(Account, Account.id == Transaction.account_id)
        .join(User, User.id == Account.member_id)
        .outerjoin(Category, Category.id == Transaction.category_id)
        .where(Account.household_id == household_id)
    )


@router.get("/transactions")
async def transactions(
    auth: CurrentAuth,
    db: DbSession,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
    search: Annotated[str | None, Query(max_length=100)] = None,
    category_id: Annotated[uuid.UUID | None, Query()] = None,
    account_id: Annotated[uuid.UUID | None, Query()] = None,
    member_id: Annotated[uuid.UUID | None, Query()] = None,
    type: Annotated[str | None, Query(pattern="^(debit|credit)$")] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> TransactionPage:
    start, end = date_bounds(date_from, date_to)
    query = _transaction_query(auth.household.id).where(
        Transaction.date >= datetime.combine(start, time.min, UTC),
        Transaction.date < datetime.combine(end + timedelta(days=1), time.min, UTC),
    )
    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(Transaction.description.ilike(term), Transaction.merchant_name.ilike(term))
        )
    for column, value in (
        (Transaction.category_id, category_id),
        (Transaction.account_id, account_id),
        (Account.member_id, member_id),
        (Transaction.type, type),
    ):
        if value is not None:
            query = query.where(column == value)
    if cursor:
        cursor_date, cursor_id = decode_cursor(cursor)
        query = query.where(
            or_(
                Transaction.date < cursor_date,
                and_(Transaction.date == cursor_date, Transaction.id < cursor_id),
            )
        )
    rows = (await db.execute(query.order_by(Transaction.date.desc(), Transaction.id.desc()).limit(limit + 1))).all()
    has_more = len(rows) > limit
    rows = rows[:limit]
    items = [
        TransactionRead(
            id=row.id,
            date=row.date,
            description=row.description,
            merchant_name=row.merchant_name,
            amount=row.amount,
            type=row.type,
            status=row.status,
            source=row.source,
            category_id=row.category_id,
            category_name=category_name,
            account_id=row.account_id,
            account_name=account_name,
            member_id=row_member_id,
            member_name=member_name,
            installment_current=row.installment_current,
            installment_total=row.installment_total,
        )
        for row, account_name, row_member_id, member_name, category_name in rows
    ]
    next_cursor = encode_cursor(items[-1].date, items[-1].id) if has_more and items else None
    return TransactionPage(items=items, next_cursor=next_cursor)


@router.patch("/transactions/{transaction_id}/category")
async def update_transaction_category(
    transaction_id: uuid.UUID,
    payload: TransactionCategoryUpdate,
    auth: CurrentAuth,
    db: DbSession,
) -> Message:
    transaction = await db.scalar(
        select(Transaction)
        .join(Account, Account.id == Transaction.account_id)
        .where(Transaction.id == transaction_id, Account.household_id == auth.household.id)
    )
    if transaction is None:
        raise HTTPException(status_code=404, detail="Transação não encontrada")
    if payload.category_id is not None:
        allowed = await db.scalar(
            select(Category.id).where(
                Category.id == payload.category_id,
                or_(Category.household_id.is_(None), Category.household_id == auth.household.id),
            )
        )
        if allowed is None:
            raise HTTPException(status_code=422, detail="Categoria inválida")
    transaction.category_id = payload.category_id
    await db.commit()
    return Message(message="Categoria atualizada")


async def _totals(db: AsyncSession, household_id: uuid.UUID, start: date, end: date) -> tuple[Decimal, Decimal]:
    income, expense = (
        await db.execute(
            select(
                func.coalesce(func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), 0),
                func.coalesce(func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)), 0),
            )
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Account.household_id == household_id,
                Transaction.date >= datetime.combine(start, time.min, UTC),
                Transaction.date < datetime.combine(end + timedelta(days=1), time.min, UTC),
            )
        )
    ).one()
    return Decimal(income), Decimal(expense)


async def _net_worth_at(
    db: AsyncSession, household_id: uuid.UUID, end: date
) -> Decimal | None:
    cutoff = datetime.combine(end + timedelta(days=1), time.min, UTC)
    latest = (
        select(
            AccountBalanceSnapshot.account_id,
            func.max(AccountBalanceSnapshot.recorded_at).label("recorded_at"),
        )
        .join(Account, Account.id == AccountBalanceSnapshot.account_id)
        .where(Account.household_id == household_id, AccountBalanceSnapshot.recorded_at < cutoff)
        .group_by(AccountBalanceSnapshot.account_id)
        .subquery()
    )
    value = await db.scalar(
        select(
            func.sum(
                case(
                    (Account.type == "credit", -AccountBalanceSnapshot.balance),
                    else_=AccountBalanceSnapshot.balance,
                )
            )
        )
        .join(Account, Account.id == AccountBalanceSnapshot.account_id)
        .join(
            latest,
            and_(
                latest.c.account_id == AccountBalanceSnapshot.account_id,
                latest.c.recorded_at == AccountBalanceSnapshot.recorded_at,
            ),
        )
    )
    return Decimal(value) if value is not None else None


@router.get("/analytics/kpis")
async def kpis(
    auth: CurrentAuth,
    db: DbSession,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> KpisRead:
    start, end = date_bounds(date_from, date_to)
    days = (end - start).days + 1
    previous_end = start - timedelta(days=1)
    previous_start = previous_end - timedelta(days=days - 1)
    income, expense = await _totals(db, auth.household.id, start, end)
    previous_income, previous_expense = await _totals(
        db, auth.household.id, previous_start, previous_end
    )
    net_worth = await _net_worth_at(db, auth.household.id, end)
    previous_net_worth = await _net_worth_at(db, auth.household.id, previous_end)
    if net_worth is None:
        net_worth = Decimal(
            await db.scalar(
                select(
                    func.coalesce(
                        func.sum(
                            case((Account.type == "credit", -Account.balance), else_=Account.balance)
                        ),
                        0,
                    )
                ).where(Account.household_id == auth.household.id)
            )
            or 0
        )
    balance = income - expense
    previous_balance = previous_income - previous_expense
    return KpisRead(
        income=KpiRead(value=income, variation=variation(income, previous_income)),
        expense=KpiRead(value=expense, variation=variation(expense, previous_expense)),
        balance=KpiRead(value=balance, variation=variation(balance, previous_balance)),
        net_worth=KpiRead(
            value=net_worth,
            variation=variation(net_worth, previous_net_worth) if previous_net_worth is not None else None,
        ),
        date_from=start,
        date_to=end,
    )


def _month_start(value: date) -> date:
    return value.replace(day=1)


def _shift_month(value: date, amount: int) -> date:
    index = value.year * 12 + value.month - 1 + amount
    return date(index // 12, index % 12 + 1, 1)


@router.get("/analytics/trends")
async def trends(
    auth: CurrentAuth,
    db: DbSession,
    date_to: Annotated[date | None, Query()] = None,
) -> list[TrendRead]:
    end_month = _month_start(date_to or datetime.now(UTC).date())
    start_month = _shift_month(end_month, -11)
    month = func.date_trunc("month", Transaction.date)
    rows = (
        await db.execute(
            select(
                month,
                func.coalesce(func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), 0),
                func.coalesce(func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)), 0),
            )
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Account.household_id == auth.household.id,
                Transaction.date >= datetime.combine(start_month, time.min, UTC),
                Transaction.date < datetime.combine(_shift_month(end_month, 1), time.min, UTC),
            )
            .group_by(month)
            .order_by(month)
        )
    ).all()
    values = {row[0].date(): (Decimal(row[1]), Decimal(row[2])) for row in rows}
    return [
        TrendRead(
            month=current,
            income=values.get(current, (Decimal(0), Decimal(0)))[0],
            expense=values.get(current, (Decimal(0), Decimal(0)))[1],
            balance=values.get(current, (Decimal(0), Decimal(0)))[0]
            - values.get(current, (Decimal(0), Decimal(0)))[1],
        )
        for current in (_shift_month(start_month, offset) for offset in range(12))
    ]


@router.get("/analytics/expenses-by-category")
async def expenses_by_category(
    auth: CurrentAuth,
    db: DbSession,
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> list[CategoryExpenseRead]:
    start, end = date_bounds(date_from, date_to)
    rows = (
        await db.execute(
            select(Category.id, func.coalesce(Category.name, "Sem categoria"), func.sum(-Transaction.amount))
            .join(Account, Account.id == Transaction.account_id)
            .outerjoin(Category, Category.id == Transaction.category_id)
            .where(
                Account.household_id == auth.household.id,
                Transaction.amount < 0,
                Transaction.date >= datetime.combine(start, time.min, UTC),
                Transaction.date < datetime.combine(end + timedelta(days=1), time.min, UTC),
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(-Transaction.amount).desc())
        )
    ).all()
    return [
        CategoryExpenseRead(category_id=category_id, category=name, amount=Decimal(amount))
        for category_id, name, amount in rows
    ]
