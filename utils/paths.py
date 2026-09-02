"""Rutas de la aplicación.

Distingue entre ejecutar desde el código fuente y ejecutar el .exe empaquetado
con PyInstaller, para que los archivos editables por el usuario (.env,
config.json, logs) queden siempre junto al ejecutable y los recursos de solo
lectura (imágenes, migraciones) se lean desde el paquete.
"""

import sys
from pathlib import Path


def is_frozen() -> bool:
    """True cuando corre como ejecutable empaquetado."""
    return bool(getattr(sys, "frozen", False))


def app_dir() -> Path:
    """Carpeta de archivos editables: junto al .exe, o la raíz del proyecto en desarrollo."""
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent.parent


def resource_path(*parts: str) -> Path:
    """Ruta a un recurso empaquetado de solo lectura (imágenes, migraciones)."""
    base = getattr(sys, "_MEIPASS", None)
    root = Path(base) if base else app_dir()
    return root.joinpath(*parts)
