import json
import os

import pytest

from model.errors import ConfigError
from utils.config import load_settings


@pytest.fixture(autouse=True)
def clean_environment(monkeypatch):
    for name in ("DB_HOST", "DB_PORT", "DB_NAME", "DB_USER", "DB_PASSWORD", "ADMIN_PASSWORD"):
        monkeypatch.delenv(name, raising=False)


def write_files(base, env: str, config: dict | None) -> None:
    (base / ".env").write_text(env, encoding="utf-8")
    if config is not None:
        (base / "config.json").write_text(json.dumps(config), encoding="utf-8")


def test_loads_database_business_and_printer(tmp_path):
    write_files(
        tmp_path,
        "DB_HOST=127.0.0.1\nDB_PORT=5434\nDB_NAME=tienda\nDB_USER=pos\nDB_PASSWORD=secreta\nADMIN_PASSWORD=admin\n",
        {
            "business": {"name": "Tienda", "nit": "1", "address": "Calle", "phone": "3", "receipt_footer": "Gracias"},
            "printer": {"enabled": False, "vendor_id": "0x0483", "product_id": 1803, "paper_width_chars": 48},
        },
    )
    settings = load_settings(tmp_path)

    assert settings.database.host == "127.0.0.1"
    assert settings.database.port == 5434
    assert settings.database.password == "secreta"
    assert settings.admin_password == "admin"
    assert settings.business.name == "Tienda"
    assert settings.printer.enabled is False
    assert settings.printer.vendor_id == 0x0483
    assert settings.printer.product_id == 1803
    assert settings.printer.paper_width_chars == 48
    assert settings.printer.in_ep == 0x81  # valor por defecto


def test_missing_password_is_a_clear_error(tmp_path):
    write_files(tmp_path, "DB_HOST=localhost\n", {"business": {}, "printer": {}})
    with pytest.raises(ConfigError, match="DB_PASSWORD"):
        load_settings(tmp_path)


def test_missing_config_json_is_a_clear_error(tmp_path):
    write_files(tmp_path, "DB_PASSWORD=x\n", None)
    with pytest.raises(ConfigError, match="config.json"):
        load_settings(tmp_path)


def test_invalid_printer_value_is_a_clear_error(tmp_path):
    write_files(tmp_path, "DB_PASSWORD=x\n", {"printer": {"vendor_id": "no-es-numero"}})
    with pytest.raises(ConfigError, match="printer"):
        load_settings(tmp_path)


def test_environment_overrides_are_not_required(tmp_path):
    write_files(tmp_path, "DB_PASSWORD=x\n", {})
    settings = load_settings(tmp_path)
    assert settings.database.host == "localhost"
    assert settings.database.port == 5432
    assert settings.business.name == "Mi Tienda"
    assert os.getenv("DB_PASSWORD") == "x"


def test_backup_section_has_defaults_and_overrides(tmp_path):
    write_files(tmp_path, "DB_PASSWORD=x\n", {})
    defaults = load_settings(tmp_path).backup
    assert defaults.enabled is True
    assert defaults.directory == "backups"
    assert defaults.keep == 30

    write_files(tmp_path, "DB_PASSWORD=x\n", {"backup": {"enabled": False, "directory": "D:/copias", "keep": 7}})
    custom = load_settings(tmp_path).backup
    assert custom.enabled is False
    assert custom.directory == "D:/copias"
    assert custom.keep == 7


def test_printer_modes_paper_width_and_window(tmp_path):
    write_files(
        tmp_path, "DB_PASSWORD=x\n", {"printer": {"mode": "network", "host": "192.168.0.50", "paper_width_mm": 58}}
    )
    printer = load_settings(tmp_path).printer
    assert printer.mode == "network" and printer.host == "192.168.0.50" and printer.port == 9100
    assert printer.paper_width_mm == 58 and printer.paper_width_chars == 32

    write_files(tmp_path, "DB_PASSWORD=x\n", {"printer": {"name": "POS-80", "paper_width_chars": 42}})
    printer = load_settings(tmp_path).printer
    assert printer.mode == "windows" and printer.name == "POS-80"
    assert printer.paper_width_mm == 80 and printer.paper_width_chars == 42, "un valor explícito manda"
    assert printer.cut is True

    write_files(tmp_path, "DB_PASSWORD=x\n", {"printer": {"mode": "fax"}})
    with pytest.raises(ConfigError, match="printer.mode"):
        load_settings(tmp_path)

    write_files(tmp_path, "DB_PASSWORD=x\n", {})
    window = load_settings(tmp_path).window
    assert window.maximized is True and window.geometry == "1520x750"

    write_files(tmp_path, "DB_PASSWORD=x\n", {"window": {"maximized": False, "width": 1366, "height": 768}})
    window = load_settings(tmp_path).window
    assert window.maximized is False and window.geometry == "1366x768"


def test_save_window_state_keeps_the_rest_of_the_config(tmp_path):
    from utils.config import save_window_state

    write_files(tmp_path, "DB_PASSWORD=x\n", {"business": {"name": "Tienda"}, "window": {"maximized": True}})
    save_window_state(tmp_path, maximized=False, width=1400, height=800)
    settings = load_settings(tmp_path)
    assert settings.business.name == "Tienda"
    assert settings.window.maximized is False and settings.window.geometry == "1400x800"
    save_window_state(tmp_path, maximized=True, width=1900, height=1000)
    settings = load_settings(tmp_path)
    assert settings.window.maximized is True and settings.window.geometry == "1400x800", "maximizada no pisa el tamaño"
