"""Proveedores y compras. Una compra entra mercancía y recalcula el costo promedio."""

from __future__ import annotations

import datetime as dt
from decimal import ROUND_HALF_UP, Decimal

import psycopg2
import psycopg2.errors

from model.errors import AppError, ProductNotFoundError
from model.purchase import Purchase, PurchaseItem
from model.stock_movement import KIND_PURCHASE
from model.supplier import Supplier

CENTS = Decimal("0.01")


class PurchasesMixin:
    # ------------------------------------------------------------------ proveedores
    def list_suppliers(self, include_inactive: bool = False) -> list[Supplier]:
        sql = "SELECT id, name, nit, phone, email, address, active FROM suppliers"
        if not include_inactive:
            sql += " WHERE active"
        sql += " ORDER BY lower(name)"
        with self._transaction() as cur:
            cur.execute(sql)
            return [_supplier_from(row) for row in cur.fetchall()]

    def save_supplier(self, supplier: Supplier) -> Supplier:
        """Crea el proveedor si no tiene id, o actualiza sus datos si ya existe."""
        name = supplier.name.strip()
        if not name:
            raise AppError("El nombre del proveedor es obligatorio.")
        values = (name, supplier.nit.strip(), supplier.phone.strip(), supplier.email.strip(), supplier.address.strip())
        with self._transaction() as cur:
            try:
                if supplier.id is None:
                    cur.execute(
                        """
                        INSERT INTO suppliers (name, nit, phone, email, address)
                        VALUES (%s, %s, %s, %s, %s)
                        RETURNING id, name, nit, phone, email, address, active
                        """,
                        values,
                    )
                    saved = _supplier_from(cur.fetchone())
                    self._log(cur, "add_supplier", details={"after": {"name": name, "nit": supplier.nit}})
                else:
                    cur.execute(
                        """
                        UPDATE suppliers
                           SET name = %s, nit = %s, phone = %s, email = %s, address = %s, active = %s
                         WHERE id = %s
                     RETURNING id, name, nit, phone, email, address, active
                        """,
                        (*values, supplier.active, supplier.id),
                    )
                    row = cur.fetchone()
                    if row is None:
                        raise AppError("El proveedor ya no existe.")
                    saved = _supplier_from(row)
                    self._log(cur, "modify_supplier", details={"after": {"name": name, "active": supplier.active}})
            except psycopg2.errors.UniqueViolation as exc:
                raise AppError(f"Ya existe un proveedor llamado '{name}'.") from exc
        return saved

    # ------------------------------------------------------------------ compras
    def add_purchase(self, purchase: Purchase) -> int:
        """Registra la compra, suma existencias y actualiza el costo promedio ponderado de cada producto."""
        if not purchase.items:
            raise AppError("La compra no tiene productos.")
        for item in purchase.items:
            if item.quantity <= 0 or item.unit_cost < 0:
                raise AppError(f"Cantidad o costo inválidos para {item.name}.")
        with self._transaction() as cur:
            cur.execute(
                """
                INSERT INTO purchases (supplier_id, invoice_number, "user", total, notes)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING id
                """,
                (
                    purchase.supplier_id,
                    purchase.invoice_number.strip(),
                    self.current_user,
                    purchase.total,
                    purchase.notes,
                ),
            )
            purchase_id = int(cur.fetchone()["id"])
            for item in purchase.items:
                previous = self._fetch_product(cur, item.code)
                if previous is None:
                    raise ProductNotFoundError(f"No existe un producto activo con el código {item.code}.")
                new_stock = previous.stock + item.quantity
                if previous.stock > 0:
                    new_cost = (previous.cost * previous.stock + item.unit_cost * item.quantity) / new_stock
                else:
                    new_cost = item.unit_cost
                new_cost = new_cost.quantize(CENTS, rounding=ROUND_HALF_UP)
                cur.execute(
                    "UPDATE products SET stock = %s, cost = %s WHERE code = %s", (new_stock, new_cost, item.code)
                )
                cur.execute(
                    "INSERT INTO purchase_items (purchase_id, codep, quantity, unit_cost) VALUES (%s, %s, %s, %s)",
                    (purchase_id, item.code, item.quantity, item.unit_cost),
                )
                self._record_movement(
                    cur,
                    item.code,
                    item.quantity,
                    KIND_PURCHASE,
                    new_stock,
                    f"Compra {purchase_id}",
                    purchase.supplier_name,
                )
            self._log(
                cur,
                "purchase",
                str(purchase_id),
                {
                    "compra": purchase_id,
                    "proveedor": purchase.supplier_name,
                    "factura": purchase.invoice_number,
                    "total": purchase.total,
                    "unidades": purchase.units,
                },
            )
        return purchase_id

    def list_purchases(self, start: dt.date, end: dt.date) -> list[Purchase]:
        with self._transaction() as cur:
            cur.execute(
                """
                SELECT pu.id, pu.supplier_id, COALESCE(s.name, '') AS supplier_name, pu.invoice_number,
                       pu.purchased_at, pu."user", pu.notes,
                       pi.codep, p.name, pi.quantity, pi.unit_cost
                  FROM purchases pu
                  LEFT JOIN suppliers s ON s.id = pu.supplier_id
                  LEFT JOIN purchase_items pi ON pi.purchase_id = pu.id
                  LEFT JOIN products p ON p.code = pi.codep
                 WHERE pu.purchased_at >= %s AND pu.purchased_at < %s + INTERVAL '1 day'
                 ORDER BY pu.purchased_at DESC, pu.id DESC, pi.id
                """,
                (start, end),
            )
            rows = cur.fetchall()
        purchases: dict[int, Purchase] = {}
        for row in rows:
            entry = purchases.get(row["id"])
            if entry is None:
                entry = Purchase(
                    id=int(row["id"]),
                    supplier_id=row["supplier_id"],
                    supplier_name=row["supplier_name"],
                    invoice_number=row["invoice_number"] or "",
                    purchased_at=row["purchased_at"],
                    user=row["user"],
                    notes=row["notes"] or "",
                )
                purchases[entry.id] = entry
            if row["codep"] is not None:
                entry.items.append(
                    PurchaseItem(
                        row["codep"], row["name"] or row["codep"], int(row["quantity"]), Decimal(row["unit_cost"])
                    )
                )
        return list(purchases.values())


def _supplier_from(row) -> Supplier:
    return Supplier(
        id=int(row["id"]),
        name=row["name"],
        nit=row["nit"] or "",
        phone=row["phone"] or "",
        email=row["email"] or "",
        address=row["address"] or "",
        active=bool(row["active"]),
    )
