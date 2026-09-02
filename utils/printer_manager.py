"""Impresión de recibos en impresora térmica ESC/POS por USB.

Este módulo no conoce la interfaz gráfica: no abre diálogos ni bloquea nada.
Si la impresora falla lanza PrinterError y el controlador decide qué mostrar.

``render_receipt`` arma las líneas del recibo como datos puros, así el formato
se puede probar sin impresora.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from decimal import Decimal

from model.errors import PrinterError
from model.receipt import PAYMENT_CASH, Receipt
from utils.config import BusinessSettings, PrinterSettings
from utils.formatters import format_price

logger = logging.getLogger(__name__)

ESC_RESET = b"\x1b\x40"


@dataclass(frozen=True)
class ReceiptLine:
    text: str
    align: str = "left"  # left | center | right
    bold: bool = False


def render_receipt(
    receipt: Receipt,
    business: BusinessSettings,
    width: int,
    received: Decimal | None = None,
    change: Decimal | None = None,
) -> list[ReceiptLine]:
    """Convierte un recibo en líneas de texto listas para una impresora de ``width`` columnas."""
    separator = ReceiptLine("-" * width)
    lines: list[ReceiptLine] = [ReceiptLine(business.name.upper(), "center", bold=True)]
    for detail in (
        business.address,
        f"NIT: {business.nit}" if business.nit else "",
        f"Tel: {business.phone}" if business.phone else "",
    ):
        if detail:
            lines.append(ReceiptLine(detail[:width], "center"))
    lines.append(separator)
    lines.append(ReceiptLine(f"RECIBO: {receipt.id if receipt.id is not None else '-'}"))
    lines.append(ReceiptLine(f"FECHA: {receipt.date:%Y-%m-%d} {receipt.time:%H:%M}"))
    lines.append(ReceiptLine(f"PAGO: {receipt.payment_method}"))
    lines.append(separator)

    for name, quantity, unit_price, total in _grouped_items(receipt):
        lines.append(ReceiptLine(name[:width]))
        detail = f"{quantity} x ${format_price(unit_price)}"
        amount = f"${format_price(total)}"
        lines.append(ReceiptLine(_justify(detail, amount, width)))

    lines.append(separator)
    lines.append(ReceiptLine(_justify("TOTAL", f"${format_price(receipt.total)}", width), bold=True))
    if receipt.payment_method == PAYMENT_CASH and received is not None:
        lines.append(ReceiptLine(_justify("RECIBIDO", f"${format_price(received)}", width)))
        lines.append(ReceiptLine(_justify("CAMBIO", f"${format_price(change or Decimal(0))}", width)))
    if business.receipt_footer:
        lines.append(ReceiptLine(""))
        lines.append(ReceiptLine(business.receipt_footer[:width], "center"))
    return lines


class ReceiptPrinter:
    def __init__(self, printer: PrinterSettings, business: BusinessSettings) -> None:
        self._printer = printer
        self._business = business

    @property
    def enabled(self) -> bool:
        return self._printer.enabled

    def print_receipt(
        self,
        receipt: Receipt,
        received: Decimal | None = None,
        change: Decimal | None = None,
    ) -> None:
        """Imprime el recibo. Lanza PrinterError si la impresora no responde."""
        if not self._printer.enabled:
            logger.info("Impresión desactivada en config.json; recibo %s no impreso", receipt.id)
            return
        lines = render_receipt(receipt, self._business, self._printer.paper_width_chars, received, change)
        device = self._open()
        try:
            device._raw(ESC_RESET)
            for line in lines:
                device.set(align=line.align, bold=line.bold)
                device.text(line.text + "\n")
            device.text("\n\n")
            device.cut()
        except Exception as exc:  # la librería lanza tipos variados según el fallo USB
            logger.error("Error imprimiendo recibo %s", receipt.id, exc_info=True)
            raise PrinterError(f"No se pudo imprimir el recibo: {exc}") from exc
        finally:
            _close_quietly(device)

    def _open(self):
        try:
            from escpos.printer import Usb
        except ImportError as exc:
            raise PrinterError("La librería de impresión (python-escpos) no está instalada.") from exc
        s = self._printer
        try:
            return Usb(
                idVendor=s.vendor_id,
                idProduct=s.product_id,
                timeout=s.timeout_ms,
                in_ep=s.in_ep,
                out_ep=s.out_ep,
            )
        except Exception as exc:
            logger.error("No se pudo abrir la impresora USB", exc_info=True)
            raise PrinterError(
                "No se encontró la impresora. Verifique que esté encendida y conectada por USB."
            ) from exc


def _grouped_items(receipt: Receipt) -> list[tuple[str, int, Decimal, Decimal]]:
    """Agrupa líneas del mismo producto: (nombre, cantidad, precio unitario, total)."""
    grouped: dict[str, list] = {}
    for sp in receipt.sold_products:
        entry = grouped.get(sp.code)
        if entry is None:
            grouped[sp.code] = [sp.product.name, sp.quantity, sp.unit_price]
        else:
            entry[1] += sp.quantity
    return [(name, qty, price, price * qty) for name, qty, price in grouped.values()]


def _justify(left: str, right: str, width: int) -> str:
    gap = width - len(left) - len(right)
    if gap < 1:
        return f"{left} {right}"
    return left + " " * gap + right


def _close_quietly(device) -> None:
    try:
        device.close()
    except Exception:
        logger.warning("No se pudo cerrar la impresora", exc_info=True)
