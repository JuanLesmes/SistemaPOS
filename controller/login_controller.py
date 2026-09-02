"""Inicio de sesión."""

from __future__ import annotations

import logging
import tkinter as tk

from controller.common import guarded
from model.db_connection import DBConnection
from view.login_view import LoginView

logger = logging.getLogger(__name__)


class LoginController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.view = LoginView(parent, self, main_controller.settings.business)

    def on_show(self, keep_username: bool = False) -> None:
        self.view.reset(keep_username=keep_username)

    @guarded
    def event_login(self) -> None:
        username = self.view.get_username()
        password = self.view.get_password()
        if not username or not password:
            self.view.set_error("Escriba usuario y contraseña.")
            return
        user = self.db.authenticate(username, password)
        if user is None:
            logger.warning("Inicio de sesión fallido para '%s'", username)
            self.view.set_error("Usuario o contraseña incorrectos, o usuario inactivo.")
            return
        self.view.reset()
        self.main_controller.on_login(user)
