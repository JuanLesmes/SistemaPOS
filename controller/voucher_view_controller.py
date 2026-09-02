"""Ventana emergente con el resumen del recibo recién cobrado."""

from __future__ import annotations

import tkinter as tk
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
    ) -> None:
        self.view = VoucherView(parent, self, business, receipt, received, change)

    def event_close(self) -> None:
        if self.view.winfo_exists():
            self.view.destroy()
