import sqlite3
from datetime import datetime


class Database:
    def __init__(self, db_path="projectguard.db"):
        self.db_path = db_path
        self._create_tables()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _create_tables(self):
        conn = self._connect()
        c = conn.cursor()

        # Таблица пользователей
        c.execute('''CREATE TABLE IF NOT EXISTS users (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        telegram_id INTEGER,
                        username TEXT,
                        full_name TEXT,
                        role TEXT,
                        created_at TEXT
                    )''')

        # Таблица защит
        c.execute('''CREATE TABLE IF NOT EXISTS protections (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        dealer TEXT,
                        city TEXT,
                        article TEXT,
                        quantity INTEGER,
                        client_name TEXT,
                        phone_last4 TEXT,
                        created_by TEXT,
                        created_at TEXT,
                        expires_at TEXT,
                        status TEXT CHECK(status IN ('active','closed','changed','extended','success')),
                        updated_at TEXT,
                        comment TEXT,
                        address TEXT,
                        order_number TEXT
                    )''')

        # История изменений
        c.execute('''CREATE TABLE IF NOT EXISTS protection_history (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        protection_id INTEGER,
                        changed_by TEXT,
                        field TEXT,
                        old_value TEXT,
                        new_value TEXT,
                        timestamp TEXT
                    )''')

        conn.commit()
        conn.close()

    # ✅ Универсальный метод выборки всех строк
    def fetchall(self, query, params=()):
        """Универсальный метод выборки всех строк (для SELECT-запросов)."""
        conn = self._connect()
        c = conn.cursor()
        c.execute(query, params)
        rows = c.fetchall()
        conn.close()
        return rows

    # ======== Пользователи ========
    def add_user(self, telegram_id, username, full_name, role="manager"):
        conn = self._connect()
        c = conn.cursor()
        c.execute("INSERT INTO users (telegram_id, username, full_name, role, created_at) VALUES (?, ?, ?, ?, ?)",
                  (telegram_id, username, full_name, role, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()

    def get_user(self, telegram_id):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users WHERE telegram_id=?", (telegram_id,))
        user = c.fetchone()
        conn.close()
        return user

    def get_all_users(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM users")
        users = c.fetchall()
        conn.close()
        return users

    def update_user_role(self, telegram_id, new_role):
        conn = self._connect()
        c = conn.cursor()
        c.execute("UPDATE users SET role=?, created_at=? WHERE telegram_id=?",
                  (new_role, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), telegram_id))
        conn.commit()
        conn.close()

    def delete_user(self, telegram_id):
        conn = self._connect()
        c = conn.cursor()
        c.execute("DELETE FROM users WHERE telegram_id=?", (telegram_id,))
        conn.commit()
        conn.close()

    # ======== Защиты ========
    def add_protection(self, **data):
        """Добавление новой защиты (универсально — через именованные аргументы)."""
        conn = self._connect()
        c = conn.cursor()
        c.execute('''INSERT INTO protections 
                    (dealer, city, article, quantity, client_name, phone_last4, created_by, created_at, expires_at, status, comment, address)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                  (data.get('dealer'),
                   data.get('city'),
                   data.get('article'),
                   data.get('quantity'),
                   data.get('client_name'),
                   data.get('phone_last4'),
                   data.get('created_by') or data.get('manager'),
                   data.get('created_at'),
                   data.get('expires_at'),
                   'active',
                   data.get('comment', ''),
                   data.get('address', '')
                   ))
        conn.commit()
        conn.close()

    def get_active_protections(self):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM protections WHERE status='active'")
        rows = c.fetchall()
        conn.close()
        return rows

    def get_protection_by_id(self, pid):
        conn = self._connect()
        c = conn.cursor()
        c.execute("SELECT * FROM protections WHERE id=?", (pid,))
        row = c.fetchone()
        conn.close()
        return row

    def update_protection_status(self, pid, status):
        conn = self._connect()
        c = conn.cursor()
        c.execute("UPDATE protections SET status=?, updated_at=? WHERE id=?",
                  (status, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid))
        conn.commit()
        conn.close()

    def update_order_number(self, pid, order_number):
        conn = self._connect()
        c = conn.cursor()
        c.execute("UPDATE protections SET order_number=?, status='success', updated_at=? WHERE id=?",
                  (order_number, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pid))
        conn.commit()
        conn.close()

    def close_expired_protections(self):
        conn = self._connect()
        c = conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        c.execute("UPDATE protections SET status='closed', updated_at=? WHERE expires_at < ? AND status='active'", (now, now))
        conn.commit()
        conn.close()

    # ======== История изменений ========
    def add_history(self, protection_id, changed_by, field, old_value, new_value):
        conn = self._connect()
        c = conn.cursor()
        c.execute('''INSERT INTO protection_history (protection_id, changed_by, field, old_value, new_value, timestamp)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (protection_id, changed_by, field, old_value, new_value, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
        conn.close()
