import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated
from urllib.parse import parse_qs, urlsplit

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import CurrentAuth
from app.database import DbSession
from app.models import Account, Invoice, InvoiceItem, Transaction
from app.schemas import (
    InvoiceIngestRead,
    InvoiceIngestRequest,
    InvoiceItemRead,
    InvoiceRead,
    InvoiceResolveRequest,
)
from app.sefaz import (
    LOCAL_TIMEZONE,
    SefazError,
    SefazUnavailable,
    digits,
    fetch_nfce,
    normalize_nfce_url,
)

router = APIRouter(prefix="/invoices", tags=["invoices"])


def choose_match(
    candidates: Sequence[Transaction], merchant_cnpj: str | None
) -> tuple[Transaction | None, Decimal]:
    if len(candidates) == 1:
        confidence = (
            Decimal("1.00")
            if merchant_cnpj and digits(candidates[0].merchant_cnpj) == merchant_cnpj
            else Decimal("0.90")
        )
        return candidates[0], confidence
    cnpj_matches = [
        candidate
        for candidate in candidates
        if merchant_cnpj and digits(candidate.merchant_cnpj) == merchant_cnpj
    ]
    return (cnpj_matches[0], Decimal("1.00")) if len(cnpj_matches) == 1 else (None, Decimal("0.50"))


def _explicit_voucher(payment_method: str | None) -> bool:
    normalized = (payment_method or "").lower()
    return any(
        word in normalized for word in ("vale", "alimenta", "refei", "alelo", "sodexo", "ticket")
    )


async def _candidates(db: AsyncSession, invoice: Invoice) -> list[Transaction]:
    local_date = invoice.issue_datetime.astimezone(LOCAL_TIMEZONE).date()
    start = datetime.combine(local_date, time.min, LOCAL_TIMEZONE).astimezone(UTC)
    end = (datetime.combine(local_date, time.min, LOCAL_TIMEZONE) + timedelta(days=3)).astimezone(
        UTC
    )
    exact_or_installment = or_(
        -Transaction.amount == invoice.total_amount,
        and_(
            Transaction.installment_current == 1,
            Transaction.installment_total > 1,
            -Transaction.amount * Transaction.installment_total == invoice.total_amount,
        ),
    )
    return list(
        (
            await db.scalars(
                select(Transaction)
                .join(Account, Account.id == Transaction.account_id)
                .where(
                    Account.household_id == invoice.household_id,
                    Transaction.source == "pluggy",
                    Transaction.id.not_in(
                        select(Invoice.matched_transaction_id).where(
                            Invoice.id != invoice.id,
                            Invoice.matched_transaction_id.is_not(None),
                        )
                    ),
                    Transaction.date >= start,
                    Transaction.date < end,
                    exact_or_installment,
                )
                .order_by(Transaction.date, Transaction.id)
            )
        ).all()
    )


async def _voucher_transaction(db: AsyncSession, invoice: Invoice) -> Transaction | None:
    return await db.scalar(select(Transaction).where(Transaction.source_invoice_id == invoice.id))


async def _ensure_voucher(db: AsyncSession, invoice: Invoice) -> None:
    if await _voucher_transaction(db, invoice) is None:
        db.add(
            Transaction(
                account_id=None,
                pluggy_transaction_id=None,
                source_invoice_id=invoice.id,
                date=invoice.issue_datetime,
                amount=-invoice.total_amount,
                description=invoice.merchant_name,
                merchant_name=invoice.merchant_name,
                merchant_cnpj=invoice.merchant_cnpj,
                category_id=None,
                type="debit",
                status="posted",
                installment_current=None,
                installment_total=None,
                source="voucher",
                raw={"invoice_access_key": invoice.access_key},
            )
        )


async def reconcile_invoice(db: AsyncSession, invoice: Invoice) -> None:
    candidates = await _candidates(db, invoice)
    match, confidence = choose_match(candidates, invoice.merchant_cnpj)
    voucher = await _voucher_transaction(db, invoice)
    if match:
        if voucher:
            await db.delete(voucher)
        invoice.payment_status = "reconciled"
        invoice.matched_transaction_id = match.id
        invoice.match_confidence = confidence
        return
    if candidates:
        if voucher:
            await db.delete(voucher)
        invoice.payment_status = "reconciled"
        invoice.matched_transaction_id = None
        invoice.match_confidence = confidence
        return

    invoice.payment_status = "voucher"
    invoice.matched_transaction_id = None
    invoice.match_confidence = Decimal(
        "1.00" if _explicit_voucher(invoice.payment_method_raw) else "0.80"
    )
    if voucher is None:
        await _ensure_voucher(db, invoice)


async def reconcile_unmatched_invoices(db: AsyncSession, household_id: uuid.UUID) -> None:
    invoices = (
        await db.scalars(
            select(Invoice).where(
                Invoice.household_id == household_id,
                Invoice.matched_transaction_id.is_(None),
            )
        )
    ).all()
    for invoice in invoices:
        await reconcile_invoice(db, invoice)


async def invoice_read(db: AsyncSession, invoice: Invoice) -> InvoiceRead:
    items = (
        await db.scalars(
            select(InvoiceItem).where(InvoiceItem.invoice_id == invoice.id).order_by(InvoiceItem.id)
        )
    ).all()
    return InvoiceRead(
        id=invoice.id,
        access_key=invoice.access_key,
        number=invoice.number,
        series=invoice.series,
        issue_datetime=invoice.issue_datetime,
        total_amount=invoice.total_amount,
        merchant_cnpj=invoice.merchant_cnpj,
        merchant_name=invoice.merchant_name,
        payment_method_raw=invoice.payment_method_raw,
        payment_status=invoice.payment_status,
        matched_transaction_id=invoice.matched_transaction_id,
        match_confidence=invoice.match_confidence,
        needs_review=invoice.payment_status == "reconciled"
        and invoice.matched_transaction_id is None,
        items=[
            InvoiceItemRead(
                id=item.id,
                description=item.description,
                product_code=item.product_code,
                quantity=item.quantity,
                unit=item.unit,
                unit_price=item.unit_price,
                total_price=item.total_price,
                category_id=item.category_id,
            )
            for item in items
        ],
    )


async def _existing_invoice(
    db: AsyncSession, access_key: str, household_id: uuid.UUID
) -> Invoice | None:
    invoice = await db.scalar(select(Invoice).where(Invoice.access_key == access_key))
    if invoice and invoice.household_id != household_id:
        raise HTTPException(status_code=409, detail="Esta nota já pertence a outro household")
    return invoice


@router.post("/ingest")
async def ingest_invoice(
    payload: InvoiceIngestRequest, auth: CurrentAuth, db: DbSession
) -> InvoiceIngestRead:
    try:
        source_url = normalize_nfce_url(payload.url)
    except SefazError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    access_key = parse_qs(urlsplit(source_url).query)["p"][0].split("|", 1)[0]
    existing = await _existing_invoice(db, access_key, auth.household.id)
    if existing:
        return InvoiceIngestRead(invoice=await invoice_read(db, existing), created=False)

    try:
        parsed = await fetch_nfce(source_url)
    except SefazUnavailable as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except SefazError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    invoice = Invoice(
        household_id=auth.household.id,
        member_id=auth.user.id,
        access_key=parsed.access_key,
        number=parsed.number,
        series=parsed.series,
        issue_datetime=parsed.issue_datetime,
        gross_amount=parsed.gross_amount,
        discount_amount=parsed.discount_amount,
        total_amount=parsed.total_amount,
        merchant_cnpj=parsed.merchant_cnpj,
        merchant_name=parsed.merchant_name,
        merchant_address=parsed.merchant_address,
        source_url=parsed.source_url,
        payment_method_raw=parsed.payment_method_raw,
        payment_status="voucher",
        matched_transaction_id=None,
        match_confidence=Decimal(0),
        protocol=parsed.protocol,
        raw=parsed.raw,
    )
    db.add(invoice)
    try:
        await db.flush()
        db.add_all(
            [
                InvoiceItem(
                    invoice_id=invoice.id,
                    description=item.description,
                    product_code=item.product_code,
                    ncm=None,
                    quantity=item.quantity,
                    unit=item.unit,
                    unit_price=item.unit_price,
                    total_price=item.total_price,
                    category_id=None,
                )
                for item in parsed.items
            ]
        )
        await reconcile_invoice(db, invoice)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _existing_invoice(db, parsed.access_key, auth.household.id)
        if existing:
            return InvoiceIngestRead(invoice=await invoice_read(db, existing), created=False)
        raise
    return InvoiceIngestRead(invoice=await invoice_read(db, invoice), created=True)


@router.get("")
async def list_invoices(
    auth: CurrentAuth,
    db: DbSession,
    limit: Annotated[int, Query(ge=1, le=100)] = 25,
) -> list[InvoiceRead]:
    invoices = (
        await db.scalars(
            select(Invoice)
            .where(Invoice.household_id == auth.household.id)
            .order_by(Invoice.issue_datetime.desc(), Invoice.id.desc())
            .limit(limit)
        )
    ).all()
    return [await invoice_read(db, invoice) for invoice in invoices]


@router.get("/{invoice_id}")
async def get_invoice(invoice_id: uuid.UUID, auth: CurrentAuth, db: DbSession) -> InvoiceRead:
    invoice = await db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.household_id == auth.household.id)
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    return await invoice_read(db, invoice)


@router.post("/{invoice_id}/resolve")
async def resolve_invoice(
    invoice_id: uuid.UUID,
    payload: InvoiceResolveRequest,
    auth: CurrentAuth,
    db: DbSession,
) -> InvoiceRead:
    invoice = await db.scalar(
        select(Invoice).where(Invoice.id == invoice_id, Invoice.household_id == auth.household.id)
    )
    if invoice is None:
        raise HTTPException(status_code=404, detail="Nota não encontrada")
    voucher = await _voucher_transaction(db, invoice)
    if payload.transaction_id:
        transaction = await db.scalar(
            select(Transaction)
            .join(Account, Account.id == Transaction.account_id)
            .where(
                Transaction.id == payload.transaction_id,
                Transaction.source == "pluggy",
                Account.household_id == auth.household.id,
            )
        )
        if transaction is None:
            raise HTTPException(status_code=422, detail="Transação inválida")
        already_matched = await db.scalar(
            select(Invoice.id).where(
                Invoice.id != invoice.id,
                Invoice.matched_transaction_id == transaction.id,
            )
        )
        if already_matched:
            raise HTTPException(status_code=409, detail="Transação já conciliada com outra nota")
        if voucher:
            await db.delete(voucher)
        invoice.payment_status = "reconciled"
        invoice.matched_transaction_id = transaction.id
    else:
        invoice.matched_transaction_id = None
        invoice.payment_status = "voucher"
        if voucher is None:
            await _ensure_voucher(db, invoice)
    invoice.match_confidence = Decimal("1.00")
    await db.commit()
    return await invoice_read(db, invoice)
