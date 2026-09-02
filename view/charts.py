"""Gráficos ligeros dibujados con el lienzo de Tk, sin dependencias externas."""

from __future__ import annotations

import math
import tkinter as tk
from collections.abc import Callable, Sequence
from decimal import Decimal

import customtkinter as ctk

from utils.formatters import format_price
from view import theme

MAX_VALUE_LABELS = 14
MAX_AXIS_LABELS = 12


def compact_money(value: Decimal | int | float) -> str:
    """Versión corta para ejes: 1.250.000 -> "1,3 M"; 12.500 -> "12,5 k"."""
    amount = float(value)
    if abs(amount) >= 1_000_000:
        return f"{amount / 1_000_000:.1f} M".replace(".", ",")
    if abs(amount) >= 1_000:
        return f"{amount / 1_000:.1f} k".replace(".", ",").replace(",0 k", " k")
    return f"{amount:.0f}"


class BarChart(ctk.CTkFrame):
    """Gráfico de barras verticales que se redibuja al cambiar de tamaño."""

    def __init__(
        self, parent, title: str, empty_text: str = "Sin datos en el período", height: int | None = None
    ) -> None:
        super().__init__(parent, fg_color=theme.SURFACE, corner_radius=14, border_width=1, border_color=theme.BORDER)
        if height is not None:
            self.configure(height=height)
            self.pack_propagate(False)
        self._labels: list[str] = []
        self._values: list[float] = []
        self._empty_text = empty_text
        ctk.CTkLabel(self, text=title, font=theme.font(15, bold=True), text_color=theme.TEXT, anchor="w").pack(
            fill="x", padx=16, pady=(12, 0)
        )
        self.canvas = tk.Canvas(self, bg=theme.SURFACE, highlightthickness=0, bd=0)
        self.canvas.pack(fill="both", expand=True, padx=12, pady=(6, 12))
        self.canvas.bind("<Configure>", lambda _event: self._render())

    def set_data(self, labels: Sequence[str], values: Sequence[Decimal | int | float]) -> None:
        self._labels = list(labels)
        self._values = [float(v) for v in values]
        self._render()

    def _render(self) -> None:
        """Dibuja el gráfico. No se llama _draw porque CustomTkinter usa ese nombre internamente."""
        canvas = self.canvas
        canvas.delete("all")
        width, height = canvas.winfo_width(), canvas.winfo_height()
        if width < 60 or height < 60:
            return
        if not self._values or max(self._values) <= 0:
            canvas.create_text(width / 2, height / 2, text=self._empty_text, fill=theme.MUTED, font=theme.font(13))
            return

        left, right, top, bottom = 58, 12, 18, height - 26
        plot_width, plot_height = width - right - left, bottom - top
        max_value = max(self._values)
        step = _nice_step(max_value / 3)
        axis_top = math.ceil(max_value / step) * step

        # Rejilla y etiquetas del eje vertical
        level = 0.0
        while level <= axis_top + 1e-9:
            y = bottom - (level / axis_top) * plot_height
            canvas.create_line(left, y, left + plot_width, y, fill=theme.BORDER)
            canvas.create_text(
                left - 6, y, text=compact_money(level), anchor="e", fill=theme.MUTED, font=theme.font(10)
            )
            level += step

        count = len(self._values)
        slot = plot_width / count
        bar_width = max(4.0, slot * 0.68)
        label_every = max(1, math.ceil(count / MAX_AXIS_LABELS))
        show_values = count <= MAX_VALUE_LABELS
        for index, (label, value) in enumerate(zip(self._labels, self._values, strict=True)):
            x0 = left + index * slot + (slot - bar_width) / 2
            x1 = x0 + bar_width
            y = bottom - (value / axis_top) * plot_height if axis_top else bottom
            if value > 0:
                canvas.create_rectangle(x0, y, x1, bottom, fill=theme.PRIMARY, outline="")
                if show_values:
                    canvas.create_text(
                        (x0 + x1) / 2, y - 7, text=compact_money(value), fill=theme.TEXT, font=theme.font(10, bold=True)
                    )
            if index % label_every == 0:
                canvas.create_text((x0 + x1) / 2, bottom + 12, text=label, fill=theme.MUTED, font=theme.font(10))
        canvas.create_line(left, bottom, left + plot_width, bottom, fill=theme.MUTED)


class HorizontalBars(ctk.CTkFrame):
    """Lista de barras horizontales con etiqueta, valor y porcentaje del total."""

    def __init__(
        self,
        parent,
        title: str,
        colors: Callable[[str], str] | None = None,
        empty_text: str = "Sin datos en el período",
    ) -> None:
        super().__init__(parent, fg_color=theme.SURFACE, corner_radius=14, border_width=1, border_color=theme.BORDER)
        self._colors = colors or (lambda _label: theme.PRIMARY)
        self._empty_text = empty_text
        ctk.CTkLabel(self, text=title, font=theme.font(15, bold=True), text_color=theme.TEXT, anchor="w").pack(
            fill="x", padx=16, pady=(12, 4)
        )
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=16, pady=(0, 12))

    def set_data(self, items: Sequence[tuple[str, Decimal]]) -> None:
        for child in self.body.winfo_children():
            child.destroy()
        total = sum((value for _label, value in items), Decimal(0))
        if total <= 0:
            ctk.CTkLabel(self.body, text=self._empty_text, font=theme.font(13), text_color=theme.MUTED).pack(
                expand=True
            )
            return
        self.body.grid_columnconfigure(1, weight=1)
        for row, (label, value) in enumerate(items):
            share = float(value / total) if total else 0.0
            ctk.CTkLabel(self.body, text=label, font=theme.font(13), text_color=theme.TEXT, anchor="w", width=120).grid(
                row=row, column=0, sticky="w", pady=4
            )
            bar = ctk.CTkProgressBar(
                self.body, height=12, corner_radius=6, progress_color=self._colors(label), fg_color=theme.SURFACE_ALT
            )
            bar.set(share)
            bar.grid(row=row, column=1, sticky="ew", padx=8, pady=4)
            ctk.CTkLabel(
                self.body,
                text=f"${format_price(value)}  ·  {share * 100:.0f} %",
                font=theme.font(12, bold=True),
                text_color=theme.TEXT,
                anchor="e",
                width=130,
            ).grid(row=row, column=2, sticky="e", pady=4)


def _nice_step(raw: float) -> float:
    """Redondea el paso del eje a 1, 2 o 5 veces una potencia de diez."""
    if raw <= 0:
        return 1.0
    magnitude = 10 ** math.floor(math.log10(raw))
    for factor in (1, 2, 5, 10):
        if raw <= factor * magnitude:
            return factor * magnitude
    return 10 * magnitude
