"""Acceso a PostgreSQL.

Única capa de la aplicación que ejecuta SQL. Cada método público corre dentro
de una transacción: si algo falla a mitad de camino no queda nada a medias.
Los errores esperados se lanzan como subclases de AppError con un mensaje
listo para mostrar al usuario; los controladores solo tienen que capturarlos.
"""

from __future__ import annotations

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date
from decimal import Decimal

import psycopg2
import psycopg2.errors
from psycopg2.extras import DictCursor

from model.audit_log import AuditEntry
from model.errors import (
    AppError,
    CategoryInUseError,
    DatabaseUnavailableError,
    DuplicateProductError,
    InsufficientStockError,
    ProductNotFoundError,
)
from model.migrations import run_migrations
from model.product import Product
from model.receipt import Receipt
from model.sold_product import SoldProduct
from utils.config import DatabaseSettings

logger = logging.getLogger(__name__)

SEARCH_LIMIT = 50

_PRODUCT_SELECT = """
    SELECT p.code, p.name, p.cost, p.price, p.stock, p.description, p.active,
           c.category_name AS category
      FROM products p
      JOIN categories c ON c.idcategory = p.category
"""

# Acciones antiguas que no representan cambios del catálogo y no se muestran en auditoría.
_HIDDEN_AUDIT_ACTIONS = ("update_stock",)


class DBConnection:
    def __init__(self, settings: DatabaseSettings) -> None:
        self._settings = settings
        self._conn = None
        self._connect()
        applied = run_migrations(self._conn)
        if applied:
            logger.info("Migraciones aplicadas: %s", ", ".join(applied))

    # ------------------------------------------------------------------ conexión
    def _connect(self) -> None:
        s = self._settings
        try:
            self._conn = psycopg2.connect(
                host=s.host,
                port=s.port,
                dbname=s.name,
                user=s.user,
                password=s.password,
                client_encoding="UTF8",
                connect_timeout=5,
            )
        except UnicodeDecodeError as exc:
            # PostgreSQL en Windows responde en el idioma del sistema (Latin-1) antes
            # de negociar la codificación. El texto no se puede leer, pero casi
            # siempre significa usuario, clave o base incorrectos.
            raise DatabaseUnavailableError(
                f"PostgreSQL rechazó la conexión a {s.host}:{s.port}. "
                "Revise usuario, clave y nombre de la base en el archivo .env."
            ) from exc
        except psycopg2.OperationalError as exc:
            raise DatabaseUnavailableError(
                f"No se pudo conectar a PostgreSQL en {s.host}:{s.port}: {_first_line(exc)}"
            ) from exc
        self._conn.autocommit = False
        logger.info("Conectado a PostgreSQL %s:%s base %s", s.host, s.port, s.name)

    def close(self) -> None:
        if self._conn is not None and not self._conn.closed:
            self._conn.close()
            logger.info("Conexión cerrada")

    @contextmanager
    def _transaction(self) -> Iterator[DictCursor]:
        """Abre un cursor dentro de una transacción; confirma al salir o revierte si hay error."""
        if self._conn is None or self._conn.closed:
            self._connect()
        try:
            with self._conn.cursor(cursor_factory=DictCursor) as cur:
                yield cur
            self._conn.commit()
        except (psycopg2.InterfaceError, psycopg2.OperationalError) as exc:
            self._rollback_quietly()
            raise DatabaseUnavailableError("Se perdió la conexión con la base de datos. Intente de nuevo.") from exc
        except Exception:
            self._rollback_quietly()
            raise

    def _rollback_quietly(self) -> None:
        try:
            if self._conn is not None and not self._conn.closed:
                self._conn.rollback()
        except psycopg2.Error:
            logger.warning("No se pudo revertir la transacción", exc_info=True)

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
            except psycopg2.errors.ForeignKeyViolation as exc:
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
        sql = _PRODUCT_SELECT + " WHERE p.active"
        params: list[object] = []
        if category:
            sql += " AND c.category_name = %s"
            params.append(category)
        sql += " ORDER BY lower(p.name)"
        with self._transaction() as cur:
            cur.execute(sql, params)
            return [_product_from(row) for row in cur.fetchall()]

    def get_product(self, code: str, include_inactive: bool = False) -> Product | None:
        with self._transaction() as cur:
            return self._fetch_product(cur, code, include_inactive)

    def search_products(self, term: str) -> list[Product]:
        """Busca por nombre, descripción o código; primero las coincidencias en el nombre."""
        pattern = f"%{_escape_like(term.strip().lower())}%"
        if pattern == "%%":
            return []
        with self._transaction() as cur:
            cur.execute(
                _PRODUCT_SELECT
                + """
                 WHERE p.active
                   AND (lower(p.name) LIKE %s OR lower(p.description) LIKE %s OR lower(p.code) LIKE %s)
                 ORDER BY CASE WHEN lower(p.name) LIKE %s THEN 0 ELSE 1 END, lower(p.name)
                 LIMIT %s
                """,
                (pattern, pattern, pattern, pattern, SEARCH_LIMIT),
            )
            return [_product_from(row) for row in cur.fetchall()]

    def add_product(self, product: Product) -> None:
        """Crea el producto. Si existía inactivo con el mismo código, lo reactiva con los datos nuevos."""
        _validate_product(product)
        with self._transaction() as cur:
            existing = self._fetch_product(cur, product.code, include_inactive=True)
            if existing is not None and existing.active:
                raise DuplicateProductError(f"Ya existe un producto con el código {product.code}.")
            category_id = self._category_id(cur, product.category, create=True)
            if existing is None:
                cur.execute(
                    """
                    INSERT INTO products (code, name, cost, price, stock, category, description, active)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, TRUE)
                    """,
                    (
                        product.code,
                        product.name,
                        product.cost,
                        product.price,
                        product.stock,
                        category_id,
                        product.description,
                    ),
                )
                self._log(cur, "add_product", product.code, {"before": {}, "after": _snapshot(product)})
            else:
                cur.execute(
                    """
                    UPDATE products
                       SET name = %s, cost = %s, price = %s, stock = %s,
                           category = %s, description = %s, active = TRUE
                     WHERE code = %s
                    """,
                    (
                        product.name,
                        product.cost,
                        product.price,
                        product.stock,
                        category_id,
                        product.description,
                        product.code,
                    ),
                )
                self._log(
                    cur,
                    "reactivate_product",
                    product.code,
                    {"before": _snapshot(existing), "after": _snapshot(product)},
                )

    def update_product(self, product: Product) -> None:
        """Actualiza nombre, costo, precio, stock, categoría y descripción de un producto activo."""
        _validate_product(product)
        with self._transaction() as cur:
            previous = self._fetch_product(cur, product.code)
            if previous is None:
                raise ProductNotFoundError(f"No existe un producto activo con el código {product.code}.")
            category_id = self._category_id(cur, product.category, create=True)
            cur.execute(
                """
                UPDATE products
                   SET name = %s, cost = %s, price = %s, stock = %s, category = %s, description = %s
                 WHERE code = %s AND active
                """,
                (
                    product.name,
                    product.cost,
                    product.price,
                    product.stock,
                    category_id,
                    product.description,
                    product.code,
                ),
            )
            self._log(
                cur,
                "modify_product",
                product.code,
                {"before": _snapshot(previous), "after": _snapshot(product)},
            )

    def add_stock(self, code: str, quantity: int) -> Product:
        """Suma (o resta, si es negativo) unidades y devuelve el producto actualizado."""
        if quantity == 0:
            raise AppError("La cantidad debe ser distinta de cero.")
        with self._transaction() as cur:
            previous = self._fetch_product(cur, code)
            if previous is None:
                raise ProductNotFoundError(f"No existe un producto activo con el código {code}.")
            cur.execute(
                """
                UPDATE products
                   SET stock = stock + %s
                 WHERE code = %s AND active AND stock + %s >= 0
             RETURNING stock
                """,
                (quantity, code, quantity),
            )
            row = cur.fetchone()
            if row is None:
                raise InsufficientStockError(
                    f"'{previous.name}' solo tiene {previous.stock} unidades; no se pueden retirar {-quantity}."
                )
            self._log(
                cur,
                "update_stock",
                code,
                {"before": {"stock": previous.stock}, "after": {"stock": row["stock"]}},
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
            self._log(cur, "deactivate_product", code, {"before": _snapshot(previous), "after": {}})

    # ------------------------------------------------------------------ ventas
    def add_receipt(self, receipt: Receipt) -> int:
        """Guarda el recibo, sus líneas y descuenta existencias, todo o nada."""
        if not receipt.sold_products:
            raise AppError("La venta no tiene productos.")
        with self._transaction() as cur:
            cur.execute(
                """
                INSERT INTO receipts (total, date, time, payment_method)
                VALUES (%s, %s, %s, %s)
                RETURNING idreceipt
                """,
                (receipt.total, receipt.date, receipt.time, receipt.payment_method),
            )
            receipt_id = int(cur.fetchone()["idreceipt"])
            for sp in receipt.sold_products:
                cur.execute(
                    """
                    UPDATE products
                       SET stock = stock - %s
                     WHERE code = %s AND active AND stock >= %s
                 RETURNING stock
                    """,
                    (sp.quantity, sp.code, sp.quantity),
                )
                if cur.fetchone() is None:
                    current = self._fetch_product(cur, sp.code)
                    available = current.stock if current else 0
                    raise InsufficientStockError(
                        f"No hay existencias suficientes de '{sp.product.name}': "
                        f"hay {available} y la venta pide {sp.quantity}."
                    )
                cur.execute(
                    """
                    INSERT INTO sold_products (idreceipt, codep, quantity, unit_price, unit_cost)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (receipt_id, sp.code, sp.quantity, sp.unit_price, sp.unit_cost),
                )
        logger.info(
            "Venta registrada: recibo %s, %s líneas, total %s (%s)",
            receipt_id,
            len(receipt.sold_products),
            receipt.total,
            receipt.payment_method,
        )
        return receipt_id

    def get_receipts_in_range(self, start: date, end: date) -> list[Receipt]:
        """Recibos con sus líneas entre dos fechas inclusive, en una sola consulta."""
        with self._transaction() as cur:
            cur.execute(
                """
                SELECT r.idreceipt, r.total, r.date, r.time, r.payment_method,
                       sp.codep, sp.quantity, sp.unit_price, sp.unit_cost,
                       p.name, p.cost, p.price, p.stock, p.description, p.active,
                       c.category_name AS category
                  FROM receipts r
                  LEFT JOIN sold_products sp ON sp.idreceipt = r.idreceipt
                  LEFT JOIN products p ON p.code = sp.codep
                  LEFT JOIN categories c ON c.idcategory = p.category
                 WHERE r.date BETWEEN %s AND %s
                 ORDER BY r.date, r.time, r.idreceipt, sp.idsale
                """,
                (start, end),
            )
            rows = cur.fetchall()

        receipts: dict[int, Receipt] = {}
        for row in rows:
            receipt_id = int(row["idreceipt"])
            receipt = receipts.get(receipt_id)
            if receipt is None:
                receipt = Receipt(
                    id=receipt_id,
                    date=row["date"],
                    time=row["time"],
                    payment_method=row["payment_method"],
                    total=Decimal(row["total"]),
                )
                receipts[receipt_id] = receipt
            if row["codep"] is None:
                continue
            receipt.sold_products.append(
                SoldProduct(
                    product=_product_from(row) if row["name"] is not None else _missing_product(row["codep"]),
                    quantity=int(row["quantity"]),
                    unit_price=Decimal(row["unit_price"]),
                    unit_cost=Decimal(row["unit_cost"]),
                )
            )
        return list(receipts.values())

    # ------------------------------------------------------------------ auditoría
    def get_logs_by_date(self, day: date) -> list[AuditEntry]:
        with self._transaction() as cur:
            cur.execute(
                """
                SELECT timestamp, action, code, details, "user"
                  FROM audit_logs
                 WHERE timestamp >= %s AND timestamp < %s + INTERVAL '1 day'
                   AND action <> ALL(%s)
                 ORDER BY timestamp
                """,
                (day, day, list(_HIDDEN_AUDIT_ACTIONS)),
            )
            return [
                AuditEntry(
                    timestamp=row["timestamp"],
                    action=row["action"],
                    code=row["code"],
                    details=row["details"],
                    user=row["user"],
                )
                for row in cur.fetchall()
            ]

    # ------------------------------------------------------------------ internos
    def _fetch_product(self, cur: DictCursor, code: str, include_inactive: bool = False) -> Product | None:
        sql = _PRODUCT_SELECT + " WHERE p.code = %s"
        if not include_inactive:
            sql += " AND p.active"
        cur.execute(sql, (code,))
        row = cur.fetchone()
        return _product_from(row) if row else None

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
        self._log(cur, "add_category", details={"category_name": name})
        return int(cur.fetchone()["idcategory"])

    def _log(
        self,
        cur: DictCursor,
        action: str,
        code: str | None = None,
        details: dict | None = None,
        user: str | None = None,
    ) -> None:
        payload = json.dumps(details, ensure_ascii=False, default=str) if details is not None else None
        cur.execute(
            'INSERT INTO audit_logs (action, code, details, "user") VALUES (%s, %s, %s, %s)',
            (action, code, payload, user),
        )


# ---------------------------------------------------------------------- helpers
def _product_from(row) -> Product:
    return Product(
        code=row["code"],
        name=row["name"],
        cost=Decimal(row["cost"]),
        price=Decimal(row["price"]),
        stock=int(row["stock"]),
        category=row["category"],
        description=row["description"] or "",
        active=bool(row["active"]),
    )


def _missing_product(code: str) -> Product:
    """Producto de una venta antigua que ya no existe en el catálogo."""
    return Product(
        code=code,
        name="(producto eliminado)",
        cost=Decimal(0),
        price=Decimal(0),
        stock=0,
        category="",
        active=False,
    )


def _snapshot(product: Product) -> dict:
    return {
        "name": product.name,
        "cost": product.cost,
        "price": product.price,
        "stock": product.stock,
        "category": product.category,
        "description": product.description,
    }


def _validate_product(product: Product) -> None:
    if not product.code.strip():
        raise AppError("El código del producto es obligatorio.")
    if not product.name.strip():
        raise AppError("El nombre del producto es obligatorio.")
    if product.cost < 0 or product.price < 0:
        raise AppError("Costo y precio no pueden ser negativos.")
    if product.stock < 0:
        raise AppError("Las existencias no pueden ser negativas.")


def _escape_like(text: str) -> str:
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


def _first_line(exc: BaseException) -> str:
    text = str(exc).strip()
    return text.splitlines()[0] if text else exc.__class__.__name__
