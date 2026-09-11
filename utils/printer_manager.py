"""Impresión de recibos en impresoras térmicas ESC/POS.

Tres formas de llegar a la impresora, según ``printer.mode`` en config.json:
instalada en Windows (se le envía ESC/POS crudo por el spooler, sirve por
USB, red o Bluetooth), de red por IP (puerto 9100) o USB directo con libusb.

Este módulo no conoce la interfaz gráfica: no abre diálogos ni bloquea nada.
Si la impresora falla lanza PrinterError y el controlador decide qué mostrar.

``render_receipt`` arma las líneas del recibo como datos puros, así el formato
se puede probar sin impresora.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass
from decimal import Decimal

from model.errors import PrinterError
from model.receipt import PAYMENT_CASH, Receipt
from model.shift import Shift, ShiftSummary
from utils.config import MODE_NETWORK, MODE_USB, MODE_WINDOWS, BusinessSettings, PrinterSettings
from utils.formatters import format_price

logger = logging.getLogger(__name__)

ESC_RESET = b"\x1b\x40"
MODE_NAMES = {MODE_WINDOWS: "Impresora de Windows", MODE_NETWORK: "Red", MODE_USB: "USB directo"}


def list_windows_printers() -> list[str]:
    """Nombres de las impresoras instaladas en Windows (vacío si no se puede consultar)."""
    try:
        import win32print
    except ImportError:
        return []
    try:
        flags = win32print.PRINTER_ENUM_LOCAL | win32print.PRINTER_ENUM_CONNECTIONS
        return [entry[2] for entry in win32print.EnumPrinters(flags)]
    except Exception:
        logger.warning("No se pudieron listar las impresoras de Windows", exc_info=True)
        return []


def default_windows_printer() -> str:
    try:
        import win32print

        return win32print.GetDefaultPrinter()
    except Exception:
        return ""


def describe_connection(settings: PrinterSettings) -> str:
    """Texto corto de cómo está conectada la impresora, para el tiquete de prueba y los mensajes."""
    if settings.mode == MODE_WINDOWS:
        return f"{MODE_NAMES[MODE_WINDOWS]}: {settings.name or 'predeterminada'}"
    if settings.mode == MODE_NETWORK:
        return f"{MODE_NAMES[MODE_NETWORK]}: {settings.host}:{settings.port}"
    return f"{MODE_NAMES[MODE_USB]}: {settings.vendor_id:#06x}:{settings.product_id:#06x}"


def render_test_ticket(business: BusinessSettings, settings: PrinterSettings, when: dt.datetime | None = None) -> list:
    """Tiquete de prueba: si la regla llega al borde derecho, el ancho de papel configurado es correcto."""
    width = settings.paper_width_chars
    now = when or dt.datetime.now()
    separator = ReceiptLine("-" * width)
    ruler = "".join(str(index % 10) for index in range(1, width + 1))
    return [
        ReceiptLine(business.name.upper()[:width], "center", bold=True),
        ReceiptLine("PRUEBA DE IMPRESION", "center", bold=True),
        separator,
        ReceiptLine(f"FECHA: {now:%Y-%m-%d %H:%M}"),
        ReceiptLine(f"PAPEL: {settings.paper_width_mm} mm ({width} columnas)"[:width]),
        ReceiptLine(describe_connection(settings)[:width]),
        separator,
        ReceiptLine(ruler),
        separator,
        ReceiptLine("Si la linea de numeros llega"),
        ReceiptLine("completa al borde derecho, el"),
        ReceiptLine("ancho de papel es correcto."),
        ReceiptLine(""),
        ReceiptLine("Impresora lista.", "center", bold=True),
    ]


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
    if receipt.cashier:
        lines.append(ReceiptLine(f"ATENDIÓ: {receipt.cashier}"[:width]))
    lines.append(separator)

    for name, quantity, unit_price, total in _grouped_items(receipt):
        lines.append(ReceiptLine(name[:width]))
        detail = f"{quantity} x ${format_price(unit_price)}"
        amount = f"${format_price(total)}"
        lines.append(ReceiptLine(_justify(detail, amount, width)))

    lines.append(separator)
    if receipt.discount_total > 0:
        lines.append(ReceiptLine(_justify("DESCUENTO", f"-${format_price(receipt.discount_total)}", width)))
    lines.append(ReceiptLine(_justify("TOTAL", f"${format_price(receipt.total)}", width), bold=True))
    if receipt.tax_total > 0:
        lines.append(ReceiptLine(_justify("IVA incluido", f"${format_price(receipt.tax_total)}", width)))
    if len(receipt.payments) > 1:
        for payment in receipt.payments:
            lines.append(ReceiptLine(_justify(f"  {payment.method}", f"${format_price(payment.amount)}", width)))
    if receipt.payment_method == PAYMENT_CASH and received is not None:
        lines.append(ReceiptLine(_justify("RECIBIDO", f"${format_price(received)}", width)))
        lines.append(ReceiptLine(_justify("CAMBIO", f"${format_price(change or Decimal(0))}", width)))
    if business.receipt_footer:
        lines.append(ReceiptLine(""))
        lines.append(ReceiptLine(business.receipt_footer[:width], "center"))
    return lines


def render_shift_close(
    summary: ShiftSummary, shift: Shift, business: BusinessSettings, width: int
) -> list[ReceiptLine]:
    """Tiquete de cierre de turno (informe Z)."""
    separator = ReceiptLine("-" * width)
    lines = [
        ReceiptLine(business.name.upper(), "center", bold=True),
        ReceiptLine("CIERRE DE CAJA", "center", bold=True),
        separator,
        ReceiptLine(f"TURNO: {shift.id}"),
        ReceiptLine(f"ABRIO: {shift.opened_at:%Y-%m-%d %H:%M} {shift.opened_by or ''}"[:width]),
    ]
    if shift.closed_at:
        lines.append(ReceiptLine(f"CERRO: {shift.closed_at:%Y-%m-%d %H:%M} {shift.closed_by or ''}"[:width]))
    lines.append(separator)
    lines.append(ReceiptLine(_justify("Recibos", str(summary.receipt_count), width)))
    lines.append(ReceiptLine(_justify("Anulados", str(summary.voided_count), width)))
    lines.append(ReceiptLine(_justify("Efectivo", f"${format_price(summary.cash_sales)}", width)))
    lines.append(ReceiptLine(_justify("Tarjeta", f"${format_price(summary.card_sales)}", width)))
    lines.append(ReceiptLine(_justify("Transferencia", f"${format_price(summary.transfer_sales)}", width)))
    lines.append(ReceiptLine(_justify("Devoluciones", f"-${format_price(summary.returns)}", width)))
    lines.append(ReceiptLine(_justify("TOTAL VENTAS", f"${format_price(summary.total_sales)}", width), bold=True))
    lines.append(separator)
    lines.append(ReceiptLine(_justify("Base inicial", f"${format_price(shift.opening_cash)}", width)))
    lines.append(ReceiptLine(_justify("Efectivo esperado", f"${format_price(summary.expected_cash)}", width)))
    if shift.counted_cash is not None and shift.difference is not None:
        lines.append(ReceiptLine(_justify("Efectivo contado", f"${format_price(shift.counted_cash)}", width)))
        sign = "-" if shift.difference < 0 else ""
        lines.append(
            ReceiptLine(_justify("Diferencia", f"{sign}${format_price(abs(shift.difference))}", width), bold=True)
        )
    if shift.notes:
        lines.append(separator)
        lines.append(ReceiptLine(shift.notes[:width]))
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
        self.print_lines(lines, f"recibo {receipt.id}")

    def print_shift_close(self, summary: ShiftSummary, shift: Shift) -> None:
        if not self._printer.enabled:
            return
        self.print_lines(render_shift_close(summary, shift, self._business, self._printer.paper_width_chars), "cierre")

    @property
    def drawer_enabled(self) -> bool:
        return self._printer.enabled and self._printer.open_drawer

    def open_drawer(self) -> None:
        """Abre el cajón monedero conectado a la impresora (pulso ESC/POS)."""
        if not self.drawer_enabled:
            return
        device = self._open()
        try:
            device.cashdraw(2)
        except Exception as exc:
            logger.error("No se pudo abrir el cajón", exc_info=True)
            raise PrinterError(f"No se pudo abrir el cajón monedero: {exc}") from exc
        finally:
            _close_quietly(device)

    def print_test(self) -> None:
        """Imprime el tiquete de prueba aunque la impresión esté desactivada; abre el cajón si está configurado."""
        lines = render_test_ticket(self._business, self._printer)
        self.print_lines(lines, "tiquete de prueba", pulse_drawer=self._printer.open_drawer)

    def print_lines(self, lines: list[ReceiptLine], what: str = "tiquete", pulse_drawer: bool = False) -> None:
        device = self._open()
        try:
            device._raw(ESC_RESET)
            for line in lines:
                device.set(align=line.align, bold=line.bold)
                device.text(line.text + "\n")
            device.text("\n\n")
            if self._printer.cut:
                device.cut()
            else:
                device.text("\n\n\n")
            if pulse_drawer:
                device.cashdraw(2)
        except Exception as exc:  # la librería lanza tipos variados según el fallo
            logger.error("Error imprimiendo %s", what, exc_info=True)
            raise PrinterError(f"No se pudo imprimir el {what}: {exc}") from exc
        finally:
            _close_quietly(device)

    def _open(self):
        """Abre la conexión según el modo configurado. Lanza PrinterError con un mensaje accionable."""
        s = self._printer
        try:
            from escpos import printer as backends
        except ImportError as exc:
            raise PrinterError("La librería de impresión (python-escpos) no está instalada.") from exc
        if s.mode == MODE_WINDOWS:
            if not backends.Win32Raw.is_usable():
                raise PrinterError("Falta el componente pywin32 para imprimir por Windows. Reinstale la aplicación.")
            device = backends.Win32Raw(s.name)
            try:
                device.open(job_name="SistemaPOS")
            except Exception as exc:
                logger.error("No se pudo abrir la impresora de Windows", exc_info=True)
                which = f"'{s.name}'" if s.name else "predeterminada"
                raise PrinterError(
                    f"No se pudo usar la impresora de Windows {which}. Verifique que esté instalada, encendida "
                    "y sin trabajos atascados en la cola de impresión."
                ) from exc
            return device
        if s.mode == MODE_NETWORK:
            device = backends.Network(s.host, s.port, timeout=max(2, s.timeout_ms / 1000))
            try:
                device.open()
            except Exception as exc:
                logger.error("No se pudo conectar con la impresora de red", exc_info=True)
                raise PrinterError(
                    f"No responde la impresora de red en {s.host}:{s.port}. "
                    "Verifique la IP, el cable y que esté encendida."
                ) from exc
            return device
        device = backends.Usb(
            idVendor=s.vendor_id, idProduct=s.product_id, timeout=s.timeout_ms, in_ep=s.in_ep, out_ep=s.out_ep
        )
        try:
            device.open()
        except Exception as exc:
            logger.error("No se pudo abrir la impresora USB", exc_info=True)
            raise PrinterError(
                "No se encontró la impresora USB. Verifique que esté encendida, que los IDs de config.json sean "
                "los de la impresora y que tenga el controlador WinUSB (Zadig)."
            ) from exc
        return device


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
