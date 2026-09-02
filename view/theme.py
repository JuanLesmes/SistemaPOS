"""Paleta, fuentes y estilos compartidos por todas las pantallas.

Cualquier cambio visual global se hace aquí y no en cada vista.
"""

from __future__ import annotations

from tkinter import ttk

BACKGROUND = "#9db7b1"
HEADER = "#10a2a7"
ACCENT = "#b57426"
ACCENT_HOVER = "#c7853a"
PRIMARY = "#0000FF"
PRIMARY_HOVER = "#3333CC"
SUCCESS = "#28A745"
SUCCESS_HOVER = "#218838"
WARNING = "#FFD700"
WARNING_HOVER = "#E6C200"
DANGER = "#D32F2F"
DANGER_HOVER = "#B71C1C"
WHITE = "#FFFFFF"
BLACK = "#000000"
MUTED = "#555555"
BORDER = "#CCCCCC"
SELECTION = "#A0E7E5"
PANEL = "#E0E0E0"

FONT_FAMILY = "Segoe UI"


def font(size: int, bold: bool = False) -> tuple:
    return (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)


def table_style(name: str, row_height: int = 28) -> str:
    """Registra un estilo de ttk.Treeview con la paleta y devuelve su nombre."""
    style = ttk.Style()
    style.theme_use("clam")
    style.configure(
        f"{name}.Treeview.Heading",
        background=HEADER,
        foreground=WHITE,
        font=font(13, bold=True),
        padding=4,
    )
    style.configure(
        f"{name}.Treeview",
        font=font(12),
        rowheight=row_height,
        fieldbackground=WHITE,
        background=WHITE,
        foreground=BLACK,
        bordercolor=BORDER,
        borderwidth=1,
    )
    style.map(
        f"{name}.Treeview",
        background=[("selected", SELECTION)],
        foreground=[("selected", BLACK)],
    )
    return f"{name}.Treeview"


def clear_table(tree: ttk.Treeview) -> None:
    tree.delete(*tree.get_children())
