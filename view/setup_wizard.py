"""Asistente de configuración inicial: se muestra la primera vez que abre la aplicación."""

from __future__ import annotations

import contextlib
import logging
import threading
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk
import psycopg2

from model.errors import AppError
from utils import printer_manager, setup
from utils.config import (
    MODE_NETWORK,
    MODE_USB,
    MODE_WINDOWS,
    PAPER_COLUMNS,
    WINDOW_SIZES,
    BusinessSettings,
    DatabaseSettings,
)
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
COMBO_STYLE = {
    "height": 34,
    "font": theme.font(13),
    "dropdown_font": theme.font(13),
    "fg_color": theme.SURFACE_ALT,
    "border_color": theme.BORDER,
    "button_color": theme.PRIMARY,
    "button_hover_color": theme.PRIMARY_HOVER,
    "text_color": theme.TEXT,
    "state": "readonly",
}
DEFAULT_PORT = "5432"
DEFAULT_DB = "inventario"
DEFAULT_USER = "postgres"
DEFAULT_PRINTER = "(la predeterminada de Windows)"
MODE_LABELS = {
    MODE_WINDOWS: "Impresora instalada en Windows (recomendado)",
    MODE_NETWORK: "Impresora de red por IP",
    MODE_USB: "USB directo con libusb (avanzado)",
}
PAPER_LABELS = {mm: f"{mm} mm ({columns} columnas)" for mm, columns in PAPER_COLUMNS.items()}
POLL_MS = 200


class SetupWizard(ctk.CTkToplevel):
    """Ventana modal. ``self.saved`` queda en True si se escribió la configuración."""

    def __init__(self, parent: tk.Misc, base_dir: Path | None = None) -> None:
        super().__init__(parent, fg_color=theme.BACKGROUND)
        self.saved = False
        self.base_dir = base_dir
        self.title("Configuración inicial")
        # Cabe en una pantalla de 1366x768 con barra de tareas; en pantallas más chicas el contenido se desplaza.
        width = min(1300, self.winfo_screenwidth() - 40)
        height = min(740, self.winfo_screenheight() - 90)
        self.geometry(f"{width}x{height}")
        self.minsize(900, 560)
        self.protocol("WM_DELETE_WINDOW", self._cancel)
        self._entries: dict[str, ctk.CTkEntry] = {}
        self._printing = False
        self._build()
        self.transient(parent)
        with contextlib.suppress(tk.TclError):  # en pruebas la ventana no llega a mostrarse
            self.grab_set()

    # ------------------------------------------------------------------ construcción
    def _build(self) -> None:
        self.grid_columnconfigure((0, 1, 2), weight=1, uniform="cols")
        self.grid_rowconfigure(1, weight=1)
        header = HeaderBar(
            self, "Bienvenido a SistemaPOS", "Complete estos datos una sola vez; después se pueden cambiar"
        )
        header.grid(row=0, column=0, columnspan=3, sticky="ew")

        # Contenedor con desplazamiento: si la pantalla es baja, las tarjetas se pueden recorrer y el pie no se oculta.
        body = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=theme.BORDER)
        body.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=(10, 4), pady=(4, 0))
        body.grid_columnconfigure((0, 1, 2), weight=1, uniform="cols")
        columns = []
        for index in range(3):
            frame = ctk.CTkFrame(body, fg_color="transparent")
            frame.grid(
                row=0, column=index, sticky="nsew", padx=(6 if index == 0 else 5, 6 if index == 2 else 5), pady=6
            )
            columns.append(frame)
        self._build_business(columns[0])
        self._build_database(columns[1])
        self._build_printer(columns[2])

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.grid(row=2, column=0, columnspan=3, sticky="ew", padx=16, pady=(0, 12))
        self.error_label = ctk.CTkLabel(
            footer, text="", font=theme.font(12), text_color=theme.DANGER, anchor="w", justify="left", wraplength=820
        )
        self.error_label.pack(side="left", fill="x", expand=True)
        button(footer, "Cancelar", self._cancel, kind="secondary", width=130).pack(side="right")
        self.save_button = button(footer, "Guardar y continuar", self._save, kind="success", width=210)
        self.save_button.pack(side="right", padx=(0, 10))

    def _build_business(self, parent) -> None:
        business = Card(parent, "Datos del negocio (salen en el recibo)", padding=10)
        business.pack(fill="x")
        self._field(business.body, "business_name", "Nombre del negocio", "")
        self._field(business.body, "nit", "NIT", "")
        self._field(business.body, "address", "Dirección", "")
        self._field(business.body, "phone", "Teléfono", "")
        self._field(business.body, "footer", "Pie del recibo", "Gracias por su compra")

        admin = Card(parent, "Primer administrador (usuario: admin)", padding=10)
        admin.pack(fill="x", pady=(10, 0))
        self._field(admin.body, "admin_password", "Clave", "", secret=True)
        self._field(admin.body, "admin_repeat", "Repita la clave", "", secret=True)

    def _build_database(self, parent) -> None:
        database = Card(parent, "Base de datos PostgreSQL", padding=10)
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
        self.connection_label = ctk.CTkLabel(
            test_row, text="", font=theme.font(12), text_color=theme.MUTED, anchor="w", justify="left", wraplength=230
        )
        self.connection_label.pack(side="left", padx=(10, 0), fill="x", expand=True)

        screen = Card(parent, "Pantalla", padding=10)
        screen.pack(fill="x", pady=(10, 0))
        self.maximized_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(
            screen.body,
            text="Abrir la aplicación maximizada (recomendado)",
            variable=self.maximized_var,
            font=theme.font(13),
            progress_color=theme.PRIMARY,
        ).pack(anchor="w", pady=(2, 4))
        section_label(screen.body, "Tamaño de la ventana cuando no está maximizada").pack(anchor="w", pady=(4, 1))
        self.size_box = ctk.CTkComboBox(screen.body, values=list(WINDOW_SIZES), **COMBO_STYLE)
        self.size_box.set(WINDOW_SIZES[1])
        self.size_box.pack(fill="x")
        ctk.CTkLabel(
            screen.body,
            text="Si el usuario cambia el tamaño de la ventana, la aplicación lo recuerda.",
            font=theme.font(11),
            text_color=theme.MUTED,
            anchor="w",
        ).pack(anchor="w", pady=(4, 0))

    def _build_printer(self, parent) -> None:
        printer = Card(parent, "Impresora de recibos", padding=10)
        printer.pack(fill="x")
        self.printer_var = tk.BooleanVar(value=False)
        self.drawer_var = tk.BooleanVar(value=False)
        self.cut_var = tk.BooleanVar(value=True)
        ctk.CTkSwitch(
            printer.body,
            text="Imprimir recibos",
            variable=self.printer_var,
            font=theme.font(13),
            progress_color=theme.PRIMARY,
        ).pack(anchor="w", pady=(2, 2))

        section_label(printer.body, "Conexión").pack(anchor="w", pady=(4, 1))
        self.mode_box = ctk.CTkComboBox(printer.body, values=list(MODE_LABELS.values()), **COMBO_STYLE)
        self.mode_box.set(MODE_LABELS[MODE_WINDOWS])
        self.mode_box.pack(fill="x")

        section_label(printer.body, "Impresora instalada en Windows").pack(anchor="w", pady=(4, 1))
        row = ctk.CTkFrame(printer.body, fg_color="transparent")
        row.pack(fill="x")
        row.grid_columnconfigure(0, weight=1)
        self.printer_box = ctk.CTkComboBox(row, values=[DEFAULT_PRINTER], **COMBO_STYLE)
        self.printer_box.grid(row=0, column=0, sticky="ew")
        button(row, "Actualizar", self._refresh_printers, kind="secondary", size="sm", height=34, width=96).grid(
            row=0, column=1, padx=(6, 0)
        )
        self._refresh_printers()

        self._field(printer.body, "printer_host", "IP de la impresora (solo para conexión por red)", "")

        section_label(printer.body, "Ancho del papel").pack(anchor="w", pady=(4, 1))
        self.paper_box = ctk.CTkComboBox(printer.body, values=list(PAPER_LABELS.values()), **COMBO_STYLE)
        self.paper_box.set(PAPER_LABELS[80])
        self.paper_box.pack(fill="x")

        ctk.CTkSwitch(
            printer.body,
            text="Cortar el papel al final del recibo",
            variable=self.cut_var,
            font=theme.font(13),
            progress_color=theme.PRIMARY,
        ).pack(anchor="w", pady=(8, 2))
        ctk.CTkSwitch(
            printer.body,
            text="Abrir el cajón monedero al cobrar en efectivo",
            variable=self.drawer_var,
            font=theme.font(13),
            progress_color=theme.PRIMARY,
        ).pack(anchor="w", pady=(0, 4))

        test_row = ctk.CTkFrame(printer.body, fg_color="transparent")
        test_row.pack(fill="x", pady=(6, 0))
        self.print_button = button(
            test_row, "Imprimir prueba", self._print_test, kind="accent", size="sm", height=36, width=150
        )
        self.print_button.pack(side="left")
        self.print_label = ctk.CTkLabel(
            test_row, text="", font=theme.font(12), text_color=theme.MUTED, anchor="w", justify="left", wraplength=230
        )
        self.print_label.pack(side="left", padx=(10, 0), fill="x", expand=True)
        ctk.CTkLabel(
            printer.body,
            text=(
                "Instale la impresora en Windows con el controlador del fabricante (o el genérico "
                '"Generic / Text Only") y elíjala aquí. Sirve por USB, red o Bluetooth.'
            ),
            font=theme.font(11),
            text_color=theme.MUTED,
            anchor="w",
            justify="left",
            wraplength=380,
        ).pack(anchor="w", pady=(6, 0))

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

    def _refresh_printers(self) -> None:
        names = printer_manager.list_windows_printers()
        current = self.printer_box.get()
        self.printer_box.configure(values=[DEFAULT_PRINTER, *names])
        if current in names:
            self.printer_box.set(current)
        else:
            default = printer_manager.default_windows_printer()
            self.printer_box.set(default if default in names else DEFAULT_PRINTER)

    def collect(self) -> setup.SetupData:
        port_text = self.value("port").strip() or DEFAULT_PORT
        try:
            port = int(port_text)
        except ValueError:
            port = 0
        mode = next((code for code, label in MODE_LABELS.items() if label == self.mode_box.get()), MODE_WINDOWS)
        paper = next((mm for mm, label in PAPER_LABELS.items() if label == self.paper_box.get()), 80)
        chosen = self.printer_box.get()
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
            printer_mode=mode,
            printer_name="" if chosen == DEFAULT_PRINTER else chosen,
            printer_host=self.value("printer_host").strip(),
            paper_width_mm=paper,
            cut_paper=bool(self.cut_var.get()),
            window_maximized=bool(self.maximized_var.get()),
            window_size=self.size_box.get(),
        )

    # ------------------------------------------------------------------ acciones
    def _test_connection(self) -> None:
        data = self.collect()
        error = setup.test_connection(data.database)
        if error is None:
            self.connection_label.configure(text="Conexión correcta.", text_color=theme.SUCCESS)
            return
        suggestion = setup.suggest_port(data.database, error)
        if suggestion is not None:
            self.set_value("port", str(suggestion))
            self.connection_label.configure(
                text=f"En el puerto {data.database.port} no hay nada, pero en el {suggestion} sí: lo cambié. "
                "Toque Probar conexión de nuevo.",
                text_color=theme.WARNING,
            )
            return
        self.connection_label.configure(text=setup.friendly_error(data.database, error), text_color=theme.DANGER)

    def _print_test(self) -> None:
        """Imprime un tiquete de prueba en un hilo aparte para que la ventana no se congele."""
        if self._printing:
            return
        data = self.collect()
        problems = setup.validate_printer(data)
        if problems:
            self.print_label.configure(text=problems[0], text_color=theme.DANGER)
            return
        self._printing = True
        self.print_button.configure(state="disabled")
        self.print_label.configure(text="Enviando el tiquete de prueba...", text_color=theme.MUTED)
        outcome: dict[str, str | None] = {}

        def run() -> None:
            try:
                setup.run_test_print(data)
                outcome["error"] = None
            except AppError as exc:
                outcome["error"] = str(exc)
            except Exception as exc:  # cualquier fallo del controlador se muestra sin cerrar el asistente
                logger.exception("Error inesperado en la impresión de prueba")
                outcome["error"] = f"Error inesperado: {exc}"

        threading.Thread(target=run, name="printer-test", daemon=True).start()
        self.after(POLL_MS, lambda: self._poll_print(outcome))

    def _poll_print(self, outcome: dict) -> None:
        if "error" not in outcome:
            self.after(POLL_MS, lambda: self._poll_print(outcome))
            return
        self._printing = False
        self.print_button.configure(state="normal")
        if outcome["error"] is None:
            self.print_label.configure(
                text="Tiquete enviado. Revise que salió completo y que la regla llega al borde.",
                text_color=theme.SUCCESS,
            )
        else:
            self.print_label.configure(text=outcome["error"], text_color=theme.DANGER)

    def _save(self) -> None:
        data = self.collect()
        errors = setup.validate(data)
        if errors:
            self.error_label.configure(text="\n".join(errors))
            return
        error = setup.test_connection(data.database)
        if error is not None:
            suggestion = setup.suggest_port(data.database, error)
            if suggestion is not None:
                self.set_value("port", str(suggestion))
                self.error_label.configure(
                    text=f"PostgreSQL no responde en el puerto {data.database.port} pero sí en el {suggestion}: "
                    "lo cambié. Toque Guardar de nuevo."
                )
                return
            self.error_label.configure(
                text=f"No se pudo conectar a PostgreSQL: {setup.friendly_error(data.database, error)}"
            )
            return
        try:
            created = setup.ensure_database_exists(data.database)
            setup.write_files(data, self.base_dir)
            admin_note = setup.prepare_admin(
                data.database,
                data.admin_password,
                lambda question: messagebox.askyesno("Usuarios existentes", question, parent=self),
            )
        except (psycopg2.Error, OSError, AppError) as exc:
            logger.exception("No se pudo guardar la configuración inicial")
            self.error_label.configure(text=f"No se pudo guardar la configuración: {exc}")
            return
        self.saved = True
        note = f"La base de datos '{data.database.name}' fue creada. " if created else ""
        messagebox.showinfo(
            "Configuración guardada", f"{note}{admin_note}\n\nInicie sesión con el usuario admin.", parent=self
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
