import shutil
import sqlite3
import os
import sys
import datetime
from model.product import Product
from model.receipt import Receipt
from model.sold_product import SoldProduct

class DBConnection:
    def __init__(self, db_name="local.db"):
        # Obtener la ruta base del programa
        if getattr(sys, 'frozen', False):  # Si está empaquetado con PyInstaller
            base_path = os.path.dirname(sys.executable)
        else:  # Si se ejecuta desde el código fuente
            base_path = os.path.abspath(".")

        # Si el parámetro db_name ya contiene directorio, lo usamos tal cual; de lo contrario, se agrega "data"
        if os.path.dirname(db_name):
            self.db_path = os.path.join(base_path, db_name)
            self.db_dir = os.path.dirname(self.db_path)
        else:
            self.db_dir = os.path.join(base_path, "data")
            self.db_path = os.path.join(self.db_dir, db_name)

        # Asegurar que la base de datos exista en el directorio correcto
        self.ensure_db_exists()

        # Conectar a la base de datos con commit automático
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.execute("PRAGMA foreign_keys = 1;")
        self.cursor = self.conn.cursor()
        self.create_tables()

    def ensure_db_exists(self):
        """Crea la base de datos si no existe en el directorio correcto."""
        # Asegurar que el directorio exista
        if not os.path.exists(self.db_dir):
            os.makedirs(self.db_dir, exist_ok=True)

        # Calcular la ruta de la base de datos original (desde el código fuente)
        base_path_source = os.path.abspath(".")
        if os.path.basename(base_path_source).lower() == "data":
            original_db_path = os.path.join(base_path_source, "local.db")
        else:
            original_db_path = os.path.join(base_path_source, "data", "local.db")

        # Si la base de datos no existe en el destino, intenta copiarla desde el código fuente
        if not os.path.exists(self.db_path):
            if os.path.exists(original_db_path):
                shutil.copy2(original_db_path, self.db_path)
                print(f"Base de datos copiada a {self.db_path}")
            else:
                print(f"No se encontró la base de datos original. Creando una nueva en: {self.db_path}")
                open(self.db_path, 'w').close()  # Crea el archivo vacío

    def create_tables(self):
        """Crea las tablas necesarias si no existen en la base de datos."""
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            idCategory INTEGER PRIMARY KEY AUTOINCREMENT,
            category_name TEXT
        );
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            code TEXT PRIMARY KEY,
            name TEXT,
            cost REAL,
            price REAL,
            stock INTEGER,
            category INTEGER,
            description TEXT,
            FOREIGN KEY(category) REFERENCES categories(idCategory) ON DELETE CASCADE
        );
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            idReceipt INTEGER PRIMARY KEY AUTOINCREMENT,
            total REAL,
            date TEXT,
            time TEXT,
            payment_method TEXT
        );
        """)
        self.cursor.execute("""
        CREATE TABLE IF NOT EXISTS sold_products (
            idSale INTEGER PRIMARY KEY AUTOINCREMENT,
            idReceipt INTEGER,
            codeP TEXT,
            quantity INTEGER,
            FOREIGN KEY(idReceipt) REFERENCES receipts(idReceipt) ON DELETE CASCADE,
            FOREIGN KEY(codeP) REFERENCES products(code) ON DELETE CASCADE
        );
        """)
        self.conn.commit()

    def get_categories(self):
        self.cursor.execute("SELECT category_name FROM categories")
        return [row[0] for row in self.cursor.fetchall()]

    def add_category(self, category_name):
        self.cursor.execute("INSERT INTO categories (category_name) VALUES (?)", (category_name,))
        self.conn.commit()

    def get_category_id(self, cat_name):
        self.cursor.execute("SELECT idCategory FROM categories WHERE category_name=?", (cat_name,))
        row = self.cursor.fetchone()
        return row[0] if row else None

    def delete_category(self, category_name):
        """Elimina la categoría y devuelve True si se eliminó correctamente."""
        try:
            self.cursor.execute("DELETE FROM categories WHERE category_name = ?", (category_name,))
            self.conn.commit()
            return True
        except Exception as e:
            print("Error al eliminar categoría:", e)
            return False

    def get_products(self):
        self.cursor.execute("""
            SELECT p.code, p.name, p.cost, p.price, p.stock, c.category_name, p.description
            FROM products p
            JOIN categories c ON p.category=c.idCategory
        """)
        return [Product(*row) for row in self.cursor.fetchall()]

    def get_products_by_category(self, category_name):
        self.cursor.execute("""
            SELECT p.code, p.name, p.cost, p.price, p.stock, c.category_name, p.description
            FROM products p
            JOIN categories c ON p.category=c.idCategory
            WHERE c.category_name=?
        """, (category_name,))
        return [Product(*row) for row in self.cursor.fetchall()]

    def get_product(self, code):
        self.cursor.execute("""
            SELECT p.code, p.name, p.cost, p.price, p.stock, c.category_name, p.description
            FROM products p
            JOIN categories c ON p.category=c.idCategory
            WHERE p.code=?
        """, (code,))
        row = self.cursor.fetchone()
        return Product(*row) if row else None

    def add_product(self, product):
        cat_id = self.get_category_id(product.category)
        if cat_id is None:
            self.add_category(product.category)
            cat_id = self.get_category_id(product.category)
        self.cursor.execute("""
            INSERT INTO products (code, name, cost, price, stock, category, description)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (product.code, product.name, product.cost, product.price, product.stock, cat_id, product.description))
        self.conn.commit()

    def update_product(self, name, cost, price, stock, category, description, code):
        """Actualiza los datos de un producto."""
        cat_id = self.get_category_id(category)
        if cat_id is None:
            self.add_category(category)
            cat_id = self.get_category_id(category)
        self.cursor.execute("""
            UPDATE products 
            SET name=?, cost=?, price=?, stock=?, category=?, description=? 
            WHERE code=?
        """, (name, cost, price, stock, cat_id, description, code))
        self.conn.commit()

    def update_stock(self, code, quantity):
        self.cursor.execute("SELECT stock FROM products WHERE code=?", (code,))
        row = self.cursor.fetchone()
        if row:
            new_stock = row[0] + quantity
            self.cursor.execute("UPDATE products SET stock=? WHERE code=?", (new_stock, code))
            self.conn.commit()

    def add_receipt(self, receipt):
        self.cursor.execute("""
            INSERT INTO receipts (total, date, time, payment_method)
            VALUES (?, ?, ?, ?)
        """, (receipt.total_sale, receipt.date.isoformat(), receipt.time.strftime("%H:%M:%S"), receipt.payment_method))
        self.conn.commit()
        receipt_id = self.cursor.lastrowid

        for sp in receipt.sold_products:
            self.cursor.execute("""
                INSERT INTO sold_products (idReceipt, codeP, quantity) VALUES (?, ?, ?)
            """, (receipt_id, sp.product.code, sp.quantity))
            self.update_stock(sp.product.code, -sp.quantity)
        self.conn.commit()
        receipt.id = receipt_id
    
    def get_receipts_in_range(self, start_date, end_date):
        start_str = start_date.isoformat()
        end_str = end_date.isoformat()
        self.cursor.execute("""
            SELECT idReceipt, total, date, time, payment_method
            FROM receipts
            WHERE date BETWEEN ? AND ?
        """, (start_str, end_str))
        rows = self.cursor.fetchall()
        receipts = []
        for r in rows:
            rec = Receipt(
                id=r[0],
                total_sale=r[1],
                date=datetime.date.fromisoformat(r[2]),
                time=datetime.datetime.strptime(r[3], "%H:%M:%S").time(),
                payment_method=r[4]
            )
            rec.sold_products = self.get_sold_products_for_receipt(rec.id)
            receipts.append(rec)
        return receipts

    def get_sold_products_for_receipt(self, receipt_id):
        self.cursor.execute("SELECT codeP, quantity FROM sold_products WHERE idReceipt=?", (receipt_id,))
        rows = self.cursor.fetchall()
        sps = []
        for r in rows:
            p = self.get_product(r[0])
            if p:
                sp = SoldProduct(receipt_id, p, r[1])
                sps.append(sp)
        return sps

    def delete_product(self, code):
        """Elimina un producto por su código."""
        self.cursor.execute("DELETE FROM products WHERE code = ?", (code,))
        self.conn.commit()

    def clear_database(self):
        """Elimina todos los datos de la base de datos preservando la estructura."""
        try:
            self.cursor.execute("DELETE FROM sold_products;")
            self.cursor.execute("DELETE FROM receipts;")
            self.cursor.execute("DELETE FROM products;")
            self.cursor.execute("DELETE FROM categories;")
            self.conn.commit()
            print("Base de datos limpiada con éxito.")
        except Exception as e:
            print("Error al limpiar la base de datos:", e)

    def close_connection(self):
        """Cierra la conexión a la base de datos para asegurar que los cambios se guarden."""
        self.conn.commit()
        self.conn.close()
