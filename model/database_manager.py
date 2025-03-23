import sqlite3

class DatabaseManager:
    def __init__(self, db_path="data/local.db"):
        self.conn = sqlite3.connect(db_path)
        self.cur = self.conn.cursor()
        self._initialize_tables()

    def _initialize_tables(self):
        self.cur.execute("""
            CREATE TABLE IF NOT EXISTS productos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre TEXT,
                precio REAL,
                cantidad INTEGER
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
