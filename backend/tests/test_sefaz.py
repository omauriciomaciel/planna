from decimal import Decimal
from types import SimpleNamespace

import pytest

from app.invoices import _normalize_product, _similarity, choose_match
from app.sefaz import SefazError, normalize_nfce_url, parse_brl_decimal, parse_nfce_html

ACCESS_KEY = "27260620300157007403651160000125469449142260"
URL = f"https://nfce.sefaz.al.gov.br/QRCode/consultarNFCe.jsp?p={ACCESS_KEY}%7C2%7C1"
HTML = """
<div id="conteudo">
  <div class="txtTopo">Mercado da Esquina</div>
  <div class="text">Rua das Flores, 10</div>
  <div class="text">CNPJ: 20.300.157/0001-74</div>
  <table>
    <tr>
      <td>
        <span class="txtTit">Arroz</span>
        <span class="RCod">(Código: 123)</span>
        <span class="Rqtd"><strong>Qtde.:</strong> 2,0000</span>
        <span class="RUN"><strong>UN:</strong> UN</span>
        <span class="RvlUnit"><strong>Vl. Unit.:</strong> 10,00</span>
        <span class="valor"><strong>Vl. Total:</strong> 20,00</span>
      </td>
    </tr>
  </table>
  <div id="totalNota">
    <div id="linhaTotal"><label>Qtd. total de itens:</label><span class="totalNumb">1</span></div>
    <div id="linhaTotal"><label>Valor total R$:</label><span class="totalNumb">20,00</span></div>
    <div id="linhaTotal"><label>Descontos R$:</label><span class="totalNumb">0,00</span></div>
    <div id="linhaTotal"><label>Valor a pagar R$:</label><span class="totalNumb">20,00</span></div>
    <div id="linhaForma"></div>
    <div id="linhaTotal"><label class="tx">Vale Alimentação</label><span class="totalNumb">20,00</span></div>
  </div>
</div>
<div id="infos">
  Número: 12546 Série: 116 Emissão: 10/09/2026 18:30:00
  Protocolo de Autorização: 123456 10/09/2026 18:31:00
</div>
"""


def test_parses_real_sefaz_contract_with_decimal_money() -> None:
    invoice = parse_nfce_html(URL, HTML)

    assert invoice.access_key == ACCESS_KEY
    assert invoice.merchant_cnpj == "20300157000174"
    assert invoice.total_amount == Decimal("20.00")
    assert invoice.payment_method_raw == "Vale Alimentação"
    assert invoice.items[0].quantity == Decimal("2.0000")
    assert invoice.items[0].unit_price == Decimal("10.00")
    assert parse_brl_decimal("R$ 1.234,56") == Decimal("1234.56")


def test_rejects_non_sefaz_urls_and_resolves_ambiguous_cnpj() -> None:
    with pytest.raises(SefazError):
        normalize_nfce_url(f"https://example.com/?p={ACCESS_KEY}%7C2")

    first = SimpleNamespace(merchant_cnpj="11.111.111/0001-11")
    second = SimpleNamespace(merchant_cnpj="20.300.157/0001-74")
    match, confidence = choose_match([first, second], "20300157000174")
    assert match is second
    assert confidence == Decimal("1.00")


def test_product_similarity_normalizes_accents_and_rejects_different_items() -> None:
    detergent = _normalize_product("DETERGENTE YPÊ 500 ML")
    assert _similarity(detergent, _normalize_product("Detergente Ype 500ml")) >= 0.82
    assert _similarity(detergent, _normalize_product("Coca Cola 2 litros")) < 0.82
