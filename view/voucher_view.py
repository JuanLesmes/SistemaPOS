"""Ventana emergente con el resumen del recibo."""

from __future__ import annotations

from decimal import Decimal
from tkinter import ttk

import customtkinter as ctk

from model.receipt import PAYMENT_CASH, Receipt
from utils.config import BusinessSettings
from utils.formatters import format_price
from view import theme

COLUMNS = (
    ("cantidad", "Cantidad", 80, "center"),
    ("nombre", "Producto", 260, "w"),
    ("precio", "Precio unitario", 150, "e"),
    ("total", "Total", 150, "e"),
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
    ) -> None:
        super().__init__(parent)
        self.controller = controller
        self.business = business
        self.receipt = receipt
        self.received = received
        self.change = change

        self.title("Recibo de venta")
        self.geometry("760x640+100+100")
        self.minsize(700, 560)
        self.configure(fg_color=theme.PANEL)
        self.transient(parent)
        self.protocol("WM_DELETE_WINDOW", self.controller.event_close)
        self.bind("<Escape>", lambda _event: self.controller.event_close())

        self._create_widgets()
        self._load_receipt()
        self.lift()
        self.focus_force()

    def _create_widgets(self) -> None:
        header = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=0)
        header.pack(side="top", fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(
            header, text=self.business.name.upper(), font=theme.font(18, bold=True), text_color=theme.BLACK
        ).pack(anchor="w")
        details = " | ".join(
            part
            for part in (
                f"NIT: {self.business.nit}" if self.business.nit else "",
                f"Tel: {self.business.phone}" if self.business.phone else "",
                self.business.address,
            )
            if part
        )
        if details:
            ctk.CTkLabel(header, text=details, font=theme.font(12), text_color=theme.BLACK).pack(
                anchor="w", pady=(5, 0)
            )
        ctk.CTkFrame(self, height=4, fg_color=theme.HEADER, corner_radius=0).pack(fill="x", padx=20, pady=(8, 10))

        data = ctk.CTkFrame(self, fg_color=theme.PANEL, corner_radius=0)
        data.pack(side="top", fill="x", padx=20, pady=(0, 10))
        ctk.CTkLabel(
            data,
            text=f"Recibo N° {str(self.receipt.id or 0).zfill(8)}",
            font=theme.font(14, bold=True),
            text_color=theme.BLACK,
        ).pack(anchor="w")
        ctk.CTkLabel(
            data,
            text=f"Fecha: {self.receipt.date:%d/%m/%Y}   Hora: {self.receipt.time:%H:%M}   "
            f"Pago: {self.receipt.payment_method}",
            font=theme.font(12),
            text_color=theme.BLACK,
        ).pack(anchor="w", pady=(4, 0))

        table_frame = ctk.CTkFrame(
            self, fg_color=theme.WHITE, corner_radius=10, border_color=theme.BORDER, border_width=1
        )
        table_frame.pack(side="top", fill="both", expand=True, padx=20, pady=10)
        self.tree = ttk.Treeview(
            table_frame, columns=[c[0] for c in COLUMNS], show="headings", style=theme.table_style("Voucher")
        )
        for key, title, width, anchor in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor)
        scrollbar = ctk.CTkScrollbar(table_frame, command=self.tree.yview)
        scrollbar.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.pack(side="left", fill="both", expand=True, padx=(10, 0), pady=10)

        footer = ctk.CTkFrame(self, fg_color=theme.PANEL)
        footer.pack(side="top", fill="x", padx=20, pady=10)
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_columnconfigure(1, weight=1)
        ctk.CTkButton(
            footer,
            text="Volver a ventas",
            fg_color=theme.SUCCESS,
            hover_color=theme.SUCCESS_HOVER,
            text_color=theme.WHITE,
            font=theme.font(12, bold=True),
            corner_radius=10,
            width=180,
            height=40,
            command=self.controller.event_close,
        ).grid(row=0, column=0, sticky="w")

        totals = ctk.CTkFrame(footer, fg_color=theme.PANEL)
        totals.grid(row=0, column=1, sticky="e")
        self.total_label = ctk.CTkLabel(totals, text="", font=theme.font(14, bold=True), text_color=theme.BLACK)
        self.received_label = ctk.CTkLabel(totals, text="", font=theme.font(12), text_color=theme.BLACK)
        self.change_label = ctk.CTkLabel(totals, text="", font=theme.font(12), text_color=theme.BLACK)
        for label in (self.total_label, self.received_label, self.change_label):
            label.pack(anchor="e")

    def _load_receipt(self) -> None:
        theme.clear_table(self.tree)
        for sp in self.receipt.sold_products:
            self.tree.insert(
                "",
                "end",
                values=(sp.quantity, sp.product.name, format_price(sp.unit_price), format_price(sp.total)),
            )
        self.total_label.configure(text=f"TOTAL: ${format_price(self.receipt.total)}")
        if self.receipt.payment_method == PAYMENT_CASH and self.received is not None:
            self.received_label.configure(text=f"Recibido: ${format_price(self.received)}")
            self.change_label.configure(text=f"Cambio: ${format_price(self.change)}")
