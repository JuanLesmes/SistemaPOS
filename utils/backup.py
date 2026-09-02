"""Copias de seguridad de PostgreSQL con pg_dump y restauración con pg_restore.

Las copias se guardan en formato personalizado (``-F c``), que permite
restaurar con ``pg_restore``. Se conservan las más recientes y las demás se
borran para no llenar el disco.
"""

from __future__ import annotations

import datetime as dt
import logging
import os
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

from model.errors import AppError
from utils.config import BackupSettings, DatabaseSettings

logger = logging.getLogger(__name__)

BACKUP_SUFFIX = ".backup"
PG_ROOT = Path(r"C:\Program Files\PostgreSQL")


@dataclass(frozen=True)
class BackupFile:
    path: Path
    created_at: dt.datetime
    size_bytes: int

    @property
    def size_text(self) -> str:
        size = self.size_bytes
        for unit in ("B", "KB", "MB", "GB"):
            if size < 1024 or unit == "GB":
                return f"{size:.0f} {unit}" if unit == "B" else f"{size:.1f} {unit}".replace(".", ",")
            size /= 1024
        return f"{size:.1f} GB"


class BackupError(AppError):
    """No se pudo hacer o restaurar la copia."""


def find_tool(name: str, explicit: str = "") -> Path | None:
    """Busca pg_dump o pg_restore: ruta configurada, PATH, o la instalación más nueva de PostgreSQL."""
    if explicit:
        candidate = Path(explicit)
        if candidate.is_dir():
            candidate = candidate / f"{name}.exe"
        if candidate.exists():
            return candidate
    found = shutil.which(name)
    if found:
        return Path(found)
    if PG_ROOT.exists():
        versions = sorted(
            (p for p in PG_ROOT.iterdir() if p.is_dir()), key=lambda p: _version_key(p.name), reverse=True
        )
        for version in versions:
            candidate = version / "bin" / f"{name}.exe"
            if candidate.exists():
                return candidate
    return None


def backup_directory(settings: BackupSettings, base_dir: Path) -> Path:
    directory = Path(settings.directory)
    if not directory.is_absolute():
        directory = base_dir / directory
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def list_backups(directory: Path) -> list[BackupFile]:
    files = []
    for path in directory.glob(f"*{BACKUP_SUFFIX}"):
        stat = path.stat()
        files.append(BackupFile(path, dt.datetime.fromtimestamp(stat.st_mtime), stat.st_size))
    return sorted(files, key=lambda f: f.created_at, reverse=True)


def last_backup(directory: Path) -> BackupFile | None:
    backups = list_backups(directory)
    return backups[0] if backups else None


def backup_due(directory: Path, today: dt.date | None = None) -> bool:
    """True si hoy todavía no se ha hecho ninguna copia."""
    latest = last_backup(directory)
    return latest is None or latest.created_at.date() < (today or dt.date.today())


def apply_retention(directory: Path, keep: int) -> list[Path]:
    """Borra las copias más viejas dejando las ``keep`` más recientes. Devuelve las borradas."""
    deleted = []
    for old in list_backups(directory)[max(keep, 1) :]:
        try:
            old.path.unlink()
            deleted.append(old.path)
        except OSError:
            logger.warning("No se pudo borrar la copia vieja %s", old.path, exc_info=True)
    return deleted


def run_backup(database: DatabaseSettings, settings: BackupSettings, base_dir: Path) -> Path:
    """Ejecuta pg_dump y devuelve la ruta del archivo creado."""
    tool = find_tool("pg_dump", settings.pg_bin)
    if tool is None:
        raise BackupError(
            "No se encontró pg_dump. Instale las herramientas de PostgreSQL o indique la carpeta bin en "
            "config.json (backup.pg_bin)."
        )
    directory = backup_directory(settings, base_dir)
    target = directory / f"{database.name}_{dt.datetime.now():%Y%m%d_%H%M%S}{BACKUP_SUFFIX}"
    command = [
        str(tool),
        "-h",
        database.host,
        "-p",
        str(database.port),
        "-U",
        database.user,
        "-F",
        "c",
        "-f",
        str(target),
        database.name,
    ]
    _run(command, database.password, "pg_dump")
    if not target.exists() or target.stat().st_size == 0:
        raise BackupError("pg_dump terminó pero el archivo de copia quedó vacío.")
    apply_retention(directory, settings.keep)
    logger.info("Copia de seguridad creada: %s", target)
    return target


def restore_backup(database: DatabaseSettings, settings: BackupSettings, backup_file: Path) -> None:
    """Restaura una copia sobre la base configurada (reemplaza los datos actuales)."""
    tool = find_tool("pg_restore", settings.pg_bin)
    if tool is None:
        raise BackupError("No se encontró pg_restore. Instale las herramientas de PostgreSQL.")
    if not backup_file.exists():
        raise BackupError(f"No existe el archivo {backup_file}.")
    command = [
        str(tool),
        "-h",
        database.host,
        "-p",
        str(database.port),
        "-U",
        database.user,
        "-d",
        database.name,
        "--clean",
        "--if-exists",
        "--no-owner",
        str(backup_file),
    ]
    _run(command, database.password, "pg_restore")
    logger.info("Copia restaurada desde %s", backup_file)


def _run(command: list[str], password: str, tool: str) -> None:
    env = {**os.environ, "PGPASSWORD": password, "PGCLIENTENCODING": "UTF8"}
    try:
        completed = subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=600,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise BackupError(f"No se pudo ejecutar {tool}: {exc}") from exc
    if completed.returncode != 0:
        detail = (completed.stderr or completed.stdout or "").strip().splitlines()
        raise BackupError(f"{tool} falló: {detail[-1] if detail else 'sin detalle'}")


def _version_key(name: str) -> tuple:
    try:
        return tuple(int(part) for part in name.split("."))
    except ValueError:
        return (0,)
