import asyncio
import re
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation
from urllib.parse import parse_qs, quote, unquote, urlsplit
from zoneinfo import ZoneInfo

import httpx
from bs4 import BeautifulSoup, Tag

SEFAZ_HOST = "nfce.sefaz.al.gov.br"
SEFAZ_URL = f"https://{SEFAZ_HOST}/QRCode/consultarNFCe.jsp"
LOCAL_TIMEZONE = ZoneInfo("America/Maceio")


class SefazError(ValueError):
    pass


class SefazUnavailable(SefazError):
    pass


@dataclass(frozen=True)
class ParsedInvoiceItem:
    description: str
    product_code: str | None
    quantity: Decimal
    unit: str | None
    unit_price: Decimal
    total_price: Decimal


@dataclass(frozen=True)
class ParsedInvoice:
    access_key: str
    number: str | None
    series: str | None
    issue_datetime: datetime
    gross_amount: Decimal
    discount_amount: Decimal
    total_amount: Decimal
    merchant_cnpj: str | None
    merchant_name: str
    merchant_address: str | None
    source_url: str
    payment_method_raw: str | None
    protocol: str | None
    items: list[ParsedInvoiceItem]
    raw: dict[str, object]


def _clean(value: str) -> str:
    return " ".join(value.replace("\xa0", " ").split())


def digits(value: str | None) -> str | None:
    normalized = re.sub(r"\D", "", value or "")
    return normalized or None


def parse_brl_decimal(value: str) -> Decimal:
    normalized = re.sub(r"[^\d,.-]", "", value).replace(".", "").replace(",", ".")
    try:
        return Decimal(normalized)
    except InvalidOperation as exc:
        raise SefazError(f"Valor inválido na nota: {value}") from exc


def normalize_nfce_url(value: str) -> str:
    candidate = value.strip()
    if "://" not in candidate:
        candidate = unquote(candidate)
        payload = candidate.removeprefix("p=")
        if "|" not in payload:
            raise SefazError("Cole o link completo ou o conteúdo do QR code da NFC-e")
        candidate = f"{SEFAZ_URL}?p={quote(payload, safe='')}"

    parsed = urlsplit(candidate)
    try:
        valid_port = parsed.port in (None, 443)
    except ValueError as exc:
        raise SefazError("URL da NFC-e inválida") from exc
    if parsed.scheme != "https" or parsed.hostname != SEFAZ_HOST or not valid_port:
        raise SefazError("Apenas links oficiais da NFC-e de Alagoas são aceitos")

    payload = parse_qs(parsed.query).get("p", [""])[0]
    access_key = payload.split("|", 1)[0]
    if not re.fullmatch(r"\d{44}", access_key):
        raise SefazError("O QR code não contém uma chave de acesso válida")
    return candidate


def _value_after_label(node: Tag, field: str) -> str:
    strong = node.find("strong")
    text = _clean(node.get_text(" ", strip=True))
    if strong:
        label = _clean(strong.get_text(" ", strip=True))
        text = text.removeprefix(label).lstrip(": ")
    if not text:
        raise SefazError(f"Campo {field} ausente em um item da nota")
    return text


def _item_text(row: Tag, class_name: str, field: str) -> str:
    node = row.find("span", class_=class_name)
    if not isinstance(node, Tag):
        raise SefazError(f"Campo {field} ausente em um item da nota")
    return _value_after_label(node, field)


def parse_nfce_html(url: str, html: bytes | str) -> ParsedInvoice:
    source_url = normalize_nfce_url(url)
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find("div", id="conteudo")
    if not isinstance(content, Tag):
        raise SefazError("A página da SEFAZ não contém os dados da nota")

    merchant_node = content.find("div", class_="txtTopo")
    merchant_name = _clean(merchant_node.get_text(" ", strip=True)) if merchant_node else ""
    if not merchant_name:
        raise SefazError("O estabelecimento não foi encontrado na nota")

    text_nodes = content.find_all("div", class_="text")
    merchant_address = next(
        (_clean(node.get_text(" ", strip=True)) for node in text_nodes if "CNPJ" not in node.text),
        None,
    )
    cnpj_text = next(
        (_clean(node.get_text(" ", strip=True)) for node in text_nodes if "CNPJ" in node.text),
        None,
    )

    totals: dict[str, str] = {}
    total_node = content.find("div", id="totalNota")
    if isinstance(total_node, Tag):
        for row in total_node.find_all("div", id="linhaTotal"):
            label = row.find("label")
            amount = row.find("span", class_="totalNumb")
            if label and amount and "tx" not in (label.get("class") or []):
                totals[_clean(label.get_text(" ", strip=True)).rstrip(":")] = _clean(
                    amount.get_text(" ", strip=True)
                )
        payment_label = total_node.find("div", id="linhaForma")
        payment_row = (
            payment_label.find_next_sibling("div", id="linhaTotal") if payment_label else None
        )
        if isinstance(payment_row, Tag):
            label = payment_row.find("label", class_="tx")
            amount = payment_row.find("span", class_="totalNumb")
            if label:
                totals["forma_pagamento"] = _clean(label.get_text(" ", strip=True))
            if amount:
                totals["valor_pago_na_forma"] = _clean(amount.get_text(" ", strip=True))

    total_text = totals.get("Valor a pagar R$") or totals.get("Valor total R$")
    if not total_text:
        raise SefazError("O valor total não foi encontrado na nota")
    total_amount = parse_brl_decimal(total_text)
    gross_amount = parse_brl_decimal(totals.get("Valor total R$", total_text))
    discount_amount = parse_brl_decimal(totals.get("Descontos R$", "0"))

    info_node = soup.find("div", id="infos")
    info_text = _clean(info_node.get_text(" ", strip=True)) if info_node else ""
    number = re.search(r"Número:\s*(\d+)", info_text)
    series = re.search(r"Série:\s*(\d+)", info_text)
    issued = re.search(r"Emissão:\s*(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})", info_text)
    protocol = re.search(
        r"Protocolo de Autorização:\s*(\d+\s+\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2}:\d{2})",
        info_text,
    )
    if not issued:
        raise SefazError("A data de emissão não foi encontrada na nota")
    issue_datetime = datetime.strptime(issued.group(1), "%d/%m/%Y %H:%M:%S").replace(
        tzinfo=LOCAL_TIMEZONE
    )

    table = content.find("table")
    if not isinstance(table, Tag):
        raise SefazError("A lista de itens não foi encontrada na nota")
    items: list[ParsedInvoiceItem] = []
    raw_items: list[dict[str, str | None]] = []
    for row in table.find_all("tr"):
        title = row.find("span", class_="txtTit")
        if not title:
            continue
        code_node = row.find("span", class_="RCod")
        code = (
            _clean(code_node.get_text(" ", strip=True)).replace("(Código:", "").rstrip(")").strip()
            if code_node
            else None
        )
        raw_item = {
            "produto": _clean(title.get_text(" ", strip=True)),
            "codigo": code,
            "quantidade": _item_text(row, "Rqtd", "quantidade"),
            "unidade": _item_text(row, "RUN", "unidade"),
            "valor_unitario": _item_text(row, "RvlUnit", "valor unitário"),
            "valor_total": _item_text(row, "valor", "valor total"),
        }
        raw_items.append(raw_item)
        items.append(
            ParsedInvoiceItem(
                description=raw_item["produto"] or "Item",
                product_code=raw_item["codigo"],
                quantity=parse_brl_decimal(raw_item["quantidade"] or "0"),
                unit=raw_item["unidade"],
                unit_price=parse_brl_decimal(raw_item["valor_unitario"] or "0"),
                total_price=parse_brl_decimal(raw_item["valor_total"] or "0"),
            )
        )
    if not items:
        raise SefazError("A nota não contém itens legíveis")

    expected_count = totals.get("Qtd. total de itens")
    if expected_count and int(parse_brl_decimal(expected_count)) != len(items):
        raise SefazError("A quantidade de itens da nota não confere")

    payload = parse_qs(urlsplit(source_url).query)["p"][0]
    raw_header: dict[str, str | None] = {
        **totals,
        "codigo_nota": payload.split("|", 1)[0],
        "estabelecimento_nome": merchant_name,
        "estabelecimento_endereco": merchant_address,
        "cnpj": cnpj_text,
        "numero": number.group(1) if number else None,
        "serie": series.group(1) if series else None,
        "emissao": issued.group(1),
        "protocolo_autorizacao": protocol.group(1) if protocol else None,
    }
    return ParsedInvoice(
        access_key=raw_header["codigo_nota"] or "",
        number=raw_header["numero"],
        series=raw_header["serie"],
        issue_datetime=issue_datetime,
        gross_amount=gross_amount,
        discount_amount=discount_amount,
        total_amount=total_amount,
        merchant_cnpj=digits(cnpj_text),
        merchant_name=merchant_name,
        merchant_address=merchant_address,
        source_url=source_url,
        payment_method_raw=totals.get("forma_pagamento"),
        protocol=raw_header["protocolo_autorizacao"],
        items=items,
        raw={"nota_info": raw_header, "items": raw_items},
    )


async def fetch_nfce(url: str) -> ParsedInvoice:
    source_url = normalize_nfce_url(url)
    headers = {"User-Agent": "Planna/0.2 (+painel-financeiro-domestico)"}
    async with httpx.AsyncClient(timeout=10, headers=headers) as client:
        for attempt in range(3):
            try:
                response = await client.get(source_url)
                response.raise_for_status()
                return parse_nfce_html(source_url, response.content)
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code < 500 or attempt == 2:
                    raise SefazUnavailable("A SEFAZ recusou a consulta da nota") from exc
            except httpx.RequestError as exc:
                if attempt == 2:
                    raise SefazUnavailable("Não foi possível consultar a SEFAZ") from exc
            await asyncio.sleep(0.25 * (2**attempt))
    raise SefazUnavailable("Não foi possível consultar a SEFAZ")
