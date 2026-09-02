"""Configuración inicial: detección del primer arranque, validación y escritura de archivos."""

from __future__ import annotations

import contextlib
import json
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
    assert settings.backup.enabled is True


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

    wizard = SetupWizard(root, base_dir=tmp_path)
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
