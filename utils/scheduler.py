from apscheduler.schedulers.asyncio import AsyncIOScheduler
from database.db import fetchall, execute
async def close_expired_protections():
    rows = fetchall("""SELECT id FROM protections
        WHERE status='active' AND datetime(expires_at) < datetime('now') AND (close_reason IS NULL OR close_reason='')""")
    for r in rows:
        execute("UPDATE protections SET status='closed', updated_at=datetime('now'), close_reason='Срок истёк' WHERE id=?", (r["id"],))
def setup_scheduler():
    scheduler = AsyncIOScheduler(timezone="Europe/Moscow")
    scheduler.add_job(close_expired_protections, "interval", hours=12, id="close_expired")
    scheduler.start(); return scheduler
