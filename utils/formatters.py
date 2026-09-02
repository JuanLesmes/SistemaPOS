"""Formato y lectura de dinero y cantidades.

Convención colombiana: punto como separador de miles y coma como separador
decimal. "1.500" son mil quinientos pesos; "1.500,50" son mil quinientos con
cincuenta centavos.
"""

from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

ZERO = Decimal(0)


def format_price(value: Decimal | int | float | str | None, decimals: int = 0) -> str:
    """Devuelve el valor con puntos de miles y coma decimal, sin símbolo de moneda."""
    amount = to_decimal(value)
    step = Decimal(1).scaleb(-decimals)
    amount = amount.quantize(step, rounding=ROUND_HALF_UP)
    text = f"{amount:,.{decimals}f}"
    return text.replace(",", "\0").replace(".", ",").replace("\0", ".")


def format_money_input(value: Decimal) -> str:
    """Formato para campos de entrada: sin decimales cuando el valor es entero."""
    decimals = 0 if value == value.to_integral_value() else 2
    return format_price(value, decimals)


def parse_money(text: str) -> Decimal:
    """Convierte texto escrito por el usuario en Decimal. Lanza ValueError si no es válido."""
    cleaned = text.strip().replace("$", "").replace(" ", "")
    if not cleaned:
        raise ValueError("El valor está vacío.")
    cleaned = cleaned.replace(".", "").replace(",", ".")
    try:
        value = Decimal(cleaned)
    except InvalidOperation as exc:
        raise ValueError(f"'{text}' no es un valor válido.") from exc
    if not value.is_finite():
        raise ValueError(f"'{text}' no es un valor válido.")
    if value < 0:
        raise ValueError("El valor no puede ser negativo.")
    return value


def parse_int(text: str, minimum: int = 0) -> int:
    """Convierte texto en entero. Lanza ValueError si no es entero o es menor que ``minimum``."""
    cleaned = text.strip().replace(".", "")
    if not cleaned:
        raise ValueError("El valor está vacío.")
    try:
        value = int(cleaned)
    except ValueError as exc:
        raise ValueError(f"'{text}' no es un número entero.") from exc
    if value < minimum:
        raise ValueError(f"El valor debe ser mayor o igual que {minimum}.")
    return value


def to_decimal(value: Decimal | int | float | str | None) -> Decimal:
    """Normaliza cualquier entrada a Decimal; texto inválido o vacío vale cero."""
    if value is None:
        return ZERO
    if isinstance(value, Decimal):
        return value
    if isinstance(value, bool):
        raise TypeError("Un booleano no es un valor monetario.")
    if isinstance(value, (int, float)):
        return Decimal(str(value))
    if isinstance(value, str):
        try:
            return parse_money(value)
        except ValueError:
            return ZERO
    raise TypeError(f"No se puede convertir {type(value).__name__} a Decimal.")
