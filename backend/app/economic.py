import re
import unicodedata
from typing import Literal

EconomicType = Literal[
    "salary",
    "benefit",
    "other_income",
    "expense",
    "transfer",
    "card_payment",
    "refund",
    "investment",
    "voucher_expense",
]

CASH_EXCLUDED_TYPES = ("transfer", "card_payment", "refund", "investment", "voucher_expense")


def normalize_text(value: str) -> str:
    value = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode().lower()
    return re.sub(r"[^a-z]+", " ", value).strip()


def economic_type(
    transaction_type: str,
    description: str,
    category: str,
    source: str,
    account_type: str | None,
) -> tuple[EconomicType, float]:
    text = normalize_text(f"{description} {category}")
    normalized_category = normalize_text(category)
    if source == "voucher" and transaction_type == "debit":
        return "voucher_expense", 1
    if normalized_category in {"transfer", "transfers", "same person transfer"} or any(
        term in text
        for term in (
            "transferencia entre contas",
            "mesma titularidade",
            "same person transfer",
            "own account transfer",
            "internal transfer",
        )
    ):
        return "transfer", 0.95
    if (
        transaction_type == "debit"
        and account_type != "credit"
        and any(
            term in text
            for term in (
                "pagamento fatura",
                "pagto fatura",
                "fatura cartao",
                "credit card payment",
            )
        )
    ):
        return "card_payment", 0.95
    if transaction_type == "credit" and any(
        term in text
        for term in ("estorno", "reembolso", "refund", "reversal", "chargeback", "cashback")
    ):
        return "refund", 0.95
    if transaction_type == "credit" and any(
        term in text
        for term in ("salario", "folha de pagamento", "provento", "holerite", "salary", "payroll")
    ):
        return "salary", 0.98
    if transaction_type == "credit" and any(
        term in text
        for term in (
            "vale alimentacao",
            "vale refeicao",
            "alelo",
            "sodexo",
            "ticket",
            "food allowance",
            "meal voucher",
        )
    ):
        return "benefit", 0.95
    if transaction_type == "debit" and any(
        term in text for term in ("aplicacao", "investimento", "aporte", "investment")
    ):
        return "investment", 0.9
    return ("other_income", 0.45) if transaction_type == "credit" else ("expense", 0.8)
