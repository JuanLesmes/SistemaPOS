-- 002: integridad de datos.
-- Corrige los problemas encontrados en la revisión del 1 de septiembre de 2026:
--   * dinero en REAL (flotante) -> NUMERIC(14,2)
--   * borrado en cascada que destruía ventas históricas -> RESTRICT
--   * ventas sin precio propio -> unit_price y unit_cost en cada línea
--   * productos borrados físicamente -> borrado lógico con "active"
--   * existencias negativas -> CHECK (stock >= 0)
-- Los constraints se agregan con NOT VALID: protegen todo lo nuevo sin fallar
-- por datos viejos que no cumplan.

-- ---------------------------------------------------------------- dinero
ALTER TABLE products
    ALTER COLUMN cost  TYPE NUMERIC(14,2) USING round(COALESCE(cost, 0)::numeric, 2),
    ALTER COLUMN price TYPE NUMERIC(14,2) USING round(COALESCE(price, 0)::numeric, 2);

ALTER TABLE receipts
    ALTER COLUMN total TYPE NUMERIC(14,2) USING round(COALESCE(total, 0)::numeric, 2);

-- ---------------------------------------------------------------- productos
UPDATE products SET name = code WHERE name IS NULL OR btrim(name) = '';
UPDATE products SET stock = 0 WHERE stock IS NULL;
UPDATE products SET description = '' WHERE description IS NULL;

ALTER TABLE products
    ALTER COLUMN name  SET NOT NULL,
    ALTER COLUMN cost  SET NOT NULL,
    ALTER COLUMN cost  SET DEFAULT 0,
    ALTER COLUMN price SET NOT NULL,
    ALTER COLUMN price SET DEFAULT 0,
    ALTER COLUMN stock SET NOT NULL,
    ALTER COLUMN stock SET DEFAULT 0,
    ALTER COLUMN description SET NOT NULL,
    ALTER COLUMN description SET DEFAULT '',
    ADD COLUMN IF NOT EXISTS active BOOLEAN NOT NULL DEFAULT TRUE;

-- Productos que quedaron sin categoría eran invisibles para la aplicación.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM products WHERE category IS NULL) THEN
        INSERT INTO categories (category_name) VALUES ('Sin categoría')
            ON CONFLICT (category_name) DO NOTHING;
        UPDATE products
           SET category = (SELECT idcategory FROM categories WHERE category_name = 'Sin categoría')
         WHERE category IS NULL;
    END IF;
END $$;

ALTER TABLE products ALTER COLUMN category SET NOT NULL;

-- ---------------------------------------------------------------- categorías
UPDATE categories SET category_name = 'Sin nombre ' || idcategory
 WHERE category_name IS NULL OR btrim(category_name) = '';
ALTER TABLE categories ALTER COLUMN category_name SET NOT NULL;

-- ---------------------------------------------------------------- recibos
UPDATE receipts SET total = 0 WHERE total IS NULL;
UPDATE receipts SET date = CURRENT_DATE WHERE date IS NULL;
UPDATE receipts SET time = CURRENT_TIME WHERE time IS NULL;
UPDATE receipts SET payment_method = 'Efectivo' WHERE payment_method IS NULL OR btrim(payment_method) = '';

ALTER TABLE receipts
    ALTER COLUMN total SET NOT NULL,
    ALTER COLUMN date  SET NOT NULL,
    ALTER COLUMN time  SET NOT NULL,
    ALTER COLUMN payment_method SET NOT NULL;

-- ---------------------------------------------------------------- líneas de venta
ALTER TABLE sold_products
    ADD COLUMN IF NOT EXISTS unit_price NUMERIC(14,2),
    ADD COLUMN IF NOT EXISTS unit_cost  NUMERIC(14,2);

-- Para las ventas antiguas el mejor dato disponible es el precio actual.
UPDATE sold_products sp
   SET unit_price = p.price,
       unit_cost  = p.cost
  FROM products p
 WHERE sp.codep = p.code
   AND sp.unit_price IS NULL;

UPDATE sold_products SET unit_price = 0 WHERE unit_price IS NULL;
UPDATE sold_products SET unit_cost  = 0 WHERE unit_cost  IS NULL;
UPDATE sold_products SET quantity   = 1 WHERE quantity   IS NULL;

ALTER TABLE sold_products
    ALTER COLUMN unit_price SET NOT NULL,
    ALTER COLUMN unit_cost  SET NOT NULL,
    ALTER COLUMN quantity   SET NOT NULL;

-- ---------------------------------------------------------------- claves foráneas
-- Se quitan las que existan (con cualquier nombre) y se recrean sin cascada.
DO $$
DECLARE
    fk RECORD;
BEGIN
    FOR fk IN
        SELECT conname, conrelid::regclass AS tabla
          FROM pg_constraint
         WHERE contype = 'f'
           AND conrelid IN ('products'::regclass, 'sold_products'::regclass)
    LOOP
        EXECUTE format('ALTER TABLE %s DROP CONSTRAINT %I', fk.tabla, fk.conname);
    END LOOP;
END $$;

ALTER TABLE products
    ADD CONSTRAINT products_category_fkey
        FOREIGN KEY (category) REFERENCES categories (idcategory) ON DELETE RESTRICT NOT VALID;

ALTER TABLE sold_products
    ADD CONSTRAINT sold_products_idreceipt_fkey
        FOREIGN KEY (idreceipt) REFERENCES receipts (idreceipt) ON DELETE RESTRICT NOT VALID,
    ADD CONSTRAINT sold_products_codep_fkey
        FOREIGN KEY (codep) REFERENCES products (code) ON DELETE RESTRICT NOT VALID;

-- ---------------------------------------------------------------- existencias
ALTER TABLE products
    ADD CONSTRAINT products_stock_no_negativo CHECK (stock >= 0) NOT VALID;

-- ---------------------------------------------------------------- índices
CREATE INDEX IF NOT EXISTS idx_receipts_date            ON receipts (date);
CREATE INDEX IF NOT EXISTS idx_sold_products_idreceipt  ON sold_products (idreceipt);
CREATE INDEX IF NOT EXISTS idx_sold_products_codep      ON sold_products (codep);
CREATE INDEX IF NOT EXISTS idx_products_name_lower      ON products (lower(name));
CREATE INDEX IF NOT EXISTS idx_products_active          ON products (active);
CREATE INDEX IF NOT EXISTS idx_audit_logs_timestamp     ON audit_logs (timestamp);
