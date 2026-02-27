import uuid

from fastapi import APIRouter, Depends, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.services.import_service import (
    parse_nubank_csv,
    parse_nubank_ofx,
    parse_ofx,
    save_credit_purchases,
    save_transactions,
)

router = APIRouter(prefix="/import", tags=["import"])


@router.post("/ofx")
async def import_ofx(
    file: UploadFile,
    account_id: str | None = None,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    content = (await file.read()).decode("latin-1")
    parsed = parse_ofx(content)
    if not parsed:
        raise HTTPException(status_code=400, detail="No transactions found in OFX file")

    acc_id = uuid.UUID(account_id) if account_id else None
    count = await save_transactions(db, user.id, parsed, acc_id)
    return {"imported": count}


@router.post("/csv")
async def import_csv(
    file: UploadFile,
    credit_card_id: str | None = None,
    file_type: str = "csv",
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
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
    db: AsyncSession = Depends(get_db),
):
    content = (await file.read()).decode("utf-8")

    if file_type == "ofx":
        parsed = parse_nubank_ofx(content)
    else:
        parsed = parse_nubank_csv(content)

    if not parsed:
        raise HTTPException(status_code=400, detail="No purchases found in file")

    card_id = uuid.UUID(credit_card_id) if credit_card_id else None
    count = await save_credit_purchases(db, user.id, parsed, card_id)
    return {"imported": count}
