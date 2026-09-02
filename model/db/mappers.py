"""Conversión de filas de PostgreSQL a entidades del modelo."""

from __future__ import annotations

from decimal import Decimal

from model.product import Product
from model.user import User

PRODUCT_SELECT = """
    SELECT p.code, p.name, p.cost, p.price, p.stock, p.description, p.active, p.min_stock, p.tax_rate,
           c.category_name AS category
      FROM products p
      JOIN categories c ON c.idcategory = p.category
"""


def product_from(row) -> Product:
    return Product(
        code=row["code"],
        name=row["name"],
        cost=Decimal(row["cost"]),
        price=Decimal(row["price"]),
        stock=int(row["stock"]),
        category=row["category"],
        description=row["description"] or "",
        active=bool(row["active"]),
        min_stock=int(row["min_stock"]),
        tax_rate=Decimal(row["tax_rate"]),
    )


def missing_product(code: str) -> Product:
    """Producto de una venta antigua que ya no existe en el catálogo."""
    return Product(
        code=code, name="(producto eliminado)", cost=Decimal(0), price=Decimal(0), stock=0, category="", active=False
    )


def product_snapshot(product: Product) -> dict:
    return {
        "name": product.name,
        "cost": product.cost,
        "price": product.price,
        "stock": product.stock,
        "min_stock": product.min_stock,
        "tax_rate": product.tax_rate,
        "category": product.category,
        "description": product.description,
    }


def user_from(row) -> User:
    return User(
        id=int(row["id"]),
        username=row["username"],
        full_name=row["full_name"] or "",
        role=row["role"],
        active=bool(row["active"]),
    )
