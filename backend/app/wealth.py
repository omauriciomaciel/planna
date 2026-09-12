import uuid
from collections import defaultdict
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal
from typing import Any

from fastapi import APIRouter, HTTPException, status
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentAuth
from app.database import DbSession
from app.models import (
    Account,
    Asset,
    AssetValueHistory,
    HouseholdMember,
    Invoice,
    Liability,
    LiabilityValueHistory,
    NetWorthSnapshot,
    PluggyItem,
    Transaction,
    User,
)
from app.pluggy import client
from app.schemas import (
    AllocationRead,
    AssetCreate,
    AssetRead,
    AssetUpdate,
    LiabilityCreate,
    LiabilityRead,
    LiabilityUpdate,
    Message,
    NetWorthHistoryRead,
    NetWorthRead,
    ValueHistoryRead,
    WealthAssetRead,
    WealthLiabilityRead,
)

router = APIRouter(tags=["wealth"])
ZERO = Decimal(0)


def financial_rates(
    total_assets: Decimal,
    total_liabilities: Decimal,
    income: Decimal,
    expense: Decimal,
    monthly_debt_payments: Decimal,
) -> tuple[float | None, float | None, float | None]:
    debt_ratio = float(total_liabilities / total_assets) if total_assets else None
    income_commitment = float(monthly_debt_payments / income) if income else None
    savings_rate = float((income - expense) / income) if income else None
    return debt_ratio, income_commitment, savings_rate


def required_name(value: str) -> str:
    if name := value.strip():
        return name
    raise HTTPException(status_code=422, detail="Nome é obrigatório")


def investment_values(data: dict[str, Any]) -> dict[str, Any]:
    valued_at = datetime.now(UTC)
    if data.get("date"):
        parsed = datetime.fromisoformat(str(data["date"]))
        valued_at = parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)
    return {
        "type": "pension" if str(data.get("subtype", "")).upper() == "RETIREMENT" else "investment",
        "name": str(data.get("name") or "Investimento")[:160],
        "current_value": max(Decimal(str(data.get("balance") or 0)), ZERO),
        "valued_at": valued_at,
    }


def loan_values(data: dict[str, Any]) -> dict[str, Any]:
    payments = data.get("payments") or {}
    balance = payments.get("contractOutstandingBalance")
    if balance is None:
        balance = data.get("contractAmount") or 0
    raw_type = str(data.get("type") or "").upper()
    due_date = data.get("firstInstalmentDueDate") or data.get("firstInstallmentDueDate")
    due_day = datetime.fromisoformat(str(due_date)).day if due_date else None
    return {
        "type": "financing" if "FINANCIAMENTO" in raw_type or "IMOBIL" in raw_type else "loan",
        "name": str(data.get("productName") or "Empréstimo")[:160],
        "current_balance": max(Decimal(str(balance)), ZERO),
        "original_amount": Decimal(str(data["contractAmount"]))
        if data.get("contractAmount") is not None
        else None,
        "interest_rate": Decimal(str(data["CET"])) if data.get("CET") is not None else None,
        "due_day": due_day,
    }


async def _member_allowed(db: AsyncSession, household_id: uuid.UUID, member_id: uuid.UUID) -> bool:
    return (
        await db.scalar(
            select(HouseholdMember.user_id).where(
                HouseholdMember.household_id == household_id,
                HouseholdMember.user_id == member_id,
            )
        )
        is not None
    )


async def sync_pluggy_wealth(db: AsyncSession, item: PluggyItem) -> None:
    # ponytail: closed Pluggy positions remain until the API exposes a reliable closed/deleted signal.
    for raw in await client.investments(item.pluggy_item_id):
        external_ref = f"{item.pluggy_item_id}:{raw['id']}"
        asset = await db.scalar(
            select(Asset).where(Asset.source == "pluggy", Asset.external_ref == external_ref)
        )
        if asset is None:
            asset = Asset(
                household_id=item.household_id,
                member_id=item.member_id,
                source="pluggy",
                external_ref=external_ref,
                **investment_values(raw),
            )
            db.add(asset)
            await db.flush()
            db.add(AssetValueHistory(asset_id=asset.id, value=asset.current_value))
            continue
        previous = asset.current_value
        for field, value in investment_values(raw).items():
            setattr(asset, field, value)
        if asset.current_value != previous:
            db.add(AssetValueHistory(asset_id=asset.id, value=asset.current_value))

    for raw in await client.loans(item.pluggy_item_id):
        external_ref = f"{item.pluggy_item_id}:{raw['id']}"
        liability = await db.scalar(
            select(Liability).where(
                Liability.source == "pluggy", Liability.external_ref == external_ref
            )
        )
        if liability is None:
            liability = Liability(
                household_id=item.household_id,
                member_id=item.member_id,
                source="pluggy",
                external_ref=external_ref,
                monthly_payment=None,
                **loan_values(raw),
            )
            db.add(liability)
            await db.flush()
            db.add(
                LiabilityValueHistory(liability_id=liability.id, balance=liability.current_balance)
            )
            continue
        previous = liability.current_balance
        for field, value in loan_values(raw).items():
            setattr(liability, field, value)
        if liability.current_balance != previous:
            db.add(
                LiabilityValueHistory(liability_id=liability.id, balance=liability.current_balance)
            )


async def _month_totals(
    db: AsyncSession, household_id: uuid.UUID, month: date
) -> tuple[Decimal, Decimal]:
    next_month = (month.replace(day=28) + timedelta(days=4)).replace(day=1)
    income, expense = (
        await db.execute(
            select(
                func.coalesce(
                    func.sum(case((Transaction.amount > 0, Transaction.amount), else_=0)), 0
                ),
                func.coalesce(
                    func.sum(case((Transaction.amount < 0, -Transaction.amount), else_=0)), 0
                ),
            )
            .outerjoin(Account, Account.id == Transaction.account_id)
            .outerjoin(Invoice, Invoice.id == Transaction.source_invoice_id)
            .where(
                or_(
                    Account.household_id == household_id,
                    Invoice.household_id == household_id,
                ),
                Transaction.date >= datetime.combine(month, time.min, UTC),
                Transaction.date < datetime.combine(next_month, time.min, UTC),
            )
        )
    ).one()
    return Decimal(income), Decimal(expense)


async def net_worth_data(db: AsyncSession, household_id: uuid.UUID) -> NetWorthRead:
    stored_assets = (
        await db.execute(
            select(Asset, User.name)
            .join(User, User.id == Asset.member_id)
            .where(Asset.household_id == household_id)
            .order_by(Asset.type, Asset.name)
        )
    ).all()
    stored_liabilities = (
        await db.execute(
            select(Liability, User.name)
            .join(User, User.id == Liability.member_id)
            .where(Liability.household_id == household_id)
            .order_by(Liability.type, Liability.name)
        )
    ).all()
    account_rows = (
        await db.execute(
            select(Account, User.name, PluggyItem.pluggy_item_id)
            .join(User, User.id == Account.member_id)
            .join(PluggyItem, PluggyItem.id == Account.item_id)
            .where(Account.household_id == household_id)
            .order_by(Account.type, Account.name)
        )
    ).all()

    detailed_investment_items = {
        asset.external_ref.split(":", 1)[0]
        for asset, _ in stored_assets
        if asset.source == "pluggy" and asset.external_ref
    }
    assets = [
        WealthAssetRead(
            id=str(asset.id),
            member_id=asset.member_id,
            member_name=member_name,
            type=asset.type,
            name=asset.name,
            value=asset.current_value,
            source=asset.source,
            valued_at=asset.valued_at,
            editable=asset.source == "manual",
        )
        for asset, member_name in stored_assets
    ]
    liabilities = [
        WealthLiabilityRead(
            id=str(liability.id),
            member_id=liability.member_id,
            member_name=member_name,
            type=liability.type,
            name=liability.name,
            balance=liability.current_balance,
            monthly_payment=liability.monthly_payment,
            source=liability.source,
            editable=liability.source == "manual",
        )
        for liability, member_name in stored_liabilities
    ]

    for account, member_name, pluggy_item_id in account_rows:
        balance = Decimal(account.balance)
        if account.type == "investment" and pluggy_item_id in detailed_investment_items:
            continue
        if account.type in {"bank", "investment"} and balance >= 0:
            assets.append(
                WealthAssetRead(
                    id=f"account:{account.id}",
                    member_id=account.member_id,
                    member_name=member_name,
                    type="cash" if account.type == "bank" else "investment",
                    name=account.name,
                    value=balance,
                    source="pluggy",
                    valued_at=None,
                    editable=False,
                )
            )
        elif account.type == "credit" and balance < 0:
            assets.append(
                WealthAssetRead(
                    id=f"account:{account.id}",
                    member_id=account.member_id,
                    member_name=member_name,
                    type="cash",
                    name=f"Crédito em {account.name}",
                    value=-balance,
                    source="pluggy",
                    valued_at=None,
                    editable=False,
                )
            )
        elif balance:
            debt = abs(balance)
            is_credit = account.type == "credit"
            liabilities.append(
                WealthLiabilityRead(
                    id=f"account:{account.id}",
                    member_id=account.member_id,
                    member_name=member_name,
                    type="credit_card" if is_credit else "loan",
                    name=account.name,
                    balance=debt,
                    monthly_payment=debt if is_credit else None,
                    source="pluggy",
                    editable=False,
                )
            )

    total_assets = sum((item.value for item in assets), ZERO)
    total_liabilities = sum((item.balance for item in liabilities), ZERO)
    monthly_debt_payments = sum((item.monthly_payment or ZERO for item in liabilities), ZERO)
    month = datetime.now(UTC).date().replace(day=1)
    income, expense = await _month_totals(db, household_id, month)
    debt_ratio, income_commitment, savings_rate = financial_rates(
        total_assets, total_liabilities, income, expense, monthly_debt_payments
    )
    allocation_values: dict[str, Decimal] = defaultdict(lambda: ZERO)
    for item in assets:
        allocation_values[item.type] += item.value
    return NetWorthRead(
        total_assets=total_assets,
        total_liabilities=total_liabilities,
        net_worth=total_assets - total_liabilities,
        debt_ratio=debt_ratio,
        income_commitment=income_commitment,
        savings_rate=savings_rate,
        monthly_income=income,
        monthly_expense=expense,
        monthly_debt_payments=monthly_debt_payments,
        assets=assets,
        liabilities=liabilities,
        allocation=[
            AllocationRead(type=asset_type, value=value)
            for asset_type, value in sorted(
                allocation_values.items(), key=lambda item: item[1], reverse=True
            )
            if value
        ],
    )


async def record_snapshot(db: AsyncSession, household_id: uuid.UUID) -> NetWorthSnapshot:
    wealth = await net_worth_data(db, household_id)
    month = datetime.now(UTC).date().replace(day=1)
    snapshot = await db.scalar(
        select(NetWorthSnapshot).where(
            NetWorthSnapshot.household_id == household_id,
            NetWorthSnapshot.ref_month == month,
        )
    )
    if snapshot is None:
        snapshot = NetWorthSnapshot(household_id=household_id, ref_month=month)
        db.add(snapshot)
    snapshot.total_assets = wealth.total_assets
    snapshot.total_liabilities = wealth.total_liabilities
    snapshot.net_worth = wealth.net_worth
    snapshot.debt_ratio = Decimal(str(wealth.debt_ratio)) if wealth.debt_ratio is not None else None
    snapshot.savings_rate = (
        Decimal(str(wealth.savings_rate)) if wealth.savings_rate is not None else None
    )
    await db.flush()
    return snapshot


def _asset_read(asset: Asset, member_name: str) -> AssetRead:
    return AssetRead(
        id=asset.id,
        member_id=asset.member_id,
        member_name=member_name,
        type=asset.type,
        name=asset.name,
        current_value=asset.current_value,
        source=asset.source,
        valued_at=asset.valued_at,
    )


def _liability_read(liability: Liability, member_name: str) -> LiabilityRead:
    return LiabilityRead(
        id=liability.id,
        member_id=liability.member_id,
        member_name=member_name,
        type=liability.type,
        name=liability.name,
        current_balance=liability.current_balance,
        original_amount=liability.original_amount,
        interest_rate=liability.interest_rate,
        monthly_payment=liability.monthly_payment,
        due_day=liability.due_day,
        source=liability.source,
    )


@router.get("/assets")
async def list_assets(auth: CurrentAuth, db: DbSession) -> list[AssetRead]:
    rows = (
        await db.execute(
            select(Asset, User.name)
            .join(User, User.id == Asset.member_id)
            .where(Asset.household_id == auth.household.id)
            .order_by(Asset.type, Asset.name)
        )
    ).all()
    return [_asset_read(asset, member_name) for asset, member_name in rows]


@router.post("/assets", status_code=status.HTTP_201_CREATED)
async def create_asset(payload: AssetCreate, auth: CurrentAuth, db: DbSession) -> AssetRead:
    member_id = payload.member_id or auth.user.id
    if not await _member_allowed(db, auth.household.id, member_id):
        raise HTTPException(status_code=422, detail="Membro inválido")
    asset = Asset(
        household_id=auth.household.id,
        member_id=member_id,
        type=payload.type,
        name=required_name(payload.name),
        current_value=payload.current_value,
        source="manual",
        valued_at=payload.valued_at or datetime.now(UTC),
    )
    db.add(asset)
    await db.flush()
    db.add(AssetValueHistory(asset_id=asset.id, value=asset.current_value))
    await record_snapshot(db, auth.household.id)
    await db.commit()
    member_name = await db.scalar(select(User.name).where(User.id == member_id))
    return _asset_read(asset, member_name or "Membro")


@router.patch("/assets/{asset_id}")
async def update_asset(
    asset_id: uuid.UUID, payload: AssetUpdate, auth: CurrentAuth, db: DbSession
) -> AssetRead:
    row = (
        await db.execute(
            select(Asset, User.name)
            .join(User, User.id == Asset.member_id)
            .where(Asset.id == asset_id, Asset.household_id == auth.household.id)
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    asset, member_name = row
    if asset.source != "manual":
        raise HTTPException(
            status_code=409, detail="Ativos do Pluggy são atualizados pela sincronização"
        )
    values = payload.model_dump(exclude_unset=True)
    member_id = values.pop("member_id", None)
    if member_id is not None:
        if not await _member_allowed(db, auth.household.id, member_id):
            raise HTTPException(status_code=422, detail="Membro inválido")
        asset.member_id = member_id
        member_name = await db.scalar(select(User.name).where(User.id == member_id)) or "Membro"
    if values.get("name") is not None:
        values["name"] = required_name(values["name"])
    if values.get("valued_at") is None:
        values.pop("valued_at", None)
    changed_value = "current_value" in values and values["current_value"] != asset.current_value
    for field, value in values.items():
        setattr(asset, field, value)
    if changed_value:
        asset.valued_at = values.get("valued_at") or datetime.now(UTC)
        db.add(AssetValueHistory(asset_id=asset.id, value=asset.current_value))
    await record_snapshot(db, auth.household.id)
    await db.commit()
    return _asset_read(asset, member_name)


@router.delete("/assets/{asset_id}")
async def delete_asset(asset_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> Message:
    asset = await db.scalar(
        select(Asset).where(Asset.id == asset_id, Asset.household_id == auth.household.id)
    )
    if asset is None:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    if asset.source != "manual":
        raise HTTPException(
            status_code=409, detail="Ativos do Pluggy são removidos pela sincronização"
        )
    await db.delete(asset)
    await db.flush()
    await record_snapshot(db, auth.household.id)
    await db.commit()
    return Message(message="Ativo removido")


@router.get("/assets/{asset_id}/history")
async def asset_history(
    asset_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> list[ValueHistoryRead]:
    allowed = await db.scalar(
        select(Asset.id).where(Asset.id == asset_id, Asset.household_id == auth.household.id)
    )
    if allowed is None:
        raise HTTPException(status_code=404, detail="Ativo não encontrado")
    rows = (
        await db.scalars(
            select(AssetValueHistory)
            .where(AssetValueHistory.asset_id == asset_id)
            .order_by(AssetValueHistory.recorded_at)
        )
    ).all()
    return [ValueHistoryRead(recorded_at=row.recorded_at, value=row.value) for row in rows]


@router.get("/liabilities")
async def list_liabilities(auth: CurrentAuth, db: DbSession) -> list[LiabilityRead]:
    rows = (
        await db.execute(
            select(Liability, User.name)
            .join(User, User.id == Liability.member_id)
            .where(Liability.household_id == auth.household.id)
            .order_by(Liability.type, Liability.name)
        )
    ).all()
    return [_liability_read(liability, member_name) for liability, member_name in rows]


@router.post("/liabilities", status_code=status.HTTP_201_CREATED)
async def create_liability(
    payload: LiabilityCreate, auth: CurrentAuth, db: DbSession
) -> LiabilityRead:
    member_id = payload.member_id or auth.user.id
    if not await _member_allowed(db, auth.household.id, member_id):
        raise HTTPException(status_code=422, detail="Membro inválido")
    liability = Liability(
        household_id=auth.household.id,
        member_id=member_id,
        type=payload.type,
        name=required_name(payload.name),
        current_balance=payload.current_balance,
        original_amount=payload.original_amount,
        interest_rate=payload.interest_rate,
        monthly_payment=payload.monthly_payment,
        due_day=payload.due_day,
        source="manual",
    )
    db.add(liability)
    await db.flush()
    db.add(LiabilityValueHistory(liability_id=liability.id, balance=liability.current_balance))
    await record_snapshot(db, auth.household.id)
    await db.commit()
    member_name = await db.scalar(select(User.name).where(User.id == member_id))
    return _liability_read(liability, member_name or "Membro")


@router.patch("/liabilities/{liability_id}")
async def update_liability(
    liability_id: uuid.UUID,
    payload: LiabilityUpdate,
    auth: CurrentAuth,
    db: DbSession,
) -> LiabilityRead:
    row = (
        await db.execute(
            select(Liability, User.name)
            .join(User, User.id == Liability.member_id)
            .where(
                Liability.id == liability_id,
                Liability.household_id == auth.household.id,
            )
        )
    ).one_or_none()
    if row is None:
        raise HTTPException(status_code=404, detail="Passivo não encontrado")
    liability, member_name = row
    if liability.source != "manual":
        raise HTTPException(
            status_code=409, detail="Passivos do Pluggy são atualizados pela sincronização"
        )
    values = payload.model_dump(exclude_unset=True)
    member_id = values.pop("member_id", None)
    if member_id is not None:
        if not await _member_allowed(db, auth.household.id, member_id):
            raise HTTPException(status_code=422, detail="Membro inválido")
        liability.member_id = member_id
        member_name = await db.scalar(select(User.name).where(User.id == member_id)) or "Membro"
    if values.get("name") is not None:
        values["name"] = required_name(values["name"])
    changed_balance = (
        "current_balance" in values and values["current_balance"] != liability.current_balance
    )
    for field, value in values.items():
        setattr(liability, field, value)
    if changed_balance:
        db.add(LiabilityValueHistory(liability_id=liability.id, balance=liability.current_balance))
    await record_snapshot(db, auth.household.id)
    await db.commit()
    return _liability_read(liability, member_name)


@router.delete("/liabilities/{liability_id}")
async def delete_liability(liability_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> Message:
    liability = await db.scalar(
        select(Liability).where(
            Liability.id == liability_id,
            Liability.household_id == auth.household.id,
        )
    )
    if liability is None:
        raise HTTPException(status_code=404, detail="Passivo não encontrado")
    if liability.source != "manual":
        raise HTTPException(
            status_code=409, detail="Passivos do Pluggy são removidos pela sincronização"
        )
    await db.delete(liability)
    await db.flush()
    await record_snapshot(db, auth.household.id)
    await db.commit()
    return Message(message="Passivo removido")


@router.get("/liabilities/{liability_id}/history")
async def liability_history(
    liability_id: uuid.UUID, auth: CurrentAuth, db: DbSession
) -> list[ValueHistoryRead]:
    allowed = await db.scalar(
        select(Liability.id).where(
            Liability.id == liability_id,
            Liability.household_id == auth.household.id,
        )
    )
    if allowed is None:
        raise HTTPException(status_code=404, detail="Passivo não encontrado")
    rows = (
        await db.scalars(
            select(LiabilityValueHistory)
            .where(LiabilityValueHistory.liability_id == liability_id)
            .order_by(LiabilityValueHistory.recorded_at)
        )
    ).all()
    return [ValueHistoryRead(recorded_at=row.recorded_at, value=row.balance) for row in rows]


@router.get("/net-worth")
async def net_worth(auth: CurrentAuth, db: DbSession) -> NetWorthRead:
    return await net_worth_data(db, auth.household.id)


@router.get("/net-worth/history")
async def net_worth_history(auth: CurrentAuth, db: DbSession) -> list[NetWorthHistoryRead]:
    rows = (
        await db.scalars(
            select(NetWorthSnapshot)
            .where(NetWorthSnapshot.household_id == auth.household.id)
            .order_by(NetWorthSnapshot.ref_month)
        )
    ).all()
    return [
        NetWorthHistoryRead(
            month=row.ref_month,
            total_assets=row.total_assets,
            total_liabilities=row.total_liabilities,
            net_worth=row.net_worth,
        )
        for row in rows
    ]
