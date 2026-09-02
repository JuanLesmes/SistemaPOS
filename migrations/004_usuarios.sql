-- 004: usuarios con roles y cajero en cada recibo.

CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    username      TEXT NOT NULL UNIQUE,
    full_name     TEXT NOT NULL DEFAULT '',
    password_hash TEXT NOT NULL,
    role          TEXT NOT NULL CHECK (role IN ('admin', 'supervisor', 'cajero')),
    active        BOOLEAN NOT NULL DEFAULT TRUE,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_login_at TIMESTAMPTZ
);

-- Quién atendió cada venta (nombre de usuario). Las ventas anteriores quedan sin dato.
ALTER TABLE receipts ADD COLUMN IF NOT EXISTS cashier TEXT;
CREATE INDEX IF NOT EXISTS idx_receipts_cashier ON receipts (cashier);
