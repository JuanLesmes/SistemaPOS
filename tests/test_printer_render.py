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


class _FakeDevice:
    def __init__(self):
        self.raw: list[bytes] = []
        self.texts: list[str] = []
        self.cuts = 0
        self.drawer_pulses = 0
        self.closed = False

    def _raw(self, data):
        self.raw.append(data)

    def set(self, **kwargs):
        pass

    def text(self, value):
        self.texts.append(value)

    def cut(self):
        self.cuts += 1

    def cashdraw(self, pin):
        self.drawer_pulses += 1

    def close(self):
        self.closed = True


def _printer(**overrides):
    from utils.config import PrinterSettings

    base = dict(enabled=True, vendor_id=1, product_id=2, in_ep=0x81, out_ep=0x02, timeout_ms=1000, paper_width_chars=48)
    base.update(overrides)
    return PrinterSettings(**base)


def test_test_ticket_ruler_matches_the_paper_width():
    from utils.printer_manager import render_test_ticket

    lines = render_test_ticket(BUSINESS, _printer(paper_width_chars=32, paper_width_mm=58))
    texts = [line.text for line in lines]
    assert all(len(text) <= 32 for text in texts)
    ruler = next(text for text in texts if text.startswith("1234567890"))
    assert len(ruler) == 32
    assert any("58 mm (32 columnas)" in text for text in texts)
    assert any("Impresora de Windows" in text for text in texts)


def test_print_test_sends_lines_cuts_and_pulses_drawer(monkeypatch):
    from utils.printer_manager import ReceiptPrinter

    device = _FakeDevice()
    printer = ReceiptPrinter(_printer(open_drawer=True), BUSINESS)
    monkeypatch.setattr(printer, "_open", lambda: device)
    printer.print_test()
    assert device.raw[0] == b"\x1b\x40"
    assert any("PRUEBA DE IMPRESION" in text for text in device.texts)
    assert device.cuts == 1 and device.drawer_pulses == 1 and device.closed

    quiet = _FakeDevice()
    printer = ReceiptPrinter(_printer(cut=False), BUSINESS)
    monkeypatch.setattr(printer, "_open", lambda: quiet)
    printer.print_test()
    assert quiet.cuts == 0 and quiet.drawer_pulses == 0


def test_windows_printer_that_does_not_exist_gives_a_clear_error():
    import pytest

    from model.errors import PrinterError
    from utils.printer_manager import ReceiptPrinter

    printer = ReceiptPrinter(_printer(mode="windows", name="Impresora que no existe 12345"), BUSINESS)
    with pytest.raises(PrinterError, match="Impresora que no existe"):
        printer.print_test()
