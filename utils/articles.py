import re
from database.db import fetchall, executemany
ARTICLE_ENTRY_RE = re.compile(r"^(\d{4})\s+(замок|клей)$", re.IGNORECASE)
def seed_articles(defaults):
    existing = {(r["code"], r["kind"]) for r in fetchall("SELECT code, kind FROM articles")}
    to_add = [(c,k) for c,k in defaults if (c,k) not in existing]
    if to_add:
        executemany("INSERT OR IGNORE INTO articles(code, kind, active) VALUES (?,?,1)", to_add)
def parse_articles_input(text: str):
    parts = [p.strip() for p in text.split(",") if p.strip()]
    if not 1 <= len(parts) <= 3:
        return None, "Можно указать от 1 до 3 артикулов через запятую. Например: 8001 замок, 8002 клей"
    out = []
    for p in parts:
        m = ARTICLE_ENTRY_RE.match(p)
        if not m:
            return None, f"Неверный формат '{p}'. Используйте '#### замок' или '#### клей'."
        out.append((m.group(1), m.group(2).lower()))
    return out, None
def validate_articles_exist(parsed_list):
    missing = []
    for code, kind in parsed_list:
        row = fetchall("SELECT 1 FROM articles WHERE code=? AND kind=? AND active=1 LIMIT 1", (code, kind))
        if not row:
            missing.append(f"{code} {kind}")
    return (len(missing)==0), missing
