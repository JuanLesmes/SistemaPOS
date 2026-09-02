from __future__ import annotations

import datetime as dt
import json
from dataclasses import dataclass


@dataclass(frozen=True)
class AuditEntry:
    """Un evento del registro de auditoría."""

    timestamp: dt.datetime
    action: str
    code: str | None
    details: str | None
    user: str | None

    def changes(self) -> tuple[dict, dict]:
        """Devuelve (antes, después) a partir del JSON de detalles.

        Si los detalles no son JSON con esa forma, se devuelven como texto crudo
        en la columna "después" para que el usuario los vea igual.
        """
        if not self.details:
            return {}, {}
        try:
            data = json.loads(self.details)
        except (TypeError, ValueError):
            return {}, {"detalle": self.details}
        if not isinstance(data, dict):
            return {}, {"detalle": str(data)}
        before = data.get("before")
        after = data.get("after")
        if isinstance(before, dict) or isinstance(after, dict):
            return before or {}, after or {}
        return {}, data
