"""Administración de usuarios: lista a la izquierda, formulario a la derecha."""

from __future__ import annotations

import customtkinter as ctk

from model.user import ROLE_LABELS, ROLES, User
from view import theme
from view.widgets import Card, HeaderBar, button, clear_entry, fill_table, make_table, section_label, set_entry_text

COLUMNS = (
    ("username", "Usuario", 130, "w", False),
    ("name", "Nombre", 220, "w"),
    ("role", "Rol", 130, "w", False),
    ("active", "Estado", 90, "center", False),
)

ENTRY_STYLE = {
    "height": 40,
    "font": theme.font(14),
    "fg_color": theme.SURFACE_ALT,
    "border_color": theme.BORDER,
    "text_color": theme.TEXT,
    "placeholder_text_color": theme.MUTED,
}


class UsersView(ctk.CTkFrame):
    def __init__(self, parent, controller) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND, corner_radius=0)
        self.controller = controller
        self._users: list[User] = []
        self.pack(fill="both", expand=True)
        self._build()

    def _build(self) -> None:
        self.grid_columnconfigure(0, weight=3, uniform="cols")
        self.grid_columnconfigure(1, weight=2, uniform="cols")
        self.grid_rowconfigure(1, weight=1)

        header = HeaderBar(self, "Usuarios", "Quién puede entrar y qué puede hacer cada uno")
        header.grid(row=0, column=0, columnspan=2, sticky="ew")
        header.add_action("Volver al menú", self.controller.event_back)

        table_card = Card(self, "Usuarios registrados", padding=10)
        table_card.grid(row=1, column=0, sticky="nsew", padx=(16, 8), pady=14)
        table_box = ctk.CTkFrame(table_card.body, fg_color="transparent")
        table_box.pack(fill="both", expand=True)
        self.tree = make_table(table_box, COLUMNS, "Users")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        ctk.CTkLabel(
            table_card.body,
            text="Administrador: todo.  Supervisor: vende, gestiona inventario, ve reportes, anula y da descuentos.  "
            "Cajero: vende y consulta inventario.",
            font=theme.font(12),
            text_color=theme.MUTED,
            anchor="w",
            justify="left",
            wraplength=760,
        ).pack(anchor="w", pady=(8, 0))

        form = Card(self, "Datos del usuario", padding=14)
        form.grid(row=1, column=1, sticky="nsew", padx=(8, 16), pady=14)
        body = form.body

        section_label(body, "Usuario (para iniciar sesión)").pack(anchor="w", pady=(0, 4))
        self.username_entry = ctk.CTkEntry(body, placeholder_text="ej. maria", **ENTRY_STYLE)
        self.username_entry.pack(fill="x")
        section_label(body, "Nombre completo").pack(anchor="w", pady=(12, 4))
        self.name_entry = ctk.CTkEntry(body, placeholder_text="ej. María Pérez", **ENTRY_STYLE)
        self.name_entry.pack(fill="x")
        section_label(body, "Rol").pack(anchor="w", pady=(12, 4))
        self.role_box = ctk.CTkComboBox(
            body,
            values=[ROLE_LABELS[role] for role in ROLES],
            state="readonly",
            height=40,
            font=theme.font(14),
            dropdown_font=theme.font(13),
            fg_color=theme.SURFACE_ALT,
            border_color=theme.BORDER,
            button_color=theme.PRIMARY,
            button_hover_color=theme.PRIMARY_HOVER,
            text_color=theme.TEXT,
        )
        self.role_box.set(ROLE_LABELS[ROLES[-1]])
        self.role_box.pack(fill="x")

        self.password_label = section_label(body, "Contraseña (mínimo 4 caracteres)")
        self.password_label.pack(anchor="w", pady=(12, 4))
        self.password_entry = ctk.CTkEntry(body, placeholder_text="solo al crear", show="•", **ENTRY_STYLE)
        self.password_entry.pack(fill="x")

        self.active_var = ctk.BooleanVar(value=True)
        self.active_switch = ctk.CTkSwitch(
            body,
            text="Activo (puede iniciar sesión)",
            variable=self.active_var,
            font=theme.font(13),
            progress_color=theme.SUCCESS,
        )
        self.active_switch.pack(anchor="w", pady=(14, 0))

        actions = ctk.CTkFrame(body, fg_color="transparent")
        actions.pack(fill="x", pady=(22, 0))
        button(actions, "Nuevo", self.controller.event_new, kind="ghost").pack(side="left")
        self.save_button = button(actions, "Crear usuario", self.controller.event_save, kind="success", width=160)
        self.save_button.pack(side="right")
        self.password_button = button(
            actions, "Cambiar contraseña", self.controller.event_change_password, kind="secondary", width=170
        )
        self.password_button.pack(side="right", padx=(0, 10))
        self._editing: User | None = None
        self.set_editing(None)

    # ------------------------------------------------------------------ API para el controlador
    def load_table(self, users: list[User]) -> None:
        self._users = list(users)
        fill_table(
            self.tree,
            ((u.username, u.full_name, u.role_label, "Activo" if u.active else "Inactivo") for u in users),
            extra_tags=lambda row: ("muted",) if row[3] == "Inactivo" else (),
            empty_message="No hay usuarios",
        )

    def set_editing(self, user: User | None) -> None:
        """Con un usuario cargado se editan nombre, rol y estado; con None se crea uno nuevo."""
        self._editing = user
        if user is None:
            set_entry_text(self.username_entry, "")
            set_entry_text(self.name_entry, "")
            self.role_box.set(ROLE_LABELS[ROLES[-1]])
            self.active_var.set(True)
            self.username_entry.configure(state="normal")
            self.password_entry.configure(state="normal")
            self.password_label.configure(text="Contraseña (mínimo 4 caracteres)")
            self.save_button.configure(text="Crear usuario")
            self.password_button.pack_forget()
        else:
            set_entry_text(self.username_entry, user.username)
            self.username_entry.configure(state="disabled")
            set_entry_text(self.name_entry, user.full_name)
            self.role_box.set(user.role_label)
            self.active_var.set(user.active)
            clear_entry(self.password_entry)
            self.password_entry.configure(state="disabled")
            self.password_label.configure(text="Contraseña (use el botón para cambiarla)")
            self.save_button.configure(text="Guardar cambios")
            self.password_button.pack(side="right", padx=(0, 10))
        clear_entry(self.password_entry)

    def editing(self) -> User | None:
        return self._editing

    def get_username(self) -> str:
        return self.username_entry.get().strip().lower()

    def get_full_name(self) -> str:
        return self.name_entry.get().strip()

    def get_role(self) -> str:
        label = self.role_box.get()
        return next((role for role, text in ROLE_LABELS.items() if text == label), ROLES[-1])

    def get_password(self) -> str:
        return self.password_entry.get()

    def is_active(self) -> bool:
        return bool(self.active_var.get())

    def _on_select(self, _event) -> None:
        selection = self.tree.selection()
        if not selection:
            return
        index = self.tree.index(selection[0])
        if index < len(self._users):
            self.controller.event_select(self._users[index])
