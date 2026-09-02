"""Categorías, productos, existencias y kárdex."""

from __future__ import annotations

import datetime as dt

import psycopg2
import psycopg2.errors
from psycopg2.extras import DictCursor

from model.db.base import escape_like
from model.db.mappers import PRODUCT_SELECT, product_from, product_snapshot
from model.errors import (
    AppError,
    CategoryInUseError,
    DuplicateProductError,
    InsufficientStockError,
    ProductNotFoundError,
)
from model.product import Product
from model.stock_movement import KIND_ADJUSTMENT, KIND_INITIAL, StockMovement

SEARCH_LIMIT = 50
MOVEMENTS_LIMIT = 300


class CatalogMixin:
    # ------------------------------------------------------------------ categorías
    def get_categories(self) -> list[str]:
        with self._transaction() as cur:
            cur.execute("SELECT category_name FROM categories ORDER BY lower(category_name)")
            return [row["category_name"] for row in cur.fetchall()]

    def add_category(self, name: str) -> bool:
        """Crea la categoría. Devuelve False si ya existía."""
        name = name.strip()
        if not name:
            raise AppError("El nombre de la categoría no puede estar vacío.")
        with self._transaction() as cur:
            cur.execute(
                "INSERT INTO categories (category_name) VALUES (%s)"
                " ON CONFLICT (category_name) DO NOTHING RETURNING idcategory",
                (name,),
            )
            created = cur.fetchone() is not None
            if created:
                self._log(cur, "add_category", details={"category_name": name})
            return created

    def delete_category(self, name: str) -> bool:
        """Elimina la categoría. Devuelve False si no existía. Falla si tiene productos."""
        with self._transaction() as cur:
            try:
                cur.execute("DELETE FROM categories WHERE category_name = %s", (name,))
            except (psycopg2.errors.ForeignKeyViolation, psycopg2.errors.RestrictViolation) as exc:
                raise CategoryInUseError(
                    f"La categoría '{name}' tiene productos asociados (activos o inactivos). "
                    "Cambie esos productos de categoría antes de eliminarla."
                ) from exc
            deleted = cur.rowcount > 0
            if deleted:
                self._log(cur, "delete_category", details={"category_name": name})
            return deleted

    # ------------------------------------------------------------------ productos
    def get_products(self, category: str | None = None) -> list[Product]:
        """Productos activos, opcionalmente filtrados por categoría."""
        sql = PRODUCT_SELECT + " WHERE p.active"
        params: list[object] = []
        if category:
            sql += " AND c.category_name = %s"
            params.append(category)
        sql += " ORDER BY lower(p.name)"
        with self._transaction() as cur:
            cur.execute(sql, params)
            return [product_from(row) for row in cur.fetchall()]

    def get_product(self, code: str, include_inactive: bool = False) -> Product | None:
        with self._transaction() as cur:
            return self._fetch_product(cur, code, include_inactive)

    def search_products(self, term: str) -> list[Product]:
        """Busca por nombre, descripción o código; primero las coincidencias en el nombre."""
        pattern = f"%{escape_like(term.strip().lower())}%"
        if pattern == "%%":
            return []
        with self._transaction() as cur:
            cur.execute(
                PRODUCT_SELECT
                + """
                 WHERE p.active
                   AND (lower(p.name) LIKE %s OR lower(p.description) LIKE %s OR lower(p.code) LIKE %s)
                 ORDER BY CASE WHEN lower(p.name) LIKE %s THEN 0 ELSE 1 END, lower(p.name)
                 LIMIT %s
                """,
                (pattern, pattern, pattern, pattern, SEARCH_LIMIT),
            )
            return [product_from(row) for row in cur.fetchall()]

    def get_best_sellers(self, days: int = 30, limit: int = 60) -> list[Product]:
        """Productos activos ordenados por unidades vendidas en los últimos ``days`` días."""
        with self._transaction() as cur:
            cur.execute(
                PRODUCT_SELECT
                + """
                  JOIN sold_products sp ON sp.codep = p.code
                  JOIN receipts r ON r.idreceipt = sp.idreceipt
                 WHERE p.active AND r.status = 'completed' AND r.date >= CURRENT_DATE - %s
                 GROUP BY p.code, p.name, p.cost, p.price, p.stock, p.description, p.active,
                          p.min_stock, p.tax_rate, c.category_name
                 ORDER BY SUM(sp.quantity) DESC, lower(p.name)
                 LIMIT %s
                """,
                (days, limit),
            )
            return [product_from(row) for row in cur.fetchall()]

    def add_product(self, product: Product) -> None:
        """Crea el producto. Si existía inactivo con el mismo código, lo reactiva con los datos nuevos."""
        _validate_product(product)
        with self._transaction() as cur:
            existing = self._fetch_product(cur, product.code, include_inactive=True)
            if existing is not None and existing.active:
                raise DuplicateProductError(f"Ya existe un producto con el código {product.code}.")
            category_id = self._category_id(cur, product.category, create=True)
            values = (
                product.name,
                product.cost,
                product.price,
                product.stock,
                category_id,
                product.description,
                product.min_stock,
                product.tax_rate,
            )
            if existing is None:
                cur.execute(
                    """
                    INSERT INTO products
                        (code, name, cost, price, stock, category, description, min_stock, tax_rate, active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, TRUE)
                    """,
                    (product.code, *values),
                )
                self._log(cur, "add_product", product.code, {"before": {}, "after": product_snapshot(product)})
            else:
                cur.execute(
                    """
                    UPDATE products
                       SET name = %s, cost = %s, price = %s, stock = %s, category = %s,
                           description = %s, min_stock = %s, tax_rate = %s, active = TRUE
                     WHERE code = %s
                    """,
                    (*values, product.code),
                )
                self._log(
                    cur,
                    "reactivate_product",
                    product.code,
                    {"before": product_snapshot(existing), "after": product_snapshot(product)},
                )
            if product.stock > 0:
                self._record_movement(cur, product.code, product.stock, KIND_INITIAL, product.stock, "Alta de producto")

    def update_product(self, product: Product) -> None:
        """Actualiza los datos de un producto activo. Las existencias se cambian con ``adjust_stock``."""
        _validate_product(product)
        with self._transaction() as cur:
            previous = self._fetch_product(cur, product.code)
            if previous is None:
                raise ProductNotFoundError(f"No existe un producto activo con el código {product.code}.")
            category_id = self._category_id(cur, product.category, create=True)
            cur.execute(
                """
                UPDATE products
                   SET name = %s, cost = %s, price = %s, category = %s, description = %s,
                       min_stock = %s, tax_rate = %s
                 WHERE code = %s AND active
                """,
                (
                    product.name,
                    product.cost,
                    product.price,
                    category_id,
                    product.description,
                    product.min_stock,
                    product.tax_rate,
                    product.code,
                ),
            )
            after = product_snapshot(product)
            after["stock"] = previous.stock  # las existencias no se editan desde el formulario
            self._log(cur, "modify_product", product.code, {"before": product_snapshot(previous), "after": after})

    def adjust_stock(self, code: str, quantity: int, reason: str = "") -> Product:
        """Suma (o resta, si es negativo) unidades con un motivo, y lo deja en el kárdex y la auditoría."""
        if quantity == 0:
            raise AppError("La cantidad debe ser distinta de cero.")
        with self._transaction() as cur:
            previous = self._fetch_product(cur, code)
            if previous is None:
                raise ProductNotFoundError(f"No existe un producto activo con el código {code}.")
            cur.execute(
                "UPDATE products SET stock = stock + %s WHERE code = %s AND active AND stock + %s >= 0 RETURNING stock",
                (quantity, code, quantity),
            )
            row = cur.fetchone()
            if row is None:
                raise InsufficientStockError(
                    f"'{previous.name}' solo tiene {previous.stock} unidades; no se pueden retirar {-quantity}."
                )
            stock_after = int(row["stock"])
            self._record_movement(cur, code, quantity, KIND_ADJUSTMENT, stock_after, reason=reason)
            self._log(
                cur,
                "stock_in" if quantity > 0 else "stock_out",
                code,
                {
                    "before": {"stock": previous.stock},
                    "after": {"stock": stock_after},
                    "reason": reason,
                },
            )
            updated = self._fetch_product(cur, code)
        assert updated is not None
        return updated

    def deactivate_product(self, code: str) -> None:
        """Borrado lógico: el producto deja de verse y venderse, pero sus ventas históricas quedan."""
        with self._transaction() as cur:
            previous = self._fetch_product(cur, code)
            if previous is None:
                raise ProductNotFoundError(f"No existe un producto activo con el código {code}.")
            cur.execute("UPDATE products SET active = FALSE WHERE code = %s", (code,))
            self._log(cur, "deactivate_product", code, {"before": product_snapshot(previous), "after": {}})

    # ------------------------------------------------------------------ kárdex
    def get_stock_movements(
        self,
        code: str | None = None,
        start: dt.date | None = None,
        end: dt.date | None = None,
        limit: int = MOVEMENTS_LIMIT,
    ) -> list[StockMovement]:
        conditions = []
        params: list[object] = []
        if code:
            conditions.append("m.codep = %s")
            params.append(code)
        if start:
            conditions.append("m.created_at >= %s")
            params.append(start)
        if end:
            conditions.append("m.created_at < %s + INTERVAL '1 day'")
            params.append(end)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        params.append(limit)
        with self._transaction() as cur:
            cur.execute(
                f"""
                SELECT m.id, m.codep, p.name, m.kind, m.quantity, m.stock_after, m.reference, m.reason,
                       m."user", m.created_at
                  FROM stock_movements m
                  JOIN products p ON p.code = m.codep
                  {where}
                 ORDER BY m.created_at DESC, m.id DESC
                 LIMIT %s
                """,
                params,
            )
            return [
                StockMovement(
                    id=int(row["id"]),
                    code=row["codep"],
                    product_name=row["name"],
                    kind=row["kind"],
                    quantity=int(row["quantity"]),
                    stock_after=int(row["stock_after"]),
                    reference=row["reference"] or "",
                    reason=row["reason"] or "",
                    user=row["user"],
                    created_at=row["created_at"],
                )
                for row in cur.fetchall()
            ]

    # ------------------------------------------------------------------ internos
    def _fetch_product(self, cur: DictCursor, code: str, include_inactive: bool = False) -> Product | None:
        sql = PRODUCT_SELECT + " WHERE p.code = %s"
        if not include_inactive:
            sql += " AND p.active"
        cur.execute(sql, (code,))
        row = cur.fetchone()
        return product_from(row) if row else None

    def _category_id(self, cur: DictCursor, name: str, create: bool = False) -> int:
        name = name.strip()
        if not name:
            raise AppError("Seleccione una categoría.")
        cur.execute("SELECT idcategory FROM categories WHERE category_name = %s", (name,))
        row = cur.fetchone()
        if row is not None:
            return int(row["idcategory"])
        if not create:
            raise AppError(f"La categoría '{name}' no existe.")
        cur.execute("INSERT INTO categories (category_name) VALUES (%s) RETURNING idcategory", (name,))
        category_id = int(cur.fetchone()["idcategory"])  # leer antes de ejecutar otra consulta
        self._log(cur, "add_category", details={"category_name": name})
        return category_id

    def _record_movement(
        self,
        cur: DictCursor,
        code: str,
        quantity: int,
        kind: str,
        stock_after: int,
        reference: str = "",
        reason: str = "",
    ) -> None:
        cur.execute(
            """
            INSERT INTO stock_movements (codep, kind, quantity, stock_after, reference, reason, "user")
            VALUES (%s, %s, %s, %s, %s, %s, %s)
            """,
            (code, kind, quantity, stock_after, reference, reason, self.current_user),
        )


def _validate_product(product: Product) -> None:
    if not product.code.strip():
        raise AppError("El código del producto es obligatorio.")
    if not product.name.strip():
        raise AppError("El nombre del producto es obligatorio.")
    if product.cost < 0 or product.price < 0:
        raise AppError("Costo y precio no pueden ser negativos.")
    if product.stock < 0:
        raise AppError("Las existencias no pueden ser negativas.")
    if product.min_stock < 0:
        raise AppError("El stock mínimo no puede ser negativo.")
    if product.tax_rate < 0 or product.tax_rate > 100:
        raise AppError("El IVA debe estar entre 0 y 100 por ciento.")
