"""Ventana emergente con el resumen del recibo: productos, total y cambio."""

from __future__ import annotations

from decimal import Decimal

import customtkinter as ctk

from model.receipt import PAYMENT_CASH, Receipt
from utils.config import BusinessSettings
from utils.formatters import format_price
from view import theme
from view.widgets import button, fill_table, make_table

COLUMNS = (
    ("cantidad", "Cant.", 70, "center", False),
    ("nombre", "Producto", 280, "w"),
    ("precio", "Precio", 120, "e", False),
    ("total", "Total", 120, "e", False),
)


class VoucherView(ctk.CTkToplevel):
    def __init__(
        self,
        parent,
        controller,
        business: BusinessSettings,
        receipt: Receipt,
        received: Decimal | None,
        change: Decimal,
        can_print: bool = False,
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.business = business
        self.receipt = receipt
        self.received = received
        self.change = change
        self.can_print = can_print

        self.title("Recibo de venta")
        self.geometry("720x620+120+90")
        self.minsize(640, 540)
        self.configure(fg_color=theme.BACKGROUND)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.controller.event_close)
        self.bind("<Escape>", lambda _event: self.controller.event_close())
        self.bind("<Return>", lambda _event: self.controller.event_close())

        self._create_widgets()
        self.lift()
        self.focus_force()

    def _create_widgets(self) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0)
        header.pack(side="top", fill="x")
        ctk.CTkLabel(
            header, text=self.business.name, font=theme.font(20, bold=True), text_color=theme.ON_DARK, anchor="w"
        ).pack(anchor="w", padx=24, pady=(16, 0))
        details = "  ·  ".join(
            part
            for part in (
                f"NIT {self.business.nit}" if self.business.nit else "",
                self.business.address,
                f"Tel. {self.business.phone}" if self.business.phone else "",
            )
            if part
        )
        ctk.CTkLabel(header, text=details, font=theme.font(12), text_color=theme.ON_DARK_MUTED, anchor="w").pack(
            anchor="w", padx=24, pady=(0, 14)
        )

        info = ctk.CTkFrame(self, fg_color="transparent")
        info.pack(fill="x", padx=24, pady=(14, 6))
        ctk.CTkLabel(
            info,
            text=f"Recibo N° {str(self.receipt.id or 0).zfill(6)}",
            font=theme.font(16, bold=True),
            text_color=theme.TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            info,
            text=f"{self.receipt.date:%d/%m/%Y}  {self.receipt.time:%H:%M}   ·   {self.receipt.payment_method}",
            font=theme.font(13),
            text_color=theme.MUTED,
        ).pack(side="right")

        table_card = ctk.CTkFrame(
            self, fg_color=theme.SURFACE, corner_radius=14, border_width=1, border_color=theme.BORDER
        )
        table_card.pack(fill="both", expand=True, padx=24, pady=6)
        table_box = ctk.CTkFrame(table_card, fg_color="transparent")
        table_box.pack(fill="both", expand=True, padx=10, pady=10)
        tree = make_table(table_box, COLUMNS, "Voucher", height=8)
        fill_table(
            tree,
            (
                (sp.quantity, sp.product.name, format_price(sp.unit_price), format_price(sp.total))
                for sp in self.receipt.sold_products
            ),
        )

        totals = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=14, border_width=1, border_color=theme.BORDER)
        totals.pack(fill="x", padx=24, pady=(6, 10))
        totals.grid_columnconfigure(0, weight=1)
        self._total_row(
            totals, 0, "Total", f"${format_price(self.receipt.total)}", theme.font(22, bold=True), theme.TEXT
        )
        if self.receipt.payment_method == PAYMENT_CASH and self.received is not None:
            self._total_row(totals, 1, "Recibido", f"${format_price(self.received)}", theme.font(15), theme.MUTED)
            self._total_row(
                totals, 2, "Cambio", f"${format_price(self.change)}", theme.font(26, bold=True), theme.SUCCESS
            )

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=24, pady=(0, 20))
        button(actions, "Volver a ventas  (Enter)", self.controller.event_close, kind="primary", width=220).pack(
            side="right"
        )
        if self.can_print:
            button(actions, "Imprimir recibo", self.controller.event_print, kind="secondary", width=170).pack(
                side="right", padx=(0, 10)
            )

    @staticmethod
    def _total_row(parent, row: int, label: str, value: str, value_font, color: str) -> None:
        ctk.CTkLabel(parent, text=label, font=theme.font(14), text_color=theme.MUTED, anchor="w").grid(
            row=row, column=0, sticky="w", padx=18, pady=6
        )
        ctk.CTkLabel(parent, text=value, font=value_font, text_color=color, anchor="e").grid(
            row=row, column=1, sticky="e", padx=18, pady=6
        )
