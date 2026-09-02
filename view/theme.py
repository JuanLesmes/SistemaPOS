"""Paleta, fuentes y estilos compartidos por todas las pantallas.

Diseño plano y claro, pensado para una caja con luz de día y pantalla táctil:
fondos neutros fríos, un solo color de marca (teal) para acciones principales,
ámbar para el dinero en efectivo y colores semánticos para éxito, alerta y
peligro. Cualquier cambio visual global se hace aquí y no en cada vista.
"""

from __future__ import annotations

from tkinter import ttk

# Fondos y superficies
BACKGROUND = "#F3F5F7"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#EEF2F5"
SURFACE_HOVER = "#E2EAF0"
ZEBRA = "#F7F9FB"

# Marca
HEADER = "#0F6F95"
HEADER_HOVER = "#0B5F83"
HEADER_DEEP = "#094D6B"
PRIMARY = "#1388A8"
PRIMARY_HOVER = "#0F6F95"
PRIMARY_SOFT = "#D9EEF3"
ACCENT = "#F0A830"
ACCENT_HOVER = "#D98F1B"
ACCENT_SOFT = "#FBEBCF"

# Semánticos
SUCCESS = "#2E9E5B"
SUCCESS_HOVER = "#25834B"
SUCCESS_SOFT = "#DDF3E4"
WARNING = "#E67E22"
WARNING_HOVER = "#C96A15"
WARNING_SOFT = "#FDEBD9"
DANGER = "#D64545"
DANGER_HOVER = "#B83A3A"
DANGER_SOFT = "#FBE3E3"

# Texto y bordes
TEXT = "#13242E"
MUTED = "#5C6B78"
ON_DARK = "#FFFFFF"
ON_DARK_MUTED = "#CFE9F1"
WHITE = "#FFFFFF"
BORDER = "#D5DDE3"
SELECTION = "#CFE9F1"

# Alias que conservan las vistas antiguas
BLACK = TEXT
PANEL = SURFACE_ALT

# Colores de los billetes colombianos (familia 2016) para los atajos de cobro
BILL_COLORS = {
    1000: "#B7950B",
    2000: "#2C6FB7",
    5000: "#8B5E3C",
    10000: "#C0392B",
    20000: "#E67E22",
    50000: "#7D3C98",
    100000: "#27AE60",
}

LOW_STOCK_THRESHOLD = 3

FONT_FAMILY = "Segoe UI"


def font(size: int, bold: bool = False) -> tuple:
    return (FONT_FAMILY, size, "bold") if bold else (FONT_FAMILY, size)


_configured_base = False


def _configure_base_styles(style: ttk.Style) -> None:
    global _configured_base
    if _configured_base:
        return
    style.theme_use("clam")
    style.configure(
        "TCombobox",
        fieldbackground=SURFACE,
        background=SURFACE_ALT,
        foreground=TEXT,
        arrowcolor=TEXT,
        bordercolor=BORDER,
        lightcolor=SURFACE,
        darkcolor=SURFACE,
        padding=4,
    )
    style.configure(
        "Vertical.TScrollbar", background=SURFACE_ALT, troughcolor=SURFACE, bordercolor=SURFACE, arrowcolor=MUTED
    )
    _configured_base = True


def table_style(name: str, row_height: int = 30) -> str:
    """Registra un estilo de ttk.Treeview con la paleta y devuelve su nombre."""
    style = ttk.Style()
    _configure_base_styles(style)
    style.configure(
        f"{name}.Treeview.Heading",
        background=SURFACE_ALT,
        foreground=TEXT,
        font=font(12, bold=True),
        padding=6,
        relief="flat",
        bordercolor=BORDER,
    )
    style.map(f"{name}.Treeview.Heading", background=[("active", SURFACE_HOVER)])
    style.configure(
        f"{name}.Treeview",
        font=font(12),
        rowheight=row_height,
        fieldbackground=SURFACE,
        background=SURFACE,
        foreground=TEXT,
        bordercolor=BORDER,
        borderwidth=0,
        relief="flat",
    )
    style.map(
        f"{name}.Treeview",
        background=[("selected", SELECTION)],
        foreground=[("selected", TEXT)],
    )
    return f"{name}.Treeview"


def clear_table(tree: ttk.Treeview) -> None:
    tree.delete(*tree.get_children())
