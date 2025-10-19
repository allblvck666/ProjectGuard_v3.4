CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    telegram_id INTEGER NOT NULL UNIQUE,
    username TEXT,
    full_name TEXT,
    role TEXT CHECK(role IN ('admin','manager')) NOT NULL DEFAULT 'manager',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS protections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    dealer TEXT NOT NULL,
    city TEXT NOT NULL,
    article TEXT NOT NULL,
    quantity INTEGER NOT NULL,
    client_name TEXT NOT NULL,
    phone_last4 TEXT NOT NULL,
    object_city TEXT,
    address TEXT,
    created_by INTEGER NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    expires_at DATETIME NOT NULL,
    status TEXT CHECK(status IN ('active','closed','changed','extended')) NOT NULL DEFAULT 'active',
    updated_at DATETIME,
    comment TEXT,
    base_days INTEGER DEFAULT 5,
    extend_count INTEGER DEFAULT 0,
    max_extend_manager INTEGER DEFAULT 2,
    close_reason TEXT,
    FOREIGN KEY(created_by) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS protection_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    protection_id INTEGER NOT NULL,
    changed_by INTEGER NOT NULL,
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(protection_id) REFERENCES protections(id),
    FOREIGN KEY(changed_by) REFERENCES users(id)
);
CREATE TABLE IF NOT EXISTS articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL,
    kind TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 1,
    UNIQUE(code, kind)
);
