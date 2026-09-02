"""Diálogos modales reutilizables: formulario corto y tabla de solo lectura.

Los controladores los invocan a través de un atributo (``self.ask_form``) para
que las pruebas puedan reemplazarlos sin abrir ventanas.
"""

from __future__ import annotations

from collections.abc import Sequence

import customtkinter as ctk

from view import theme
from view.widgets import button, fill_table, make_table, section_label

ENTRY_STYLE = {
    "height": 40,
    "font": theme.font(14),
    "fg_color": theme.SURFACE_ALT,
    "border_color": theme.BORDER,
    "text_color": theme.TEXT,
    "placeholder_text_color": theme.MUTED,
}


class FormDialog(ctk.CTkToplevel):
    """Ventana modal con campos de texto o de opción. ``result`` queda en None si se cancela.

    ``fields``: tuplas (clave, etiqueta, valor inicial) o (clave, etiqueta, valor inicial, opciones).
    """

    def __init__(
        self, parent, title: str, fields: Sequence[tuple], intro: str = "", submit_text: str = "Aceptar"
    ) -> None:
        super().__init__(parent)
        self.result: dict[str, str] | None = None
        self._entries: dict[str, ctk.CTkEntry | ctk.CTkComboBox] = {}
        self.title(title)
        self.configure(fg_color=theme.SURFACE)
        self.resizable(False, False)
        self.transient(parent.winfo_toplevel())

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=24, pady=20)
        ctk.CTkLabel(body, text=title, font=theme.font(18, bold=True), text_color=theme.TEXT, anchor="w").pack(
            anchor="w"
        )
        if intro:
            ctk.CTkLabel(
                body, text=intro, font=theme.font(12), text_color=theme.MUTED, anchor="w", justify="left"
            ).pack(anchor="w", pady=(2, 6))
        first = None
        for spec in fields:
            key, label, initial = spec[0], spec[1], spec[2]
            options = spec[3] if len(spec) > 3 else None
            section_label(body, label).pack(anchor="w", pady=(10, 4))
            if options:
                widget = ctk.CTkComboBox(
                    body,
                    values=list(options),
                    state="readonly",
                    width=360,
                    height=40,
                    font=theme.font(14),
                    dropdown_font=theme.font(13),
                    fg_color=theme.SURFACE_ALT,
                    border_color=theme.BORDER,
                    button_color=theme.PRIMARY,
                    button_hover_color=theme.PRIMARY_HOVER,
                    text_color=theme.TEXT,
                )
                widget.set(initial if initial in options else options[0])
            else:
                widget = ctk.CTkEntry(body, width=360, **ENTRY_STYLE)
                if initial:
                    widget.insert(0, str(initial))
                widget.bind("<Return>", lambda _event: self._submit())
            widget.pack(fill="x")
            self._entries[key] = widget
            first = first or widget

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", pady=(20, 0))
        button(actions, submit_text, self._submit, kind="primary", width=150).pack(side="right")
        button(actions, "Cancelar", self._cancel, kind="ghost", width=120).pack(side="right", padx=(0, 10))
        self.bind("<Escape>", lambda _event: self._cancel())
        self.protocol("WM_DELETE_WINDOW", self._cancel)

        self.update_idletasks()
        _center_over(self, parent.winfo_toplevel())
        self.grab_set()
        if first is not None:
            first.focus_set()

    def _submit(self) -> None:
        self.result = {key: widget.get() for key, widget in self._entries.items()}
        self.destroy()

    def _cancel(self) -> None:
        self.result = None
        self.destroy()


def ask_form(parent, title: str, fields: Sequence[tuple], intro: str = "", submit_text: str = "Aceptar") -> dict | None:
    """Abre el formulario y espera a que se cierre. Devuelve los valores o None si se canceló."""
    dialog = FormDialog(parent, title, fields, intro=intro, submit_text=submit_text)
    parent.wait_window(dialog)
    return dialog.result


class TableDialog(ctk.CTkToplevel):
    """Ventana modal de solo lectura con una tabla (por ejemplo, el kárdex de un producto)."""

    def __init__(self, parent, title: str, columns: Sequence[tuple], rows, subtitle: str = "", size=(900, 560)) -> None:
        super().__init__(parent)
        self.title(title)
        self.geometry(f"{size[0]}x{size[1]}")
        self.minsize(600, 400)
        self.configure(fg_color=theme.BACKGROUND)
        self.transient(parent.winfo_toplevel())

        header = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0)
        header.pack(fill="x")
        ctk.CTkLabel(header, text=title, font=theme.font(18, bold=True), text_color=theme.ON_DARK, anchor="w").pack(
            anchor="w", padx=20, pady=(14, 0)
        )
        ctk.CTkLabel(header, text=subtitle, font=theme.font(12), text_color=theme.ON_DARK_MUTED, anchor="w").pack(
            anchor="w", padx=20, pady=(0, 12)
        )
        card = ctk.CTkFrame(self, fg_color=theme.SURFACE, corner_radius=14, border_width=1, border_color=theme.BORDER)
        card.pack(fill="both", expand=True, padx=16, pady=12)
        box = ctk.CTkFrame(card, fg_color="transparent")
        box.pack(fill="both", expand=True, padx=10, pady=10)
        self.tree = make_table(box, columns, f"Dialog{abs(hash(title)) % 10000}")
        fill_table(self.tree, rows, empty_message="Sin registros")
        button(self, "Cerrar", self.destroy, kind="primary", width=140).pack(pady=(0, 14))
        self.bind("<Escape>", lambda _event: self.destroy())
        _center_over(self, parent.winfo_toplevel())
        self.grab_set()


def _center_over(window, parent) -> None:
    window.update_idletasks()
    width, height = window.winfo_width(), window.winfo_height()
    x = parent.winfo_rootx() + (parent.winfo_width() - width) // 2
    y = parent.winfo_rooty() + (parent.winfo_height() - height) // 2
    window.geometry(f"+{max(0, x)}+{max(0, y)}")
