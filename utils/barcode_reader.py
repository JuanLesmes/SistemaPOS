"""Lector de código de barras.

Los lectores USB se comportan como un teclado: escriben el código y pulsan
Enter. Esta clase escucha las teclas de toda la ventana, acumula los
caracteres y entrega el código completo al recibir Enter.

Las teclas escritas dentro de un campo de texto se ignoran, así el cajero
puede digitar el monto recibido sin que se mezcle con los códigos.
"""

from __future__ import annotations

import logging
import time
import tkinter as tk
from collections.abc import Callable
from tkinter import ttk

logger = logging.getLogger(__name__)

# Si pasa más de este tiempo entre teclas, lo acumulado se descarta.
RESET_AFTER_SECONDS = 3.0
ALLOWED_EXTRA_CHARS = "-_."


class BarcodeReader:
    def __init__(self, root: tk.Misc, on_code: Callable[[str], None]) -> None:
        self._root = root
        self._on_code = on_code
        self._buffer = ""
        self._last_key_at = 0.0
        self._enabled = False
        self._binding = root.bind("<Key>", self._on_key, add="+")

    @property
    def enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._buffer = ""
        self._enabled = True

    def disable(self) -> None:
        self._buffer = ""
        self._enabled = False

    def _on_key(self, event: tk.Event) -> None:
        if not self._enabled or _is_text_input(event.widget):
            return

        now = time.monotonic()
        if now - self._last_key_at > RESET_AFTER_SECONDS:
            self._buffer = ""
        self._last_key_at = now

        if event.keysym in ("Return", "KP_Enter"):
            code = self._buffer.strip()
            self._buffer = ""
            if code:
                logger.debug("Código leído: %s", code)
                self._on_code(code)
            return

        char = event.char
        if char and (char.isalnum() or char in ALLOWED_EXTRA_CHARS):
            self._buffer += char


def _is_text_input(widget: object) -> bool:
    return isinstance(widget, (tk.Entry, tk.Text, ttk.Entry, tk.Spinbox))
