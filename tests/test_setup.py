"""Configuración inicial: detección del primer arranque, validación y escritura de archivos."""

from __future__ import annotations

import contextlib
import json
import time
import tkinter as tk
from dataclasses import replace
from tkinter import messagebox

import pytest

from utils import setup
from utils.config import BusinessSettings, DatabaseSettings, load_settings
from utils.setup import SetupData

ENV_VARS = ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "ADMIN_PASSWORD")


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ENV_VARS:
        monkeypatch.delenv(name, raising=False)


def _data(**overrides) -> SetupData:
    base = SetupData(
        business=BusinessSettings("Tienda", "1", "Calle", "3", "Gracias"),
        database=DatabaseSettings("localhost", 5434, "inventario", "postgres", "clave"),
        admin_password="admin123",
        admin_password_repeat="admin123",
        printer_enabled=True,
        open_drawer=False,
    )
    return replace(base, **overrides)


def test_needs_setup_until_env_and_config_exist(tmp_path):
    assert setup.needs_setup(tmp_path)
    (tmp_path / ".env").write_text("DB_PASSWORD=\n", encoding="utf-8")
    (tmp_path / "config.json").write_text("{}", encoding="utf-8")
    assert setup.needs_setup(tmp_path), "sin clave de la base sigue faltando configuración"
    (tmp_path / ".env").write_text("DB_PASSWORD=x\n", encoding="utf-8")
    assert not setup.needs_setup(tmp_path)


def test_validate_reports_every_problem():
    assert setup.validate(_data()) == []
    errors = setup.validate(
        _data(admin_password="abc", admin_password_repeat="abc", database=DatabaseSettings("", 0, "", "", ""))
    )
    joined = " ".join(errors)
    assert len(errors) == 6
    for word in ("servidor", "puerto", "base de datos", "usuario", "clave de PostgreSQL", "administrador"):
        assert word in joined
    assert setup.validate(_data(admin_password_repeat="otra")) == ["Las dos claves del administrador no coinciden."]
    assert setup.validate(_data(business=BusinessSettings("", "", "", "", ""))) == ["Escriba el nombre del negocio."]


def test_write_files_round_trip_with_load_settings(tmp_path):
    env_path, config_path = setup.write_files(_data(), tmp_path)
    assert env_path.exists() and config_path.exists()
    assert not setup.needs_setup(tmp_path)

    settings = load_settings(tmp_path)
    assert settings.database.port == 5434 and settings.database.password == "clave"
    assert settings.admin_password == "admin123"
    assert settings.business.name == "Tienda" and settings.business.receipt_footer == "Gracias"
    assert settings.printer.enabled is True and settings.printer.open_drawer is False
    assert settings.printer.mode == "windows" and settings.printer.cut is True
    assert settings.backup.enabled is True
    assert settings.window.maximized is True

    custom = _data(
        printer_mode="network",
        printer_host="10.0.0.9",
        paper_width_mm=58,
        window_maximized=False,
        window_size="1366x768",
    )
    setup.write_files(custom, tmp_path)
    settings = load_settings(tmp_path)
    assert settings.printer.mode == "network" and settings.printer.host == "10.0.0.9"
    assert settings.printer.paper_width_chars == 32
    assert settings.window.maximized is False and settings.window.geometry == "1366x768"
    assert setup.validate(_data(printer_mode="network", printer_host="")) == ["Escriba la IP de la impresora de red."]


def test_write_files_keeps_existing_printer_ids(tmp_path):
    (tmp_path / "config.json").write_text(json.dumps({"printer": {"vendor_id": "0x1234", "product_id": 7}}))
    setup.write_files(_data(printer_enabled=False, open_drawer=True), tmp_path)
    config = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert config["printer"]["vendor_id"] == "0x1234" and config["printer"]["product_id"] == 7
    assert config["printer"]["enabled"] is False and config["printer"]["open_drawer"] is True


@pytest.fixture
def root():
    try:
        window = tk.Tk()
    except tk.TclError:
        pytest.skip("No hay entorno gráfico disponible.")
    window.withdraw()
    yield window
    with contextlib.suppress(tk.TclError):
        window.destroy()


def test_wizard_validates_then_writes_configuration(root, tmp_path, monkeypatch):
    from view.setup_wizard import SetupWizard

    created: list[str] = []
    monkeypatch.setattr(setup, "test_connection", lambda database: None)
    monkeypatch.setattr(setup, "ensure_database_exists", lambda database: created.append(database.name) or True)
    monkeypatch.setattr(messagebox, "showinfo", lambda *args, **kwargs: None)
    monkeypatch.setattr(setup, "prepare_admin", lambda database, password, confirm: "nota")
    monkeypatch.setattr("utils.printer_manager.list_windows_printers", lambda: ["POS-80", "Otra"])
    monkeypatch.setattr("utils.printer_manager.default_windows_printer", lambda: "POS-80")
    printed: list[str] = []
    monkeypatch.setattr(setup, "run_test_print", lambda data: printed.append(data.printer_name))

    wizard = SetupWizard(root, base_dir=tmp_path)
    assert wizard.printer_box.get() == "POS-80", "propone la impresora predeterminada de Windows"
    wizard._print_test()
    deadline = time.monotonic() + 5
    while wizard._printing and time.monotonic() < deadline:
        root.update()
        time.sleep(0.05)
    assert printed == ["POS-80"] and "Tiquete enviado" in wizard.print_label.cget("text")
    wizard.set_value("business_name", "Tienda Prueba")
    wizard.set_value("port", "5434")
    wizard.set_value("db_password", "clave")
    wizard._save()  # falta la clave del administrador
    assert not wizard.saved and "administrador" in wizard.error_label.cget("text")
    assert setup.needs_setup(tmp_path)

    wizard.set_value("admin_password", "admin123")
    wizard.set_value("admin_repeat", "admin123")
    wizard._save()
    assert wizard.saved and created == ["inventario"]
    assert not setup.needs_setup(tmp_path)
    settings = load_settings(tmp_path)
    assert settings.business.name == "Tienda Prueba" and settings.database.port == 5434
    assert settings.database.password == "clave" and settings.admin_password == "admin123"
    assert settings.printer.mode == "windows" and settings.printer.name == "POS-80"
    assert settings.printer.paper_width_mm == 80 and settings.printer.paper_width_chars == 48
    assert settings.window.maximized is True and settings.window.geometry == "1520x750"


def test_port_detection_and_friendly_errors(monkeypatch):
    import socket

    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(5)  # cada sondeo deja una conexión en cola sin aceptar
    port = server.getsockname()[1]
    monkeypatch.setattr(setup, "COMMON_PORTS", (port,))
    try:
        assert setup.listening_ports("127.0.0.1", ports=(port,)) == [port]
        wrong_port = port - 1 if port > 1024 else port + 1
        database = DatabaseSettings("127.0.0.1", wrong_port, "inventario", "postgres", "x")
        assert setup.suggest_port(database, "connection to server failed: Connection refused") == port
        assert setup.suggest_port(database, "password authentication failed") is None
        same_port = DatabaseSettings("127.0.0.1", port, "inventario", "postgres", "x")
        assert setup.suggest_port(same_port, "Connection refused") is None
    finally:
        server.close()

    refused = setup.friendly_error(DatabaseSettings("localhost", 5432, "i", "u", "p"), "Connection refused (0x274D)")
    assert "5432" in refused and "PostgreSQL" in refused
    assert "clave" in setup.friendly_error(
        DatabaseSettings("localhost", 5432, "i", "u", "p"), "FATAL: password authentication failed"
    )
    assert setup.friendly_error(DatabaseSettings("localhost", 5432, "i", "u", "p"), "otro error") == "otro error"


class _FakeUsersDB:
    def __init__(self, users):
        self.users = users  # username -> (id, active)
        self.passwords: dict[int, str] = {}
        self.created: list[str] = []
        self.current_user = None

    def count_users(self):
        return len(self.users)

    def get_user(self, username):
        from model.user import ROLE_ADMIN, User

        entry = self.users.get(username)
        return None if entry is None else User(entry[0], username, "Administrador", ROLE_ADMIN, entry[1])

    def create_user(self, username, full_name, role, password):
        self.created.append(username)

    def set_password(self, user_id, password):
        self.passwords[user_id] = password

    def update_user(self, user_id, full_name, role, active):
        for username, (uid, _active) in self.users.items():
            if uid == user_id:
                self.users[username] = (uid, active)

    def close(self):
        pass


def test_prepare_admin_handles_empty_existing_and_missing_admin(monkeypatch):
    database = DatabaseSettings("localhost", 5434, "inventario", "postgres", "x")
    holder = {}
    monkeypatch.setattr(setup, "DBConnection", lambda settings: holder["db"])

    holder["db"] = _FakeUsersDB({})
    assert "creará" in setup.prepare_admin(database, "nueva", lambda q: True)
    assert holder["db"].created == []  # lo crea la aplicación al arrancar

    holder["db"] = _FakeUsersDB({"admin": (1, False), "caja": (2, True)})
    note = setup.prepare_admin(database, "nueva", lambda q: True)
    assert "reemplazada" in note and holder["db"].passwords == {1: "nueva"}
    assert holder["db"].users["admin"] == (1, True), "un admin inactivo se reactiva"

    holder["db"] = _FakeUsersDB({"admin": (1, True)})
    note = setup.prepare_admin(database, "nueva", lambda q: False)
    assert "conservó" in note and holder["db"].passwords == {}

    holder["db"] = _FakeUsersDB({"caja": (2, True)})
    note = setup.prepare_admin(database, "nueva", lambda q: True)
    assert "agregó" in note and holder["db"].created == ["admin"]
