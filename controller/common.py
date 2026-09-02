"""Utilidades compartidas por los controladores."""

from __future__ import annotations

import functools
import logging
from collections.abc import Callable
from tkinter import messagebox

from model.errors import AppError

logger = logging.getLogger(__name__)


def guarded(method: Callable) -> Callable:
    """Decora un manejador de evento de la interfaz.

    Los errores de negocio (AppError) y de validación (ValueError) se muestran
    al usuario tal cual. Cualquier otro error se registra en el log con su
    traza y se muestra un aviso genérico, para que la aplicación no se cierre.
    """

    @functools.wraps(method)
    def wrapper(self, *args, **kwargs):
        try:
            return method(self, *args, **kwargs)
        except (AppError, ValueError) as exc:
            messagebox.showerror("No se pudo completar", str(exc))
        except Exception:
            logger.exception("Error inesperado en %s", method.__qualname__)
            messagebox.showerror(
                "Error inesperado",
                "Ocurrió un error inesperado. Revise el archivo logs/app.log.",
            )
        return None

    return wrapper
