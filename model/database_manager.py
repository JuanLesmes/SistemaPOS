import sqlite3

class DatabaseManager:
    def __init__(self, db_path="data/local.db"):
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()
        self._initialize_tables()

    def _initialize_tables(self):
        # ——— Tabla de productos ———
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                precio REAL,
                cantidad INTEGER
            );
        """)

        # ——— Tabla de auditoría ———
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS audit_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                action TEXT NOT NULL,       -- 'add_product', 'update_stock', etc.
                code TEXT,                  -- código de producto o categoría
                details TEXT,               -- JSON o descripción de cambios
                user TEXT                   -- opcional: quién hizo el cambio
            );
        """)

        self.conn.commit()

    def execute(self, query, params=None):
        params = params or []
        self.cur.execute(query, params)
        self.conn.commit()
        return self.cur

    def fetchall(self):
        return self.cur.fetchall()

    def fetchone(self):
        return self.cur.fetchone()
