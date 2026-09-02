"""Menú principal: acceso a ventas, inventario, reportes y auditoría."""

from __future__ import annotations

import logging

import customtkinter as ctk
from PIL import Image

from utils.paths import resource_path
from view import theme

logger = logging.getLogger(__name__)

LOGO_SIZE = (300, 300)


class MenuView(ctk.CTkFrame):
    def __init__(self, parent, controller, business_name: str) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND)
        self.controller = controller
        self.business_name = business_name
        self.pack(fill="both", expand=True)
        self._create_widgets()

    def _create_widgets(self) -> None:
        left = ctk.CTkFrame(self, fg_color=theme.HEADER, width=300, corner_radius=0)
        left.pack(side="left", fill="y")
        left.pack_propagate(False)

        container = ctk.CTkFrame(left, fg_color=theme.HEADER, corner_radius=0)
        container.place(relx=0.5, rely=0.5, anchor="center")

        ctk.CTkLabel(
            container,
            text=f"Bienvenido a\n{self.business_name}",
            font=theme.font(24, bold=True),
            text_color=theme.BLACK,
            justify="center",
            wraplength=260,
        ).pack(pady=30)

        button_style = {
            "width": 220,
            "height": 50,
            "corner_radius": 15,
            "font": theme.font(16, bold=True),
            "text_color": theme.WHITE,
        }
        actions = (
            ("Ventas", self.controller.event_go_sales, theme.ACCENT, "#935d1e"),
            ("Inventario", self.controller.event_go_inventory, theme.ACCENT, "#935d1e"),
            ("Reporte de ventas", self.controller.event_go_report, theme.ACCENT, "#935d1e"),
            ("Auditoría", self.controller.event_go_auditlog, theme.ACCENT, "#935d1e"),
            ("Salir", self.controller.event_exit, theme.DANGER, theme.DANGER_HOVER),
        )
        for text, command, color, hover in actions:
            ctk.CTkButton(
                container,
                text=text,
                fg_color=color,
                hover_color=hover,
                command=command,
                **button_style,
            ).pack(pady=10)

        right = ctk.CTkFrame(self, fg_color=theme.BACKGROUND, corner_radius=0)
        right.pack(side="left", fill="both", expand=True, padx=10, pady=10)

        logo_container = ctk.CTkFrame(right, fg_color=theme.BACKGROUND, corner_radius=0)
        logo_container.place(relx=0.5, rely=0.5, anchor="center")
        self._place_logo(logo_container)

    def _place_logo(self, container) -> None:
        logo_path = resource_path("images", "logo.png")
        try:
            image = Image.open(logo_path).resize(LOGO_SIZE, Image.Resampling.LANCZOS)
        except (OSError, ValueError):
            logger.warning("No se pudo cargar el logo en %s", logo_path)
            ctk.CTkLabel(
                container,
                text=self.business_name,
                font=theme.font(32, bold=True),
                text_color=theme.HEADER,
            ).pack()
            return
        self._logo = ctk.CTkImage(light_image=image, size=LOGO_SIZE)
        ctk.CTkLabel(container, image=self._logo, text="", fg_color=theme.BACKGROUND).pack()
