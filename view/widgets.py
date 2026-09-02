"""Componentes reutilizables construidos sobre CustomTkinter.

Todas las pantallas se arman con estas piezas para que botones, tarjetas,
cabeceras y tablas se vean iguales en toda la aplicación.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Sequence
from tkinter import ttk

import customtkinter as ctk

from view import theme

BUTTON_HEIGHTS = {"sm": 34, "md": 44, "lg": 54}
BUTTON_FONTS = {"sm": 13, "md": 14, "lg": 17}

# kind -> (fondo, fondo al pasar el mouse, color de texto, borde)
BUTTON_KINDS: dict[str, tuple[str, str, str, str | None]] = {
    "primary": (theme.PRIMARY, theme.PRIMARY_HOVER, theme.ON_DARK, None),
    "secondary": (theme.SURFACE, theme.SURFACE_HOVER, theme.TEXT, theme.BORDER),
    "ghost": (theme.SURFACE_ALT, theme.SURFACE_HOVER, theme.TEXT, None),
    "success": (theme.SUCCESS, theme.SUCCESS_HOVER, theme.ON_DARK, None),
    "warning": (theme.WARNING, theme.WARNING_HOVER, theme.ON_DARK, None),
    "danger": (theme.DANGER, theme.DANGER_HOVER, theme.ON_DARK, None),
    "danger-soft": (theme.DANGER_SOFT, "#F5CFCF", theme.DANGER, None),
    "accent": (theme.ACCENT, theme.ACCENT_HOVER, theme.TEXT, None),
    "header": (theme.HEADER_HOVER, theme.HEADER_DEEP, theme.ON_DARK, None),
}


def button(
    parent,
    text: str,
    command: Callable[[], None] | None,
    kind: str = "primary",
    size: str = "md",
    **kwargs,
) -> ctk.CTkButton:
    """Botón con tamaño táctil y estilo consistente. ``kwargs`` sobreescribe cualquier opción."""
    fg, hover, text_color, border = BUTTON_KINDS[kind]
    options = {
        "fg_color": fg,
        "hover_color": hover,
        "text_color": text_color,
        "height": BUTTON_HEIGHTS[size],
        "font": theme.font(BUTTON_FONTS[size], bold=True),
        "corner_radius": 10,
        "border_width": 1 if border else 0,
        "border_color": border or fg,
    }
    options.update(kwargs)
    return ctk.CTkButton(parent, text=text, command=command, **options)


class HeaderBar(ctk.CTkFrame):
    """Barra superior con título, subtítulo y un área de acciones a la derecha."""

    def __init__(self, parent, title: str, subtitle: str = "") -> None:
        super().__init__(parent, fg_color=theme.HEADER, corner_radius=0, height=66)
        self.grid_propagate(False)
        self.grid_columnconfigure(1, weight=1)
        titles = ctk.CTkFrame(self, fg_color="transparent")
        titles.grid(row=0, column=0, sticky="w", padx=24, pady=8)
        self.title_label = ctk.CTkLabel(
            titles, text=title, font=theme.font(20, bold=True), text_color=theme.ON_DARK, anchor="w"
        )
        self.title_label.pack(anchor="w")
        self.subtitle_label = ctk.CTkLabel(
            titles, text=subtitle, font=theme.font(12), text_color=theme.ON_DARK_MUTED, anchor="w"
        )
        self.subtitle_label.pack(anchor="w")
        # Tamaño explícito: sin botones, un CTkFrame vacío pediría 200 px y empujaría el título fuera de la barra.
        self.actions = ctk.CTkFrame(self, fg_color="transparent", width=8, height=38)
        self.actions.grid(row=0, column=2, sticky="e", padx=16)

    def set_subtitle(self, text: str) -> None:
        self.subtitle_label.configure(text=text)

    def add_action(self, text: str, command: Callable[[], None], kind: str = "header", **kwargs) -> ctk.CTkButton:
        widget = button(self.actions, text, command, kind=kind, size="sm", height=38, **kwargs)
        widget.pack(side="left", padx=(8, 0))
        return widget


class Card(ctk.CTkFrame):
    """Superficie blanca con borde suave. El contenido va en ``self.body``."""

    def __init__(self, parent, title: str | None = None, padding: int = 12, **kwargs) -> None:
        options = {"fg_color": theme.SURFACE, "corner_radius": 14, "border_width": 1, "border_color": theme.BORDER}
        options.update(kwargs)
        super().__init__(parent, **options)
        self.title_row: ctk.CTkFrame | None = None
        self.title_label: ctk.CTkLabel | None = None
        if title is not None:
            self.title_row = ctk.CTkFrame(self, fg_color="transparent")
            self.title_row.pack(fill="x", padx=padding + 4, pady=(padding, 2))
            self.title_label = ctk.CTkLabel(
                self.title_row, text=title, font=theme.font(15, bold=True), text_color=theme.TEXT, anchor="w"
            )
            self.title_label.pack(side="left")
        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.pack(fill="both", expand=True, padx=padding, pady=(4 if title else padding, padding))


class StatCard(ctk.CTkFrame):
    """Indicador con etiqueta y valor grande, con una franja de color a la izquierda.

    Con ``set_command`` se vuelve clicable y con ``set_active`` se resalta como filtro activo.
    """

    def __init__(self, parent, label: str, value: str = "", accent: str = theme.PRIMARY) -> None:
        super().__init__(parent, fg_color=theme.SURFACE, corner_radius=14, border_width=1, border_color=theme.BORDER)
        self._accent = accent
        self._command: Callable[[], None] | None = None
        # Altura explícita: un CTkFrame sin altura pide 200 px y estiraría la tarjeta.
        stripe = ctk.CTkFrame(self, fg_color=accent, width=6, height=44, corner_radius=3)
        stripe.pack(side="left", fill="y", padx=(12, 0), pady=12)
        box = ctk.CTkFrame(self, fg_color="transparent")
        box.pack(side="left", fill="both", expand=True, padx=12, pady=10)
        self.label = ctk.CTkLabel(box, text=label, font=theme.font(12), text_color=theme.MUTED, anchor="w")
        self.label.pack(anchor="w")
        self.value_label = ctk.CTkLabel(
            box, text=value, font=theme.font(20, bold=True), text_color=theme.TEXT, anchor="w"
        )
        self.value_label.pack(anchor="w")
        self._widgets = (self, stripe, box, self.label, self.value_label)

    def set_value(self, text: str) -> None:
        self.value_label.configure(text=text)

    def set_note(self, text: str, color: str = theme.MUTED) -> None:
        """Línea pequeña bajo el valor, por ejemplo la variación frente al período anterior."""
        if not hasattr(self, "note_label"):
            self.note_label = ctk.CTkLabel(
                self.value_label.master, text="", font=theme.font(11, bold=True), text_color=color, anchor="w"
            )
            self.note_label.pack(anchor="w")
            self._widgets = (*self._widgets, self.note_label)
            if self._command is not None:
                self.set_command(self._command)
        self.note_label.configure(text=text, text_color=color)

    def set_command(self, command: Callable[[], None]) -> None:
        self._command = command
        for widget in self._widgets:
            widget.configure(cursor="hand2")
            widget.bind("<Button-1>", lambda _event: command())
            widget.bind("<Enter>", lambda _event: self.configure(fg_color=theme.SURFACE_HOVER))
            widget.bind("<Leave>", self._on_leave)

    def set_active(self, active: bool) -> None:
        self.configure(border_color=self._accent if active else theme.BORDER, border_width=2 if active else 1)

    def _on_leave(self, event) -> None:
        under = self.winfo_containing(event.x_root, event.y_root)
        if under is None or not str(under).startswith(str(self)):
            self.configure(fg_color=theme.SURFACE)


class Keypad(ctk.CTkFrame):
    """Teclado numérico de 3 x 4 con tecla de borrado."""

    BACKSPACE = "←"
    KEYS = (("7", "8", "9"), ("4", "5", "6"), ("1", "2", "3"), ("000", "0", BACKSPACE))

    def __init__(self, parent, on_key: Callable[[str], None], key_height: int = 38) -> None:
        super().__init__(parent, fg_color="transparent")
        for column in range(3):
            self.grid_columnconfigure(column, weight=1, uniform="keys")
        for row_index, row in enumerate(self.KEYS):
            self.grid_rowconfigure(row_index, weight=1)
            for column, key in enumerate(row):
                button(
                    self,
                    key,
                    lambda k=key: on_key(k),
                    kind="secondary",
                    height=key_height,
                    font=theme.font(16, bold=True),
                ).grid(row=row_index, column=column, sticky="nsew", padx=3, pady=3)


def make_table(
    parent,
    columns: Sequence[tuple],
    style_name: str,
    height: int = 10,
    selectmode: str = "browse",
) -> ttk.Treeview:
    """Crea una tabla con barra de desplazamiento dentro de ``parent`` (que usa grid).

    ``columns``: tuplas (clave, título, ancho, anclaje[, estira]).
    """
    tree = ttk.Treeview(
        parent,
        columns=[column[0] for column in columns],
        show="headings",
        style=theme.table_style(style_name),
        height=height,
        selectmode=selectmode,
    )
    for key, title, width, anchor, *rest in columns:
        stretch = rest[0] if rest else True
        tree.heading(key, text=title, anchor=anchor)
        tree.column(key, width=width, minwidth=40, anchor=anchor, stretch=stretch)
    scrollbar = ttk.Scrollbar(parent, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    # Cuando una fila tiene varias etiquetas, ttk usa la que se configuró PRIMERO:
    # los colores semánticos van antes que la cebra para que sí se vean.
    tree.tag_configure("low", background=theme.WARNING_SOFT)
    tree.tag_configure("out", background=theme.DANGER_SOFT, foreground=theme.DANGER)
    tree.tag_configure("muted", foreground=theme.MUTED)
    tree.tag_configure("ok", background=theme.SUCCESS_SOFT)
    tree.tag_configure("bad", background=theme.DANGER_SOFT)
    tree.tag_configure("warn", background=theme.WARNING_SOFT)
    tree.tag_configure("even", background=theme.SURFACE)
    tree.tag_configure("odd", background=theme.ZEBRA)
    tree.grid(row=0, column=0, sticky="nsew")
    scrollbar.grid(row=0, column=1, sticky="ns")
    parent.grid_rowconfigure(0, weight=1)
    parent.grid_columnconfigure(0, weight=1)
    return tree


def fill_table(
    tree: ttk.Treeview,
    rows: Iterable[Sequence],
    extra_tags: Callable[[Sequence], tuple[str, ...]] | None = None,
    empty_message: str | None = None,
) -> None:
    """Reemplaza el contenido de la tabla con filas cebra y etiquetas opcionales por fila."""
    theme.clear_table(tree)
    count = 0
    for index, row in enumerate(rows):
        tags = ("odd" if index % 2 else "even",)
        if extra_tags is not None:
            tags = tags + extra_tags(row)
        tree.insert("", "end", values=tuple(row)[: len(tree["columns"])], tags=tags)
        count += 1
    if count == 0 and empty_message:
        columns = list(tree["columns"])
        placeholder = [""] * len(columns)
        # El mensaje va en la primera columna que se estira, que es la más ancha.
        target = next((i for i, key in enumerate(columns) if tree.column(key, "stretch")), 0)
        placeholder[target] = empty_message
        tree.insert("", "end", values=placeholder, tags=("muted",))


def section_label(parent, text: str) -> ctk.CTkLabel:
    return ctk.CTkLabel(
        parent, text=text, font=theme.font(12, bold=True), text_color=theme.MUTED, anchor="w", height=20
    )


def clear_entry(entry: ctk.CTkEntry) -> None:
    """Vacía una entrada sin borrar su texto de ayuda.

    CustomTkinter guarda el texto de ayuda (placeholder) dentro de la misma caja;
    si se llama a ``delete`` mientras está activo, desaparece hasta el siguiente
    cambio de foco. Cuando la caja ya muestra la ayuda no hay nada que borrar.
    """
    if getattr(entry, "_placeholder_text_active", False):
        return
    entry.delete(0, "end")


def set_entry_text(entry: ctk.CTkEntry, value: str) -> None:
    clear_entry(entry)
    if value:
        entry.insert(0, value)
