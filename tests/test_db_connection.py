"""Pruebas contra un PostgreSQL real.

Se saltan a menos que existan TEST_DB_HOST, TEST_DB_PORT, TEST_DB_USER y
TEST_DB_PASSWORD. Con ellas se crea una base temporal para cada prueba y se
elimina al terminar, así nunca tocan la base de la tienda.
"""

import datetime as dt
import os
import uuid
from decimal import Decimal

import pytest

psycopg2 = pytest.importorskip("psycopg2")

from model.db_connection import DBConnection  # noqa: E402
from model.errors import CategoryInUseError, DuplicateProductError, InsufficientStockError  # noqa: E402
from model.product import Product  # noqa: E402
from model.receipt import PAYMENT_CASH, Receipt  # noqa: E402
from model.sold_product import SoldProduct  # noqa: E402
from utils.config import DatabaseSettings  # noqa: E402

REQUIRED = ("TEST_DB_HOST", "TEST_DB_PORT", "TEST_DB_USER", "TEST_DB_PASSWORD")
pytestmark = pytest.mark.skipif(
    any(not os.getenv(name) for name in REQUIRED),
    reason="Defina TEST_DB_HOST, TEST_DB_PORT, TEST_DB_USER y TEST_DB_PASSWORD para probar contra PostgreSQL.",
)

LEGACY_SCHEMA = """
CREATE TABLE categories (idCategory SERIAL PRIMARY KEY, category_name TEXT UNIQUE);
CREATE TABLE products (
    code TEXT PRIMARY KEY, name TEXT, cost REAL, price REAL, stock INTEGER,
    category INTEGER REFERENCES categories(idCategory) ON DELETE CASCADE, description TEXT);
CREATE TABLE receipts (idReceipt SERIAL PRIMARY KEY, total REAL, date DATE, time TIME, payment_method TEXT);
CREATE TABLE sold_products (
    idSale SERIAL PRIMARY KEY, idReceipt INTEGER REFERENCES receipts(idReceipt) ON DELETE CASCADE,
    codeP TEXT REFERENCES products(code) ON DELETE CASCADE, quantity INTEGER);
CREATE TABLE audit_logs (
    id SERIAL PRIMARY KEY, timestamp TIMESTAMP NOT NULL DEFAULT NOW(), action VARCHAR(50) NOT NULL,
    code TEXT, details TEXT, "user" TEXT);
INSERT INTO categories (category_name) VALUES ('Bebidas');
INSERT INTO products VALUES ('111', 'Agua', 500.0, 1000.0, 3, 1, NULL);
INSERT INTO receipts (total, date, time, payment_method) VALUES (2000.0, '2026-08-01', '10:00', 'Efectivo');
INSERT INTO sold_products (idReceipt, codeP, quantity) VALUES (1, '111', 2);
"""


def _admin_connection():
    conn = psycopg2.connect(
        host=os.environ["TEST_DB_HOST"],
        port=int(os.environ["TEST_DB_PORT"]),
        dbname="postgres",
        user=os.environ["TEST_DB_USER"],
        password=os.environ["TEST_DB_PASSWORD"],
    )
    conn.autocommit = True
    return conn


@pytest.fixture
def temp_settings():
    name = f"sistemapos_test_{uuid.uuid4().hex[:8]}"
    admin = _admin_connection()
    with admin.cursor() as cur:
        cur.execute(f'CREATE DATABASE "{name}"')
    settings = DatabaseSettings(
        host=os.environ["TEST_DB_HOST"],
        port=int(os.environ["TEST_DB_PORT"]),
        name=name,
        user=os.environ["TEST_DB_USER"],
        password=os.environ["TEST_DB_PASSWORD"],
    )
    yield settings
    with admin.cursor() as cur:
        cur.execute(f'DROP DATABASE "{name}" WITH (FORCE)')
    admin.close()


@pytest.fixture
def db(temp_settings):
    connection = DBConnection(temp_settings)
    yield connection
    connection.close()


def make_product(code="A1", stock=10, category="General") -> Product:
    return Product(
        code=code, name=f"Producto {code}", cost=Decimal(600), price=Decimal(1000), stock=stock, category=category
    )


def test_migrations_run_once(temp_settings):
    DBConnection(temp_settings).close()
    second = DBConnection(temp_settings)  # no debe volver a aplicar nada ni fallar
    second.close()


def test_add_product_creates_category_and_duplicates_are_rejected(db):
    db.add_product(make_product(category="Nueva"))
    assert "Nueva" in db.get_categories()
    with pytest.raises(DuplicateProductError):
        db.add_product(make_product())


def test_sale_discounts_stock_and_keeps_price_snapshot(db):
    db.add_product(make_product(stock=5))
    product = db.get_product("A1")
    receipt = Receipt.create(PAYMENT_CASH, [SoldProduct(product, 2)])
    receipt.id = db.add_receipt(receipt)

    assert db.get_product("A1").stock == 3
    product.price = Decimal(9999)
    db.update_product(product)
    stored = db.get_receipts_in_range(receipt.date, receipt.date)
    assert stored[0].sold_products[0].unit_price == Decimal(1000)
    assert stored[0].total == Decimal(2000)


def test_best_sellers_rank_by_units_sold(db):
    db.add_product(make_product("A1", stock=10))
    db.add_product(make_product("B2", stock=10))
    db.add_product(make_product("C3", stock=10))
    a1, b2 = db.get_product("A1"), db.get_product("B2")
    db.add_receipt(Receipt.create(PAYMENT_CASH, [SoldProduct(a1, 1), SoldProduct(b2, 5)]))
    db.add_receipt(Receipt.create(PAYMENT_CASH, [SoldProduct(a1, 2)]))

    assert [p.code for p in db.get_best_sellers()] == ["B2", "A1"]
    assert [p.code for p in db.get_best_sellers(limit=1)] == ["B2"]


def test_sale_without_stock_leaves_nothing_behind(db):
    db.add_product(make_product(stock=1))
    product = db.get_product("A1")
    receipt = Receipt.create(PAYMENT_CASH, [SoldProduct(product, 2)])
    with pytest.raises(InsufficientStockError):
        db.add_receipt(receipt)
    assert db.get_product("A1").stock == 1
    assert db.get_receipts_in_range(receipt.date, receipt.date) == []


def test_deactivated_product_keeps_history_and_can_be_recreated(db):
    db.add_product(make_product(stock=2))
    product = db.get_product("A1")
    receipt = Receipt.create(PAYMENT_CASH, [SoldProduct(product, 1)])
    db.add_receipt(receipt)

    db.deactivate_product("A1")
    assert db.get_product("A1") is None
    assert db.get_receipts_in_range(receipt.date, receipt.date)[0].sold_products[0].product.name == "Producto A1"

    db.add_product(make_product(stock=7))
    assert db.get_product("A1").stock == 7


def test_category_with_products_cannot_be_deleted(db):
    db.add_product(make_product(category="Ocupada"))
    with pytest.raises(CategoryInUseError):
        db.delete_category("Ocupada")
    db.add_category("Libre")
    assert db.delete_category("Libre") is True
    assert db.delete_category("Libre") is False


def test_legacy_database_is_migrated_in_place(temp_settings):
    raw = psycopg2.connect(
        host=temp_settings.host,
        port=temp_settings.port,
        dbname=temp_settings.name,
        user=temp_settings.user,
        password=temp_settings.password,
    )
    with raw, raw.cursor() as cur:
        cur.execute(LEGACY_SCHEMA)
    raw.close()

    db = DBConnection(temp_settings)
    try:
        product = db.get_product("111")
        assert product.price == Decimal("1000.00")
        assert isinstance(product.price, Decimal)
        sale_day = dt.date(2026, 8, 1)
        receipts = db.get_receipts_in_range(sale_day, sale_day)
        assert receipts[0].sold_products[0].unit_price == Decimal("1000.00")
        with pytest.raises(CategoryInUseError):
            db.delete_category("Bebidas")
    finally:
        db.close()
