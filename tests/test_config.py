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
