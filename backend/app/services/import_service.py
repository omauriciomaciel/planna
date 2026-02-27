import csv
import io
import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.transaction import TransactionStatus, TransactionType
from app.repositories.credit_purchase import CreditPurchaseRepository
from app.repositories.transaction import TransactionRepository


def parse_ofx(content: str) -> list[dict]:
    """Parse OFX file content and return list of transaction dicts."""
    transactions = []
    blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL)

    for block in blocks:
        dt_match = re.search(r"<DTPOSTED>([\d]+)", block)
        amt_match = re.search(r"<TRNAMT>([-\d.,]+)", block)
        memo_match = re.search(r"<MEMO>(.+?)(?:\n|<)", block)

        if not (dt_match and amt_match):
            continue

        dt_str = dt_match.group(1)[:8]
        tx_date = date(int(dt_str[:4]), int(dt_str[4:6]), int(dt_str[6:8]))

        amt_str = amt_match.group(1).replace(",", ".")
        amount = Decimal(amt_str)

        description = memo_match.group(1).strip() if memo_match else "Sem descrição"

        tx_type = TransactionType.INCOME if amount > 0 else TransactionType.EXPENSE

        transactions.append({
            "date": tx_date,
            "due_date": tx_date,
            "description": description,
            "type": tx_type,
            "amount": abs(amount),
            "status": TransactionStatus.PAID,
        })

    return transactions


def parse_nubank_csv(content: str) -> list[dict]:
    """Parse Nubank credit card CSV and return list of purchase dicts."""
    purchases = []
    reader = csv.DictReader(io.StringIO(content))

    for row in reader:
        title = row.get("title", "").strip()

        if "Pagamento recebido" in title:
            continue

        amount_str = row.get("amount", "0").replace(",", ".")
        amount = Decimal(amount_str)

        date_str = row.get("date", "")
        try:
            purchase_date = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            continue

        installment_match = re.search(r"Parcela\s+(\d+)/(\d+)", title, re.IGNORECASE)
        current = 1
        total = 1
        if installment_match:
            current = int(installment_match.group(1))
            total = int(installment_match.group(2))

        total_amount = amount * total if total > 1 else amount

        purchases.append({
            "purchase_date": purchase_date,
            "merchant": title,
            "installment_amount": amount,
            "total_amount": total_amount,
            "current_installment": current,
            "total_installments": total,
        })

    return purchases


def parse_nubank_ofx(content: str) -> list[dict]:
    """Parse Nubank OFX (credit card variant) and return list of purchase dicts."""
    purchases = []
    blocks = re.findall(r"<STMTTRN>(.*?)</STMTTRN>", content, re.DOTALL)

    for block in blocks:
        dt_match = re.search(r"<DTPOSTED>([\d]+)", block)
        amt_match = re.search(r"<TRNAMT>([-\d.,]+)", block)
        memo_match = re.search(r"<MEMO>(.+?)(?:\n|<)", block)

        if not (dt_match and amt_match):
            continue

        dt_str = dt_match.group(1)[:8]
        purchase_date = date(int(dt_str[:4]), int(dt_str[4:6]), int(dt_str[6:8]))

        amt_str = amt_match.group(1).replace(",", ".")
        amount = abs(Decimal(amt_str))

        merchant = memo_match.group(1).strip() if memo_match else "Sem descrição"

        installment_match = re.search(r"Parcela\s+(\d+)/(\d+)", merchant, re.IGNORECASE)
        current = 1
        total = 1
        if installment_match:
            current = int(installment_match.group(1))
            total = int(installment_match.group(2))

        total_amount = amount * total if total > 1 else amount

        purchases.append({
            "purchase_date": purchase_date,
            "merchant": merchant,
            "installment_amount": amount,
            "total_amount": total_amount,
            "current_installment": current,
            "total_installments": total,
        })

    return purchases


class ImportService:
    def __init__(
        self,
        transaction_repo: TransactionRepository,
        credit_purchase_repo: CreditPurchaseRepository,
    ):
        self.transaction_repo = transaction_repo
        self.credit_purchase_repo = credit_purchase_repo

    async def save_transactions(
        self,
        user_id: uuid.UUID,
        parsed: list[dict],
        account_id: uuid.UUID | None = None,
    ) -> int:
        return await self.transaction_repo.bulk_create(user_id, parsed, account_id)

    async def save_credit_purchases(
        self,
        user_id: uuid.UUID,
        parsed: list[dict],
        credit_card_id: uuid.UUID | None = None,
    ) -> int:
        return await self.credit_purchase_repo.bulk_create(
            user_id, parsed, credit_card_id
        )


def get_transaction_repository(
    db: AsyncSession = Depends(get_db),
) -> TransactionRepository:
    return TransactionRepository(db)


def get_credit_purchase_repository(
    db: AsyncSession = Depends(get_db),
) -> CreditPurchaseRepository:
    return CreditPurchaseRepository(db)


def get_import_service(
    transaction_repo: TransactionRepository = Depends(get_transaction_repository),
    credit_purchase_repo: CreditPurchaseRepository = Depends(get_credit_purchase_repository),
) -> ImportService:
    return ImportService(transaction_repo, credit_purchase_repo)
