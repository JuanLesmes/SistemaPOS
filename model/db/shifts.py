"""Turnos de caja: apertura con base, resumen en curso y cierre con arqueo."""

from __future__ import annotations

from decimal import Decimal

from model.errors import AppError
from model.receipt import PAYMENT_CARD, PAYMENT_CASH, PAYMENT_TRANSFER, STATUS_COMPLETED
from model.shift import Shift, ShiftSummary

ZERO = Decimal(0)
SHIFTS_LIMIT = 100


class ShiftsMixin:
    def get_open_shift(self) -> Shift | None:
        with self._transaction() as cur:
            cur.execute(f"{_SHIFT_SELECT} WHERE closed_at IS NULL ORDER BY opened_at DESC LIMIT 1")
            row = cur.fetchone()
            return _shift_from(row) if row else None

    def open_shift(self, opening_cash: Decimal) -> Shift:
        if opening_cash < 0:
            raise AppError("La base inicial no puede ser negativa.")
        with self._transaction() as cur:
            cur.execute("SELECT id FROM shifts WHERE closed_at IS NULL LIMIT 1")
            if cur.fetchone() is not None:
                raise AppError("Ya hay un turno abierto. Ciérrelo antes de abrir otro.")
            cur.execute(
                f"INSERT INTO shifts (opened_by, opening_cash) VALUES (%s, %s) RETURNING {_SHIFT_COLUMNS}",
                (self.current_user, opening_cash),
            )
            shift = _shift_from(cur.fetchone())
            self._log(cur, "shift_open", str(shift.id), {"turno": shift.id, "base": opening_cash})
        return shift

    def shift_summary(self, shift_id: int) -> ShiftSummary:
        with self._transaction() as cur:
            cur.execute(f"{_SHIFT_SELECT} WHERE id = %s", (shift_id,))
            row = cur.fetchone()
            if row is None:
                raise AppError(f"El turno {shift_id} no existe.")
            shift = _shift_from(row)
            cur.execute(
                """
                SELECT p.method, COALESCE(sum(p.amount), 0) AS amount
                  FROM receipts r
                  JOIN payments p ON p.idreceipt = r.idreceipt
                 WHERE r.shift_id = %s AND r.status = %s
                 GROUP BY p.method
                """,
                (shift_id, STATUS_COMPLETED),
            )
            by_method = {r["method"]: Decimal(r["amount"]) for r in cur.fetchall()}
            cur.execute(
                "SELECT count(*) FILTER (WHERE status = %s) AS completed,"
                "       count(*) FILTER (WHERE status <> %s) AS voided"
                "  FROM receipts WHERE shift_id = %s",
                (STATUS_COMPLETED, STATUS_COMPLETED, shift_id),
            )
            counts = cur.fetchone()
            cur.execute(
                """
                SELECT COALESCE(sum(sr.total), 0) AS returned
                  FROM sale_returns sr JOIN receipts r ON r.idreceipt = sr.idreceipt
                 WHERE r.shift_id = %s
                """,
                (shift_id,),
            )
            returned = Decimal(cur.fetchone()["returned"])
        return ShiftSummary(
            shift=shift,
            receipt_count=int(counts["completed"]),
            cash_sales=by_method.get(PAYMENT_CASH, ZERO),
            card_sales=by_method.get(PAYMENT_CARD, ZERO),
            transfer_sales=by_method.get(PAYMENT_TRANSFER, ZERO),
            returns=returned,
            voided_count=int(counts["voided"]),
        )

    def close_shift(self, shift_id: int, counted_cash: Decimal, notes: str = "") -> Shift:
        if counted_cash < 0:
            raise AppError("El efectivo contado no puede ser negativo.")
        summary = self.shift_summary(shift_id)
        if not summary.shift.is_open:
            raise AppError("Ese turno ya estaba cerrado.")
        expected = summary.expected_cash
        with self._transaction() as cur:
            cur.execute(
                f"""
                UPDATE shifts
                   SET closed_at = now(), closed_by = %s, expected_cash = %s, counted_cash = %s,
                       difference = %s, notes = %s
                 WHERE id = %s AND closed_at IS NULL
             RETURNING {_SHIFT_COLUMNS}
                """,
                (self.current_user, expected, counted_cash, counted_cash - expected, notes.strip(), shift_id),
            )
            row = cur.fetchone()
            if row is None:
                raise AppError("Ese turno ya estaba cerrado.")
            shift = _shift_from(row)
            self._log(
                cur,
                "shift_close",
                str(shift_id),
                {
                    "turno": shift_id,
                    "esperado": expected,
                    "contado": counted_cash,
                    "diferencia": counted_cash - expected,
                },
            )
        return shift

    def list_shifts(self, limit: int = SHIFTS_LIMIT) -> list[Shift]:
        with self._transaction() as cur:
            cur.execute(f"{_SHIFT_SELECT} ORDER BY opened_at DESC LIMIT %s", (limit,))
            return [_shift_from(row) for row in cur.fetchall()]


_SHIFT_COLUMNS = (
    "id, opened_at, opened_by, opening_cash, closed_at, closed_by, expected_cash, counted_cash, difference, notes"
)
_SHIFT_SELECT = f"SELECT {_SHIFT_COLUMNS} FROM shifts"


def _shift_from(row) -> Shift:
    return Shift(
        id=int(row["id"]),
        opened_at=row["opened_at"],
        opened_by=row["opened_by"],
        opening_cash=Decimal(row["opening_cash"]),
        closed_at=row["closed_at"],
        closed_by=row["closed_by"],
        expected_cash=Decimal(row["expected_cash"]) if row["expected_cash"] is not None else None,
        counted_cash=Decimal(row["counted_cash"]) if row["counted_cash"] is not None else None,
        difference=Decimal(row["difference"]) if row["difference"] is not None else None,
        notes=row["notes"] or "",
    )
