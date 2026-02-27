import csv
import io
import re
import uuid
from datetime import date, datetime
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.credit_purchase import CreditPurchase
from app.models.transaction import Transaction, TransactionStatus, TransactionType


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

        # Extract installment info from title
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


async def save_transactions(
    db: AsyncSession,
    user_id: uuid.UUID,
    parsed: list[dict],
    account_id: uuid.UUID | None = None,
) -> int:
    """Save parsed OFX transactions to database. Returns count of saved rows."""
    count = 0
    for item in parsed:
        tx = Transaction(
            user_id=user_id,
            date=item["date"],
            due_date=item.get("due_date"),
            description=item["description"],
            account_id=account_id,
            type=item["type"],
            amount=item["amount"],
            status=item["status"],
        )
        db.add(tx)
        count += 1
    await db.commit()
    return count


async def save_credit_purchases(
    db: AsyncSession,
    user_id: uuid.UUID,
    parsed: list[dict],
    credit_card_id: uuid.UUID | None = None,
) -> int:
    """Save parsed credit card purchases to database. Returns count of saved rows."""
    count = 0
    for item in parsed:
        purchase = CreditPurchase(
            user_id=user_id,
            purchase_date=item["purchase_date"],
            credit_card_id=credit_card_id,
            merchant=item["merchant"],
            total_amount=item["total_amount"],
            installment_amount=item["installment_amount"],
            current_installment=item["current_installment"],
            total_installments=item["total_installments"],
        )
        db.add(purchase)
        count += 1
    await db.commit()
    return count
