import json
import uuid
from collections.abc import Sequence
from datetime import UTC, datetime, time, timedelta
from decimal import Decimal
from typing import Annotated
from urllib.parse import parse_qs, urlsplit

import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import SessionLocal
from app.dependencies import CurrentAuth, DbSession
from app.economic import normalize_text
from app.models import (
    Account,
    Category,
    Invoice,
    InvoiceItem,
    ProductCategoryCache,
    Transaction,
    User,
)
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
PRODUCT_CATEGORIES = (
    "Alimentos",
    "Bebidas",
    "Limpeza",
    "Higiene",
    "Padaria",
    "Carnes",
    "Frios",
    "Hortifruti",
    "Congelados",
    "Pet",
    "Outros",
)


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


def _normalize_product(value: str) -> str:
    return normalize_text(value)


def _similarity(left: str, right: str) -> float:
    previous = list(range(len(right) + 1))
    for i, char in enumerate(left, 1):
        current = [i]
        for j, other in enumerate(right, 1):
            current.append(min(current[-1] + 1, previous[j] + 1, previous[j - 1] + (char != other)))
        previous = current
    return 1 - previous[-1] / max(len(left), len(right), 1)


async def _product_categories(db: AsyncSession) -> dict[str, uuid.UUID]:
    for name in PRODUCT_CATEGORIES:
        await db.execute(
            insert(Category)
            .values(
                id=uuid.uuid4(),
                household_id=None,
                name=name,
                kind="expense",
                is_system=True,
                external_id=f"invoice:{normalize_text(name).replace(' ', '-')}",
            )
            .on_conflict_do_nothing(index_elements=[Category.external_id])
        )
    rows = (
        await db.execute(
            select(Category.name, Category.id).where(Category.external_id.like("invoice:%"))
        )
    ).all()
    return dict(rows)


async def _llm_product_categories(items: list[InvoiceItem]) -> dict[int, str]:
    if not items or settings.openai_api_key is None:
        return {}
    schema = {
        "type": "object",
        "properties": {
            "items": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "index": {"type": "integer"},
                        "category": {"type": "string", "enum": list(PRODUCT_CATEGORIES)},
                    },
                    "required": ["index", "category"],
                    "additionalProperties": False,
                },
            }
        },
        "required": ["items"],
        "additionalProperties": False,
    }
    payload = {
        "model": settings.openai_model,
        "instructions": "Classifique cada item de nota fiscal em exatamente uma categoria permitida.",
        "input": json.dumps(
            [{"index": index, "description": item.description} for index, item in enumerate(items)],
            ensure_ascii=False,
        ),
        "text": {
            "format": {
                "type": "json_schema",
                "name": "invoice_categories",
                "strict": True,
                "schema": schema,
            }
        },
        "store": False,
    }
    async with httpx.AsyncClient(timeout=None) as client:
        response = await client.post(
            "https://api.openai.com/v1/responses",
            headers={"Authorization": f"Bearer {settings.openai_api_key.get_secret_value()}"},
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
    return {
        int(item["index"]): str(item["category"])
        for item in json.loads(text).get("items", [])
        if str(item.get("category")) in PRODUCT_CATEGORIES
    }


async def categorize_invoice_items(
    db: AsyncSession, items: list[InvoiceItem], *, allow_ai: bool
) -> None:
    categories = await _product_categories(db)
    cached = list(
        (
            await db.scalars(
                select(ProductCategoryCache).where(ProductCategoryCache.category_name != "Outros")
            )
        ).all()
    )
    rules = {
        "bebidas": "Bebidas",
        "refrigerante": "Bebidas",
        "suco": "Bebidas",
        "detergente": "Limpeza",
        "sabao": "Limpeza",
        "shampoo": "Higiene",
        "carne": "Carnes",
        "frango": "Carnes",
        "arroz": "Alimentos",
        "feijao": "Alimentos",
        "pao": "Padaria",
        "leite": "Frios",
        "racao": "Pet",
    }
    resolved: dict[int, tuple[str, str, Decimal]] = {}
    unresolved: list[tuple[int, InvoiceItem]] = []
    for index, item in enumerate(items):
        normalized = _normalize_product(item.description)
        match = next(
            (
                entry
                for entry in cached
                if entry.product_code
                and item.product_code
                and entry.product_code == item.product_code
            ),
            None,
        )
        if match is None:
            candidate = max(
                cached,
                key=lambda entry: _similarity(normalized, entry.normalized_description),
                default=None,
            )
            match = (
                candidate
                if candidate and _similarity(normalized, candidate.normalized_description) >= 0.82
                else None
            )
        category_name = (
            match.category_name
            if match
            else next((value for key, value in rules.items() if key in normalized), None)
        )
        if category_name is None:
            unresolved.append((index, item))
        else:
            resolved[index] = (
                category_name,
                match.source if match else "rule",
                match.confidence if match else Decimal("0.70"),
            )
    if unresolved and allow_ai:
        try:
            classified = await _llm_product_categories([item for _, item in unresolved])
            for llm_index, category_name in classified.items():
                if 0 <= llm_index < len(unresolved):
                    resolved[unresolved[llm_index][0]] = (
                        category_name,
                        "llm",
                        Decimal("0.90"),
                    )
        except (
            httpx.HTTPError,
            json.JSONDecodeError,
            KeyError,
            StopIteration,
            TypeError,
            ValueError,
        ):
            pass
    for index, item in enumerate(items):
        category_name, source, confidence = resolved.get(
            index, ("Outros", "fallback", Decimal("0.30"))
        )
        item.category_id = categories[category_name]
        if category_name == "Outros":
            continue
        values = {
            "id": uuid.uuid4(),
            "product_code": item.product_code,
            "normalized_description": _normalize_product(item.description),
            "category_name": category_name,
            "source": source,
            "confidence": confidence,
        }
        if item.product_code:
            await db.execute(
                insert(ProductCategoryCache)
                .values(**values)
                .on_conflict_do_update(
                    index_elements=[ProductCategoryCache.product_code],
                    set_={key: value for key, value in values.items() if key != "id"},
                )
            )
        elif not any(
            entry.normalized_description == values["normalized_description"] for entry in cached
        ):
            db.add(ProductCategoryCache(**values))


async def _categorize_invoice_in_background(invoice_id: uuid.UUID) -> None:
    async with SessionLocal() as db:
        try:
            invoice = await db.get(Invoice, invoice_id)
            if invoice is None:
                return
            items = list(
                (
                    await db.scalars(
                        select(InvoiceItem).where(InvoiceItem.invoice_id == invoice_id)
                    )
                ).all()
            )
            allow_ai = (
                await db.scalar(select(User.ai_consent_at).where(User.id == invoice.member_id))
            ) is not None
            await categorize_invoice_items(db, items, allow_ai=allow_ai)
            await db.commit()
        except Exception:  # noqa: BLE001 - background classification must not affect ingestion
            await db.rollback()


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
                economic_type="voucher_expense",
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
    payload: InvoiceIngestRequest,
    auth: CurrentAuth,
    db: DbSession,
    background_tasks: BackgroundTasks,
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
        invoice_items = [
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
        db.add_all(invoice_items)
        await reconcile_invoice(db, invoice)
        await db.commit()
    except IntegrityError:
        await db.rollback()
        existing = await _existing_invoice(db, parsed.access_key, auth.household.id)
        if existing:
            return InvoiceIngestRead(invoice=await invoice_read(db, existing), created=False)
        raise
    background_tasks.add_task(_categorize_invoice_in_background, invoice.id)
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
