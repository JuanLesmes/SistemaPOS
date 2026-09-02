"""Menú principal: accesos a las pantallas según los permisos del usuario."""

from __future__ import annotations

import datetime as dt
import logging
from collections.abc import Callable
from pathlib import Path

import customtkinter as ctk
from PIL import Image

from model import permissions
from model.user import User
from utils.config import BusinessSettings
from utils.paths import app_dir
from utils.version import APP_NAME, APP_VERSION, VENDOR
from view import theme
from view.widgets import button

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
COLUMNS = 3


class MenuView(ctk.CTkFrame):
    def __init__(self, parent, controller, business: BusinessSettings) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self.business = business
        self._logo_image: ctk.CTkImage | None = None
        self._tiles: list[tuple[str, _Tile]] = []
        self.pack(fill="both", expand=True)
        self._create_widgets()
        self._bind_shortcuts()
        self._tick_clock()

    # ------------------------------------------------------------------ construcción
    def _create_widgets(self) -> None:
        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)
        self._create_header().grid(row=0, column=0, sticky="ew")
        self._create_tiles().grid(row=1, column=0, sticky="nsew", padx=48, pady=(16, 6))
        self._create_footer().grid(row=2, column=0, sticky="ew", padx=48, pady=(0, 16))

    def _create_header(self) -> ctk.CTkFrame:
        header = ctk.CTkFrame(self, fg_color=theme.HEADER, corner_radius=0)
        header.grid_columnconfigure(1, weight=1)

        logo = self._load_logo()
        if logo is not None:
            ctk.CTkLabel(header, image=logo, text="").grid(row=0, column=0, rowspan=2, padx=(32, 18), pady=14)
        left_pad = 0 if logo is not None else 32

        ctk.CTkLabel(
            header, text=self.business.name, font=theme.font(26, bold=True), text_color=theme.ON_DARK, anchor="w"
        ).grid(row=0, column=1, sticky="w", padx=(left_pad, 0), pady=(14, 0))
        self.user_label = ctk.CTkLabel(header, text="", font=theme.font(13), text_color=theme.ON_DARK_MUTED, anchor="w")
        self.user_label.grid(row=1, column=1, sticky="w", padx=(left_pad, 0), pady=(0, 14))

        self.clock_label = ctk.CTkLabel(
            header, text="", font=theme.font(14), text_color=theme.ON_DARK, anchor="e", justify="right"
        )
        self.clock_label.grid(row=0, column=2, rowspan=2, sticky="e", padx=32)
        return header

    def _create_tiles(self) -> ctk.CTkFrame:
        area = ctk.CTkFrame(self, fg_color="transparent")
        for column in range(COLUMNS):
            area.grid_columnconfigure(column, weight=1, uniform="tiles")
        tiles = (
            (
                permissions.SELL,
                "Ventas",
                "Cobrar, cola de clientes, descuentos y recibos.",
                "F1",
                self.controller.event_go_sales,
                True,
            ),
            (
                permissions.INVENTORY_VIEW,
                "Inventario",
                "Productos, existencias, kárdex y valor del inventario.",
                "F2",
                self.controller.event_go_inventory,
                False,
            ),
            (
                permissions.INVENTORY_EDIT,
                "Compras",
                "Ingresar mercancía de proveedores y actualizar costos.",
                "F3",
                self.controller.event_go_purchases,
                False,
            ),
            (
                permissions.DASHBOARD,
                "Dashboard",
                "Hallazgos, horas pico, más vendidos y reposición.",
                "F4",
                self.controller.event_go_dashboard,
                False,
            ),
            (
                permissions.REPORTS,
                "Reporte de ventas",
                "Ventas por fechas, anulaciones, devoluciones y Excel.",
                "F5",
                self.controller.event_go_report,
                False,
            ),
            (
                permissions.SELL,
                "Cierre de caja",
                "Abrir turno, contar el efectivo y cerrar con arqueo.",
                "F6",
                self.controller.event_go_shift,
                False,
            ),
            (
                permissions.MANAGE_USERS,
                "Usuarios",
                "Cuentas, roles y contraseñas.",
                "F7",
                self.controller.event_go_users,
                False,
            ),
            (
                permissions.AUDIT,
                "Auditoría",
                "Quién cambió qué, con colores por tipo de cambio.",
                "F8",
                self.controller.event_go_auditlog,
                False,
            ),
            (
                permissions.SETTINGS,
                "Copias de seguridad",
                "Respaldo de la base de datos y restauración.",
                "F9",
                self.controller.event_go_backups,
                False,
            ),
        )
        for index, (permission, title, description, key, command, primary) in enumerate(tiles):
            row, column = divmod(index, COLUMNS)
            area.grid_rowconfigure(row, weight=1, uniform="tiles")
            tile = _Tile(area, title, description, key, command, primary)
            tile.grid(row=row, column=column, sticky="nsew", padx=8, pady=8)
            self._tiles.append((permission, tile))
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
        ).grid(row=0, column=0, sticky="w", padx=8)
        button(footer, "Cerrar sesión", self.controller.event_logout, kind="secondary", width=150, height=40).grid(
            row=0, column=1, sticky="e", padx=(0, 10)
        )
        button(footer, "Salir", self.controller.event_exit, kind="danger", width=120, height=40).grid(
            row=0, column=2, sticky="e", padx=8
        )
        return footer

    # ------------------------------------------------------------------ API para el controlador
    def set_user(self, user: User | None) -> None:
        if user is None:
            self.user_label.configure(text="")
            allowed: frozenset[str] = frozenset()
        else:
            self.user_label.configure(text=f"{user.display_name}  ·  {user.role_label}")
            allowed = permissions.permissions_of(user)
        for permission, tile in self._tiles:
            tile.set_enabled(permission in allowed)

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
        for index in range(len(self._tiles)):
            top.bind(f"<F{index + 1}>", lambda _event, i=index: self._when_visible(i), add="+")

    def _when_visible(self, index: int) -> None:
        """Los atajos solo actúan mientras el menú está en pantalla y el acceso está habilitado."""
        if self.winfo_ismapped() and index < len(self._tiles):
            self._tiles[index][1].activate()

    def _tick_clock(self) -> None:
        now = dt.datetime.now()
        date_text = f"{DAYS[now.weekday()]} {now.day} de {MONTHS[now.month - 1]} de {now.year}"
        self.clock_label.configure(text=f"{date_text}\n{now:%H:%M}")
        self.after(CLOCK_REFRESH_MS, self._tick_clock)


class _Tile(ctk.CTkFrame):
    """Acceso grande y clicable, con título, descripción y atajo. Se puede deshabilitar por permisos."""

    def __init__(
        self,
        parent,
        title: str,
        description: str,
        shortcut: str,
        command: Callable[[], None],
        primary: bool,
    ) -> None:
        self._command = command
        self.enabled = True
        if primary:
            self._normal, self._hover = theme.HEADER, theme.HEADER_HOVER
            self._text, self._muted, badge_bg = theme.ON_DARK, theme.ON_DARK_MUTED, theme.HEADER_HOVER
        else:
            self._normal, self._hover = theme.SURFACE, theme.SURFACE_HOVER
            self._text, self._muted, badge_bg = theme.TEXT, theme.MUTED, theme.SURFACE_ALT
        super().__init__(
            parent,
            fg_color=self._normal,
            corner_radius=16,
            border_width=0 if primary else 1,
            border_color=theme.BORDER,
            cursor="hand2",
        )
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        self.title_label = ctk.CTkLabel(
            self, text=title, font=theme.font(20, bold=True), text_color=self._text, anchor="w"
        )
        self.title_label.grid(row=0, column=0, sticky="w", padx=20, pady=(16, 2))
        self.badge = ctk.CTkLabel(
            self,
            text=shortcut,
            font=theme.font(12, bold=True),
            text_color=self._text,
            fg_color=badge_bg,
            corner_radius=8,
            width=42,
            height=26,
        )
        self.badge.grid(row=0, column=1, sticky="ne", padx=16, pady=14)
        self.description_label = ctk.CTkLabel(
            self,
            text=description,
            font=theme.font(13),
            text_color=self._muted,
            anchor="nw",
            justify="left",
            wraplength=300,
        )
        self.description_label.grid(row=1, column=0, columnspan=2, sticky="nw", padx=20, pady=(0, 16))

        for widget in (self, *self.winfo_children()):
            widget.bind("<Button-1>", self._on_click)
            widget.bind("<Enter>", self._on_enter)
            widget.bind("<Leave>", self._on_leave)

    def set_enabled(self, enabled: bool) -> None:
        self.enabled = enabled
        if enabled:
            self.configure(fg_color=self._normal, cursor="hand2")
            self.title_label.configure(text_color=self._text)
            self.description_label.configure(text_color=self._muted)
            self.badge.configure(text_color=self._text)
        else:
            self.configure(fg_color=theme.SURFACE_ALT, cursor="arrow")
            for label in (self.title_label, self.description_label, self.badge):
                label.configure(text_color=theme.MUTED)

    def activate(self) -> None:
        if self.enabled:
            self._command()

    def _on_click(self, _event) -> None:
        self.activate()

    def _on_enter(self, _event) -> None:
        if self.enabled:
            self.configure(fg_color=self._hover)

    def _on_leave(self, event) -> None:
        under = self.winfo_containing(event.x_root, event.y_root)
        if self.enabled and (under is None or not str(under).startswith(str(self))):
            self.configure(fg_color=self._normal)
