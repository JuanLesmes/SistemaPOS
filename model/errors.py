"""Errores de negocio de la aplicación.

Todos heredan de AppError y llevan un mensaje pensado para mostrarse tal cual
al usuario. Los controladores los capturan y los presentan; el modelo los lanza.
"""


class AppError(Exception):
    """Error esperado dentro de la operación normal del negocio."""


class ConfigError(AppError):
    """Falta o es inválido un archivo de configuración."""


class DatabaseUnavailableError(AppError):
    """No se pudo conectar con PostgreSQL."""


class ProductNotFoundError(AppError):
    """El código de producto no existe o está inactivo."""


class DuplicateProductError(AppError):
    """Ya existe un producto activo con ese código."""


class InsufficientStockError(AppError):
    """La venta pide más unidades de las que hay en existencia."""


class CategoryInUseError(AppError):
    """La categoría tiene productos asociados y no puede borrarse."""


class PrinterError(AppError):
    """La impresora no respondió o no está conectada."""
