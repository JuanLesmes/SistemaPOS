"""Migraciones de esquema.

Archivos SQL numerados en la carpeta ``migrations/`` (``001_nombre.sql``,
``002_nombre.sql``...). Cada uno se aplica una sola vez, en orden y dentro de
su propia transacción; la tabla ``schema_migrations`` recuerda cuáles ya
corrieron. Para cambiar el esquema se agrega un archivo nuevo, nunca se edita
uno ya aplicado.
"""

from __future__ import annotations

import logging
from pathlib import Path

import psycopg2

from model.errors import ConfigError, DatabaseUnavailableError
from utils.paths import resource_path

logger = logging.getLogger(__name__)

MIGRATIONS_TABLE = "schema_migrations"


def run_migrations(conn, migrations_dir: Path | None = None) -> list[str]:
    """Aplica las migraciones pendientes y devuelve los nombres de las aplicadas."""
    directory = migrations_dir or resource_path("migrations")
    files = sorted(directory.glob("*.sql"))
    if not files:
        raise ConfigError(f"No se encontraron migraciones en {directory}.")

    with conn, conn.cursor() as cur:
        cur.execute(
            f"CREATE TABLE IF NOT EXISTS {MIGRATIONS_TABLE} ("
            " version INTEGER PRIMARY KEY,"
            " name TEXT NOT NULL,"
            " applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
        )
        cur.execute(f"SELECT version FROM {MIGRATIONS_TABLE}")
        applied = {row[0] for row in cur.fetchall()}

    done: list[str] = []
    for path in files:
        version = _version_of(path)
        if version in applied:
            continue
        sql = path.read_text(encoding="utf-8")
        try:
            with conn, conn.cursor() as cur:
                cur.execute(sql)
                cur.execute(
                    f"INSERT INTO {MIGRATIONS_TABLE} (version, name) VALUES (%s, %s)",
                    (version, path.stem),
                )
        except psycopg2.Error as exc:
            message = str(exc).strip().splitlines()[0] if str(exc).strip() else exc.__class__.__name__
            raise DatabaseUnavailableError(f"Falló la migración {path.name}: {message}") from exc
        logger.info("Migración aplicada: %s", path.stem)
        done.append(path.stem)
    return done


def _version_of(path: Path) -> int:
    prefix = path.name.split("_", 1)[0]
    try:
        return int(prefix)
    except ValueError as exc:
        raise ConfigError(
            f"El archivo de migración {path.name} debe empezar con un número, por ejemplo 003_nombre.sql."
        ) from exc
