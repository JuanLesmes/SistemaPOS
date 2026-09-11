"""Imprime el tiquete de prueba con la configuración de config.json.

Ejecutar desde la raíz del proyecto: python scripts/test_printer.py
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from model.errors import AppError  # noqa: E402
from utils.config import load_settings  # noqa: E402
from utils.printer_manager import ReceiptPrinter, describe_connection, list_windows_printers  # noqa: E402


def main() -> int:
    try:
        settings = load_settings()
        print("Impresoras instaladas en Windows:", ", ".join(list_windows_printers()) or "ninguna")
        print("Configurada:", describe_connection(settings.printer))
        ReceiptPrinter(settings.printer, settings.business).print_test()
    except AppError as exc:
        print(f"Error: {exc}")
        return 1
    print("Tiquete de prueba enviado. Verifique la impresora.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
