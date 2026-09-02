-- 005: impuestos, stock mínimo, pagos por recibo, movimientos de inventario (kárdex),
-- anulaciones, devoluciones, proveedores, compras y turnos de caja.

-- ---------------------------------------------------------------- productos
ALTER TABLE products
    ADD COLUMN IF NOT EXISTS min_stock INTEGER NOT NULL DEFAULT 3,
    ADD COLUMN IF NOT EXISTS tax_rate  NUMERIC(5,2) NOT NULL DEFAULT 0;

ALTER TABLE sold_products
    ADD COLUMN IF NOT EXISTS tax_rate NUMERIC(5,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS discount NUMERIC(14,2) NOT NULL DEFAULT 0;

-- ---------------------------------------------------------------- turnos de caja
CREATE TABLE IF NOT EXISTS shifts (
    id            SERIAL PRIMARY KEY,
    opened_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    opened_by     TEXT,
    opening_cash  NUMERIC(14,2) NOT NULL DEFAULT 0,
    closed_at     TIMESTAMPTZ,
    closed_by     TEXT,
    expected_cash NUMERIC(14,2),
    counted_cash  NUMERIC(14,2),
    difference    NUMERIC(14,2),
    notes         TEXT NOT NULL DEFAULT ''
);

-- ---------------------------------------------------------------- recibos
ALTER TABLE receipts
    ADD COLUMN IF NOT EXISTS status         TEXT NOT NULL DEFAULT 'completed',
    ADD COLUMN IF NOT EXISTS discount_total NUMERIC(14,2) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS shift_id       INTEGER REFERENCES shifts (id) ON DELETE RESTRICT,
    ADD COLUMN IF NOT EXISTS voided_at      TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS voided_by      TEXT,
    ADD COLUMN IF NOT EXISTS void_reason    TEXT;

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conname = 'receipts_status_check') THEN
        ALTER TABLE receipts ADD CONSTRAINT receipts_status_check CHECK (status IN ('completed', 'voided'));
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_receipts_shift ON receipts (shift_id);

-- ---------------------------------------------------------------- pagos (permite pago mixto)
CREATE TABLE IF NOT EXISTS payments (
    id        SERIAL PRIMARY KEY,
    idreceipt INTEGER NOT NULL REFERENCES receipts (idreceipt) ON DELETE RESTRICT,
    method    TEXT NOT NULL,
    amount    NUMERIC(14,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_payments_receipt ON payments (idreceipt);

-- Un pago por recibo para las ventas anteriores a esta versión.
INSERT INTO payments (idreceipt, method, amount)
SELECT r.idreceipt, r.payment_method, r.total
  FROM receipts r
 WHERE NOT EXISTS (SELECT 1 FROM payments p WHERE p.idreceipt = r.idreceipt);

-- ---------------------------------------------------------------- kárdex
CREATE TABLE IF NOT EXISTS stock_movements (
    id          SERIAL PRIMARY KEY,
    codep       TEXT NOT NULL REFERENCES products (code) ON DELETE RESTRICT,
    kind        TEXT NOT NULL CHECK (kind IN ('sale', 'void', 'return', 'purchase', 'adjustment', 'initial')),
    quantity    INTEGER NOT NULL,
    stock_after INTEGER NOT NULL,
    reference   TEXT NOT NULL DEFAULT '',
    reason      TEXT NOT NULL DEFAULT '',
    "user"      TEXT,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_stock_movements_codep ON stock_movements (codep, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_stock_movements_date ON stock_movements (created_at DESC);

-- ---------------------------------------------------------------- devoluciones
CREATE TABLE IF NOT EXISTS sale_returns (
    id         SERIAL PRIMARY KEY,
    idreceipt  INTEGER NOT NULL REFERENCES receipts (idreceipt) ON DELETE RESTRICT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    "user"     TEXT,
    reason     TEXT NOT NULL DEFAULT '',
    total      NUMERIC(14,2) NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS sale_return_items (
    id         SERIAL PRIMARY KEY,
    return_id  INTEGER NOT NULL REFERENCES sale_returns (id) ON DELETE CASCADE,
    codep      TEXT NOT NULL REFERENCES products (code) ON DELETE RESTRICT,
    quantity   INTEGER NOT NULL CHECK (quantity > 0),
    unit_price NUMERIC(14,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_sale_returns_receipt ON sale_returns (idreceipt);

-- ---------------------------------------------------------------- proveedores y compras
CREATE TABLE IF NOT EXISTS suppliers (
    id      SERIAL PRIMARY KEY,
    name    TEXT NOT NULL UNIQUE,
    nit     TEXT NOT NULL DEFAULT '',
    phone   TEXT NOT NULL DEFAULT '',
    email   TEXT NOT NULL DEFAULT '',
    address TEXT NOT NULL DEFAULT '',
    active  BOOLEAN NOT NULL DEFAULT TRUE
);
CREATE TABLE IF NOT EXISTS purchases (
    id             SERIAL PRIMARY KEY,
    supplier_id    INTEGER REFERENCES suppliers (id) ON DELETE RESTRICT,
    invoice_number TEXT NOT NULL DEFAULT '',
    purchased_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    "user"         TEXT,
    total          NUMERIC(14,2) NOT NULL DEFAULT 0,
    notes          TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS purchase_items (
    id          SERIAL PRIMARY KEY,
    purchase_id INTEGER NOT NULL REFERENCES purchases (id) ON DELETE CASCADE,
    codep       TEXT NOT NULL REFERENCES products (code) ON DELETE RESTRICT,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_cost   NUMERIC(14,2) NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_purchases_date ON purchases (purchased_at DESC);

-- ---------------------------------------------------------------- ventas en espera con descuentos
ALTER TABLE pending_sales ADD COLUMN IF NOT EXISTS discount_total NUMERIC(14,2) NOT NULL DEFAULT 0;
ALTER TABLE pending_sale_items ADD COLUMN IF NOT EXISTS discount NUMERIC(14,2) NOT NULL DEFAULT 0;
