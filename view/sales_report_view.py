"""Reporte de ventas por rango de fechas."""

from __future__ import annotations

import datetime as dt
from tkinter import ttk

import customtkinter as ctk
from tkcalendar import DateEntry

from model.report import SalesReportRow, SalesTotals
from utils.formatters import format_price
from view import theme

COLUMNS = (
    ("recibo", "Recibo", 70, "center"),
    ("fecha", "Fecha", 90, "center"),
    ("hora", "Hora", 60, "center"),
    ("codigo", "Código", 110, "w"),
    ("nombre", "Producto", 240, "w"),
    ("cantidad", "Cantidad", 70, "center"),
    ("total", "Total", 110, "e"),
    ("pago", "Pago", 110, "center"),
)
EMPTY_ROW = ("", "", "", "", "Sin datos para mostrar", "", "", "")


class SalesReportView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND)
        self.controller = controller
        self.pack(fill="both", expand=True)
        self.pack_propagate(False)
        self._create_widgets()

    def _create_widgets(self) -> None:
        button_style = {"corner_radius": 12, "height": 40, "width": 160, "font": theme.font(14, bold=True)}

        header = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0, height=60)
        header.pack(side="top", fill="x")
        header.pack_propagate(False)
        ctk.CTkLabel(header, text="Reporte de ventas", text_color=theme.WHITE, font=theme.font(20, bold=True)).place(
            relx=0.5, rely=0.5, anchor="center"
        )

        main = ctk.CTkFrame(self, fg_color=theme.BACKGROUND, corner_radius=0)
        main.pack(side="top", fill="both", expand=True, padx=20, pady=10)

        table_frame = ctk.CTkFrame(
            main, fg_color=theme.WHITE, corner_radius=8, border_width=1, border_color=theme.BORDER
        )
        table_frame.pack(side="left", fill="both", expand=True, padx=(0, 20))
        scrollbar = ctk.CTkScrollbar(table_frame)
        scrollbar.pack(side="right", fill="y", padx=(0, 5), pady=5)
        self.tree = ttk.Treeview(
            table_frame,
            columns=[c[0] for c in COLUMNS],
            show="headings",
            style=theme.table_style("SalesReport", row_height=24),
            yscrollcommand=scrollbar.set,
        )
        scrollbar.configure(command=self.tree.yview)
        for key, title, width, anchor in COLUMNS:
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, anchor=anchor)
        self.tree.pack(fill="both", expand=True, padx=5, pady=5)

        sidebar = ctk.CTkFrame(main, fg_color=theme.BACKGROUND, corner_radius=0, width=260)
        sidebar.pack(side="right", fill="y")
        sidebar.pack_propagate(False)

        ctk.CTkLabel(sidebar, text="Fecha inicio", text_color=theme.BLACK, font=theme.font(14, bold=True)).pack(
            anchor="w", pady=(10, 2), padx=10
        )
        self.start_date = _date_entry(sidebar)
        self.start_date.pack(anchor="w", padx=10)
        ctk.CTkLabel(sidebar, text="Fecha fin", text_color=theme.BLACK, font=theme.font(14, bold=True)).pack(
            anchor="w", pady=(10, 2), padx=10
        )
        self.end_date = _date_entry(sidebar)
        self.end_date.pack(anchor="w", padx=10)

        ctk.CTkButton(
            sidebar,
            text="Consultar",
            fg_color=theme.PRIMARY,
            hover_color=theme.PRIMARY_HOVER,
            text_color=theme.WHITE,
            command=self.controller.event_search,
            **button_style,
        ).pack(anchor="w", pady=15, padx=10)

        ctk.CTkLabel(sidebar, text="Total recaudado", text_color=theme.BLACK, font=theme.font(16, bold=True)).pack(
            anchor="w", pady=(20, 2), padx=10
        )
        self.total_label = ctk.CTkLabel(sidebar, text="$0", text_color=theme.BLACK, font=theme.font(16, bold=True))
        self.total_label.pack(anchor="w", padx=10)
        self.cash_label = ctk.CTkLabel(sidebar, text="Efectivo: $0", text_color=theme.BLACK, font=theme.font(14))
        self.cash_label.pack(anchor="w", pady=2, padx=10)
        self.card_label = ctk.CTkLabel(sidebar, text="Tarjeta: $0", text_color=theme.BLACK, font=theme.font(14))
        self.card_label.pack(anchor="w", pady=2, padx=10)
        self.transfer_label = ctk.CTkLabel(
            sidebar, text="Transferencia: $0", text_color=theme.BLACK, font=theme.font(14)
        )
        self.transfer_label.pack(anchor="w", pady=2, padx=10)

        ctk.CTkButton(
            sidebar,
            text="Exportar a Excel",
            fg_color=theme.SUCCESS,
            hover_color=theme.SUCCESS_HOVER,
            text_color=theme.WHITE,
            command=self.controller.event_export,
            **button_style,
        ).pack(anchor="w", pady=15, padx=10)

        ctk.CTkButton(
            sidebar,
            text="Volver al menú",
            fg_color=theme.ACCENT,
            hover_color=theme.ACCENT_HOVER,
            text_color=theme.BLACK,
            command=self.controller.event_back,
            **button_style,
        ).pack(side="bottom", pady=20, padx=10)

    # ------------------------------------------------------------------ API para el controlador
    def load_table(self, rows: list[SalesReportRow]) -> None:
        theme.clear_table(self.tree)
        if not rows:
            self.tree.insert("", "end", values=EMPTY_ROW)
            return
        for row in rows:
            self.tree.insert(
                "",
                "end",
                values=(
                    row.receipt_id,
                    row.date.strftime("%Y-%m-%d"),
                    row.time.strftime("%H:%M"),
                    row.code,
                    row.name,
                    row.quantity,
                    f"${format_price(row.total)}",
                    row.payment_method,
                ),
            )

    def set_totals(self, totals: SalesTotals) -> None:
        self.total_label.configure(text=f"${format_price(totals.total)}")
        self.cash_label.configure(text=f"Efectivo: ${format_price(totals.cash)}")
        self.card_label.configure(text=f"Tarjeta: ${format_price(totals.card)}")
        self.transfer_label.configure(text=f"Transferencia: ${format_price(totals.transfer)}")

    def get_start_date(self) -> dt.date:
        return self.start_date.get_date()

    def get_end_date(self) -> dt.date:
        return self.end_date.get_date()


def _date_entry(parent) -> DateEntry:
    return DateEntry(
        parent,
        width=18,
        background="darkblue",
        foreground="white",
        borderwidth=2,
        date_pattern="yyyy-mm-dd",
        locale="es_CO",
    )
