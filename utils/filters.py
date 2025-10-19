from aiogram.filters import BaseFilter
from aiogram.types import Message
from database.db import fetchone
from os import getenv
class IsAdmin(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        admin_ids = {int(x.strip()) for x in getenv("ADMIN_IDS","").split(",") if x.strip().isdigit()}
        if message.from_user and message.from_user.id in admin_ids:
            return True
        row = fetchone("SELECT role FROM users WHERE telegram_id=?", (message.from_user.id,))
        return bool(row and row["role"]=="admin")
class IsManager(BaseFilter):
    async def __call__(self, message: Message) -> bool:
        row = fetchone("SELECT role FROM users WHERE telegram_id=?", (message.from_user.id,))
        return bool(row and row["role"] in ("manager","admin"))
