"""Inicio de sesión."""

from __future__ import annotations

import customtkinter as ctk

from utils.config import BusinessSettings
from utils.version import APP_NAME, APP_VERSION, VENDOR
from view import theme
from view.widgets import Card, button, clear_entry, section_label

ENTRY_STYLE = {
    "height": 44,
    "font": theme.font(15),
    "fg_color": theme.SURFACE_ALT,
    "border_color": theme.BORDER,
    "text_color": theme.TEXT,
    "placeholder_text_color": theme.MUTED,
}


class LoginView(ctk.CTkFrame):
    def __init__(self, parent, controller, business: BusinessSettings) -> None:
        super().__init__(parent, fg_color=theme.HEADER, corner_radius=0)
        self.controller = controller
        self.business = business
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        card = Card(self, padding=28, width=420)
        card.place(relx=0.5, rely=0.5, anchor="center")
        body = card.body

        ctk.CTkLabel(body, text=self.business.name, font=theme.font(24, bold=True), text_color=theme.TEXT).pack(
            anchor="w"
        )
        ctk.CTkLabel(body, text="Inicie sesión para continuar", font=theme.font(13), text_color=theme.MUTED).pack(
            anchor="w", pady=(2, 18)
        )

        section_label(body, "Usuario").pack(anchor="w", pady=(0, 4))
        self.username_entry = ctk.CTkEntry(body, placeholder_text="usuario", width=360, **ENTRY_STYLE)
        self.username_entry.pack(fill="x")
        section_label(body, "Contraseña").pack(anchor="w", pady=(12, 4))
        self.password_entry = ctk.CTkEntry(body, placeholder_text="••••••••", show="•", width=360, **ENTRY_STYLE)
        self.password_entry.pack(fill="x")

        self.error_label = ctk.CTkLabel(
            body, text="", font=theme.font(12, bold=True), text_color=theme.DANGER, anchor="w"
        )
        self.error_label.pack(fill="x", pady=(8, 0))

        button(body, "Entrar", self.controller.event_login, kind="primary", size="lg").pack(fill="x", pady=(14, 0))
        ctk.CTkLabel(
            body, text=f"{APP_NAME} {APP_VERSION}  ·  {VENDOR}", font=theme.font(11), text_color=theme.MUTED
        ).pack(anchor="w", pady=(18, 0))

        for entry in (self.username_entry, self.password_entry):
            entry.bind("<Return>", lambda _event: self.controller.event_login())

    # ------------------------------------------------------------------ API para el controlador
    def get_username(self) -> str:
        return self.username_entry.get().strip()

    def get_password(self) -> str:
        return self.password_entry.get()

    def set_error(self, text: str) -> None:
        self.error_label.configure(text=text)

    def reset(self, keep_username: bool = False) -> None:
        if not keep_username:
            clear_entry(self.username_entry)
        clear_entry(self.password_entry)
        self.set_error("")
        (self.password_entry if keep_username else self.username_entry).focus_set()
