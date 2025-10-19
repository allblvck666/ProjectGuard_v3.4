import sqlite3, os
from contextlib import contextmanager
from pathlib import Path
DB_PATH = os.getenv("DB_PATH", "database/projectguard.db")
def ensure_dirs():
    Path("database").mkdir(parents=True, exist_ok=True)
@contextmanager
def get_conn():
    ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()
def migrate():
    with get_conn() as conn, open("database/migrations.sql","r",encoding="utf-8") as f:
        conn.executescript(f.read())
def fetchone(q,p=()):
    with get_conn() as c:
        return c.execute(q,p).fetchone()
def fetchall(q,p=()):
    with get_conn() as c:
        return c.execute(q,p).fetchall()
def execute(q,p=()):
    with get_conn() as c:
        cur = c.execute(q,p)
        return cur.lastrowid
def executemany(q, seq):
    with get_conn() as c:
        c.executemany(q, seq)
