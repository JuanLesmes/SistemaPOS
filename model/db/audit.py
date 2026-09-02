"""Registro de auditoría."""

from __future__ import annotations

from datetime import date

from model.audit_log import AuditEntry

# Acciones antiguas que ya no se usan y no aportan nada en pantalla.
HIDDEN_ACTIONS = ("update_stock",)


class AuditMixin:
    def record_backup(self, filename: str) -> None:
        """Deja constancia en auditoría de una copia de seguridad hecha."""
        with self._transaction() as cur:
            self._log(cur, "backup", None, {"file": filename})

    def get_logs_by_date(self, day: date) -> list[AuditEntry]:
        with self._transaction() as cur:
            cur.execute(
                """
                SELECT timestamp, action, code, details, "user"
                  FROM audit_logs
                 WHERE timestamp >= %s AND timestamp < %s + INTERVAL '1 day'
                   AND action <> ALL(%s)
                 ORDER BY timestamp DESC, id DESC
                """,
                (day, day, list(HIDDEN_ACTIONS)),
            )
            return [
                AuditEntry(
                    timestamp=row["timestamp"],
                    action=row["action"],
                    code=row["code"],
                    details=row["details"],
                    user=row["user"],
                )
                for row in cur.fetchall()
            ]
