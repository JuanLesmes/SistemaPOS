"""Configuración inicial: detecta el primer arranque y escribe .env y config.json.

Lo usa el asistente que aparece la primera vez que se abre la aplicación en el
computador del cliente, para no tener que editar archivos a mano.
"""

from __future__ import annotations

import json
import logging
import socket
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

import psycopg2
from dotenv import dotenv_values

from model.db_connection import DBConnection
from model.user import ROLE_ADMIN
from model.users_bootstrap import FIRST_ADMIN_USERNAME
from utils.config import (
    CONFIG_FILE,
    ENV_FILE,
    MODE_NETWORK,
    MODE_WINDOWS,
    PAPER_COLUMNS,
    PRINTER_MODES,
    WINDOW_SIZES,
    BusinessSettings,
    DatabaseSettings,
    PrinterSettings,
)
from utils.paths import app_dir
from utils.printer_manager import ReceiptPrinter

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
    printer_mode: str = MODE_WINDOWS
    printer_name: str = ""
    printer_host: str = ""
    paper_width_mm: int = 80
    cut_paper: bool = True
    window_maximized: bool = True
    window_size: str = WINDOW_SIZES[1]


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
    if data.printer_enabled:
        errors.extend(validate_printer(data))
    return errors


def validate_printer(data: SetupData) -> list[str]:
    if data.printer_mode not in PRINTER_MODES:
        return ["Elija cómo está conectada la impresora."]
    if data.printer_mode == MODE_NETWORK and not data.printer_host.strip():
        return ["Escriba la IP de la impresora de red."]
    if data.paper_width_mm not in PAPER_COLUMNS:
        return ["Elija el ancho del papel."]
    return []


def printer_settings_from(data: SetupData) -> PrinterSettings:
    """Configuración de impresora equivalente a lo que el asistente va a escribir en config.json."""
    return PrinterSettings(
        enabled=True,
        vendor_id=0x0483,
        product_id=0x070B,
        in_ep=0x81,
        out_ep=0x02,
        timeout_ms=10000,
        paper_width_chars=PAPER_COLUMNS.get(data.paper_width_mm, 48),
        open_drawer=data.open_drawer,
        mode=data.printer_mode,
        name=data.printer_name,
        host=data.printer_host.strip(),
        paper_width_mm=data.paper_width_mm,
        cut=data.cut_paper,
    )


def run_test_print(data: SetupData) -> None:
    """Imprime el tiquete de prueba con lo que hay en el asistente. Lanza PrinterError si falla."""
    ReceiptPrinter(printer_settings_from(data), data.business).print_test()


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


COMMON_PORTS = (5432, 5433, 5434, 5435, 5436)


def listening_ports(host: str, ports: tuple[int, ...] = COMMON_PORTS, timeout: float = 0.4) -> list[int]:
    """Puertos de la lista en los que algo acepta conexiones TCP: candidatos a ser PostgreSQL."""
    found = []
    for port in ports:
        try:
            with socket.create_connection((host, port), timeout=timeout):
                found.append(port)
        except OSError:
            continue
    return found


def suggest_port(database: DatabaseSettings, error: str) -> int | None:
    """Si nadie responde en el puerto configurado pero sí en otro habitual, devuelve ese otro."""
    if "refused" not in error.lower() and "rechaz" not in error.lower():
        return None
    others = [port for port in listening_ports(database.host, COMMON_PORTS) if port != database.port]
    return others[0] if others else None


def friendly_error(database: DatabaseSettings, error: str) -> str:
    """Traduce los errores más comunes de PostgreSQL a algo que el usuario pueda resolver."""
    lowered = error.lower()
    if "refused" in lowered or "rechaz" in lowered:
        return (
            f"Nada responde en {database.host}:{database.port}. Revise que PostgreSQL esté instalado e iniciado "
            "(Servicios de Windows) y que el puerto sea el de su instalación."
        )
    if "password authentication failed" in lowered or "autenticaci" in lowered:
        return "PostgreSQL rechazó el usuario o la clave. Es la clave que se definió al instalar PostgreSQL."
    if "timeout" in lowered or "timed out" in lowered:
        return f"El servidor {database.host} no respondió a tiempo. Revise la red o el firewall."
    return error


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


def prepare_admin(database: DatabaseSettings, password: str, confirm_replace: Callable[[str], bool]) -> str:
    """Deja listo el usuario admin en la base elegida y devuelve una nota para mostrar al usuario.

    - Base sin usuarios: no hace nada; la aplicación crea el admin al arrancar con ADMIN_PASSWORD.
    - Ya existe un usuario admin: pregunta con ``confirm_replace`` si se reemplaza su clave por la escrita.
    - Hay usuarios pero ninguno se llama admin: lo crea con la clave escrita.
    """
    db = DBConnection(database)
    db.current_user = "asistente"
    try:
        if db.count_users() == 0:
            return "Se creará el usuario admin con la clave que escribió."
        admin = db.get_user(FIRST_ADMIN_USERNAME)
        if admin is None:
            db.create_user(FIRST_ADMIN_USERNAME, "Administrador", ROLE_ADMIN, password)
            return "La base ya tenía usuarios; se agregó el usuario admin con la clave que escribió."
        question = (
            f"La base de datos '{database.name}' ya tiene usuarios y un administrador llamado admin.\n\n"
            "¿Quiere reemplazar la clave actual de admin por la que acaba de escribir?"
        )
        if confirm_replace(question):
            db.set_password(admin.id, password)
            if not admin.active:
                db.update_user(admin.id, admin.full_name, admin.role, True)
            return "La clave del usuario admin quedó reemplazada por la que escribió."
        return "Se conservó la clave anterior del usuario admin: entre con esa."
    finally:
        db.close()


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
    printer["mode"] = data.printer_mode
    printer["name"] = data.printer_name
    printer["host"] = data.printer_host.strip()
    printer.setdefault("port", 9100)
    printer["paper_width_mm"] = data.paper_width_mm
    printer.pop("paper_width_chars", None)  # las columnas se derivan del ancho en mm
    printer["cut"] = data.cut_paper
    try:
        width_text, height_text = data.window_size.lower().split("x")
        window = {"maximized": data.window_maximized, "width": int(width_text), "height": int(height_text)}
    except ValueError:
        window = {"maximized": data.window_maximized, "width": 1520, "height": 750}
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
        "window": window,
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
