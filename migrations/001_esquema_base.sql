-- 001: esquema base.
-- Reproduce exactamente las tablas que creaba la aplicación original, para que
-- una base nueva y una base existente queden en el mismo punto de partida.
-- Las correcciones de integridad vienen en la migración 002.

CREATE TABLE IF NOT EXISTS categories (
    idcategory    SERIAL PRIMARY KEY,
    category_name TEXT UNIQUE
);

CREATE TABLE IF NOT EXISTS products (
    code        TEXT PRIMARY KEY,
    name        TEXT,
    cost        REAL,
    price       REAL,
    stock       INTEGER,
    category    INTEGER REFERENCES categories (idcategory) ON DELETE CASCADE,
    description TEXT
);

CREATE TABLE IF NOT EXISTS receipts (
    idreceipt      SERIAL PRIMARY KEY,
    total          REAL,
    date           DATE,
    time           TIME,
    payment_method TEXT
);

CREATE TABLE IF NOT EXISTS sold_products (
    idsale    SERIAL PRIMARY KEY,
    idreceipt INTEGER REFERENCES receipts (idreceipt) ON DELETE CASCADE,
    codep     TEXT REFERENCES products (code) ON DELETE CASCADE,
    quantity  INTEGER
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id        SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT now(),
    action    VARCHAR(50) NOT NULL,
    code      TEXT,
    details   TEXT,
    "user"    TEXT
);
