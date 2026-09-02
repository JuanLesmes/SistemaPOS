"""Permisos por rol.

La matriz vive en código y no en la base: es pequeña, cambia con las versiones
del producto y así queda versionada junto con las pantallas que la usan.
"""

from __future__ import annotations

from model.user import ROLE_ADMIN, ROLE_CASHIER, ROLE_SUPERVISOR, User

SELL = "sell"
INVENTORY_VIEW = "inventory_view"
INVENTORY_EDIT = "inventory_edit"
REPORTS = "reports"
DASHBOARD = "dashboard"
AUDIT = "audit"
MANAGE_USERS = "manage_users"
VOID_SALE = "void_sale"
DISCOUNT = "discount"
SETTINGS = "settings"

ALL_PERMISSIONS = frozenset(
    {SELL, INVENTORY_VIEW, INVENTORY_EDIT, REPORTS, DASHBOARD, AUDIT, MANAGE_USERS, VOID_SALE, DISCOUNT, SETTINGS}
)

ROLE_PERMISSIONS: dict[str, frozenset[str]] = {
    ROLE_ADMIN: ALL_PERMISSIONS,
    ROLE_SUPERVISOR: frozenset({SELL, INVENTORY_VIEW, INVENTORY_EDIT, REPORTS, DASHBOARD, VOID_SALE, DISCOUNT}),
    # El cajero también gestiona productos y existencias: cuando llega un pedido es quien lo ingresa.
    ROLE_CASHIER: frozenset({SELL, INVENTORY_VIEW, INVENTORY_EDIT}),
}

PERMISSION_LABELS = {
    SELL: "Vender",
    INVENTORY_VIEW: "Ver inventario",
    INVENTORY_EDIT: "Gestionar productos",
    REPORTS: "Reportes",
    DASHBOARD: "Dashboard",
    AUDIT: "Auditoría",
    MANAGE_USERS: "Usuarios",
    VOID_SALE: "Anular ventas",
    DISCOUNT: "Descuentos",
    SETTINGS: "Copias y configuración",
}


def permissions_of(user: User | None) -> frozenset[str]:
    if user is None or not user.active:
        return frozenset()
    return ROLE_PERMISSIONS.get(user.role, frozenset())


def can(user: User | None, permission: str) -> bool:
    return permission in permissions_of(user)
