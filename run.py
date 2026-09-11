"""Punto de entrada de la aplicación de escritorio."""

from __future__ import annotations

import logging
import sys
import tkinter as tk
from tkinter import messagebox

import customtkinter as ctk

from controller.main_controller import MainController
from model.db_connection import DBConnection
from model.errors import AppError
from model.users_bootstrap import ensure_first_admin
from utils.config import load_settings
from utils.logging_setup import setup_logging
from utils.paths import app_dir
from utils.setup import needs_setup
from view.setup_wizard import run_setup_wizard

MIN_WINDOW_SIZE = (1100, 650)


def main() -> int:
    setup_logging(app_dir() / "logs")
    logger = logging.getLogger("run")

    # Debe ir antes de crear cualquier ventana.
    ctk.deactivate_automatic_dpi_awareness()
    ctk.set_appearance_mode("light")
    ctk.set_default_color_theme("blue")

    root = tk.Tk()
    root.withdraw()

    if needs_setup(app_dir()):
        logger.info("Primer arranque: se abre el asistente de configuración")
        if not run_setup_wizard(root):
            logger.info("Asistente cancelado; la aplicación no arranca")
            root.destroy()
            return 1

    try:
        settings = load_settings()
        db = DBConnection(settings.database)
        ensure_first_admin(db, settings.admin_password)
    except AppError as exc:
        logger.error("No se pudo iniciar: %s", exc)
        messagebox.showerror("No se pudo iniciar", str(exc))
        root.destroy()
        return 1
    except Exception:
        logger.exception("Error inesperado al iniciar")
        messagebox.showerror("No se pudo iniciar", "Ocurrió un error inesperado. Revise el archivo logs/app.log.")
        root.destroy()
        return 1

    root.deiconify()
    root.geometry(settings.window.geometry)
    root.minsize(*MIN_WINDOW_SIZE)
    if settings.window.maximized:
        root.state("zoomed")
    MainController(root, settings, db)
    logger.info("Aplicación iniciada")
    root.mainloop()
    return 0


if __name__ == "__main__":
    sys.exit(main())
