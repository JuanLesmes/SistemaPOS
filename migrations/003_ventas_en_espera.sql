-- 003: ventas en espera.
-- Las ventas abiertas en la caja se guardan para que un cierre o un corte de
-- luz no las pierda. Al cobrar o cancelar la venta se borra de aquí.
-- El CASCADE es deliberado: las líneas pertenecen a la venta en espera y no
-- tienen valor por sí solas (no son historial).

CREATE TABLE IF NOT EXISTS pending_sales (
    id            SERIAL PRIMARY KEY,
    number        INTEGER NOT NULL,
    received_text TEXT NOT NULL DEFAULT '',
    wants_receipt BOOLEAN NOT NULL DEFAULT FALSE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS pending_sale_items (
    id              SERIAL PRIMARY KEY,
    pending_sale_id INTEGER NOT NULL REFERENCES pending_sales (id) ON DELETE CASCADE,
    codep           TEXT NOT NULL REFERENCES products (code) ON DELETE RESTRICT,
    quantity        INTEGER NOT NULL CHECK (quantity > 0),
    position        INTEGER NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_pending_sale_items_sale ON pending_sale_items (pending_sale_id);
