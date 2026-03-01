import base64
import json
import re
from datetime import date, datetime
from decimal import Decimal

import pymupdf

from app.config import settings


def extract_text_from_pdf(content: bytes) -> str:
    doc = pymupdf.open(stream=content, filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    doc.close()
    return text


def is_scanned_pdf(content: bytes) -> bool:
    text = extract_text_from_pdf(content)
    return len(text.strip()) < 50


def extract_due_date_from_text(text: str) -> date | None:
    """Try to extract invoice due date from PDF header text."""
    patterns = [
        r"[Vv]encimento[:\s]+(\d{2})[/\-](\d{2})[/\-](\d{4})",
        r"[Dd]ata\s+de\s+[Vv]encimento[:\s]+(\d{2})[/\-](\d{2})[/\-](\d{4})",
        r"[Vv]enc\.?\s*[:\s]+(\d{2})[/\-](\d{2})[/\-](\d{4})",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            day, month, year = int(match.group(1)), int(match.group(2)), int(match.group(3))
            try:
                return date(year, month, day)
            except ValueError:
                continue
    return None


def parse_pdf_text(text: str) -> list[dict]:
    """Parse credit card invoice text and extract purchases."""
    purchases = []
    due = extract_due_date_from_text(text)

    # Common patterns for Brazilian credit card invoices:
    # DD/MM or DD/MM/YYYY  MERCHANT_NAME  VALUE
    # Some invoices also show installment info like "Parcela 2/6"
    line_pattern = re.compile(
        r"(\d{2}[/\-]\d{2}(?:[/\-]\d{2,4})?)\s+"  # date
        r"(.+?)\s+"                                   # merchant
        r"(\d{1,3}(?:\.\d{3})*,\d{2})\s*$",          # amount (BRL format)
        re.MULTILINE,
    )

    current_year = date.today().year

    for match in line_pattern.finditer(text):
        date_str = match.group(1)
        merchant = match.group(2).strip()
        amount_str = match.group(3).replace(".", "").replace(",", ".")

        # Skip payment lines
        lower_merchant = merchant.lower()
        skip_keywords = ["pagamento", "encargo", "juros", "iof", "multa", "crédito"]
        if any(kw in lower_merchant for kw in skip_keywords):
            continue

        # Parse date
        parts = re.split(r"[/\-]", date_str)
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2]) if len(parts) == 3 else current_year
        if year < 100:
            year += 2000
        try:
            purchase_date = date(year, month, day)
        except ValueError:
            continue

        amount = Decimal(amount_str)

        # Check for installment info
        installment_match = re.search(r"[Pp]arcela\s+(\d+)\s*/\s*(\d+)", merchant)
        current = 1
        total = 1
        if installment_match:
            current = int(installment_match.group(1))
            total = int(installment_match.group(2))

        total_amount = amount * total if total > 1 else amount

        purchases.append({
            "purchase_date": purchase_date,
            "due_date": due if due else purchase_date,
            "merchant": merchant,
            "installment_amount": amount,
            "total_amount": total_amount,
            "current_installment": current,
            "total_installments": total,
        })

    return purchases


async def parse_pdf_with_openai(content: bytes) -> list[dict]:
    """Convert PDF pages to images, send to GPT-4o for structured extraction."""
    from openai import AsyncOpenAI

    if not settings.openai_api_key:
        raise ValueError("OPENAI_API_KEY not configured")

    client = AsyncOpenAI(api_key=settings.openai_api_key)

    doc = pymupdf.open(stream=content, filetype="pdf")
    image_contents = []
    for page in doc:
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        b64 = base64.b64encode(img_bytes).decode("utf-8")
        image_contents.append({
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{b64}"},
        })
    doc.close()

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": (
                            "Extraia todas as compras desta fatura "
                            "de cartão de crédito.\n"
                            "Retorne APENAS um JSON array "
                            "(sem markdown, sem ```json) "
                            "com objetos contendo:\n"
                            "- purchase_date (YYYY-MM-DD)\n"
                            "- due_date (YYYY-MM-DD, data de "
                            "vencimento da fatura se visível, "
                            "senão use purchase_date)\n"
                            "- merchant (nome do estabelecimento)\n"
                            "- installment_amount "
                            "(valor da parcela, decimal)\n"
                            "- total_amount "
                            "(valor total da compra, decimal)\n"
                            "- current_installment "
                            "(número da parcela atual, int)\n"
                            "- total_installments "
                            "(total de parcelas, int)\n"
                            "Ignore pagamentos, encargos, juros, "
                            "IOF e multas. Retorne apenas compras."
                        ),
                    },
                    *image_contents,
                ],
            }
        ],
        max_tokens=4096,
        temperature=0,
    )

    raw = response.choices[0].message.content or "[]"
    # Clean potential markdown fencing
    raw = raw.strip()
    if raw.startswith("```"):
        raw = re.sub(r"^```\w*\n?", "", raw)
        raw = re.sub(r"\n?```$", "", raw)
        raw = raw.strip()

    items = json.loads(raw)

    purchases = []
    for item in items:
        try:
            purchase_date = datetime.strptime(item["purchase_date"], "%Y-%m-%d").date()
            due_date_str = item.get("due_date", item["purchase_date"])
            due_dt = datetime.strptime(due_date_str, "%Y-%m-%d").date()

            purchases.append({
                "purchase_date": purchase_date,
                "due_date": due_dt,
                "merchant": str(item["merchant"]),
                "installment_amount": Decimal(str(item["installment_amount"])),
                "total_amount": Decimal(str(item["total_amount"])),
                "current_installment": int(item.get("current_installment", 1)),
                "total_installments": int(item.get("total_installments", 1)),
            })
        except (KeyError, ValueError):
            continue

    return purchases
