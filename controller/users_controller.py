"""Administración de usuarios."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox, simpledialog

from controller.common import guarded
from model.db_connection import DBConnection
from model.user import User
from view.users_view import UsersView


class UsersController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.view = UsersView(parent, self)

    @guarded
    def refresh(self) -> None:
        self.view.load_table(self.db.list_users())
        self.view.set_editing(None)

    def event_back(self) -> None:
        self.main_controller.show_menu()

    def event_new(self) -> None:
        self.view.set_editing(None)

    def event_select(self, user: User) -> None:
        self.view.set_editing(user)

    @guarded
    def event_save(self) -> None:
        editing = self.view.editing()
        full_name = self.view.get_full_name()
        role = self.view.get_role()
        if editing is None:
            username = self.view.get_username()
            if not username:
                raise ValueError("Escriba el nombre de usuario.")
            user = self.db.create_user(username, full_name, role, self.view.get_password())
            messagebox.showinfo("Usuario creado", f"'{user.username}' ya puede iniciar sesión como {user.role_label}.")
        else:
            self.db.update_user(editing.id, full_name, role, self.view.is_active())
            messagebox.showinfo("Usuario actualizado", f"Los cambios de '{editing.username}' quedaron guardados.")
            if editing.id == self.main_controller.current_user.id:
                self.main_controller.refresh_current_user()
        self.refresh()

    @guarded
    def event_change_password(self) -> None:
        editing = self.view.editing()
        if editing is None:
            return
        first = simpledialog.askstring(
            "Cambiar contraseña", f"Nueva contraseña para {editing.username}:", show="•", parent=self.view
        )
        if first is None:
            return
        second = simpledialog.askstring("Cambiar contraseña", "Repita la contraseña:", show="•", parent=self.view)
        if second is None:
            return
        if first != second:
            raise ValueError("Las contraseñas no coinciden.")
        self.db.set_password(editing.id, first)
        messagebox.showinfo("Contraseña cambiada", f"La contraseña de '{editing.username}' fue actualizada.")
