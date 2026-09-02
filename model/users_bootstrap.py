"""Creación del primer administrador cuando la base todavía no tiene usuarios."""

from __future__ import annotations

import logging

from model.errors import ConfigError
from model.user import ROLE_ADMIN

logger = logging.getLogger(__name__)

FIRST_ADMIN_USERNAME = "admin"


def ensure_first_admin(db, admin_password: str) -> bool:
    """Crea el usuario ``admin`` con la clave de ADMIN_PASSWORD si no existe ningún usuario.

    Devuelve True si lo creó. Lanza ConfigError si hace falta y no hay clave configurada.
    """
    if db.count_users() > 0:
        return False
    if not admin_password:
        raise ConfigError(
            "La base no tiene usuarios. Escriba una clave en ADMIN_PASSWORD dentro de .env "
            "para crear el primer administrador (usuario: admin)."
        )
    db.create_user(FIRST_ADMIN_USERNAME, "Administrador", ROLE_ADMIN, admin_password)
    logger.info("Primer administrador creado: %s", FIRST_ADMIN_USERNAME)
    return True
