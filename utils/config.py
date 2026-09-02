"""Carga de configuración externa.

Dos archivos junto al ejecutable (o en la raíz del proyecto en desarrollo):

- ``.env``: credenciales de PostgreSQL y clave temporal de administración.
- ``config.json``: datos del negocio que salen en el recibo y parámetros de la
  impresora térmica. Hay una plantilla en ``config.example.json``.

Nada de esto debe estar en el código fuente ni en el repositorio.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

from model.errors import ConfigError
from utils.paths import app_dir, resource_path

logger = logging.getLogger(__name__)

ENV_FILE = ".env"
ENV_EXAMPLE_FILE = ".env.example"
CONFIG_FILE = "config.json"
CONFIG_EXAMPLE_FILE = "config.example.json"


@dataclass(frozen=True)
class DatabaseSettings:
    host: str
    port: int
    name: str
    user: str
    password: str


@dataclass(frozen=True)
class BusinessSettings:
    name: str
    nit: str
    address: str
    phone: str
    receipt_footer: str
    logo: str = ""  # ruta a una imagen PNG o JPG; relativa a la carpeta del programa si no es absoluta


@dataclass(frozen=True)
class PrinterSettings:
    enabled: bool
    vendor_id: int
    product_id: int
    in_ep: int
    out_ep: int
    timeout_ms: int
    paper_width_chars: int
    open_drawer: bool = False  # abrir el cajón monedero (conectado a la impresora) al cobrar en efectivo


@dataclass(frozen=True)
class BackupSettings:
    enabled: bool = True  # copia automática al primer arranque de cada día
    directory: str = "backups"  # relativa a la carpeta del programa si no es absoluta
    keep: int = 30  # cuántas copias se conservan
    pg_bin: str = ""  # carpeta bin de PostgreSQL; vacío = se busca sola


@dataclass(frozen=True)
class Settings:
    database: DatabaseSettings
    business: BusinessSettings
    printer: PrinterSettings
    admin_password: str
    backup: BackupSettings = field(default_factory=BackupSettings)


def load_settings(base_dir: Path | None = None) -> Settings:
    """Lee .env y config.json. Lanza ConfigError con un mensaje claro si falta algo."""
    base = base_dir or app_dir()
    _copy_templates(base)
    load_dotenv(base / ENV_FILE)

    database = DatabaseSettings(
        host=os.getenv("DB_HOST", "localhost"),
        port=_env_int("DB_PORT", 5432),
        name=os.getenv("DB_NAME", "inventario"),
        user=os.getenv("DB_USER", "postgres"),
        password=os.getenv("DB_PASSWORD", ""),
    )
    if not database.password:
        raise ConfigError(
            f"Falta DB_PASSWORD en {base / ENV_FILE}. Copie .env.example como .env y escriba la clave de PostgreSQL."
        )

    config_path = base / CONFIG_FILE
    if not config_path.exists():
        raise ConfigError(
            f"No existe {config_path}. Copie {CONFIG_EXAMPLE_FILE} como {CONFIG_FILE} y ajuste los datos del negocio."
        )
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ConfigError(f"{config_path} no es un JSON válido: {exc}") from exc

    return Settings(
        database=database,
        business=_business_from(data.get("business", {})),
        printer=_printer_from(data.get("printer", {})),
        admin_password=os.getenv("ADMIN_PASSWORD", ""),
        backup=_backup_from(data.get("backup", {})),
    )


def _copy_templates(base: Path) -> None:
    """Deja las plantillas junto al ejecutable la primera vez, para que el usuario las complete."""
    for name in (ENV_EXAMPLE_FILE, CONFIG_EXAMPLE_FILE):
        target = base / name
        source = resource_path(name)
        if target.exists() or not source.exists() or source.resolve() == target.resolve():
            continue
        try:
            shutil.copyfile(source, target)
            logger.info("Plantilla copiada: %s", target)
        except OSError:
            logger.warning("No se pudo copiar la plantilla %s a %s", name, base, exc_info=True)


def _business_from(raw: dict) -> BusinessSettings:
    return BusinessSettings(
        name=str(raw.get("name", "Mi Tienda")),
        nit=str(raw.get("nit", "")),
        address=str(raw.get("address", "")),
        phone=str(raw.get("phone", "")),
        receipt_footer=str(raw.get("receipt_footer", "Gracias por su compra")),
        logo=str(raw.get("logo", "") or ""),
    )


def _printer_from(raw: dict) -> PrinterSettings:
    try:
        return PrinterSettings(
            enabled=bool(raw.get("enabled", True)),
            vendor_id=_as_int(raw.get("vendor_id", "0x0483")),
            product_id=_as_int(raw.get("product_id", "0x070b")),
            in_ep=_as_int(raw.get("in_ep", "0x81")),
            out_ep=_as_int(raw.get("out_ep", "0x02")),
            timeout_ms=_as_int(raw.get("timeout_ms", 10000)),
            paper_width_chars=_as_int(raw.get("paper_width_chars", 32)),
            open_drawer=bool(raw.get("open_drawer", False)),
        )
    except ValueError as exc:
        raise ConfigError(f"Valor inválido en la sección printer de {CONFIG_FILE}: {exc}") from exc


def _backup_from(raw: dict) -> BackupSettings:
    try:
        return BackupSettings(
            enabled=bool(raw.get("enabled", True)),
            directory=str(raw.get("directory", "backups") or "backups"),
            keep=max(1, _as_int(raw.get("keep", 30))),
            pg_bin=str(raw.get("pg_bin", "") or ""),
        )
    except ValueError as exc:
        raise ConfigError(f"Valor inválido en la sección backup de {CONFIG_FILE}: {exc}") from exc


def _as_int(value: object) -> int:
    """Acepta enteros o cadenas decimales/hexadecimales como "0x0483"."""
    if isinstance(value, bool):
        raise ValueError(f"se esperaba un número, llegó {value!r}")
    if isinstance(value, int):
        return value
    return int(str(value).strip(), 0)


def _env_int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return int(raw)
    except ValueError as exc:
        raise ConfigError(f"{name} debe ser un número entero, llegó {raw!r}") from exc
