"""Conexión, transacciones y auditoría: lo que comparten todos los módulos de datos."""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg2
from psycopg2.extras import DictCursor

from model.errors import DatabaseUnavailableError
from utils.config import DatabaseSettings

logger = logging.getLogger(__name__)


class BaseConnection:
    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings
        self._conn = None
        self.current_user: str | None = None  # nombre de usuario con sesión iniciada
        self._connect()

    # ------------------------------------------------------------------ conexión
    def _connect(self) -> None:
        s = self._settings
        try:
            self._conn = psycopg2.connect(
                host=s.host,
                port=s.port,
                dbname=s.name,
                user=s.user,
                password=s.password,
                client_encoding="UTF8",
                connect_timeout=5,
            )
        except UnicodeDecodeError as exc:
            # PostgreSQL en Windows responde en el idioma del sistema (Latin-1) antes
            # de negociar la codificación. El texto no se puede leer, pero casi
            # siempre significa usuario, clave o base incorrectos.
            raise DatabaseUnavailableError(
                f"PostgreSQL rechazó la conexión a {s.host}:{s.port}. "
                "Revise usuario, clave y nombre de la base en el archivo .env."
            ) from exc
        except psycopg2.OperationalError as exc:
            raise DatabaseUnavailableError(
                f"No se pudo conectar a PostgreSQL en {s.host}:{s.port}: {first_line(exc)}"
            ) from exc
        self._conn.autocommit = False
        logger.info("Conectado a PostgreSQL %s:%s base %s", s.host, s.port, s.name)

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            logger.info("Conexión cerrada")

    def reconnect(self) -> None:
        """Cierra y vuelve a abrir la conexión (por ejemplo, después de restaurar una copia)."""
        self.close()
        self._connect()

    @contextmanager
    def _transaction(self) -> Iterator[DictCursor]:
        """Abre un cursor dentro de una transacción; confirma al salir o revierte si hay error."""
        if self._conn is None or self._conn.closed:
            self._connect()
        try:
            with self._conn.cursor(cursor_factory=DictCursor) as cur:
                yield cur
            self._conn.commit()
        except (psycopg2.InterfaceError, psycopg2.OperationalError) as exc:
            self._rollback_quietly()
            raise DatabaseUnavailableError("Se perdió la conexión con la base de datos. Intente de nuevo.") from exc
        except Exception:
            self._rollback_quietly()
            raise

    def _rollback_quietly(self) -> None:
        try:
            if self._conn is not None and not self._conn.closed:
                self._conn.rollback()
        except psycopg2.Error:
            logger.warning("No se pudo revertir la transacción", exc_info=True)

    # ------------------------------------------------------------------ auditoría
    def _log(
        self,
        cur: DictCursor,
        action: str,
        code: str | None = None,
        details: dict | None = None,
        user: str | None = None,
    ) -> None:
        payload = json.dumps(details, ensure_ascii=False, default=str) if details is not None else None
        cur.execute(
            'INSERT INTO audit_logs (action, code, details, "user") VALUES (%s, %s, %s, %s)',
            (action, code, payload, user or self.current_user),
        )


def first_line(exc: BaseException) -> str:
    text = str(exc).strip()
    return text.splitlines()[0] if text else exc.__class__.__name__


def escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
