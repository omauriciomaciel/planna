import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile

from app.deps import get_current_user
from app.models.user import User
from app.services.import_service import (
    ImportService,
    get_import_service,
    parse_nubank_csv,
    parse_nubank_ofx,
    parse_ofx,
)
from app.services.pdf_import_service import (
    extract_text_from_pdf,
    is_scanned_pdf,
    parse_pdf_text,
    parse_pdf_with_openai,
)

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/ofx")
async def import_ofx(
    file: UploadFile,
    account_id: str | None = None,
    user: User = Depends(get_current_user),
    service: ImportService = Depends(get_import_service),
):
    content = (await file.read()).decode("latin-1")
    parsed = parse_ofx(content)
    if not parsed:
        raise HTTPException(status_code=400, detail="No transactions found in OFX file")

    return {"transactions": parsed, "count": len(parsed)}


@router.post("/ofx/confirm")
async def confirm_ofx(
    file: UploadFile,
    account_id: str | None = Form(None),
    user: User = Depends(get_current_user),
    service: ImportService = Depends(get_import_service),
):
    content = (await file.read()).decode("latin-1")
    parsed = parse_ofx(content)
    if not parsed:
        raise HTTPException(status_code=400, detail="No transactions found in OFX file")

    acc_id = uuid.UUID(account_id) if account_id else None
    count = await service.save_transactions(user.id, parsed, acc_id)
    return {"imported": count}


@router.post("/csv")
async def import_csv(
    file: UploadFile,
    credit_card_id: str | None = None,
    file_type: str = "csv",
    user: User = Depends(get_current_user),
    service: ImportService = Depends(get_import_service),
):
    content = (await file.read()).decode("utf-8")

    if file_type == "ofx":
        parsed = parse_nubank_ofx(content)
    else:
        parsed = parse_nubank_csv(content)

    if not parsed:
        raise HTTPException(status_code=400, detail="No purchases found in file")

    return {"purchases": parsed, "count": len(parsed)}


@router.post("/csv/confirm")
async def confirm_csv(
    file: UploadFile,
    credit_card_id: str | None = Form(None),
    file_type: str = Form("csv"),
    user: User = Depends(get_current_user),
    service: ImportService = Depends(get_import_service),
):
    content = (await file.read()).decode("utf-8")

    if file_type == "ofx":
        parsed = parse_nubank_ofx(content)
    else:
        parsed = parse_nubank_csv(content)

    if not parsed:
        raise HTTPException(status_code=400, detail="No purchases found in file")

    card_id = uuid.UUID(credit_card_id) if credit_card_id else None
    count = await service.save_credit_purchases(user.id, parsed, card_id)
    return {"imported": count}


def _serialize_purchases(purchases: list[dict]) -> list[dict]:
    """Convert date/Decimal fields to JSON-safe types for preview."""
    result = []
    for p in purchases:
        result.append({
            **p,
            "purchase_date": p["purchase_date"].isoformat(),
            "due_date": (
                p["due_date"].isoformat()
                if p.get("due_date")
                else p["purchase_date"].isoformat()
            ),
            "installment_amount": float(p["installment_amount"]),
            "total_amount": float(p["total_amount"]),
        })
    return result


@router.post("/pdf")
async def import_pdf(
    file: UploadFile,
    user: User = Depends(get_current_user),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    content = await file.read()

    if is_scanned_pdf(content):
        try:
            parsed = await parse_pdf_with_openai(content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
        source = "ocr"
    else:
        text = extract_text_from_pdf(content)
        parsed = parse_pdf_text(text)
        source = "text"

    if not parsed:
        raise HTTPException(status_code=400, detail="No purchases found in PDF")

    return {
        "purchases": _serialize_purchases(parsed),
        "count": len(parsed),
        "source": source,
    }


@router.post("/pdf/confirm")
async def confirm_pdf(
    file: UploadFile,
    credit_card_id: str | None = Form(None),
    user: User = Depends(get_current_user),
    service: ImportService = Depends(get_import_service),
):
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File must be a PDF")

    content = await file.read()

    if is_scanned_pdf(content):
        try:
            parsed = await parse_pdf_with_openai(content)
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e)) from None
    else:
        text = extract_text_from_pdf(content)
        parsed = parse_pdf_text(text)

    if not parsed:
        raise HTTPException(status_code=400, detail="No purchases found in PDF")

    card_id = uuid.UUID(credit_card_id) if credit_card_id else None
    count = await service.save_credit_purchases(user.id, parsed, card_id)
    return {"imported": count}
