"""Menú principal: acceso a las pantallas de la aplicación.

Cabecera con el nombre de la tienda (y su logo si está configurado), cuatro
accesos grandes en cuadrícula con atajos de teclado, y pie con la versión y
el botón de salida.
"""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from utils.config import BusinessSettings
from utils.paths import app_dir
from utils.version import APP_NAME, APP_VERSION, VENDOR
from view import theme

logger = logging.getLogger(__name__)

LOGO_HEIGHT = 60
CLOCK_REFRESH_MS = 30_000
DAYS = ("lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo")
MONTHS = (
    "enero",
    "febrero",
    "marzo",
    "abril",
    "mayo",
    "junio",
    "julio",
    "agosto",
    "septiembre",
    "octubre",
    "noviembre",
    "diciembre",
)


class MenuView(ctk.CTkFrame):
    def __init__(self, parent, controller, business: BusinessSettings) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self.business = business
        self._logo_image: ctk.CTkImage | None = None
        self.pack(fill="both", expand=True)
        self._create_widgets()
        self._bind_shortcuts()
        self._tick_clock()

    # ------------------------------------------------------------------ construcción
    def _create_widgets(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._create_header().grid(row=0, column=0, sticky="ew")
        self._create_tiles().grid(row=1, column=0, sticky="nsew", padx=64, pady=(28, 8))
        self._create_footer().grid(row=2, column=0, sticky="ew", padx=64, pady=(0, 22))

    def _create_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0)
        header.grid_columnconfigure(1, weight=1)

        logo = self._load_logo()
        if logo is not None:
            ctk.CTkLabel(header, image=logo, text="").grid(row=0, column=0, rowspan=2, padx=(32, 18), pady=18)
        left_pad = 0 if logo is not None else 32

        ctk.CTkLabel(
            header,
            text=self.business.name,
            font=theme.font(28, bold=True),
            text_color=theme.ON_DARK,
            anchor="w",
        ).grid(row=0, column=1, sticky="w", padx=(left_pad, 0), pady=(20, 0))
        ctk.CTkLabel(
            header,
            text="Punto de venta e inventario",
            font=theme.font(14),
            text_color=theme.ON_DARK_MUTED,
            anchor="w",
        ).grid(row=1, column=1, sticky="w", padx=(left_pad, 0), pady=(0, 20))

        self.clock_label = ctk.CTkLabel(
            header, text="", font=theme.font(15), text_color=theme.ON_DARK, anchor="e", justify="right"
        )
        self.clock_label.grid(row=0, column=2, rowspan=2, sticky="e", padx=32)
        return header

    def _create_tiles(self) -> ctk.CTkFrame:
        area = ctk.CTkFrame(self, fg_color="transparent")
        ctk.CTkLabel(
            area, text="¿Qué desea hacer?", font=theme.font(20, bold=True), text_color=theme.TEXT, anchor="w"
        ).grid(row=0, column=0, columnspan=2, sticky="w", padx=12, pady=(0, 10))
        for column in (0, 1):
            area.grid_columnconfigure(column, weight=1, uniform="tiles")
        for row in (1, 2):
            area.grid_rowconfigure(row, weight=1, uniform="tiles")

        tiles = (
            ("Ventas", "Registrar ventas, cobrar e imprimir recibos.", "F1", self.controller.event_go_sales, True),
            (
                "Inventario",
                "Productos, categorías, existencias y valor del inventario.",
                "F2",
                self.controller.event_go_inventory,
                False,
            ),
            (
                "Reporte de ventas",
                "Ventas por rango de fechas, totales por método de pago y exportación a Excel.",
                "F3",
                self.controller.event_go_report,
                False,
            ),
            (
                "Auditoría",
                "Historial de cambios del catálogo. Requiere la clave de administrador.",
                "F4",
                self.controller.event_go_auditlog,
                False,
            ),
        )
        for index, (title, description, shortcut, command, primary) in enumerate(tiles):
            tile = _Tile(area, title, description, shortcut, command, primary)
            tile.grid(row=1 + index // 2, column=index % 2, sticky="nsew", padx=12, pady=12)
        return area

    def _create_footer(self) -> ctk.CTkFrame:
        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            footer,
            text=f"{APP_NAME} {APP_VERSION}  ·  {VENDOR}",
            font=theme.font(12),
            text_color=theme.MUTED,
            anchor="w",
        ).grid(row=0, column=0, sticky="w", padx=12)
        ctk.CTkButton(
            footer,
            text="Salir",
            fg_color=theme.DANGER,
            hover_color=theme.DANGER_HOVER,
            text_color=theme.WHITE,
            font=theme.font(14, bold=True),
            corner_radius=12,
            width=150,
            height=42,
            command=self.controller.event_exit,
        ).grid(row=0, column=1, sticky="e", padx=12)
        return footer

    # ------------------------------------------------------------------ apoyo
    def _load_logo(self) -> ctk.CTkImage | None:
        if not self.business.logo:
            return None
        path = Path(self.business.logo)
        if not path.is_absolute():
            path = app_dir() / path
        try:
            image = Image.open(path)
        except (OSError, ValueError):
            logger.warning("No se pudo cargar el logo configurado en %s", path)
            return None
        ratio = LOGO_HEIGHT / max(image.height, 1)
        size = (max(1, round(image.width * ratio)), LOGO_HEIGHT)
        self._logo_image = ctk.CTkImage(light_image=image, size=size)
        return self._logo_image

    def _bind_shortcuts(self) -> None:
        top = self.winfo_toplevel()
        shortcuts = (
            ("<F1>", self.controller.event_go_sales),
            ("<F2>", self.controller.event_go_inventory),
            ("<F3>", self.controller.event_go_report),
            ("<F4>", self.controller.event_go_auditlog),
        )
        for key, command in shortcuts:
            top.bind(key, lambda _event, cmd=command: self._when_visible(cmd), add="+")

    def _when_visible(self, command: Callable[[], None]) -> None:
        """Los atajos solo actúan mientras el menú está en pantalla."""
        if self.winfo_ismapped():
            command()

    def _tick_clock(self) -> None:
        now = dt.datetime.now()
        date_text = f"{DAYS[now.weekday()]} {now.day} de {MONTHS[now.month - 1]} de {now.year}"
        self.clock_label.configure(text=f"{date_text}\n{now:%H:%M}")
        self.after(CLOCK_REFRESH_MS, self._tick_clock)


class _Tile(ctk.CTkFrame):
    """Acceso grande y clicable, con título, descripción y atajo."""

    def __init__(
        self,
        parent,
        title: str,
        description: str,
        shortcut: str,
        command: Callable[[], None],
        primary: bool,
    ) -> None:
        if primary:
            self._normal, self._hover = theme.HEADER, theme.HEADER_HOVER
            text_color, muted_color = theme.WHITE, theme.WHITE
            badge_bg = theme.HEADER_HOVER
        else:
            self._normal, self._hover = theme.WHITE, theme.SURFACE_HOVER
            text_color, muted_color = theme.BLACK, theme.MUTED
            badge_bg = theme.SURFACE_HOVER
        super().__init__(
            parent,
            fg_color=self._normal,
            corner_radius=18,
            border_width=0 if primary else 1,
            border_color=theme.BORDER,
            cursor="hand2",
        )
        self._command = command
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=title, font=theme.font(26, bold=True), text_color=text_color, anchor="w").grid(
            row=0, column=0, sticky="w", padx=28, pady=(26, 6)
        )
        ctk.CTkLabel(
            self,
            text=shortcut,
            font=theme.font(13, bold=True),
            text_color=text_color,
            fg_color=badge_bg,
            corner_radius=8,
            width=46,
            height=28,
        ).grid(row=0, column=1, sticky="ne", padx=22, pady=22)
        ctk.CTkLabel(
            self,
            text=description,
            font=theme.font(15),
            text_color=muted_color,
            anchor="nw",
            justify="left",
            wraplength=420,
        ).grid(row=1, column=0, columnspan=2, sticky="nw", padx=28, pady=(0, 26))

        for widget in (self, *self.winfo_children()):
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def _on_click(self, _event) -> None:
        self._command()

    def _on_enter(self, _event) -> None:
        self.configure(fg_color=self._hover)

    def _on_leave(self, event) -> None:
        under = self.winfo_containing(event.x_root, event.y_root)
        if under is None or not str(under).startswith(str(self)):
            self.configure(fg_color=self._normal)
