"""Ventana emergente con el resumen del recibo recién cobrado."""

from __future__ import annotations

import tkinter as tk
from collections.abc import Callable
from decimal import Decimal

from model.receipt import Receipt
from utils.config import BusinessSettings
from view.voucher_view import VoucherView


class VoucherViewController:
    def __init__(
        self,
        parent: tk.Misc,
        business: BusinessSettings,
        receipt: Receipt,
        received: Decimal | None,
        change: Decimal,
        on_print: Callable[[], None] | None = None,
    ) -> None:
        self._on_print = on_print
        self.view = VoucherView(parent, self, business, receipt, received, change, can_print=on_print is not None)

    def event_print(self) -> None:
        if self._on_print is not None:
            self._on_print()

    def event_close(self) -> None:
        if self.view.winfo_exists():
            self.view.destroy()
