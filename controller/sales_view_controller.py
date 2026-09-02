"""Pantalla de ventas: lectura de códigos, armado de la venta y cobro."""

from __future__ import annotations

import logging
import queue
import threading
import tkinter as tk
from decimal import Decimal
from tkinter import messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.errors import PrinterError
from model.product import Product
from model.receipt import PAYMENT_CARD, PAYMENT_CASH, PAYMENT_TRANSFER, Receipt
from model.sold_product import SoldProduct
from utils.barcode_reader import BarcodeReader
from utils.formatters import format_price, parse_money
from utils.printer_manager import ReceiptPrinter
from view.sales_view import SalesView

logger = logging.getLogger(__name__)

PRINT_POLL_MS = 250
PRINT_THREAD_PREFIX = "print-receipt-"


class SalesViewController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.lines: list[SoldProduct] = []
        self.view = SalesView(parent, self)

        settings = main_controller.settings
        self.printer = ReceiptPrinter(settings.printer, settings.business)
        self.view.set_printer_available(self.printer.enabled)
        self.reader = BarcodeReader(self.view.winfo_toplevel(), self.on_barcode)
        self._print_errors: queue.Queue[str] = queue.Queue()
        self._polling_printer = False
        self.reset_sale()

    # ------------------------------------------------------------------ ciclo de vida
    def on_show(self) -> None:
        self.reset_sale()
        self.reader.enable()
        self.view.focus_set()

    def on_hide(self) -> None:
        self.reader.disable()

    def reset_sale(self) -> None:
        self.lines.clear()
        self.view.clear_received_amount()
        self.view.reset_print_option()
        self._refresh()

    # ------------------------------------------------------------------ eventos
    @guarded
    def on_barcode(self, code: str) -> None:
        product = self.db.get_product(code)
        if product is None:
            messagebox.showwarning("Producto no encontrado", f"No existe un producto activo con el código {code}.")
            return
        self.add_line(product)

    def add_line(self, product: Product, quantity: int = 1) -> None:
        """Agrega unidades de un producto; si ya está en la venta, suma a esa línea."""
        existing = next((sp for sp in self.lines if sp.code == product.code), None)
        wanted = quantity + (existing.quantity if existing else 0)
        if wanted > product.stock:
            messagebox.showwarning(
                "Sin existencias",
                f"'{product.name}' solo tiene {product.stock} unidades disponibles.",
            )
            return
        if existing is not None:
            existing.quantity = wanted
        else:
            self.lines.append(SoldProduct(product=product, quantity=quantity))
        self._refresh()

    @guarded
    def event_remove_line(self) -> None:
        index = self.view.selected_index()
        if index is None:
            messagebox.showwarning("Seleccione un producto", "Seleccione en la tabla el producto que desea quitar.")
            return
        del self.lines[index]
        self._refresh()

    @guarded
    def event_cash_payment(self) -> None:
        if not self.lines:
            self._warn_empty_sale()
            return
        received_text = self.view.get_received_amount()
        if not received_text:
            raise ValueError("Escriba el monto recibido.")
        received = parse_money(received_text)
        total = self.total()
        if received < total:
            raise ValueError(f"Monto insuficiente: faltan ${format_price(total - received)}.")
        self._checkout(PAYMENT_CASH, received)

    @guarded
    def event_card_payment(self) -> None:
        self._checkout(PAYMENT_CARD)

    @guarded
    def event_transfer_payment(self) -> None:
        self._checkout(PAYMENT_TRANSFER)

    def event_back(self) -> None:
        self.main_controller.show_menu()

    # ------------------------------------------------------------------ apoyo
    def total(self) -> Decimal:
        return sum((sp.total for sp in self.lines), Decimal(0))

    def _refresh(self) -> None:
        self.view.load_table(self.lines)
        self.view.set_total(self.total())

    def _warn_empty_sale(self) -> None:
        messagebox.showwarning("Venta vacía", "Agregue productos antes de cobrar.")

    def _checkout(self, payment_method: str, received: Decimal | None = None) -> None:
        if not self.lines:
            self._warn_empty_sale()
            return
        receipt = Receipt.create(payment_method, self.lines)
        receipt.id = self.db.add_receipt(receipt)
        change = received - receipt.total if received is not None else Decimal(0)
        if self.view.wants_receipt():
            self._print_in_background(receipt, received, change)
        self.reset_sale()
        self.main_controller.show_voucher_view(receipt, received, change)

    def _print_in_background(self, receipt: Receipt, received: Decimal | None, change: Decimal) -> None:
        """Imprime en un hilo aparte para que la caja nunca se congele esperando la impresora."""
        if not self.printer.enabled:
            return

        def job() -> None:
            try:
                self.printer.print_receipt(receipt, received, change)
            except PrinterError as exc:
                self._print_errors.put(str(exc))
            except Exception:
                logger.exception("Error inesperado imprimiendo el recibo %s", receipt.id)
                self._print_errors.put("Error inesperado al imprimir. Revise logs/app.log.")

        threading.Thread(target=job, name=f"{PRINT_THREAD_PREFIX}{receipt.id}", daemon=True).start()
        if not self._polling_printer:
            self._polling_printer = True
            self.view.after(PRINT_POLL_MS, self._poll_print_errors)

    def _poll_print_errors(self) -> None:
        """Corre en el hilo de la interfaz: muestra los errores que dejaron los hilos de impresión."""
        self._show_pending_print_errors()
        still_printing = any(t.name.startswith(PRINT_THREAD_PREFIX) for t in threading.enumerate())
        if still_printing:
            self.view.after(PRINT_POLL_MS, self._poll_print_errors)
        else:
            self._show_pending_print_errors()
            self._polling_printer = False

    def _show_pending_print_errors(self) -> None:
        while True:
            try:
                message = self._print_errors.get_nowait()
            except queue.Empty:
                return
            messagebox.showwarning("Impresión", f"{message}\nLa venta quedó registrada.")
