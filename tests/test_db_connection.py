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
from model.errors import (  # noqa: E402
    AppError,  # noqa: E402
    CategoryInUseError,
    DuplicateProductError,
    InsufficientStockError,
)
from model.pending_sale import PendingSale  # noqa: E402
from model.product import Product  # noqa: E402
from model.receipt import PAYMENT_CASH, Receipt  # noqa: E402
from model.sold_product import SoldProduct  # noqa: E402
from model.user import ROLE_ADMIN, ROLE_CASHIER  # noqa: E402
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


def test_pending_sales_survive_reload_and_drop_inactive_products(db):
    db.add_product(make_product("A1", stock=5))
    db.add_product(make_product("B2", stock=5))
    sale = PendingSale(number=3, received_text="10.000", wants_receipt=True)
    sale.lines.append(SoldProduct(db.get_product("A1"), 2))
    sale.lines.append(SoldProduct(db.get_product("B2"), 1))
    sale.db_id = db.save_pending_sale(sale)

    sale.lines[0].quantity = 4
    assert db.save_pending_sale(sale) == sale.db_id  # actualizar conserva el id

    db.deactivate_product("B2")
    loaded = db.load_pending_sales()
    assert len(loaded) == 1
    assert loaded[0].number == 3 and loaded[0].received_text == "10.000" and loaded[0].wants_receipt is True
    assert [(sp.code, sp.quantity) for sp in loaded[0].lines] == [("A1", 4)]

    db.delete_pending_sale(sale.db_id)
    assert db.load_pending_sales() == []


def test_stock_adjustments_write_kardex(db):
    db.add_product(make_product("A1", stock=5))
    db.adjust_stock("A1", 10, "llegó pedido")
    with pytest.raises(InsufficientStockError):
        db.adjust_stock("A1", -100, "conteo")
    db.adjust_stock("A1", -3, "vencidos")
    movements = db.get_stock_movements("A1")
    assert [(m.kind, m.quantity, m.stock_after) for m in movements] == [
        ("adjustment", -3, 12),
        ("adjustment", 10, 15),
        ("initial", 5, 5),
    ]
    assert movements[0].reason == "vencidos"


def test_void_and_return_restore_stock_and_affect_totals(db):
    db.add_product(make_product("A1", stock=10))
    db.add_product(make_product("B2", stock=10))
    a1, b2 = db.get_product("A1"), db.get_product("B2")
    first = Receipt.create(PAYMENT_CASH, [SoldProduct(a1, 2), SoldProduct(b2, 1)])
    first.id = db.add_receipt(first)
    second = Receipt.create(PAYMENT_CASH, [SoldProduct(a1, 3)])
    second.id = db.add_receipt(second)

    with pytest.raises(AppError):
        db.void_receipt(second.id, "")
    voided = db.void_receipt(second.id, "cliente se arrepintió")
    assert voided.is_voided and voided.void_reason == "cliente se arrepintió"
    assert db.get_product("A1").stock == 8
    with pytest.raises(AppError):
        db.void_receipt(second.id, "otra vez")

    with pytest.raises(AppError):
        db.add_return(first.id, [("A1", 5)], "demasiado")
    result = db.add_return(first.id, [("A1", 1)], "producto defectuoso")
    assert result.total == Decimal(1000)
    assert db.get_product("A1").stock == 9
    with pytest.raises(AppError):
        db.void_receipt(first.id, "ya tiene devolución")

    receipts = db.get_receipts_in_range(first.date, first.date)
    by_id = {r.id: r for r in receipts}
    assert by_id[first.id].returned_total == Decimal(1000)
    assert by_id[first.id].payments[0].amount == Decimal(3000)
    assert by_id[second.id].is_voided
    kinds = [m.kind for m in db.get_stock_movements("A1")]
    assert kinds[:2] == ["return", "void"]


def test_purchase_updates_stock_and_weighted_cost(db):
    from model.purchase import Purchase, PurchaseItem
    from model.supplier import Supplier

    db.add_product(make_product("A1", stock=10))  # costo 600
    supplier = db.save_supplier(Supplier(id=None, name="Distribuidora Sol", nit="900.1"))
    with pytest.raises(AppError):
        db.save_supplier(Supplier(id=None, name="Distribuidora Sol"))
    purchase = Purchase(id=None, supplier_id=supplier.id, supplier_name=supplier.name, invoice_number="F-1")
    purchase.items.append(PurchaseItem("A1", "Producto A1", 10, Decimal(800)))
    purchase_id = db.add_purchase(purchase)
    product = db.get_product("A1")
    assert product.stock == 20
    assert product.cost == Decimal("700.00")  # promedio ponderado entre 600 y 800
    listed = db.list_purchases(dt.date.today(), dt.date.today())
    assert listed[0].id == purchase_id and listed[0].total == Decimal(8000)
    assert db.get_stock_movements("A1")[0].kind == "purchase"


def test_shift_open_close_and_expected_cash(db):
    db.add_product(make_product("A1", stock=10))
    with pytest.raises(AppError):
        db.open_shift(Decimal(-1))
    shift = db.open_shift(Decimal(50000))
    with pytest.raises(AppError):
        db.open_shift(Decimal(0))
    assert db.get_open_shift().id == shift.id
    receipt = Receipt.create(PAYMENT_CASH, [SoldProduct(db.get_product("A1"), 2)], shift_id=shift.id)
    receipt.id = db.add_receipt(receipt)
    db.add_return(receipt.id, [("A1", 1)], "cambio de opinión")
    summary = db.shift_summary(shift.id)
    assert summary.cash_sales == Decimal(2000) and summary.returns == Decimal(1000)
    assert summary.expected_cash == Decimal(51000)
    closed = db.close_shift(shift.id, Decimal(50500), "faltaron 500")
    assert closed.difference == Decimal(-500) and not closed.is_open
    assert db.get_open_shift() is None
    with pytest.raises(AppError):
        db.close_shift(shift.id, Decimal(0))


def test_users_login_roles_and_last_admin_guard(db):
    admin = db.create_user("Admin", "Administrador", ROLE_ADMIN, "clave1")
    assert admin.username == "admin"  # se guarda en minúsculas
    with pytest.raises(AppError):
        db.create_user("admin", "Otro", ROLE_CASHIER, "clave2")
    with pytest.raises(AppError):
        db.create_user("corta", "Clave corta", ROLE_CASHIER, "ab")
    caja = db.create_user("caja", "Cajera", ROLE_CASHIER, "caja1")

    assert db.authenticate("ADMIN", "clave1").id == admin.id
    assert db.current_user == "admin"
    assert db.authenticate("admin", "mala") is None
    db.update_user(caja.id, "Cajera", ROLE_CASHIER, active=False)
    assert db.authenticate("caja", "caja1") is None, "un usuario inactivo no entra"

    with pytest.raises(AppError):
        db.update_user(admin.id, "Administrador", ROLE_CASHIER, active=True)  # último admin
    db.set_password(admin.id, "nueva1")
    assert db.authenticate("admin", "nueva1") is not None

    db.add_product(make_product("A1", stock=3))
    receipt = Receipt.create(PAYMENT_CASH, [SoldProduct(db.get_product("A1"), 1)])
    receipt.cashier = "admin"
    db.add_receipt(receipt)
    assert db.get_receipts_in_range(receipt.date, receipt.date)[0].cashier == "admin"
    assert db.get_logs_by_date(receipt.date)[0].user == "admin"  # el más reciente es la venta


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


def test_backup_and_restore_round_trip(db, temp_settings, tmp_path):
    from utils import backup as backup_tools
    from utils.config import BackupSettings

    if backup_tools.find_tool("pg_dump") is None or backup_tools.find_tool("pg_restore") is None:
        pytest.skip("pg_dump y pg_restore no están disponibles en este equipo.")
    db.add_product(make_product("A1"))
    settings = BackupSettings(directory=str(tmp_path / "copias"), keep=2)

    path = backup_tools.run_backup(temp_settings, settings, tmp_path)
    assert path.exists() and path.stat().st_size > 0
    db.record_backup(path.name)

    db.adjust_stock("A1", -5, "antes de restaurar")
    assert db.get_product("A1").stock == 5
    db.close()
    backup_tools.restore_backup(temp_settings, settings, path)
    db.reconnect()
    assert db.get_product("A1").stock == 10, "la restauración debe devolver los datos de la copia"
