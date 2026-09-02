"""Cierre de caja: resumen del turno abierto, conteo por denominación y historial de turnos."""

from __future__ import annotations

from decimal import Decimal

import customtkinter as ctk

from model.shift import DENOMINATIONS, Shift, ShiftSummary, count_total
from utils.formatters import format_price
from view import theme
from view.widgets import Card, HeaderBar, StatCard, button, fill_table, make_table, section_label

HISTORY_COLUMNS = (
    ("opened", "Apertura", 92, "w", False),
    ("closed", "Cierre", 92, "w", False),
    ("user", "Usuario", 80, "w", False),
    ("opening", "Base", 78, "e", False),
    ("expected", "Esperado", 84, "e", False),
    ("counted", "Contado", 84, "e", False),
    ("difference", "Diferencia", 88, "e", False),
    ("notes", "Notas", 90, "w"),
)

ENTRY_STYLE = {
    "height": 34,
    "font": theme.font(13),
    "fg_color": theme.SURFACE_ALT,
    "border_color": theme.BORDER,
    "text_color": theme.TEXT,
    "placeholder_text_color": theme.MUTED,
    "justify": "right",
}


class ShiftView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self._count_entries: dict[int, ctk.CTkEntry] = {}
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=1, uniform="cols")
        self.grid_columnconfigure(1, weight=1, uniform="cols")
        self.grid_rowconfigure(2, weight=1)

        self.header = HeaderBar(self, "Cierre de caja", "")
        self.header.grid(row=0, column=0, columnspan=2, sticky="ew")
        self.open_button = self.header.add_action("Abrir turno", self.controller.event_open_shift, kind="accent")
        self.header.add_action("Volver al menú", self.controller.event_back)

        stats = ctk.CTkFrame(self, fg_color="transparent")
        stats.grid(row=1, column=0, columnspan=2, sticky="ew", padx=16, pady=(14, 8))
        cards = (
            ("opening", "Base inicial", theme.MUTED),
            ("cash", "Ventas en efectivo", theme.ACCENT),
            ("card", "Tarjeta", theme.HEADER),
            ("transfer", "Transferencia", theme.SUCCESS),
            ("returns", "Devoluciones", theme.DANGER),
            ("expected", "Efectivo esperado en caja", theme.PRIMARY),
        )
        self.stat_cards: dict[str, StatCard] = {}
        for index, (key, label, accent) in enumerate(cards):
            stats.grid_columnconfigure(index, weight=1, uniform="stats")
            card = StatCard(stats, label, "$0", accent=accent)
            card.grid(row=0, column=index, sticky="ew", padx=(0 if index == 0 else 8, 0))
            self.stat_cards[key] = card

        count_card = Card(self, "Arqueo: cuente el efectivo por denominación", padding=12)
        count_card.grid(row=2, column=0, sticky="nsew", padx=(16, 6), pady=(0, 16))
        grid = ctk.CTkFrame(count_card.body, fg_color="transparent")
        grid.pack(fill="x")
        for column in range(4):
            grid.grid_columnconfigure(column, weight=1, uniform="den")
        for index, value in enumerate(DENOMINATIONS):
            cell = ctk.CTkFrame(grid, fg_color="transparent")
            cell.grid(row=index // 4, column=index % 4, sticky="ew", padx=6, pady=4)
            section_label(cell, f"${format_price(value)}").pack(anchor="w")
            entry = ctk.CTkEntry(cell, placeholder_text="0", **ENTRY_STYLE)
            entry.pack(fill="x")
            entry.bind("<KeyRelease>", lambda _event: self._update_counted())
            self._count_entries[value] = entry

        totals = ctk.CTkFrame(count_card.body, fg_color="transparent")
        totals.pack(fill="x", pady=(14, 0))
        self.counted_label = ctk.CTkLabel(
            totals, text="Contado: $0", font=theme.font(18, bold=True), text_color=theme.TEXT
        )
        self.counted_label.pack(side="left")
        self.difference_label = ctk.CTkLabel(totals, text="", font=theme.font(15, bold=True), text_color=theme.MUTED)
        self.difference_label.pack(side="right")

        section_label(count_card.body, "Notas del cierre").pack(anchor="w", pady=(12, 4))
        self.notes_entry = ctk.CTkEntry(
            count_card.body,
            placeholder_text="ej. faltó cambio, se pagó domicilio",
            height=38,
            font=theme.font(13),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            text_color=theme.TEXT,
            placeholder_text_color=theme.MUTED,
        )
        self.notes_entry.pack(fill="x")
        self.close_button = button(
            count_card.body,
            "Cerrar turno e imprimir cierre",
            self.controller.event_close_shift,
            kind="danger",
            size="lg",
        )
        self.close_button.pack(fill="x", pady=(16, 0))

        history = Card(self, "Turnos anteriores", padding=10)
        history.grid(row=2, column=1, sticky="nsew", padx=(6, 16), pady=(0, 16))
        box = ctk.CTkFrame(history.body, fg_color="transparent")
        box.pack(fill="both", expand=True)
        self.history_tree = make_table(box, HISTORY_COLUMNS, "Shifts")

    # ------------------------------------------------------------------ API para el controlador
    def show_summary(self, summary: ShiftSummary | None) -> None:
        self._summary = summary
        if summary is None:
            self.header.set_subtitle("No hay un turno abierto")
            for card in self.stat_cards.values():
                card.set_value("$0")
            self.open_button.configure(state="normal")
            self.close_button.configure(state="disabled")
        else:
            shift = summary.shift
            opened = shift.opened_at.strftime("%d/%m/%Y %H:%M")
            self.header.set_subtitle(
                f"Turno {shift.id} abierto el {opened} por {shift.opened_by or '-'}  ·  {summary.receipt_count} recibos"
            )
            self.stat_cards["opening"].set_value(f"${format_price(shift.opening_cash)}")
            self.stat_cards["cash"].set_value(f"${format_price(summary.cash_sales)}")
            self.stat_cards["card"].set_value(f"${format_price(summary.card_sales)}")
            self.stat_cards["transfer"].set_value(f"${format_price(summary.transfer_sales)}")
            self.stat_cards["returns"].set_value(f"${format_price(summary.returns)}")
            self.stat_cards["expected"].set_value(f"${format_price(summary.expected_cash)}")
            self.open_button.configure(state="disabled")
            self.close_button.configure(state="normal")
        self._update_counted()

    def show_history(self, shifts: list[Shift]) -> None:
        fill_table(
            self.history_tree,
            (
                (
                    s.opened_at.strftime("%d/%m %H:%M"),
                    s.closed_at.strftime("%d/%m %H:%M") if s.closed_at else "abierto",
                    s.closed_by or s.opened_by or "",
                    format_price(s.opening_cash),
                    format_price(s.expected_cash) if s.expected_cash is not None else "",
                    format_price(s.counted_cash) if s.counted_cash is not None else "",
                    format_price(s.difference) if s.difference is not None else "",
                    s.notes,
                )
                for s in shifts
            ),
            extra_tags=lambda row: ("bad",) if row[6].startswith("-") else (),
            empty_message="Todavía no hay turnos cerrados",
        )

    def get_counts(self) -> dict[int, int]:
        counts: dict[int, int] = {}
        for value, entry in self._count_entries.items():
            text = entry.get().strip()
            counts[value] = int(text) if text.isdigit() else 0
        return counts

    def get_notes(self) -> str:
        return self.notes_entry.get().strip()

    def reset_counts(self) -> None:
        for entry in self._count_entries.values():
            entry.delete(0, "end")
        self.notes_entry.delete(0, "end")
        self._update_counted()

    # ------------------------------------------------------------------ interno
    def _update_counted(self) -> None:
        counted = count_total(self.get_counts())
        self.counted_label.configure(text=f"Contado: ${format_price(counted)}")
        summary = getattr(self, "_summary", None)
        if summary is None:
            self.difference_label.configure(text="")
            return
        difference: Decimal = counted - summary.expected_cash
        if difference == 0:
            self.difference_label.configure(text="Cuadra exacto", text_color=theme.SUCCESS)
        elif difference > 0:
            self.difference_label.configure(text=f"Sobran ${format_price(difference)}", text_color=theme.WARNING)
        else:
            self.difference_label.configure(text=f"Faltan ${format_price(-difference)}", text_color=theme.DANGER)
