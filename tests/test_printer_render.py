from decimal import Decimal

from model.product import Product
from model.receipt import PAYMENT_CARD, PAYMENT_CASH, Receipt
from model.sold_product import SoldProduct
from utils.config import BusinessSettings
from utils.printer_manager import render_receipt

BUSINESS = BusinessSettings(
    name="Tienda Ejemplo",
    nit="900.000.000-1",
    address="Calle 1 # 2 - 3",
    phone="300 000 0000",
    receipt_footer="Gracias",
)
WIDTH = 32


def make_receipt(payment_method: str) -> Receipt:
    product = Product(
        code="A1", name="Gaseosa 1.5 litros", cost=Decimal(2000), price=Decimal(3500), stock=5, category="Bebidas"
    )
    receipt = Receipt.create(payment_method, [SoldProduct(product, 1), SoldProduct(product, 1)])
    receipt.id = 42
    return receipt


def test_cash_receipt_lines_fit_paper_width_and_show_change():
    lines = render_receipt(make_receipt(PAYMENT_CASH), BUSINESS, WIDTH, received=Decimal(10000), change=Decimal(3000))
    texts = [line.text for line in lines]

    assert texts[0] == "TIENDA EJEMPLO"
    assert lines[0].align == "center" and lines[0].bold
    assert all(len(text) <= WIDTH for text in texts)
    assert "RECIBO: 42" in texts
    assert any(text.startswith("2 x $3.500") and text.endswith("$7.000") for text in texts)
    assert any(text.startswith("TOTAL") and text.endswith("$7.000") for text in texts)
    assert any(text.startswith("RECIBIDO") and text.endswith("$10.000") for text in texts)
    assert any(text.startswith("CAMBIO") and text.endswith("$3.000") for text in texts)
    assert texts[-1] == "Gracias"


def test_card_receipt_has_no_received_or_change_lines():
    texts = [line.text for line in render_receipt(make_receipt(PAYMENT_CARD), BUSINESS, WIDTH)]
    assert "PAGO: Tarjeta" in texts
    assert not any(text.startswith(("RECIBIDO", "CAMBIO")) for text in texts)
