"""Usuarios de la aplicación y sus roles."""

from __future__ import annotations

from dataclasses import dataclass

ROLE_ADMIN = "admin"
ROLE_SUPERVISOR = "supervisor"
ROLE_CASHIER = "cajero"
ROLES = (ROLE_ADMIN, ROLE_SUPERVISOR, ROLE_CASHIER)
ROLE_LABELS = {ROLE_ADMIN: "Administrador", ROLE_SUPERVISOR: "Supervisor", ROLE_CASHIER: "Cajero"}


@dataclass(frozen=True)
class User:
    id: int
    username: str
    full_name: str
    role: str
    active: bool = True

    @property
    def display_name(self) -> str:
        return self.full_name or self.username

    @property
    def role_label(self) -> str:
        return ROLE_LABELS.get(self.role, self.role)
