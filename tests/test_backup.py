"""Copias de seguridad: búsqueda de herramientas, listado, retención y errores claros."""

from __future__ import annotations

import datetime as dt
import os
import time
from pathlib import Path

import pytest

from utils import backup
from utils.backup import BackupError, BackupFile
from utils.config import BackupSettings, DatabaseSettings


def _touch(path: Path, days_ago: int) -> Path:
    path.write_bytes(b"x" * 10)
    stamp = time.time() - days_ago * 86_400
    os.utime(path, (stamp, stamp))
    return path


def test_find_tool_accepts_a_directory_or_the_executable(tmp_path):
    exe = tmp_path / "pg_dump.exe"
    exe.write_bytes(b"")
    assert backup.find_tool("pg_dump", str(tmp_path)) == exe
    assert backup.find_tool("pg_dump", str(exe)) == exe


def test_list_backups_newest_first_and_retention_keeps_the_latest(tmp_path):
    oldest = _touch(tmp_path / "inventario_1.backup", days_ago=3)
    middle = _touch(tmp_path / "inventario_2.backup", days_ago=2)
    newest = _touch(tmp_path / "inventario_3.backup", days_ago=0)
    (tmp_path / "otro.txt").write_text("no es copia")

    assert [b.path for b in backup.list_backups(tmp_path)] == [newest, middle, oldest]
    assert backup.last_backup(tmp_path).path == newest

    deleted = backup.apply_retention(tmp_path, keep=2)
    assert deleted == [oldest]
    assert [b.path for b in backup.list_backups(tmp_path)] == [newest, middle]


def test_backup_is_due_once_per_day(tmp_path):
    assert backup.backup_due(tmp_path) is True
    _touch(tmp_path / "inventario_hoy.backup", days_ago=0)
    assert backup.backup_due(tmp_path) is False
    _touch(tmp_path / "inventario_hoy.backup", days_ago=1)
    assert backup.backup_due(tmp_path) is True


def test_size_text_is_human_readable():
    now = dt.datetime.now()
    assert BackupFile(Path("a"), now, 512).size_text == "512 B"
    assert BackupFile(Path("a"), now, 1536).size_text == "1,5 KB"
    assert BackupFile(Path("a"), now, 3 * 1024 * 1024).size_text == "3,0 MB"


def test_backup_directory_is_relative_to_the_app_folder(tmp_path):
    directory = backup.backup_directory(BackupSettings(directory="copias"), tmp_path)
    assert directory == tmp_path / "copias" and directory.is_dir()
    absolute = backup.backup_directory(BackupSettings(directory=str(tmp_path / "abs")), Path("otra"))
    assert absolute == tmp_path / "abs"


def test_missing_pg_dump_is_a_clear_error(tmp_path, monkeypatch):
    monkeypatch.setattr(backup, "find_tool", lambda name, explicit="": None)
    database = DatabaseSettings("localhost", 5432, "inventario", "postgres", "x")
    with pytest.raises(BackupError, match="pg_dump"):
        backup.run_backup(database, BackupSettings(directory=str(tmp_path)), tmp_path)
    with pytest.raises(BackupError, match="pg_restore"):
        backup.restore_backup(database, BackupSettings(directory=str(tmp_path)), tmp_path / "x.backup")
