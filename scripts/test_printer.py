"""Imprime un recibo de prueba con la configuración de config.json.

Ejecutar desde la raíz del proyecto: python scripts/test_printer.py
"""

import datetime as dt
import sys
from decimal import Decimal
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model.errors import AppError  # noqa: E402
from model.product import Product  # noqa: E402
from model.receipt import PAYMENT_CASH, Receipt  # noqa: E402
from model.sold_product import SoldProduct  # noqa: E402
from utils.config import load_settings  # noqa: E402
from utils.printer_manager import ReceiptPrinter  # noqa: E402


def main() -> int:
    try:
        settings = load_settings()
        product = Product(
            code="0000", name="Producto de prueba", cost=Decimal(800), price=Decimal(1000), stock=1, category="Prueba"
        )
        receipt = Receipt.create(PAYMENT_CASH, [SoldProduct(product, 2)], when=dt.datetime.now())
        receipt.id = 0
        ReceiptPrinter(settings.printer, settings.business).print_receipt(
            receipt, received=Decimal(5000), change=Decimal(3000)
        )
    except AppError as exc:
        print(f"Error: {exc}")
        return 1
    print("Recibo de prueba enviado. Verifique la impresora.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
