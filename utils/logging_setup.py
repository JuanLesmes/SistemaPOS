"""Configuración única de logging para toda la aplicación.

Se llama una sola vez desde run.py. Escribe a ``logs/app.log`` con rotación y,
en desarrollo, también a la consola.
"""

import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path

from utils.paths import is_frozen

LOG_FORMAT = "%(asctime)s %(levelname)-8s %(name)s: %(message)s"
MAX_BYTES = 1_000_000
BACKUP_COUNT = 3


def setup_logging(log_dir: Path, level: int = logging.INFO) -> None:
    log_dir.mkdir(parents=True, exist_ok=True)
    handlers: list[logging.Handler] = [
        RotatingFileHandler(
            log_dir / "app.log",
            maxBytes=MAX_BYTES,
            backupCount=BACKUP_COUNT,
            encoding="utf-8",
        )
    ]
    if not is_frozen():
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=level, format=LOG_FORMAT, handlers=handlers)
