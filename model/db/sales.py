"""Ventas: recibos, pagos, anulaciones, devoluciones y ventas en espera."""

from __future__ import annotations

import logging
from datetime import date
from decimal import Decimal

from model.db.mappers import missing_product, product_from
from model.errors import AppError, InsufficientStockError
from model.pending_sale import PendingSale
from model.receipt import STATUS_COMPLETED, STATUS_VOIDED, Payment, Receipt
from model.sale_return import ReturnItem, SaleReturn
from model.sold_product import SoldProduct
from model.stock_movement import KIND_RETURN, KIND_SALE, KIND_VOID

logger = logging.getLogger(__name__)

ZERO = Decimal(0)


class SalesMixin:
    # ------------------------------------------------------------------ recibos
    def add_receipt(self, receipt: Receipt) -> int:
        """Guarda el recibo, sus líneas y pagos, y descuenta existencias, todo o nada."""
        if not receipt.sold_products:
            raise AppError("La venta no tiene productos.")
        if not receipt.payments:
            raise AppError("La venta no tiene pagos.")
        with self._transaction() as cur:
            cur.execute(
                """
                INSERT INTO receipts
                    (total, date, time, payment_method, cashier, status, discount_total, shift_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING idreceipt
                """,
                (
                    receipt.total,
                    receipt.date,
                    receipt.time,
                    receipt.payment_method,
                    receipt.cashier or self.current_user,
                    STATUS_COMPLETED,
                    receipt.discount_total,
                    receipt.shift_id,
                ),
            )
            receipt_id = int(cur.fetchone()["idreceipt"])
            for sp in receipt.sold_products:
                cur.execute(
                    """
                    UPDATE products SET stock = stock - %s
                     WHERE code = %s AND active AND stock >= %s
                 RETURNING stock
                    """,
                    (sp.quantity, sp.code, sp.quantity),
                )
                row = cur.fetchone()
                if row is None:
                    current = self._fetch_product(cur, sp.code)
                    available = current.stock if current else 0
                    raise InsufficientStockError(
                        f"No hay existencias suficientes de '{sp.product.name}': "
                        f"hay {available} y la venta pide {sp.quantity}."
                    )
                cur.execute(
                    """
                    INSERT INTO sold_products (idreceipt, codep, quantity, unit_price, unit_cost, tax_rate, discount)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (receipt_id, sp.code, sp.quantity, sp.unit_price, sp.unit_cost, sp.tax_rate, sp.discount),
                )
                self._record_movement(cur, sp.code, -sp.quantity, KIND_SALE, int(row["stock"]), f"Recibo {receipt_id}")
            for payment in receipt.payments:
                cur.execute(
                    "INSERT INTO payments (idreceipt, method, amount) VALUES (%s, %s, %s)",
                    (receipt_id, payment.method, payment.amount),
                )
            self._log(
                cur,
                "sale",
                str(receipt_id),
                {
                    "recibo": receipt_id,
                    "total": receipt.total,
                    "pago": receipt.payment_method,
                    "productos": sum(sp.quantity for sp in receipt.sold_products),
                },
            )
        logger.info(
            "Venta registrada: recibo %s, %s líneas, total %s (%s)",
            receipt_id,
            len(receipt.sold_products),
            receipt.total,
            receipt.payment_method,
        )
        return receipt_id

    def get_receipt(self, receipt_id: int) -> Receipt | None:
        receipts = self._load_receipts("WHERE r.idreceipt = %s", (receipt_id,))
        return receipts[0] if receipts else None

    def get_receipts_in_range(self, start: date, end: date) -> list[Receipt]:
        """Recibos (incluidos los anulados) con sus líneas y pagos entre dos fechas inclusive."""
        return self._load_receipts("WHERE r.date BETWEEN %s AND %s", (start, end))

    def get_receipts_of_shift(self, shift_id: int) -> list[Receipt]:
        return self._load_receipts("WHERE r.shift_id = %s", (shift_id,))

    def void_receipt(self, receipt_id: int, reason: str) -> Receipt:
        """Anula una venta completa y devuelve las unidades al inventario."""
        reason = reason.strip()
        if not reason:
            raise AppError("Escriba el motivo de la anulación.")
        with self._transaction() as cur:
            cur.execute("SELECT status FROM receipts WHERE idreceipt = %s FOR UPDATE", (receipt_id,))
            row = cur.fetchone()
            if row is None:
                raise AppError(f"El recibo {receipt_id} no existe.")
            if row["status"] == STATUS_VOIDED:
                raise AppError(f"El recibo {receipt_id} ya estaba anulado.")
            cur.execute("SELECT count(*) AS n FROM sale_returns WHERE idreceipt = %s", (receipt_id,))
            if int(cur.fetchone()["n"]) > 0:
                raise AppError("Este recibo tiene devoluciones registradas; anule por devolución, no completo.")
            cur.execute("SELECT codep, quantity FROM sold_products WHERE idreceipt = %s", (receipt_id,))
            for line in cur.fetchall():
                cur.execute(
                    "UPDATE products SET stock = stock + %s WHERE code = %s RETURNING stock",
                    (line["quantity"], line["codep"]),
                )
                stock_after = int(cur.fetchone()["stock"])
                self._record_movement(
                    cur,
                    line["codep"],
                    int(line["quantity"]),
                    KIND_VOID,
                    stock_after,
                    f"Anulación recibo {receipt_id}",
                    reason,
                )
            cur.execute(
                """
                UPDATE receipts
                   SET status = %s, voided_at = now(), voided_by = %s, void_reason = %s
                 WHERE idreceipt = %s
                """,
                (STATUS_VOIDED, self.current_user, reason, receipt_id),
            )
            self._log(cur, "void_sale", str(receipt_id), {"recibo": receipt_id, "motivo": reason})
        receipt = self.get_receipt(receipt_id)
        assert receipt is not None
        return receipt

    # ------------------------------------------------------------------ devoluciones
    def add_return(self, receipt_id: int, items: list[tuple[str, int]], reason: str) -> SaleReturn:
        """Devuelve unidades de un recibo: entran al inventario y se reembolsa su valor.

        ``items`` son pares (código, cantidad). No se puede devolver más de lo vendido menos lo ya devuelto.
        """
        reason = reason.strip()
        if not reason:
            raise AppError("Escriba el motivo de la devolución.")
        wanted = {code: qty for code, qty in items if qty > 0}
        if not wanted:
            raise AppError("Indique al menos un producto con cantidad mayor que cero.")
        with self._transaction() as cur:
            cur.execute("SELECT status FROM receipts WHERE idreceipt = %s FOR UPDATE", (receipt_id,))
            row = cur.fetchone()
            if row is None:
                raise AppError(f"El recibo {receipt_id} no existe.")
            if row["status"] == STATUS_VOIDED:
                raise AppError("El recibo está anulado; no admite devoluciones.")
            cur.execute(
                """
                SELECT sp.codep, p.name, sum(sp.quantity) AS sold,
                       sum(sp.unit_price * sp.quantity - sp.discount) / sum(sp.quantity) AS unit_net,
                       COALESCE((SELECT sum(ri.quantity) FROM sale_return_items ri
                                   JOIN sale_returns sr ON sr.id = ri.return_id
                                  WHERE sr.idreceipt = sp.idreceipt AND ri.codep = sp.codep), 0) AS returned
                  FROM sold_products sp
                  JOIN products p ON p.code = sp.codep
                 WHERE sp.idreceipt = %s
                 GROUP BY sp.idreceipt, sp.codep, p.name
                """,
                (receipt_id,),
            )
            sold = {r["codep"]: r for r in cur.fetchall()}
            for code, qty in wanted.items():
                if code not in sold:
                    raise AppError(f"El producto {code} no está en el recibo {receipt_id}.")
                available = int(sold[code]["sold"]) - int(sold[code]["returned"])
                if qty > available:
                    raise AppError(f"De '{sold[code]['name']}' solo se pueden devolver {available} unidades.")
            cur.execute(
                'INSERT INTO sale_returns (idreceipt, "user", reason) VALUES (%s, %s, %s) RETURNING id, created_at',
                (receipt_id, self.current_user, reason),
            )
            created = cur.fetchone()
            return_id = int(created["id"])
            result = SaleReturn(
                id=return_id,
                receipt_id=receipt_id,
                reason=reason,
                user=self.current_user,
                created_at=created["created_at"],
            )
            for code, qty in wanted.items():
                unit_price = Decimal(sold[code]["unit_net"]).quantize(Decimal("0.01"))
                cur.execute(
                    "INSERT INTO sale_return_items (return_id, codep, quantity, unit_price) VALUES (%s, %s, %s, %s)",
                    (return_id, code, qty, unit_price),
                )
                cur.execute("UPDATE products SET stock = stock + %s WHERE code = %s RETURNING stock", (qty, code))
                stock_after = int(cur.fetchone()["stock"])
                self._record_movement(
                    cur, code, qty, KIND_RETURN, stock_after, f"Devolución recibo {receipt_id}", reason
                )
                result.items.append(ReturnItem(code=code, name=sold[code]["name"], quantity=qty, unit_price=unit_price))
            cur.execute("UPDATE sale_returns SET total = %s WHERE id = %s", (result.total, return_id))
            self._log(
                cur,
                "sale_return",
                str(receipt_id),
                {"recibo": receipt_id, "devolucion": return_id, "total": result.total, "motivo": reason},
            )
        return result

    def returned_quantities(self, receipt_id: int) -> dict[str, int]:
        """Unidades ya devueltas por producto en un recibo."""
        with self._transaction() as cur:
            cur.execute(
                """
                SELECT ri.codep, sum(ri.quantity) AS quantity
                  FROM sale_return_items ri JOIN sale_returns sr ON sr.id = ri.return_id
                 WHERE sr.idreceipt = %s
                 GROUP BY ri.codep
                """,
                (receipt_id,),
            )
            return {row["codep"]: int(row["quantity"]) for row in cur.fetchall()}

    def get_returns_in_range(self, start: date, end: date) -> list[SaleReturn]:
        with self._transaction() as cur:
            cur.execute(
                """
                SELECT sr.id, sr.idreceipt, sr.created_at, sr."user", sr.reason,
                       ri.codep, p.name, ri.quantity, ri.unit_price
                  FROM sale_returns sr
                  LEFT JOIN sale_return_items ri ON ri.return_id = sr.id
                  LEFT JOIN products p ON p.code = ri.codep
                 WHERE sr.created_at >= %s AND sr.created_at < %s + INTERVAL '1 day'
                 ORDER BY sr.created_at, sr.id, ri.id
                """,
                (start, end),
            )
            rows = cur.fetchall()
        returns: dict[int, SaleReturn] = {}
        for row in rows:
            entry = returns.get(row["id"])
            if entry is None:
                entry = SaleReturn(
                    id=int(row["id"]),
                    receipt_id=int(row["idreceipt"]),
                    reason=row["reason"] or "",
                    user=row["user"],
                    created_at=row["created_at"],
                )
                returns[entry.id] = entry
            if row["codep"] is not None:
                entry.items.append(
                    ReturnItem(
                        row["codep"], row["name"] or row["codep"], int(row["quantity"]), Decimal(row["unit_price"])
                    )
                )
        return list(returns.values())

    # ------------------------------------------------------------------ ventas en espera
    def load_pending_sales(self) -> list[PendingSale]:
        """Ventas abiertas guardadas. Las líneas de productos ya inactivos se descartan."""
        with self._transaction() as cur:
            cur.execute(
                """
                SELECT ps.id, ps.number, ps.received_text, ps.wants_receipt, ps.discount_total,
                       i.quantity, i.codep, i.discount AS line_discount,
                       p.code, p.name, p.cost, p.price, p.stock, p.description, p.active, p.min_stock, p.tax_rate,
                       c.category_name AS category
                  FROM pending_sales ps
                  LEFT JOIN pending_sale_items i ON i.pending_sale_id = ps.id
                  LEFT JOIN products p ON p.code = i.codep AND p.active
                  LEFT JOIN categories c ON c.idcategory = p.category
                 ORDER BY ps.number, i.position, i.id
                """
            )
            rows = cur.fetchall()
        sales: dict[int, PendingSale] = {}
        for row in rows:
            sale = sales.get(row["id"])
            if sale is None:
                sale = PendingSale(
                    number=int(row["number"]),
                    received_text=row["received_text"] or "",
                    wants_receipt=bool(row["wants_receipt"]),
                    discount_total=Decimal(row["discount_total"] or 0),
                    db_id=int(row["id"]),
                )
                sales[sale.db_id] = sale
            if row["quantity"] is None:
                continue
            if row["code"] is None:
                logger.warning(
                    "Venta en espera %s: el producto %s ya no está activo; se omite", sale.number, row["codep"]
                )
                continue
            sale.lines.append(
                SoldProduct(
                    product=product_from(row),
                    quantity=int(row["quantity"]),
                    discount=Decimal(row["line_discount"] or 0),
                )
            )
        return list(sales.values())

    def save_pending_sale(self, sale: PendingSale) -> int:
        """Crea o actualiza la venta en espera con sus líneas y devuelve su id."""
        with self._transaction() as cur:
            if sale.db_id is None:
                cur.execute(
                    "INSERT INTO pending_sales (number, received_text, wants_receipt, discount_total)"
                    " VALUES (%s, %s, %s, %s) RETURNING id",
                    (sale.number, sale.received_text, sale.wants_receipt, sale.discount_total),
                )
                sale_id = int(cur.fetchone()["id"])
            else:
                sale_id = sale.db_id
                cur.execute(
                    "UPDATE pending_sales SET received_text = %s, wants_receipt = %s, discount_total = %s,"
                    " updated_at = now() WHERE id = %s",
                    (sale.received_text, sale.wants_receipt, sale.discount_total, sale_id),
                )
                cur.execute("DELETE FROM pending_sale_items WHERE pending_sale_id = %s", (sale_id,))
            for position, sp in enumerate(sale.lines):
                cur.execute(
                    "INSERT INTO pending_sale_items (pending_sale_id, codep, quantity, position, discount)"
                    " VALUES (%s, %s, %s, %s, %s)",
                    (sale_id, sp.code, sp.quantity, position, sp.discount),
                )
        return sale_id

    def delete_pending_sale(self, sale_id: int) -> None:
        with self._transaction() as cur:
            cur.execute("DELETE FROM pending_sales WHERE id = %s", (sale_id,))

    # ------------------------------------------------------------------ internos
    def _load_receipts(self, where: str, params: tuple) -> list[Receipt]:
        with self._transaction() as cur:
            cur.execute(
                f"""
                SELECT r.idreceipt, r.total, r.date, r.time, r.payment_method, r.cashier, r.status,
                       r.discount_total, r.shift_id, r.void_reason, r.voided_by,
                       sp.codep AS code, sp.quantity, sp.unit_price, sp.unit_cost, sp.tax_rate AS line_tax,
                       sp.discount AS line_discount,
                       p.name, p.cost, p.price, p.stock, p.description, p.active, p.min_stock, p.tax_rate,
                       c.category_name AS category
                  FROM receipts r
                  LEFT JOIN sold_products sp ON sp.idreceipt = r.idreceipt
                  LEFT JOIN products p ON p.code = sp.codep
                  LEFT JOIN categories c ON c.idcategory = p.category
                  {where}
                 ORDER BY r.date, r.time, r.idreceipt, sp.idsale
                """,
                params,
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
                        cashier=row["cashier"],
                        status=row["status"],
                        discount_total=Decimal(row["discount_total"] or 0),
                        shift_id=row["shift_id"],
                        void_reason=row["void_reason"],
                        voided_by=row["voided_by"],
                    )
                    receipts[receipt_id] = receipt
                if row["code"] is None:
                    continue
                receipt.sold_products.append(
                    SoldProduct(
                        product=product_from(row) if row["name"] is not None else missing_product(row["code"]),
                        quantity=int(row["quantity"]),
                        unit_price=Decimal(row["unit_price"]),
                        unit_cost=Decimal(row["unit_cost"]),
                        tax_rate=Decimal(row["line_tax"] or 0),
                        discount=Decimal(row["line_discount"] or 0),
                    )
                )
            if not receipts:
                return []
            ids = list(receipts)
            cur.execute("SELECT idreceipt, method, amount FROM payments WHERE idreceipt = ANY(%s) ORDER BY id", (ids,))
            for row in cur.fetchall():
                receipts[int(row["idreceipt"])].payments.append(Payment(row["method"], Decimal(row["amount"])))
            cur.execute(
                "SELECT idreceipt, sum(total) AS returned FROM sale_returns"
                " WHERE idreceipt = ANY(%s) GROUP BY idreceipt",
                (ids,),
            )
            for row in cur.fetchall():
                receipts[int(row["idreceipt"])].returned_total = Decimal(row["returned"])
        return list(receipts.values())
