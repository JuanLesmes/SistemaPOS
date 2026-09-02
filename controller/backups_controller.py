"""Copias de seguridad: estado, copia manual, copia automática diaria y restauración."""

from __future__ import annotations

import logging
import os
import threading
import tkinter as tk
from collections.abc import Callable
from tkinter import messagebox

from controller.common import guarded
from model.db_connection import DBConnection
from model.errors import AppError
from utils import backup
from utils.paths import app_dir
from view.backups_view import BackupsView

logger = logging.getLogger(__name__)

POLL_MS = 300


class BackupsController:
    def __init__(self, parent: tk.Frame, main_controller, db: DBConnection) -> None:
        self.main_controller = main_controller
        self.db = db
        self.settings = main_controller.settings
        self.view = BackupsView(parent, self)
        self._busy = False

    @property
    def directory(self):
        return backup.backup_directory(self.settings.backup, app_dir())

    @guarded
    def refresh(self) -> None:
        self.view.show_backups(backup.list_backups(self.directory), str(self.directory), self.settings.backup.keep)

    def event_back(self) -> None:
        self.main_controller.show_menu()

    @guarded
    def event_open_folder(self) -> None:
        os.startfile(self.directory)  # noqa: S606 - abre el explorador de Windows en la carpeta de copias

    @guarded
    def event_backup_now(self) -> None:
        self._run_in_background("Creando la copia...", self._do_backup, "Copia creada correctamente.")

    @guarded
    def event_restore(self) -> None:
        chosen = self.view.selected_backup()
        if chosen is None:
            messagebox.showwarning("Restaurar", "Seleccione en la tabla la copia que desea restaurar.")
            return
        first = messagebox.askyesno(
            "Restaurar copia",
            f"Se reemplazarán TODOS los datos actuales por los de:\n{chosen.path.name}\n\n¿Está seguro?",
            icon="warning",
        )
        if not first:
            return
        second = messagebox.askyesno(
            "Confirmación final",
            "Esta acción no se puede deshacer. Antes de continuar se hará una copia del estado actual.\n\n"
            "¿Restaurar ahora?",
            icon="warning",
        )
        if not second:
            return
        self._run_in_background(
            "Restaurando...",
            lambda: self._do_restore(chosen.path),
            "Copia restaurada. Cierre e inicie de nuevo la aplicación para trabajar con los datos restaurados.",
            after=self.main_controller.logout,
        )

    def run_daily_backup_if_due(self) -> None:
        """Copia automática silenciosa al arrancar, una vez por día. Los errores solo van al log."""
        if not self.settings.backup.enabled:
            return
        try:
            due = backup.backup_due(self.directory)
        except OSError:
            logger.warning("No se pudo revisar la carpeta de copias", exc_info=True)
            return
        if not due:
            return

        def job() -> None:
            try:
                self._do_backup()
                logger.info("Copia automática diaria hecha")
            except AppError as exc:
                logger.error("Copia automática fallida: %s", exc)
            except Exception:
                logger.exception("Copia automática fallida")

        threading.Thread(target=job, name="backup-daily", daemon=True).start()

    # ------------------------------------------------------------------ interno
    def _do_backup(self) -> None:
        path = backup.run_backup(self.settings.database, self.settings.backup, app_dir())
        self.db.record_backup(path.name)

    def _do_restore(self, backup_file) -> None:
        backup.run_backup(self.settings.database, self.settings.backup, app_dir())  # red de seguridad
        self.db.close()
        try:
            backup.restore_backup(self.settings.database, self.settings.backup, backup_file)
        finally:
            self.db.reconnect()

    def _run_in_background(self, busy_text: str, job: Callable[[], None], success: str, after=None) -> None:
        if self._busy:
            messagebox.showinfo("Copias", "Ya hay una operación en curso.")
            return
        self._busy = True
        self.view.set_busy(True, busy_text)
        outcome: dict[str, Exception | None] = {}

        def run() -> None:
            try:
                job()
                outcome["error"] = None
            except Exception as exc:  # se muestra al usuario en el hilo de la interfaz
                outcome["error"] = exc

        threading.Thread(target=run, name="backup-job", daemon=True).start()

        def poll() -> None:
            if "error" not in outcome:
                self.view.after(POLL_MS, poll)
                return
            self._busy = False
            self.view.set_busy(False, "Se hace una copia automática el primer arranque de cada día")
            self.refresh()
            error = outcome["error"]
            if error is None:
                messagebox.showinfo("Copias de seguridad", success)
                if after is not None:
                    after()
            elif isinstance(error, AppError):
                messagebox.showerror("Copias de seguridad", str(error))
            else:
                logger.error("Error inesperado en copias", exc_info=error)
                messagebox.showerror("Copias de seguridad", "Error inesperado. Revise logs/app.log.")

        self.view.after(POLL_MS, poll)
