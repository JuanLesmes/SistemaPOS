# model/db_connection.py
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
import datetime
from model.product import Product
from model.receipt import Receipt
from model.sold_product import SoldProduct

# model/db_connection.py
import psycopg2
from psycopg2 import sql
from psycopg2.extras import DictCursor
import datetime
from model.product import Product
from model.receipt import Receipt
from model.sold_product import SoldProduct

class DBConnection:
    def __init__(self, 
                 db_name="inventario",
                 user="postgres",
                 password="xxx",
                 host="localhost",
                 port="5432"):
        
        try:
            self.conn = psycopg2.connect(
                dbname=db_name,
                user=user,
                password=password,
                host=host,
                port=port,
                client_encoding='UTF8'  # Añadir codificación explícita
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor(cursor_factory=DictCursor)
            self.create_tables()
        except psycopg2.OperationalError as e:
            print(f"Error de conexión: {e}")
            raise  # Propagar el error para manejo superior


    def create_tables(self):
        """Crea las tablas necesarias si no existen en la base de datos."""
        queries = [
            """
            CREATE TABLE IF NOT EXISTS categories (
                idCategory SERIAL PRIMARY KEY,
                category_name TEXT UNIQUE
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS products (
                code TEXT PRIMARY KEY,
                name TEXT,
                cost REAL,
                price REAL,
                stock INTEGER,
                category INTEGER REFERENCES categories(idCategory) ON DELETE CASCADE,
                description TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS receipts (
                idReceipt SERIAL PRIMARY KEY,
                total REAL,
                date DATE,
                time TIME,
                payment_method TEXT
            )
            """,
            """
            CREATE TABLE IF NOT EXISTS sold_products (
                idSale SERIAL PRIMARY KEY,
                idReceipt INTEGER REFERENCES receipts(idReceipt) ON DELETE CASCADE,
                codeP TEXT REFERENCES products(code) ON DELETE CASCADE,
                quantity INTEGER
            )
            """
        ]
        
        for query in queries:
            try:
                self.cursor.execute(query)
            except Exception as e:
                print(f"Error creando tablas: {e}")

    # CATEGORÍAS
    def get_category_id(self, cat_name):
        self.cursor.execute("SELECT idCategory FROM categories WHERE category_name = %s", (cat_name,))
        row = self.cursor.fetchone()
        return row['idcategory'] if row else None

    def delete_category(self, category_name):
        try:
            self.cursor.execute("DELETE FROM categories WHERE category_name = %s", (category_name,))
            return True
        except Exception as e:
            print("Error al eliminar categoría:", e)
            return False

    # PRODUCTOS
    def get_products(self):
        self.cursor.execute("""
            SELECT p.code, p.name, p.cost, p.price, p.stock, 
                   c.category_name, p.description
            FROM products p
            JOIN categories c ON p.category = c.idCategory
        """)
        return [Product(*row) for row in self.cursor.fetchall()]

    def get_products_by_category(self, category_name):
        self.cursor.execute("""
            SELECT p.code, p.name, p.cost, p.price, p.stock, 
                   c.category_name, p.description
            FROM products p
            JOIN categories c ON p.category = c.idCategory
            WHERE c.category_name = %s
        """, (category_name,))
        return [Product(*row) for row in self.cursor.fetchall()]

    def get_product(self, code):
        self.cursor.execute("""
            SELECT p.code, p.name, p.cost, p.price, p.stock, 
                   c.category_name, p.description
            FROM products p
            JOIN categories c ON p.category = c.idCategory
            WHERE p.code = %s
        """, (code,))
        row = self.cursor.fetchone()
        return Product(*row) if row else None

    def add_product(self, product):
        cat_id = self.get_category_id(product.category)
        if not cat_id:
            self.add_category(product.category)
            cat_id = self.get_category_id(product.category)
            
        self.cursor.execute("""
            INSERT INTO products 
            (code, name, cost, price, stock, category, description)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (product.code, product.name, product.cost, 
              product.price, product.stock, cat_id, product.description))

    def update_product(self, name, cost, price, stock, category, description, code):
        cat_id = self.get_category_id(category)
        if not cat_id:
            self.add_category(category)
            cat_id = self.get_category_id(category)
            
        self.cursor.execute("""
            UPDATE products 
            SET name = %s, cost = %s, price = %s, 
                stock = %s, category = %s, description = %s
            WHERE code = %s
        """, (name, cost, price, stock, cat_id, description, code))

    def update_stock(self, code, quantity):
        self.cursor.execute("""
            UPDATE products 
            SET stock = stock + %s 
            WHERE code = %s
        """, (quantity, code))

    def delete_product(self, code):
        self.cursor.execute("DELETE FROM products WHERE code = %s", (code,))

    # RECIBOS
    def add_receipt(self, receipt):
        self.cursor.execute("""
            INSERT INTO receipts (total, date, time, payment_method)
            VALUES (%s, %s, %s, %s)
            RETURNING idReceipt
        """, (receipt.total_sale, receipt.date, receipt.time, receipt.payment_method))
        
        receipt_id = self.cursor.fetchone()['idreceipt']
        
        for sp in receipt.sold_products:
            self.cursor.execute("""
                INSERT INTO sold_products (idReceipt, codeP, quantity)
                VALUES (%s, %s, %s)
            """, (receipt_id, sp.product.code, sp.quantity))
            self.update_stock(sp.product.code, -sp.quantity)
        
        return receipt_id

    def get_receipts_in_range(self, start_date, end_date):
        self.cursor.execute("""
            SELECT idReceipt, total, date, time, payment_method
            FROM receipts
            WHERE date BETWEEN %s AND %s
        """, (start_date, end_date))
        
        receipts = []
        for row in self.cursor.fetchall():
            receipt = Receipt(
                id=row['idreceipt'],
                total_sale=row['total'],
                date=row['date'],
                time=row['time'],
                payment_method=row['payment_method']
            )
            receipt.sold_products = self.get_sold_products_for_receipt(row['idreceipt'])
            receipts.append(receipt)
        return receipts

    def get_sold_products_for_receipt(self, receipt_id):
        self.cursor.execute("""
            SELECT codeP, quantity 
            FROM sold_products 
            WHERE idReceipt = %s
        """, (receipt_id,))
        
        sold_products = []
        for row in self.cursor.fetchall():
            product = self.get_product(row['codep'])
            if product:
                sold_products.append(SoldProduct(receipt_id, product, row['quantity']))
        return sold_products

    # LIMPIEZA
    def clear_database(self):
        try:
            self.cursor.execute("DELETE FROM sold_products")
            self.cursor.execute("DELETE FROM receipts")
            self.cursor.execute("DELETE FROM products")
            self.cursor.execute("DELETE FROM categories")
        except Exception as e:
            print("Error al limpiar la base de datos:", e)

    def close_connection(self):
        self.cursor.close()
        self.conn.close()

    # MÉTODOS ADICIONALES (se mantienen similares)
    def get_categories(self):
        self.cursor.execute("SELECT category_name FROM categories")
        return [row['category_name'] for row in self.cursor.fetchall()]

    def add_category(self, category_name):
        self.cursor.execute(
            "INSERT INTO categories (category_name) VALUES (%s) ON CONFLICT DO NOTHING", 
            (category_name,)
        )