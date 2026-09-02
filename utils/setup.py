"""Configuración inicial: detecta el primer arranque y escribe .env y config.json.

Lo usa el asistente que aparece la primera vez que se abre la aplicación en el
computador del cliente, para no tener que editar archivos a mano.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from dotenv import dotenv_values

from utils.config import CONFIG_FILE, ENV_FILE, BusinessSettings, DatabaseSettings
from utils.paths import app_dir

logger = logging.getLogger(__name__)

MIN_PASSWORD = 6


@dataclass(frozen=True)
class SetupData:
    business: BusinessSettings
    database: DatabaseSettings
    admin_password: str
    admin_password_repeat: str
    printer_enabled: bool
    open_drawer: bool


def needs_setup(base: Path | None = None) -> bool:
    """True si faltan los archivos de configuración o la clave de la base."""
    base = base or app_dir()
    env_path = base / ENV_FILE
    if not env_path.exists() or not (base / CONFIG_FILE).exists():
        return True
    values = dotenv_values(env_path)
    return not (values.get("DB_PASSWORD") or "").strip()


def validate(data: SetupData) -> list[str]:
    errors = []
    if not data.business.name.strip():
        errors.append("Escriba el nombre del negocio.")
    if not data.database.host.strip():
        errors.append("Escriba el servidor de PostgreSQL (normalmente localhost).")
    if not 1 <= data.database.port <= 65535:
        errors.append("El puerto debe estar entre 1 y 65535.")
    if not data.database.name.strip():
        errors.append("Escriba el nombre de la base de datos.")
    if not data.database.user.strip():
        errors.append("Escriba el usuario de PostgreSQL.")
    if not data.database.password:
        errors.append("Escriba la clave de PostgreSQL.")
    if len(data.admin_password) < MIN_PASSWORD:
        errors.append(f"La clave del administrador debe tener al menos {MIN_PASSWORD} caracteres.")
    elif data.admin_password != data.admin_password_repeat:
        errors.append("Las dos claves del administrador no coinciden.")
    return errors


def test_connection(database: DatabaseSettings) -> str | None:
    """Intenta conectarse al servidor (base ``postgres``). Devuelve el error, o None si funciona."""
    try:
        conn = psycopg2.connect(
            host=database.host,
            port=database.port,
            dbname="postgres",
            user=database.user,
            password=database.password,
            connect_timeout=5,
        )
    except UnicodeDecodeError:
        return "PostgreSQL rechazó la conexión. Revise usuario y clave."
    except psycopg2.OperationalError as exc:
        return str(exc).strip().splitlines()[0] if str(exc).strip() else "No se pudo conectar."
    conn.close()
    return None


def ensure_database_exists(database: DatabaseSettings) -> bool:
    """Crea la base si no existe. Devuelve True si la creó."""
    conn = psycopg2.connect(
        host=database.host,
        port=database.port,
        dbname="postgres",
        user=database.user,
        password=database.password,
        connect_timeout=5,
    )
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (database.name,))
            if cur.fetchone():
                return False
            safe_name = database.name.replace('"', '""')
            cur.execute(f"CREATE DATABASE \"{safe_name}\" ENCODING 'UTF8'")
            logger.info("Base de datos creada: %s", database.name)
            return True
    finally:
        conn.close()


def write_files(data: SetupData, base: Path | None = None) -> tuple[Path, Path]:
    """Escribe .env y config.json. Devuelve las dos rutas."""
    base = base or app_dir()
    env_path = base / ENV_FILE
    env_lines = [
        "# Generado por el asistente de configuración inicial.",
        f"DB_HOST={data.database.host.strip()}",
        f"DB_PORT={data.database.port}",
        f"DB_NAME={data.database.name.strip()}",
        f"DB_USER={data.database.user.strip()}",
        f"DB_PASSWORD={data.database.password}",
        f"ADMIN_PASSWORD={data.admin_password}",
        "",
    ]
    env_path.write_text("\n".join(env_lines), encoding="utf-8")

    config_path = base / CONFIG_FILE
    existing = _read_json(config_path)
    printer = existing.get("printer", {})
    printer.setdefault("vendor_id", "0x0483")
    printer.setdefault("product_id", "0x070b")
    printer.setdefault("in_ep", "0x81")
    printer.setdefault("out_ep", "0x02")
    printer.setdefault("timeout_ms", 10000)
    printer.setdefault("paper_width_chars", 32)
    printer["enabled"] = data.printer_enabled
    printer["open_drawer"] = data.open_drawer
    config = {
        "business": {
            "name": data.business.name.strip(),
            "nit": data.business.nit.strip(),
            "address": data.business.address.strip(),
            "phone": data.business.phone.strip(),
            "receipt_footer": data.business.receipt_footer.strip() or "Gracias por su compra",
            "logo": data.business.logo,
        },
        "printer": printer,
        "backup": existing.get("backup", {"enabled": True, "directory": "backups", "keep": 30, "pg_bin": ""}),
    }
    config_path.write_text(json.dumps(config, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    logger.info("Configuración inicial escrita en %s", base)
    return env_path, config_path


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}
