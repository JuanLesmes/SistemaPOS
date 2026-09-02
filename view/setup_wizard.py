"""Asistente de configuración inicial: se muestra la primera vez que abre la aplicación."""

from __future__ import annotations

import contextlib
import logging
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import psycopg2

from utils import setup
from utils.config import BusinessSettings, DatabaseSettings
from view import theme
from view.widgets import Card, HeaderBar, button, section_label

logger = logging.getLogger(__name__)

ENTRY_STYLE = {
    "height": 34,
    "font": theme.font(13),
    "fg_color": theme.SURFACE_ALT,
    "border_color": theme.BORDER,
    "text_color": theme.TEXT,
    "placeholder_text_color": theme.MUTED,
}
DEFAULT_PORT = "5432"
DEFAULT_DB = "inventario"
DEFAULT_USER = "postgres"


class SetupWizard(ctk.CTkToplevel):
    """Ventana modal. ``self.saved`` queda en True si se escribió la configuración."""

    def __init__(self, parent: tk.Misc, base_dir: Path | None = None) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND)
        self.saved = False
        self.base_dir = base_dir
        self.title("Configuración inicial")
        self.geometry("1040x730")
        self.minsize(980, 700)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._entries: dict[str, ctk.CTkEntry] = {}
        self._build()
        self.transient(parent)
        with contextlib.suppress(tk.TclError):  # en pruebas la ventana no llega a mostrarse
            self.grab_set()

    # ------------------------------------------------------------------ construcción
    def _build(self) -> None:
        self.grid_columnconfigure((0, 1), weight=1, uniform="cols")
        self.grid_rowconfigure(1, weight=1)
        header = HeaderBar(
            self, "Bienvenido a SistemaPOS", "Complete estos datos una sola vez; después se pueden cambiar"
        )
        header.grid(row=0, column=0, columnspan=2, sticky="ew")

        left = ctk.CTkFrame(self, fg_color="transparent")
        left.grid(row=1, column=0, sticky="nsew", padx=(16, 6), pady=10)
        right = ctk.CTkFrame(self, fg_color="transparent")
        right.grid(row=1, column=1, sticky="nsew", padx=(6, 16), pady=10)

        business = Card(left, "Datos del negocio (salen en el recibo)", padding=10)
        business.pack(fill="x")
        self._field(business.body, "business_name", "Nombre del negocio", "")
        self._field(business.body, "nit", "NIT", "")
        self._field(business.body, "address", "Dirección", "")
        self._field(business.body, "phone", "Teléfono", "")
        self._field(business.body, "footer", "Pie del recibo", "Gracias por su compra")

        admin = Card(left, "Primer administrador (usuario: admin)", padding=10)
        admin.pack(fill="x", pady=(10, 0))
        self._field(admin.body, "admin_password", "Clave", "", secret=True)
        self._field(admin.body, "admin_repeat", "Repita la clave", "", secret=True)

        database = Card(right, "Base de datos PostgreSQL", padding=10)
        database.pack(fill="x")
        self._field(database.body, "host", "Servidor", "localhost")
        self._field(database.body, "port", "Puerto", DEFAULT_PORT)
        self._field(database.body, "db_name", "Nombre de la base (se crea si no existe)", DEFAULT_DB)
        self._field(database.body, "db_user", "Usuario", DEFAULT_USER)
        self._field(database.body, "db_password", "Clave de PostgreSQL", "", secret=True)
        test_row = ctk.CTkFrame(database.body, fg_color="transparent")
        test_row.pack(fill="x", pady=(8, 0))
        button(test_row, "Probar conexión", self._test_connection, kind="secondary", size="sm", width=150).pack(
            side="left"
        )
        self.connection_label = ctk.CTkLabel(test_row, text="", font=theme.font(12), text_color=theme.MUTED, anchor="w")
        self.connection_label.pack(side="left", padx=(10, 0), fill="x", expand=True)

        printer = Card(right, "Impresora térmica", padding=10)
        printer.pack(fill="x", pady=(10, 0))
        self.printer_var = tk.BooleanVar(value=False)
        self.drawer_var = tk.BooleanVar(value=False)
        ctk.CTkSwitch(
            printer.body,
            text="Imprimir recibos (impresora USB ESC/POS)",
            variable=self.printer_var,
            font=theme.font(13),
            progress_color=theme.PRIMARY,
        ).pack(anchor="w", pady=(2, 4))
        ctk.CTkSwitch(
            printer.body,
            text="Abrir el cajón monedero al cobrar en efectivo",
            variable=self.drawer_var,
            font=theme.font(13),
            progress_color=theme.PRIMARY,
        ).pack(anchor="w")
        ctk.CTkLabel(
            printer.body,
            text="Los IDs USB de la impresora se ajustan luego en config.json (scripts/find_usb.py los muestra).",
            font=theme.font(11),
            text_color=theme.MUTED,
            anchor="w",
            wraplength=440,
            justify="left",
        ).pack(anchor="w", pady=(4, 0))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, columnspan=2, sticky="ew", padx=16, pady=(0, 12))
        self.error_label = ctk.CTkLabel(
            footer, text="", font=theme.font(12), text_color=theme.DANGER, anchor="w", justify="left", wraplength=640
        )
        self.error_label.pack(side="left", fill="x", expand=True)
        button(footer, "Cancelar", self._cancel, kind="secondary", width=130).pack(side="right")
        self.save_button = button(footer, "Guardar y continuar", self._save, kind="success", width=210)
        self.save_button.pack(side="right", padx=(0, 10))

    def _field(self, parent, key: str, label: str, initial: str, secret: bool = False) -> None:
        section_label(parent, label).pack(anchor="w", pady=(4, 1))
        entry = ctk.CTkEntry(parent, show="•" if secret else "", **ENTRY_STYLE)
        entry.pack(fill="x")
        if initial:
            entry.insert(0, initial)
        self._entries[key] = entry

    # ------------------------------------------------------------------ datos
    def value(self, key: str) -> str:
        return self._entries[key].get()

    def set_value(self, key: str, text: str) -> None:
        self._entries[key].delete(0, "end")
        self._entries[key].insert(0, text)

    def collect(self) -> setup.SetupData:
        port_text = self.value("port").strip() or DEFAULT_PORT
        try:
            port = int(port_text)
        except ValueError:
            port = 0
        return setup.SetupData(
            business=BusinessSettings(
                name=self.value("business_name"),
                nit=self.value("nit"),
                address=self.value("address"),
                phone=self.value("phone"),
                receipt_footer=self.value("footer"),
            ),
            database=DatabaseSettings(
                host=self.value("host").strip() or "localhost",
                port=port,
                name=self.value("db_name").strip() or DEFAULT_DB,
                user=self.value("db_user").strip() or DEFAULT_USER,
                password=self.value("db_password"),
            ),
            admin_password=self.value("admin_password"),
            admin_password_repeat=self.value("admin_repeat"),
            printer_enabled=bool(self.printer_var.get()),
            open_drawer=bool(self.drawer_var.get()),
        )

    # ------------------------------------------------------------------ acciones
    def _test_connection(self) -> None:
        data = self.collect()
        error = setup.test_connection(data.database)
        if error is None:
            self.connection_label.configure(text="Conexión correcta.", text_color=theme.SUCCESS)
        else:
            self.connection_label.configure(text=error, text_color=theme.DANGER)

    def _save(self) -> None:
        data = self.collect()
        errors = setup.validate(data)
        if errors:
            self.error_label.configure(text="\n".join(errors))
            return
        error = setup.test_connection(data.database)
        if error is not None:
            self.error_label.configure(text=f"No se pudo conectar a PostgreSQL: {error}")
            return
        try:
            created = setup.ensure_database_exists(data.database)
            setup.write_files(data, self.base_dir)
        except (psycopg2.Error, OSError) as exc:
            logger.exception("No se pudo guardar la configuración inicial")
            self.error_label.configure(text=f"No se pudo guardar la configuración: {exc}")
            return
        self.saved = True
        note = f"La base de datos '{data.database.name}' fue creada." if created else ""
        messagebox.showinfo(
            "Configuración guardada", f"Todo listo. {note}\nInicie sesión con el usuario admin.", parent=self
        )
        self.destroy()

    def _cancel(self) -> None:
        self.saved = False
        self.destroy()


def run_setup_wizard(root: tk.Tk) -> bool:
    """Muestra el asistente y espera a que cierre. Devuelve True si se guardó la configuración."""
    wizard = SetupWizard(root)
    wizard.update_idletasks()
    x = (wizard.winfo_screenwidth() - wizard.winfo_width()) // 2
    y = (wizard.winfo_screenheight() - wizard.winfo_height()) // 2
    wizard.geometry(f"+{max(x, 0)}+{max(y, 0)}")
    wizard.lift()
    wizard.focus_force()
    root.wait_window(wizard)
    return wizard.saved
