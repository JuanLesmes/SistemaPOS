"""Acceso a PostgreSQL.

Única capa de la aplicación que ejecuta SQL. Cada método público corre dentro
de una transacción: si algo falla a mitad de camino no queda nada a medias.
Los errores esperados se lanzan como subclases de AppError con un mensaje
listo para mostrar al usuario; los controladores solo tienen que capturarlos.

La clase se arma con módulos por tema (catálogo, ventas, usuarios, compras,
turnos, auditoría) que comparten la conexión y la auditoría de ``BaseConnection``.
"""

from __future__ import annotations

import logging

from model.db.audit import AuditMixin
from model.db.base import BaseConnection
from model.db.catalog import CatalogMixin
from model.db.purchases import PurchasesMixin
from model.db.sales import SalesMixin
from model.db.shifts import ShiftsMixin
from model.db.users import UsersMixin
from model.migrations import run_migrations
from utils.config import DatabaseSettings

logger = logging.getLogger(__name__)


class DBConnection(CatalogMixin, SalesMixin, UsersMixin, PurchasesMixin, ShiftsMixin, AuditMixin, BaseConnection):
    def __init__(self, settings: DatabaseSettings) -> None:
        super().__init__(settings)
        applied = run_migrations(self._conn)
        if applied:
            logger.info("Migraciones aplicadas: %s", ", ".join(applied))
